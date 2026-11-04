import importlib.util
from http.client import IncompleteRead
from io import BytesIO
from pathlib import Path
import socket
import ssl
import unittest
from unittest.mock import MagicMock, call, patch
from urllib.error import HTTPError, URLError

spec = importlib.util.spec_from_file_location("update", Path(__file__).resolve().parents[1] / "scripts/update.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def response(data=b"verified bytes"):
    result = MagicMock()
    result.__enter__.return_value.read.return_value = data
    return result


class FetchTests(unittest.TestCase):
    def test_dns_and_timeout_retry_same_bounded_request(self):
        ready = response()
        errors = [URLError(socket.gaierror(-2, "DNS unavailable")), TimeoutError()]
        with patch.object(updater, "urlopen", side_effect=errors + [ready]) as open_url, patch("time.sleep") as sleep:
            self.assertEqual(updater.fetch("/v1/cli-releases", 32), b"verified bytes")
        self.assertEqual(sleep.call_args_list, [call(2), call(4)])
        self.assertEqual(open_url.call_count, 3)
        for args in open_url.call_args_list:
            self.assertEqual(args.args[0].full_url, "https://api.iotkit.io/v1/cli-releases")
            self.assertEqual(args.kwargs, {"timeout": 60})
        ready.__enter__.return_value.read.assert_called_once_with(33)

    def test_temporary_http_errors_retry_and_close_response(self):
        for code in (408, 429, 500, 502, 503, 504):
            with self.subTest(code=code):
                body = BytesIO(b"temporary")
                error = HTTPError("https://api.iotkit.io/test", code, "temporary", {}, body)
                with patch.object(updater, "urlopen", side_effect=[error, response()]) as open_url, patch("time.sleep") as sleep:
                    self.assertEqual(updater.fetch("/test", 32), b"verified bytes")
                self.assertEqual(open_url.call_count, 2)
                sleep.assert_called_once_with(2)
                self.assertTrue(body.closed)

    def test_transient_errors_stop_after_three_attempts(self):
        factories = [lambda: URLError(socket.gaierror(-2, "DNS unavailable")), TimeoutError, ConnectionResetError, lambda: IncompleteRead(b"partial", 7)]
        for factory in factories:
            with self.subTest(error=factory):
                error = factory()
                with patch.object(updater, "urlopen", side_effect=error) as open_url, patch("time.sleep") as sleep:
                    with self.assertRaises(type(error)):
                        updater.fetch("/test", 32)
                self.assertEqual(open_url.call_count, 3)
                self.assertEqual(sleep.call_args_list, [call(2), call(4)])

    def test_permanent_http_and_tls_errors_fail_immediately(self):
        errors = [HTTPError("https://api.iotkit.io/test", code, "permanent", {}, None) for code in (400, 401, 403, 404)]
        errors += [URLError(ssl.SSLCertVerificationError("untrusted certificate")), URLError("unsupported URL")]
        for error in errors:
            with self.subTest(error=error):
                with patch.object(updater, "urlopen", side_effect=error) as open_url, patch("time.sleep") as sleep:
                    with self.assertRaises(type(error)):
                        updater.fetch("/test", 32)
                self.assertEqual(open_url.call_count, 1)
                sleep.assert_not_called()

    def test_oversized_response_is_not_retried(self):
        with patch.object(updater, "urlopen", return_value=response(b"too long")) as open_url, patch("time.sleep") as sleep:
            with self.assertRaisesRegex(ValueError, "admitted size"):
                updater.fetch("/test", 3)
        self.assertEqual(open_url.call_count, 1)
        sleep.assert_not_called()

    def test_read_timeout_restarts_request_and_closes_failed_response(self):
        first = response()
        first.__enter__.return_value.read.side_effect = TimeoutError()
        with patch.object(updater, "urlopen", side_effect=[first, response(b"complete")]) as open_url, patch("time.sleep") as sleep:
            self.assertEqual(updater.fetch("/test", 32), b"complete")
        self.assertEqual(open_url.call_count, 2)
        first.__exit__.assert_called_once()
        sleep.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
