#!/usr/bin/env python3
"""Deterministic tests for the standard-library HTTP API quickstart."""

from __future__ import annotations

import io
import json
import sys
import threading
import time
import unittest
from datetime import datetime, timezone
from http.client import BadStatusLine, IncompleteRead
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler


# load the copyable script without requiring a package-only filename.
def load_quickstart() -> Any:
    path = Path(__file__).with_name("quickstart.py")
    spec = spec_from_file_location("workledger_http_quickstart", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load quickstart from {path}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


quickstart = load_quickstart()


# inject one immutable instant into every lease-sensitive test.
FIXED_NOW = datetime(2026, 8, 26, 12, 0, 0, tzinfo=timezone.utc)
# canonical server timestamps stay deterministic and timezone-aware.
FUTURE_LEASE = "2026-08-26T12:30:00Z"
NOTE_CREATED_AT = "2026-08-26T12:05:00Z"
# trickle fixtures exceed this short request-wide budget deterministically.
DEADLINE_TEST_TIMEOUT_SECONDS = 0.15
# resolver cleanup reserve must return before this same caller deadline.
RESOLVER_TEST_TIMEOUT_SECONDS = 0.5
# every byte arrives within a socket timeout but the whole stream exceeds it.
TRICKLE_INTERVAL_SECONDS = 0.04
# cleanup evidence must arrive well before a hung fixture could mask failure.
HANDLER_STOP_TIMEOUT_SECONDS = 1.0


# expose the fixed instant through the production clock interface.
def fixed_clock() -> datetime:
    return FIXED_NOW


# slow peers expose per-read timeout resets while stopping on disconnect.
def trickle_bytes(connection: Any, payload: bytes, stopped: threading.Event) -> None:
    try:
        for byte in payload:
            connection.sendall(bytes((byte,)))
            time.sleep(TRICKLE_INTERVAL_SECONDS)
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        stopped.set()


# real loopback servers prove redirect refusal before a second request exists.
class RunningServer:
    # bind only an ephemeral loopback port for deterministic local isolation.
    def __init__(self, handler: type[BaseHTTPRequestHandler]) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    # expose only the loopback origin selected by the operating system.
    def url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    # start serving only for the bounded lifetime of the test context.
    def __enter__(self) -> RunningServer:
        self.thread.start()
        return self

    # synchronously stop the server so no request escapes the assertion window.
    def __exit__(self, *_: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


# use inert credentials while exercising the same request construction.
def test_config(base_url: str = "https://127.0.0.1") -> Any:
    return quickstart.Config(
        base_url=base_url,
        project="quickstart-project",
        agent_id="quickstart-agent",
        agent_token="agent-test-token",
        reviewer_token="reviewer-test-token",
        run_id="repeatable-run",
    )


# reject credential and origin hazards before urllib constructs a request.
class ConfigurationSafetyTests(unittest.TestCase):
    # explicit empty proxy policy prevents environment-driven credential routing.
    def test_opener_ignores_inherited_proxy_configuration(self) -> None:
        with patch(
            "urllib.request.getproxies",
            return_value={"http": "http://proxy.invalid:8080"},
        ):
            isolated = load_quickstart()

        proxy_handlers = [
            handler
            for handler in isolated.URL_OPENER.handlers
            if isinstance(handler, ProxyHandler)
        ]
        self.assertEqual(proxy_handlers, [])

    # malformed or non-TLS remote origins cannot reach the opener.
    def test_remote_plaintext_and_non_origin_base_urls_fail_before_request(self) -> None:
        invalid_urls = (
            "http://workledger.example",
            "https://agent:secret@workledger.example",
            "https://workledger.example/api",
            "https://workledger.example?tenant=x",
            "https://workledger.example#tenant",
            "file://workledger.example",
            "https:///missing-host",
        )

        for base_url in invalid_urls:
            with self.subTest(base_url=base_url):
                with patch.object(quickstart.URL_OPENER, "open") as opener:
                    with self.assertRaises(RuntimeError):
                        quickstart.request_json(
                            test_config(base_url),
                            "GET",
                            "/api/v1/discover",
                            "agent-test-token",
                        )
                opener.assert_not_called()

    # an explicit zero port is never an absent default-port authority.
    def test_explicit_zero_port_fails_before_resolution_or_dispatch(self) -> None:
        for base_url in ("http://127.0.0.1:0", "https://workledger.example:0"):
            with self.subTest(base_url=base_url):
                config = test_config(base_url)
                with (
                    patch.object(
                        quickstart,
                        "resolve_addresses",
                        side_effect=AssertionError("resolver called for explicit port 0"),
                    ) as resolver,
                    patch.object(quickstart.URL_OPENER, "open") as opener,
                ):
                    with self.assertRaisesRegex(RuntimeError, "port 0") as raised:
                        quickstart.request_json(
                            config,
                            "GET",
                            "/api/v1/discover",
                            config.agent_token,
                        )

                resolver.assert_not_called()
                opener.assert_not_called()
                diagnostic = str(raised.exception)
                self.assertNotIn(config.agent_token, diagnostic)
                self.assertNotIn(config.reviewer_token, diagnostic)

    # retain explicit local-development HTTP without weakening remote TLS.
    def test_plaintext_loopback_and_https_origins_are_allowed(self) -> None:
        origins = {
            "http://localhost:8080": "http://localhost:8080",
            "http://127.0.0.1:8080": "http://127.0.0.1:8080",
            "http://[::1]:8080": "http://[::1]:8080",
            "https://workledger.example/": "https://workledger.example",
        }

        for base_url, expected in origins.items():
            with self.subTest(base_url=base_url):
                self.assertEqual(quickstart.validate_base_url(base_url), expected)

    # invalid header bytes fail locally and never enter diagnostics.
    def test_invalid_bearer_token_fails_before_request_without_echo(self) -> None:
        unsafe_token = "agent-token\r\ncredential-tail"
        config = quickstart.Config(
            base_url="https://workledger.invalid",
            project="quickstart-project",
            agent_id="quickstart-agent",
            agent_token=unsafe_token,
            reviewer_token="reviewer-test-token",
            run_id="repeatable-run",
        )

        with patch.object(quickstart.URL_OPENER, "open") as opener:
            with self.assertRaises(RuntimeError) as raised:
                quickstart.request_json(
                    config,
                    "GET",
                    "/api/v1/discover",
                    config.agent_token,
                )

        opener.assert_not_called()
        diagnostic = str(raised.exception)
        self.assertNotIn("agent-token", diagnostic)
        self.assertNotIn("credential-tail", diagnostic)


# loopback peers prove headers and both body classes share one deadline.
class RequestDeadlineTests(unittest.TestCase):
    # malformed resolver rows fail closed before urllib can dispatch.
    def test_resolver_rejects_unadmitted_rows_before_dispatch(self) -> None:
        invalid_rows = (
            [
                quickstart.socket.AF_INET,
                quickstart.socket.SOCK_STREAM,
                31337,
                ["127.0.0.1", 443],
            ],
            [
                quickstart.socket.AF_INET,
                quickstart.socket.SOCK_STREAM,
                quickstart.socket.IPPROTO_TCP,
                ["::1", 443],
            ],
            [
                quickstart.socket.AF_INET6,
                quickstart.socket.SOCK_STREAM,
                quickstart.socket.IPPROTO_TCP,
                ["::1", 443, -1, 0],
            ],
            [
                quickstart.socket.AF_INET6,
                quickstart.socket.SOCK_STREAM,
                quickstart.socket.IPPROTO_TCP,
                ["::1", 443, 0, quickstart.MAX_IPV6_SCOPE_ID + 1],
            ],
        )
        for row in invalid_rows:
            with self.subTest(row=row):
                with self.assertRaises(OSError):
                    quickstart.parse_resolved_addresses(json.dumps([row]).encode(), 443)

        invalid_resolver = (
            "import json; "
            "print(json.dumps([[2, 1, 31337, ['127.0.0.1', 443]]]))"
        )
        with (
            patch.object(quickstart, "RESOLVER_CODE", invalid_resolver),
            patch.object(quickstart.URL_OPENER, "open") as opener,
        ):
            with self.assertRaises(quickstart.TransportFailure):
                quickstart.request_json(
                    test_config("https://resolver.invalid"),
                    "GET",
                    "/invalid-resolution",
                    "agent-test-token",
                )
        opener.assert_not_called()

    # resolver children inherit no credentials on either supported OS family.
    def test_resolver_environment_is_a_platform_minimum_allowlist(self) -> None:
        with (
            patch.object(quickstart.os, "name", "posix"),
            patch.dict(
                quickstart.os.environ,
                {"WORKLEDGER_API_KEY": "must-not-propagate"},
                clear=True,
            ),
        ):
            self.assertEqual(quickstart.resolver_environment(), {})

        with (
            patch.object(quickstart.os, "name", "nt"),
            patch.dict(
                quickstart.os.environ,
                {
                    "SystemRoot": r"C:\Windows",
                    "WORKLEDGER_API_KEY": "must-not-propagate",
                },
                clear=True,
            ),
        ):
            self.assertEqual(
                quickstart.resolver_environment(),
                {"SystemRoot": r"C:\Windows"},
            )

        with (
            patch.object(quickstart.os, "name", "nt"),
            patch.dict(quickstart.os.environ, {}, clear=True),
        ):
            with self.assertRaises(OSError):
                quickstart.resolver_environment()

    # resolution reserves a decreasing bounded budget for kill and reap.
    def test_resolver_timeout_reserves_bounded_reap_budget(self) -> None:
        process = MagicMock()
        process.communicate.side_effect = [
            quickstart.subprocess.TimeoutExpired("resolver", 0.75),
            (b"", b""),
        ]
        with (
            patch.object(quickstart.subprocess, "Popen", return_value=process),
            patch.object(quickstart.time, "monotonic", side_effect=[0.0, 0.8]),
        ):
            with self.assertRaises(TimeoutError):
                quickstart.resolve_addresses("resolver.invalid", 443, 1.0)

        timeouts = [call.kwargs["timeout"] for call in process.communicate.call_args_list]
        self.assertAlmostEqual(timeouts[0], 0.75)
        self.assertAlmostEqual(timeouts[1], 0.2)
        process.kill.assert_called_once_with()

    # late timeout delivery cannot strand the already-killed resolver child.
    def test_late_resolver_timeout_assigns_daemon_reaper(self) -> None:
        reaped = threading.Event()
        process = MagicMock()

        def communicate(*_: Any, **kwargs: Any) -> tuple[bytes, bytes]:
            if "timeout" in kwargs:
                raise quickstart.subprocess.TimeoutExpired("resolver", kwargs["timeout"])
            reaped.set()
            return b"", b""

        process.communicate.side_effect = communicate
        with (
            patch.object(quickstart.subprocess, "Popen", return_value=process),
            patch.object(quickstart.time, "monotonic", side_effect=[0.0, 1.1]),
            patch.object(quickstart.URL_OPENER, "open") as opener,
        ):
            with self.assertRaises(TimeoutError):
                quickstart.resolve_addresses("resolver.invalid", 443, 1.0)

        self.assertTrue(reaped.wait(HANDLER_STOP_TIMEOUT_SECONDS))
        process.kill.assert_called_once_with()
        self.assertEqual(process.communicate.call_count, 2)
        self.assertAlmostEqual(process.communicate.call_args_list[0].kwargs["timeout"], 0.75)
        self.assertEqual(process.communicate.call_args_list[1].args, ())
        self.assertEqual(process.communicate.call_args_list[1].kwargs, {})
        opener.assert_not_called()

    # a resolver child must be killed and reaped before urllib dispatches.
    def test_slow_resolution_is_killed_before_dispatch(self) -> None:
        slow_resolver = "import time; time.sleep(5)"
        started = time.monotonic()
        with (
            patch.object(quickstart, "RESOLVER_CODE", slow_resolver),
            patch.object(
                quickstart,
                "REQUEST_TIMEOUT_SECONDS",
                RESOLVER_TEST_TIMEOUT_SECONDS,
            ),
            patch.object(quickstart.URL_OPENER, "open") as opener,
        ):
            with self.assertRaises(quickstart.TransportFailure):
                quickstart.request_json(
                    test_config("https://deadline.invalid"),
                    "GET",
                    "/slow-resolution",
                    "agent-test-token",
                )
        self.assertLess(time.monotonic() - started, RESOLVER_TEST_TIMEOUT_SECONDS)
        opener.assert_not_called()

    # sequential address attempts consume one monotonic remainder.
    def test_resolved_addresses_share_one_decreasing_budget(self) -> None:
        first = MagicMock()
        first.connect.side_effect = OSError("first address refused")
        second = MagicMock()
        addresses = [
            (
                quickstart.socket.AF_INET,
                quickstart.socket.SOCK_STREAM,
                quickstart.socket.IPPROTO_TCP,
                ("192.0.2.1", 80),
            ),
            (
                quickstart.socket.AF_INET,
                quickstart.socket.SOCK_STREAM,
                quickstart.socket.IPPROTO_TCP,
                ("192.0.2.2", 80),
            ),
        ]
        connection = quickstart.DeadlineHTTPConnection(
            "example.invalid",
            timeout=1.0,
            deadline=1.0,
            addresses=addresses,
        )
        with (
            patch.object(quickstart.socket, "socket", side_effect=[first, second]),
            patch.object(quickstart.time, "monotonic", side_effect=[0.1, 0.4]),
        ):
            connected = connection.create_resolved_connection(
                ("example.invalid", 80),
                1.0,
                None,
            )

        self.assertIs(connected, second)
        self.assertAlmostEqual(first.settimeout.call_args.args[0], 0.9)
        self.assertAlmostEqual(second.settimeout.call_args.args[0], 0.6)
        first.close.assert_called_once_with()

    # TLS starts with the budget left after resolution and TCP connection.
    def test_tls_handshake_receives_only_connection_remainder(self) -> None:
        raw_socket = MagicMock()
        tls_socket = MagicMock()
        tls_context = MagicMock()
        tls_context.wrap_socket.return_value = tls_socket
        addresses = [
            (
                quickstart.socket.AF_INET,
                quickstart.socket.SOCK_STREAM,
                quickstart.socket.IPPROTO_TCP,
                ("192.0.2.1", 443),
            )
        ]
        connection = quickstart.DeadlineHTTPSConnection(
            "example.invalid",
            timeout=1.0,
            context=tls_context,
            deadline=1.0,
            addresses=addresses,
        )
        with (
            patch.object(quickstart.socket, "socket", return_value=raw_socket),
            patch.object(
                quickstart.time,
                "monotonic",
                side_effect=[0.0, 0.2, 0.4, 0.7],
            ),
        ):
            connection.connect()

        raw_timeouts = [call.args[0] for call in raw_socket.settimeout.call_args_list]
        self.assertEqual(raw_timeouts, [0.8, 0.6])
        tls_context.wrap_socket.assert_called_once_with(
            raw_socket,
            server_hostname="example.invalid",
        )
        self.assertAlmostEqual(tls_socket.settimeout.call_args.args[0], 0.3)

    def test_slow_headers_stop_at_absolute_deadline(self) -> None:
        stopped = threading.Event()

        class SlowHeaderHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}"
                trickle_bytes(self.connection, response, stopped)

            def log_message(self, *_: object) -> None:
                return

        with RunningServer(SlowHeaderHandler) as server:
            with patch.object(
                quickstart,
                "REQUEST_TIMEOUT_SECONDS",
                DEADLINE_TEST_TIMEOUT_SECONDS,
            ):
                with self.assertRaises(quickstart.TransportFailure):
                    quickstart.request_json(
                        test_config(server.url),
                        "GET",
                        "/slow-headers",
                        "agent-test-token",
                    )
            self.assertTrue(stopped.wait(HANDLER_STOP_TIMEOUT_SECONDS))

    def test_slow_success_body_stops_at_absolute_deadline(self) -> None:
        stopped = threading.Event()

        class SlowSuccessHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                payload = b'{"result":"eventually"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                trickle_bytes(self.connection, payload, stopped)

            def log_message(self, *_: object) -> None:
                return

        with RunningServer(SlowSuccessHandler) as server:
            with patch.object(
                quickstart,
                "REQUEST_TIMEOUT_SECONDS",
                DEADLINE_TEST_TIMEOUT_SECONDS,
            ):
                with self.assertRaises(quickstart.TransportFailure):
                    quickstart.request_json(
                        test_config(server.url),
                        "GET",
                        "/slow-success",
                        "agent-test-token",
                    )
            self.assertTrue(stopped.wait(HANDLER_STOP_TIMEOUT_SECONDS))

    def test_slow_error_body_stops_at_absolute_deadline(self) -> None:
        stopped = threading.Event()

        class SlowErrorHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                payload = b'{"error":"eventually"}'
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                trickle_bytes(self.connection, payload, stopped)

            def log_message(self, *_: object) -> None:
                return

        with RunningServer(SlowErrorHandler) as server:
            with patch.object(
                quickstart,
                "REQUEST_TIMEOUT_SECONDS",
                DEADLINE_TEST_TIMEOUT_SECONDS,
            ):
                with self.assertRaisesRegex(quickstart.APIError, "response_read_failed"):
                    quickstart.request_json(
                        test_config(server.url),
                        "GET",
                        "/slow-error",
                        "agent-test-token",
                    )
            self.assertTrue(stopped.wait(HANDLER_STOP_TIMEOUT_SECONDS))

    def test_oversized_success_is_bounded_mutation_ambiguity(self) -> None:
        class OversizedSuccessHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                payload = b'{"result":"oversized"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_: object) -> None:
                return

        with RunningServer(OversizedSuccessHandler) as server:
            with patch.object(quickstart, "MAX_SUCCESS_BODY_BYTES", 8):
                with self.assertRaisesRegex(
                    quickstart.TransportFailure,
                    "oversized successful response",
                ):
                    quickstart.request_json(
                        test_config(server.url),
                        "POST",
                        "/oversized-success",
                        "agent-test-token",
                    )

    def test_oversized_error_is_bounded_without_body_disclosure(self) -> None:
        secret = "oversized-error-secret"

        class OversizedErrorHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                payload = json.dumps({"error": secret}).encode()
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_: object) -> None:
                return

        with RunningServer(OversizedErrorHandler) as server:
            with patch.object(quickstart, "MAX_ERROR_BODY_BYTES", 8):
                with self.assertRaisesRegex(
                    quickstart.APIError,
                    "response_read_failed",
                ) as raised:
                    quickstart.request_json(
                        test_config(server.url),
                        "GET",
                        "/oversized-error",
                        "agent-test-token",
                    )
        self.assertNotIn(secret, str(raised.exception))


# emulate the exact durable lifecycle needed to prove replay behavior.
class LifecycleAPI:
    # retain mutation counts so a terminal replay cannot hide side effects.
    def __init__(self) -> None:
        self.wo: dict[str, Any] | None = None
        self.note: dict[str, Any] | None = None
        self.preflight_calls = 0
        self.create_calls = 0
        self.claim_calls = 0
        self.patch_calls = 0
        self.note_calls = 0
        self.get_calls = 0
        self.history: list[dict[str, Any]] = []

    # return copies so client-side mutation cannot alter fake server authority.
    def current_wo(self) -> dict[str, Any]:
        if self.wo is None:
            raise AssertionError("lifecycle WO has not been created")
        current = dict(self.wo)
        if isinstance(current.get("sections"), dict):
            current["sections"] = dict(current["sections"])
        return current

    # reject role, status, and CAS drift instead of normalizing bad requests.
    @staticmethod
    def require_request(
        token: str,
        expected_token: str,
        expected_statuses: tuple[int, ...],
        wanted_statuses: tuple[int, ...],
        context: str,
    ) -> None:
        if token != expected_token:
            raise AssertionError(f"{context} used the wrong credential")
        if expected_statuses != wanted_statuses:
            raise AssertionError(f"{context} used the wrong expected statuses")

    # every fake mutation consumes the exact current revision/hash pair.
    def require_authority(self, body: dict[str, Any], context: str) -> None:
        current = self.current_wo()
        if body.get("expected_rev") != current["rev"]:
            raise AssertionError(f"{context} omitted or changed expected_rev")
        if body.get("expected_content_hash") != current["content_hash"]:
            raise AssertionError(f"{context} omitted or changed expected_content_hash")

    # accept only the routes and state changes required by the lifecycle contract.
    def __call__(
        self,
        config: Any,
        method: str,
        path: str,
        token: str,
        *,
        body: dict[str, Any] | None = None,
        expected_statuses: tuple[int, ...] = (200,),
    ) -> Any:
        if config.agent_token == config.reviewer_token:
            raise AssertionError("agent and reviewer identities must remain distinct")
        base = quickstart.wo_path(config, 1)
        if method == "GET" and path == "/api/v1/discover":
            self.require_request(
                token,
                config.agent_token,
                expected_statuses,
                (200,),
                "discover preflight",
            )
            self.preflight_calls += 1
            return {
                "version": "test",
                "endpoints": [quickstart.IDEMPOTENT_NOTE_ENDPOINT],
            }
        if method == "POST" and path == "/api/v1/wo":
            self.require_request(
                token,
                config.agent_token,
                expected_statuses,
                (200, 201),
                "create WO",
            )
            if body is None:
                raise AssertionError("create body is required")
            expected_title = f"HTTP API quickstart {config.run_id}"
            if body.get("project") != config.project or body.get("title") != expected_title:
                raise AssertionError("create body has the wrong durable identity")
            self.create_calls += 1
            if self.wo is None:
                self.wo = {
                    "id": 1,
                    "project": config.project,
                    "title": expected_title,
                    "status": "open",
                    "rev": 1,
                    "content_hash": "sha256:open",
                    "claimed_by": "",
                    "lease_expires_at": None,
                    "sections": dict(body["sections"]),
                }
                return {"wo": self.current_wo(), "created": True}
            return {
                "wo": self.current_wo(),
                "created": False,
                "deduplicated": True,
            }
        if method == "POST" and path == base + "/claim":
            self.require_request(
                token,
                config.agent_token,
                expected_statuses,
                (200,),
                "claim WO",
            )
            if body is None:
                raise AssertionError("claim body is required")
            self.require_authority(body, "claim WO")
            if body.get("claimed_by") != config.agent_id:
                raise AssertionError("claim body has the wrong actor")
            self.claim_calls += 1
            self.wo = self.current_wo()
            self.wo["claimed_by"] = config.agent_id
            self.wo["lease_expires_at"] = FUTURE_LEASE
            self.wo["rev"] = int(self.wo["rev"]) + 1
            self.wo["content_hash"] = "sha256:claimed"
            return self.current_wo()
        if method == "PATCH" and path == base:
            if body is None:
                raise AssertionError("PATCH body is required")
            self.require_authority(body, "PATCH WO")
            if body.get("claim_actor") != config.agent_id:
                raise AssertionError("PATCH body has the wrong claim_actor")
            if body.get("status") == "in_progress":
                self.require_request(
                    token,
                    config.agent_token,
                    expected_statuses,
                    (200,),
                    "execution PATCH",
                )
                if "closure_no_code" in body:
                    raise AssertionError("execution PATCH included closure_no_code")
            elif body.get("status") == "done":
                self.require_request(
                    token,
                    config.reviewer_token,
                    expected_statuses,
                    (200,),
                    "closure PATCH",
                )
                if body.get("closure_no_code") is not True:
                    raise AssertionError("closure PATCH omitted closure_no_code")
            else:
                raise AssertionError("PATCH requested an unexpected status")
            self.patch_calls += 1
            previous = str(self.current_wo()["status"])
            self.wo = self.current_wo()
            self.wo["status"] = body["status"]
            self.wo["rev"] = int(self.wo["rev"]) + 1
            self.wo["content_hash"] = f"sha256:{self.wo['status']}:{self.wo['rev']}"
            if self.wo["status"] == "done":
                self.wo["claimed_by"] = ""
                self.wo["lease_expires_at"] = None
                self.wo["sections"]["terminal_reason"] = quickstart.NO_CODE_TERMINAL_REASON
                self.wo["sections"]["terminal_reason_kind"] = "done"
            self.history.append({"field": "status", "old": previous, "new": body["status"]})
            return self.current_wo()
        if method == "POST" and path == base + "/note/idempotent":
            self.require_request(
                token,
                config.agent_token,
                expected_statuses,
                (201,),
                "add note",
            )
            if body is None:
                raise AssertionError("note body is required")
            expected_note = {
                "content": quickstart.EVIDENCE_NOTE_CONTENT,
                "idempotency_key": quickstart.derive_note_key(config.project, config.run_id),
                "claim_actor": config.agent_id,
            }
            if body != expected_note:
                raise AssertionError("note body has the wrong content or authority")
            self.note_calls += 1
            self.note = {
                "id": 7,
                "project": config.project,
                "wo_id": 1,
                "rev": 1,
                "content": body["content"],
                "idempotency_key": body["idempotency_key"],
                "created_at": NOTE_CREATED_AT,
            }
            return dict(self.note)
        if method == "GET" and path == base:
            if token not in {config.agent_token, config.reviewer_token}:
                raise AssertionError("get WO used an unknown credential")
            self.get_calls += 1
            return self.current_wo()
        if method == "GET" and path.startswith(base + "/notes?"):
            self.require_request(
                token,
                config.reviewer_token,
                expected_statuses,
                (200,),
                "list notes",
            )
            self.get_calls += 1
            return [] if self.note is None else [dict(self.note)]
        if method == "GET" and path == base + "/history":
            self.require_request(
                token,
                config.reviewer_token,
                expected_statuses,
                (200,),
                "get history",
            )
            self.get_calls += 1
            return list(self.history)
        if method == "GET" and path.startswith(base + "/note/idempotency?"):
            self.require_request(
                token,
                config.reviewer_token,
                expected_statuses,
                (200,),
                "get note binding",
            )
            self.get_calls += 1
            if self.note is None:
                raise AssertionError("note binding requested before note creation")
            return {"note": dict(self.note), "authority_hash": "sha256:authority"}
        raise AssertionError(f"unexpected request {method} {path} body={body!r}")


# the redirect target must remain completely untouched, not merely unauthenticated.
class RedirectSafetyTests(unittest.TestCase):
    # every refused status releases its source response before control returns.
    def test_redirect_refusal_closes_source_response_for_reads_and_writes(self) -> None:
        secret = "redirect-close-secret"
        handler = quickstart.RefuseRedirectHandler()
        for method in ("GET", "POST"):
            for status in (301, 302, 303, 307, 308):
                with self.subTest(method=method, status=status):
                    request = quickstart.Request(
                        "https://127.0.0.1/redirect",
                        method=method,
                    )
                    request.add_unredirected_header("Authorization", f"Bearer {secret}")
                    response = MagicMock()
                    with self.assertRaises(quickstart.RedirectRefused) as raised:
                        getattr(handler, f"http_error_{status}")(
                            request,
                            response,
                            status,
                            "redirect",
                            {},
                        )
                    response.close.assert_called_once_with()
                    self.assertNotIn(secret, str(raised.exception))

    # malformed Location is refused before urllib parses or follows it.
    def test_malformed_location_enters_keyed_replay(self) -> None:
        request_bodies: list[bytes] = []

        class OriginHandler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                content_length = int(self.headers.get("Content-Length", "0"))
                request_bodies.append(self.rfile.read(content_length))
                if len(request_bodies) == 1:
                    self.send_response(302)
                    self.send_header("Location", "http://[invalid")
                    self.end_headers()
                    return

                response = b'{"accepted": true}'
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, *_: object) -> None:
                return

        with RunningServer(OriginHandler) as origin:
            config = test_config(origin.url)
            result = quickstart.keyed_write(
                config,
                "POST",
                "/api/v1/wo",
                config.agent_token,
                {"project": config.project},
                (201,),
                lambda value: quickstart.require_object(value, "create acknowledgement"),
            )

        self.assertEqual(result, {"accepted": True})
        self.assertEqual(len(request_bodies), 2)
        self.assertEqual(request_bodies[0], request_bodies[1])

    # prove cross-origin redirect refusal with independent origin and target servers.
    def test_cross_origin_redirect_sends_no_request_or_authorization(self) -> None:
        target_requests: list[tuple[str, str | None]] = []

        class TargetHandler(BaseHTTPRequestHandler):
            # any invocation records the credential-forwarding safety violation.
            def do_GET(self) -> None:
                target_requests.append((self.path, self.headers.get("Authorization")))
                self.send_response(200)
                self.end_headers()

            # keep deterministic test output free of request logging.
            def log_message(self, *_: object) -> None:
                return

        with RunningServer(TargetHandler) as target:

            class OriginHandler(BaseHTTPRequestHandler):
                # redirect toward a separately bound origin under test control.
                def do_GET(self) -> None:
                    self.send_response(302)
                    self.send_header("Location", target.url + "/credential-sink")
                    self.end_headers()

                # keep deterministic test output free of request logging.
                def log_message(self, *_: object) -> None:
                    return

            with RunningServer(OriginHandler) as origin:
                secret = "redirect-secret-token"
                with self.assertRaises(quickstart.RedirectRefused) as raised:
                    quickstart.request_json(
                        test_config(origin.url),
                        "GET",
                        "/redirect",
                        secret,
                    )

        self.assertEqual(target_requests, [])
        self.assertNotIn(secret, str(raised.exception))

    # a refused mutation redirect receives one exact keyed replay at the origin.
    def test_mutation_redirect_enters_keyed_replay_without_touching_target(self) -> None:
        target_requests: list[str] = []
        origin_bodies: list[bytes] = []

        class TargetHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                target_requests.append(self.path)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *_: object) -> None:
                return

        with RunningServer(TargetHandler) as target:

            class OriginHandler(BaseHTTPRequestHandler):
                def do_POST(self) -> None:
                    length = int(self.headers.get("Content-Length", "0"))
                    origin_bodies.append(self.rfile.read(length))
                    if len(origin_bodies) == 1:
                        self.send_response(302)
                        self.send_header("Location", target.url + "/credential-sink")
                        self.end_headers()
                        return
                    response = {
                        "wo": {
                            "id": 42,
                            "project": "quickstart-project",
                            "title": "retry-safe create",
                            "status": "open",
                            "rev": 1,
                            "content_hash": "sha256:create",
                        },
                        "created": True,
                    }
                    payload = json.dumps(response).encode()
                    self.send_response(201)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

                def log_message(self, *_: object) -> None:
                    return

            with RunningServer(OriginHandler) as origin:
                config = test_config(origin.url)
                body = {
                    "project": config.project,
                    "title": "retry-safe create",
                    "idempotency_key": "create-key",
                }
                result = quickstart.keyed_write(
                    config,
                    "POST",
                    "/api/v1/wo",
                    config.agent_token,
                    body,
                    (200, 201),
                    lambda value: quickstart.require_create_ack(
                        value, config.project, "retry-safe create"
                    ),
                )

        self.assertTrue(result["created"])
        self.assertEqual(len(origin_bodies), 2)
        self.assertEqual(origin_bodies[0], origin_bodies[1])
        self.assertEqual(target_requests, [])

    # a refused non-keyed redirect reconciles through one authoritative GET.
    def test_claim_redirect_enters_readback_without_touching_target(self) -> None:
        target_requests: list[str] = []
        origin_methods: list[str] = []
        base = {
            "id": 42,
            "project": "quickstart-project",
            "title": "claim redirect",
            "status": "open",
            "rev": 3,
            "content_hash": "sha256:base",
        }

        class TargetHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                target_requests.append(self.path)
                self.send_response(200)
                self.end_headers()

            def log_message(self, *_: object) -> None:
                return

        with RunningServer(TargetHandler) as target:

            class OriginHandler(BaseHTTPRequestHandler):
                def do_POST(self) -> None:
                    origin_methods.append("POST")
                    length = int(self.headers.get("Content-Length", "0"))
                    self.rfile.read(length)
                    self.send_response(302)
                    self.send_header("Location", target.url + "/credential-sink")
                    self.end_headers()

                def do_GET(self) -> None:
                    origin_methods.append("GET")
                    response = {
                        **base,
                        "claimed_by": "quickstart-agent",
                        "lease_expires_at": FUTURE_LEASE,
                    }
                    payload = json.dumps(response).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

                def log_message(self, *_: object) -> None:
                    return

            with RunningServer(OriginHandler) as origin:
                result = quickstart.claim_or_reconcile(
                    test_config(origin.url), base, clock=fixed_clock
                )

        self.assertEqual(result["claimed_by"], "quickstart-agent")
        self.assertEqual(origin_methods, ["POST", "GET"])
        self.assertEqual(target_requests, [])


# keyed writes replay only exact canonical acknowledgements and bodies.
class KeyedRetryTests(unittest.TestCase):
    # an invalid note acknowledgement receives exactly one identical replay.
    def test_note_invalid_ack_replays_once_with_identical_body(self) -> None:
        note = {
            "id": 9,
            "project": "quickstart-project",
            "wo_id": 42,
            "rev": 1,
            "content": quickstart.EVIDENCE_NOTE_CONTENT,
            "idempotency_key": "note-key",
            "created_at": NOTE_CREATED_AT,
        }
        with patch.object(
            quickstart,
            "request_json",
            side_effect=["not a JSON object", note],
        ) as request:
            result = quickstart.add_evidence_note(test_config(), 42, "note-key")

        self.assertEqual(result, note)
        self.assertEqual(request.call_count, 2)
        first, second = request.call_args_list
        self.assertEqual(first.args[2], "/api/v1/wo/quickstart-project/42/note/idempotent")
        self.assertEqual(second.args[2], first.args[2])
        self.assertEqual(second.kwargs["body"], first.kwargs["body"])

    # transport and server failures preserve byte-identical create bodies.
    def test_keyed_create_replays_once_with_byte_identical_body(self) -> None:
        config = test_config()
        body = {
            "project": config.project,
            "title": "retry-safe create",
            "idempotency_key": "create-key",
        }
        created = {
            "wo": {
                "id": 42,
                "project": config.project,
                "title": "retry-safe create",
                "status": "open",
                "rev": 1,
                "content_hash": "sha256:create",
            },
            "created": True,
        }
        ambiguities = {
            "transport": URLError("connection reset"),
            "server error": HTTPError(
                config.base_url + "/api/v1/wo",
                503,
                "unavailable",
                {},
                io.BytesIO(b"service unavailable"),
            ),
        }

        for name, ambiguity in ambiguities.items():
            with self.subTest(name=name):
                response = MagicMock()
                response.status = 201
                response.read.side_effect = [json.dumps(created).encode(), b""]
                response.__enter__.return_value = response
                with patch.object(
                    quickstart.URL_OPENER,
                    "open",
                    side_effect=[ambiguity, response],
                ) as opener:
                    result = quickstart.keyed_write(
                        config,
                        "POST",
                        "/api/v1/wo",
                        config.agent_token,
                        body,
                        (200, 201),
                        lambda value: quickstart.require_create_ack(
                            value, config.project, "retry-safe create"
                        ),
                    )

                self.assertEqual(result, created)
                self.assertEqual(opener.call_count, 2)
                first_request = opener.call_args_list[0].args[0]
                second_request = opener.call_args_list[1].args[0]
                self.assertEqual(first_request.data, second_request.data)

    # parser recursion limits remain one bounded keyed ambiguity.
    def test_deep_json_ack_replays_once_without_credential_diagnostic(self) -> None:
        config = test_config()
        json_depth = sys.getrecursionlimit() * 2

        def nested_payload(secret: str) -> bytes:
            leaf = json.dumps(f"Bearer {secret}").encode()
            return (b"[" * json_depth) + leaf + (b"]" * json_depth)

        first_payload = nested_payload(config.agent_token)
        second_payload = nested_payload(config.reviewer_token)
        self.assertLess(len(first_payload), quickstart.MAX_SUCCESS_BODY_BYTES)
        with self.assertRaises(RecursionError):
            json.loads(first_payload)

        def nested_response(payload: bytes) -> MagicMock:
            response = MagicMock()
            response.status = 201
            response.read.side_effect = [payload, b""]
            response.__enter__.return_value = response
            return response

        with patch.object(
            quickstart.URL_OPENER,
            "open",
            side_effect=[
                nested_response(first_payload),
                nested_response(second_payload),
            ],
        ) as opener:
            with self.assertRaises(quickstart.TransportFailure) as raised:
                quickstart.keyed_write(
                    config,
                    "POST",
                    "/api/v1/wo",
                    config.agent_token,
                    {"project": config.project, "idempotency_key": "create-key"},
                    (201,),
                    lambda value: quickstart.require_object(
                        value, "create acknowledgement"
                    ),
                )

        self.assertEqual(opener.call_count, 2)
        first_request = opener.call_args_list[0].args[0]
        second_request = opener.call_args_list[1].args[0]
        self.assertEqual(first_request.data, second_request.data)
        diagnostic = str(raised.exception)
        self.assertNotIn(config.agent_token, diagnostic)
        self.assertNotIn(config.reviewer_token, diagnostic)
        self.assertNotIn("Bearer", diagnostic)

    # truncated successful responses remain bounded mutation ambiguities.
    def test_incomplete_success_response_enters_keyed_replay(self) -> None:
        config = test_config()
        incomplete = MagicMock()
        incomplete.status = 201
        incomplete.read.side_effect = IncompleteRead(b'{"accepted":', 4)
        incomplete.__enter__.return_value = incomplete
        complete = MagicMock()
        complete.status = 201
        complete.read.side_effect = [b'{"accepted": true}', b""]
        complete.__enter__.return_value = complete

        with patch.object(
            quickstart.URL_OPENER,
            "open",
            side_effect=[incomplete, complete],
        ) as opener:
            result = quickstart.keyed_write(
                config,
                "POST",
                "/api/v1/wo",
                config.agent_token,
                {"project": config.project},
                (201,),
                lambda value: quickstart.require_object(value, "create acknowledgement"),
            )

        self.assertEqual(result, {"accepted": True})
        self.assertEqual(opener.call_count, 2)

    # malformed HTTP framing cannot escape the mutation state machine.
    def test_bad_status_line_enters_keyed_replay_without_echo(self) -> None:
        config = test_config()
        first = BadStatusLine(f"Bearer {config.reviewer_token}")
        second = BadStatusLine(f"Bearer {config.agent_token}")

        with patch.object(
            quickstart.URL_OPENER,
            "open",
            side_effect=[first, second],
        ) as opener:
            with self.assertRaises(quickstart.TransportFailure) as raised:
                quickstart.keyed_write(
                    config,
                    "POST",
                    "/api/v1/wo",
                    config.agent_token,
                    {"project": config.project},
                    (201,),
                    lambda value: quickstart.require_object(value, "create acknowledgement"),
                )

        self.assertEqual(opener.call_count, 2)
        diagnostic = str(raised.exception)
        self.assertNotIn(config.agent_token, diagnostic)
        self.assertNotIn(config.reviewer_token, diagnostic)
        self.assertNotIn("Bearer", diagnostic)

    # a truncated HTTP error body cannot bypass bounded replay.
    def test_http_error_body_read_failure_enters_keyed_replay(self) -> None:
        config = test_config()
        error_body = MagicMock()
        error_body.read.side_effect = IncompleteRead(b'{"error":', 4)
        error = HTTPError(
            config.base_url + "/api/v1/wo",
            400,
            "bad request",
            {},
            error_body,
        )
        complete = MagicMock()
        complete.status = 201
        complete.read.side_effect = [b'{"accepted": true}', b""]
        complete.__enter__.return_value = complete

        with patch.object(
            quickstart.URL_OPENER,
            "open",
            side_effect=[error, complete],
        ) as opener:
            result = quickstart.keyed_write(
                config,
                "POST",
                "/api/v1/wo",
                config.agent_token,
                {"project": config.project},
                (201,),
                lambda value: quickstart.require_object(value, "create acknowledgement"),
            )

        self.assertEqual(result, {"accepted": True})
        self.assertEqual(opener.call_count, 2)

    # malformed mutation redirects remain uncertain even without Location handling.
    def test_http_redirect_error_enters_keyed_replay(self) -> None:
        config = test_config()
        redirect = HTTPError(
            config.base_url + "/api/v1/wo",
            302,
            "redirect without usable location",
            {},
            io.BytesIO(b"redirect refused"),
        )
        complete = MagicMock()
        complete.status = 201
        complete.read.side_effect = [b'{"accepted": true}', b""]
        complete.__enter__.return_value = complete

        with patch.object(
            quickstart.URL_OPENER,
            "open",
            side_effect=[redirect, complete],
        ) as opener:
            result = quickstart.keyed_write(
                config,
                "POST",
                "/api/v1/wo",
                config.agent_token,
                {"project": config.project},
                (201,),
                lambda value: quickstart.require_object(value, "create acknowledgement"),
            )

        self.assertEqual(result, {"accepted": True})
        self.assertEqual(opener.call_count, 2)

    # create authority cannot cross project or keyed-request identity.
    def test_create_ack_rejects_wrong_project_or_title(self) -> None:
        base = {
            "id": 42,
            "project": "quickstart-project",
            "title": "expected title",
            "status": "open",
            "rev": 1,
            "content_hash": "sha256:create",
        }
        mismatches = {
            "project": {**base, "project": "other-project"},
            "title": {**base, "title": "other title"},
        }

        for name, wo in mismatches.items():
            with self.subTest(name=name):
                with self.assertRaises(quickstart.TransportFailure):
                    quickstart.require_create_ack(
                        {"wo": wo, "created": True},
                        "quickstart-project",
                        "expected title",
                    )

    # keyed note authority includes canonical shape, content, and project.
    def test_note_ack_rejects_noncanonical_or_wrong_identity(self) -> None:
        base = {
            "id": 9,
            "project": "quickstart-project",
            "wo_id": 42,
            "rev": 1,
            "content": quickstart.EVIDENCE_NOTE_CONTENT,
            "idempotency_key": "note-key",
            "created_at": NOTE_CREATED_AT,
        }
        mismatches = {
            "project": {**base, "project": "other-project"},
            "content": {**base, "content": "wrong evidence"},
            "rev": {key: value for key, value in base.items() if key != "rev"},
            "created_at": {**base, "created_at": "timezone-free"},
        }

        for name, note in mismatches.items():
            with self.subTest(name=name):
                with self.assertRaises(quickstart.TransportFailure):
                    quickstart.require_note_ack(
                        note,
                        "quickstart-project",
                        42,
                        quickstart.EVIDENCE_NOTE_CONTENT,
                        "note-key",
                    )

    # a mutation 5xx is uncertain and its server body cannot leak credentials.
    def test_mutation_5xx_is_ambiguous_without_secret_diagnostics(self) -> None:
        secret = "server-error-secret-token"
        error = HTTPError(
            "http://workledger.invalid/api/v1/wo",
            503,
            "unavailable",
            {},
            io.BytesIO(json.dumps({"error": f"Bearer {secret}"}).encode()),
        )
        with patch.object(quickstart.URL_OPENER, "open", side_effect=error):
            with self.assertRaises(quickstart.TransportFailure) as raised:
                quickstart.request_json(
                    test_config(),
                    "POST",
                    "/api/v1/wo",
                    secret,
                    body={"project": "quickstart-project"},
                    expected_statuses=(200, 201),
                )

        diagnostic = str(raised.exception)
        self.assertNotIn(secret, diagnostic)
        self.assertNotIn("Authorization", diagnostic)

    # a non-object 2xx body cannot serve as mutation authority.
    def test_invalid_success_ack_is_ambiguous(self) -> None:
        class InvalidResponse:
            status = 201

            # supply a malformed body through the bounded-read interface.
            def read(self, _: int) -> bytes:
                return b"not-json"

            # emulate urllib's bounded response context.
            def __enter__(self) -> InvalidResponse:
                return self

            # the inert response has no cleanup side effects.
            def __exit__(self, *_: object) -> None:
                return

        with patch.object(quickstart.URL_OPENER, "open", return_value=InvalidResponse()):
            with self.assertRaises(quickstart.TransportFailure):
                quickstart.request_json(
                    test_config(),
                    "POST",
                    "/api/v1/wo",
                    "agent-test-token",
                    body={"project": "quickstart-project"},
                    expected_statuses=(200, 201),
                )


# preflight every deterministic prerequisite before the first mutation.
class PreflightAndKeyTests(unittest.TestCase):
    # create retry identity uses the same bounded deterministic contract.
    def test_create_key_derivation_is_safe_bounded_and_deterministic(self) -> None:
        safe = quickstart.derive_create_key("quickstart-project", "repeatable-run")
        self.assertEqual(safe, "quickstart-project:repeatable-run:create")

        unsafe_inputs = (
            ("quickstart-project", "run with spaces"),
            ("quickstart-project", "snowman-\N{SNOWMAN}"),
            ("quickstart-project", "x" * 200),
        )
        for project, run_id in unsafe_inputs:
            with self.subTest(run_id=run_id[:20]):
                first = quickstart.derive_create_key(project, run_id)
                second = quickstart.derive_create_key(project, run_id)
                self.assertEqual(first, second)
                self.assertLessEqual(
                    len(first.encode("utf-8")),
                    quickstart.MAX_CREATE_IDEMPOTENCY_KEY_BYTES,
                )
                self.assertTrue(all(0x21 <= byte <= 0x7E for byte in first.encode()))
                quickstart.validate_create_idempotency_key(first)

    # unsafe caller text maps to one stable visible-ASCII bounded note key.
    def test_note_key_derivation_is_safe_bounded_and_deterministic(self) -> None:
        safe = quickstart.derive_note_key("quickstart-project", "repeatable-run")
        self.assertEqual(safe, "quickstart-project:repeatable-run:note")

        unsafe_inputs = (
            ("quickstart-project", "run with spaces"),
            ("quickstart-project", "snowman-\N{SNOWMAN}"),
            ("quickstart-project", "x" * 200),
        )
        for project, run_id in unsafe_inputs:
            with self.subTest(run_id=run_id[:20]):
                first = quickstart.derive_note_key(project, run_id)
                second = quickstart.derive_note_key(project, run_id)
                self.assertEqual(first, second)
                self.assertLessEqual(
                    len(first.encode("utf-8")),
                    quickstart.MAX_NOTE_IDEMPOTENCY_KEY_BYTES,
                )
                self.assertTrue(all(0x21 <= byte <= 0x7E for byte in first.encode()))
                quickstart.validate_note_idempotency_key(first)

    # an old-server discovery response stops before create or any mutation.
    def test_missing_idempotent_note_route_fails_before_create(self) -> None:
        config = test_config()
        with patch.object(
            quickstart,
            "request_json",
            return_value={"version": "old", "endpoints": []},
        ) as request:
            with self.assertRaisesRegex(RuntimeError, "does not advertise"):
                quickstart.run_lifecycle(config, clock=fixed_clock)

        request.assert_called_once_with(
            config,
            "GET",
            "/api/v1/discover",
            config.agent_token,
        )

    # local note-key validation precedes even the read-only server preflight.
    def test_invalid_derived_note_key_stops_before_network(self) -> None:
        with (
            patch.object(quickstart, "derive_note_key", return_value="unsafe key"),
            patch.object(quickstart, "request_json") as request,
        ):
            with self.assertRaisesRegex(RuntimeError, "visible ASCII"):
                quickstart.run_lifecycle(test_config(), clock=fixed_clock)

        request.assert_not_called()

    # create-key validation also precedes the read-only server preflight.
    def test_invalid_derived_create_key_stops_before_network(self) -> None:
        with (
            patch.object(quickstart, "derive_create_key", return_value="unsafe key"),
            patch.object(quickstart, "request_json") as request,
        ):
            with self.assertRaisesRegex(RuntimeError, "visible ASCII"):
                quickstart.run_lifecycle(test_config(), clock=fixed_clock)

        request.assert_not_called()


# terminal replay is an evidence read, never a second lifecycle mutation.
class LifecycleRecoveryTests(unittest.TestCase):
    # the second invocation may read but cannot mutate an already-done WO.
    def test_second_done_run_performs_no_claim_patch_or_note(self) -> None:
        api = LifecycleAPI()
        with patch.object(quickstart, "request_json", side_effect=api):
            first = quickstart.run_lifecycle(test_config(), clock=fixed_clock)
            mutation_counts = (api.claim_calls, api.patch_calls, api.note_calls)
            reads_after_first = api.get_calls
            second = quickstart.run_lifecycle(test_config(), clock=fixed_clock)

        self.assertEqual(first["status"], "done")
        self.assertEqual(second["status"], "done")
        self.assertTrue(second["deduplicated"])
        self.assertEqual(mutation_counts, (1, 2, 1))
        self.assertEqual((api.claim_calls, api.patch_calls, api.note_calls), mutation_counts)
        self.assertGreater(api.get_calls, reads_after_first)
        self.assertEqual(api.current_wo()["claimed_by"], "")
        self.assertEqual(api.preflight_calls, 2)
        self.assertEqual(api.create_calls, 2)

    # invalid claim authority triggers one GET and no second POST.
    def test_non_keyed_invalid_ack_reconciles_without_write_retry(self) -> None:
        config = test_config()
        base = {
            "id": 42,
            "project": config.project,
            "status": "open",
            "rev": 3,
            "content_hash": "sha256:base",
        }
        reconciled = {
            **base,
            "claimed_by": config.agent_id,
            "lease_expires_at": FUTURE_LEASE,
        }
        with patch.object(
            quickstart,
            "request_json",
            side_effect=[{"id": 42, "status": "open"}, reconciled],
        ) as request:
            result = quickstart.claim_or_reconcile(config, base, clock=fixed_clock)

        self.assertEqual(result, reconciled)
        self.assertEqual([call.args[1] for call in request.call_args_list], ["POST", "GET"])

    # integer parser limits route a non-keyed write to one authority readback.
    def test_pathological_json_ack_gets_one_authoritative_readback(self) -> None:
        config = test_config()
        base = {
            "id": 42,
            "project": config.project,
            "status": "open",
            "rev": 3,
            "content_hash": "sha256:base",
        }
        reconciled = {
            **base,
            "claimed_by": config.agent_id,
            "lease_expires_at": FUTURE_LEASE,
        }
        parser_integer_limit = 640
        pathological = (
            b'{"untrusted":"Bearer '
            + config.reviewer_token.encode()
            + b'","integer":'
            + (b"9" * (parser_integer_limit + 1))
            + b"}"
        )
        invalid = MagicMock()
        invalid.status = 200
        invalid.read.side_effect = [pathological, b""]
        invalid.__enter__.return_value = invalid
        authoritative = MagicMock()
        authoritative.status = 200
        authoritative.read.side_effect = [json.dumps(reconciled).encode(), b""]
        authoritative.__enter__.return_value = authoritative

        previous_limit = sys.get_int_max_str_digits()
        try:
            sys.set_int_max_str_digits(parser_integer_limit)
            with patch.object(
                quickstart.URL_OPENER,
                "open",
                side_effect=[invalid, authoritative],
            ) as opener:
                result = quickstart.claim_or_reconcile(config, base, clock=fixed_clock)
        finally:
            sys.set_int_max_str_digits(previous_limit)

        self.assertEqual(result, reconciled)
        self.assertEqual(opener.call_count, 2)
        methods = [call.args[0].get_method() for call in opener.call_args_list]
        self.assertEqual(methods, ["POST", "GET"])

    # an expired or malformed reconciled lease cannot authorize mutation.
    def test_claim_reconciliation_rejects_non_active_lease(self) -> None:
        config = test_config()
        base = {
            "id": 42,
            "project": config.project,
            "status": "open",
            "rev": 3,
            "content_hash": "sha256:base",
        }
        leases = {
            "expired": "2026-08-26T11:59:59Z",
            "malformed": "2026-08-26 12:30:00",
        }

        for name, lease in leases.items():
            with self.subTest(name=name):
                reconciled = {
                    **base,
                    "claimed_by": config.agent_id,
                    "lease_expires_at": lease,
                }
                with patch.object(
                    quickstart,
                    "request_json",
                    side_effect=[{"id": 42}, reconciled],
                ) as request:
                    with self.assertRaisesRegex(RuntimeError, "claim outcome is ambiguous"):
                        quickstart.claim_or_reconcile(config, base, clock=fixed_clock)

                self.assertEqual(
                    [call.args[1] for call in request.call_args_list],
                    ["POST", "GET"],
                )

    # invalid PATCH authority triggers one GET and no second PATCH.
    def test_patch_invalid_ack_reconciles_without_write_retry(self) -> None:
        config = test_config()
        base = {
            "id": 42,
            "project": config.project,
            "status": "in_progress",
            "rev": 4,
            "content_hash": "sha256:in-progress",
        }
        reconciled = {
            **base,
            "status": "done",
            "rev": 5,
            "content_hash": "sha256:done",
            "sections": {"terminal_reason": quickstart.NO_CODE_TERMINAL_REASON},
        }
        with patch.object(
            quickstart,
            "request_json",
            side_effect=[{"id": 42, "status": "in_progress"}, reconciled],
        ) as request:
            result = quickstart.update_status_or_reconcile(
                config,
                base,
                "done",
                config.reviewer_token,
                no_code=True,
            )

        self.assertEqual(result, reconciled)
        self.assertEqual([call.args[1] for call in request.call_args_list], ["PATCH", "GET"])

    # status alone cannot prove that this no-code closure landed.
    def test_patch_reconciliation_rejects_wrong_terminal_reason(self) -> None:
        config = test_config()
        base = {
            "id": 42,
            "project": config.project,
            "status": "in_progress",
            "rev": 4,
            "content_hash": "sha256:in-progress",
        }
        wrong_close = {
            **base,
            "status": "done",
            "rev": 5,
            "content_hash": "sha256:done",
            "sections": {"terminal_reason": "closed with different evidence"},
        }
        with patch.object(
            quickstart,
            "request_json",
            side_effect=[{"id": 42}, wrong_close],
        ) as request:
            with self.assertRaisesRegex(RuntimeError, "update to done is ambiguous"):
                quickstart.update_status_or_reconcile(
                    config,
                    base,
                    "done",
                    config.reviewer_token,
                    no_code=True,
                )

        self.assertEqual([call.args[1] for call in request.call_args_list], ["PATCH", "GET"])

    # binding proof must match the canonical note returned by the list read.
    def test_completion_binding_rejects_note_version_drift(self) -> None:
        config = test_config()
        note_key = quickstart.derive_note_key(config.project, config.run_id)
        note = {
            "id": 7,
            "project": config.project,
            "wo_id": 42,
            "rev": 1,
            "content": quickstart.EVIDENCE_NOTE_CONTENT,
            "idempotency_key": note_key,
            "created_at": NOTE_CREATED_AT,
        }
        done = {
            "id": 42,
            "project": config.project,
            "status": "done",
            "rev": 5,
            "content_hash": "sha256:done",
            "sections": {"terminal_reason": quickstart.NO_CODE_TERMINAL_REASON},
        }
        binding = {
            "note": {**note, "rev": 2},
            "authority_hash": "sha256:authority",
        }
        with patch.object(
            quickstart,
            "request_json",
            side_effect=[done, [note], [], binding],
        ):
            with self.assertRaisesRegex(RuntimeError, "disagrees.*rev"):
                quickstart.read_completion_evidence(
                    config,
                    42,
                    note_key,
                    {"wo": done, "created": False, "deduplicated": True},
                )

    # the fake rejects self-close, missing CAS, and missing closure evidence.
    def test_lifecycle_fake_enforces_mutation_contract(self) -> None:
        config = test_config()
        api = LifecycleAPI()
        api.wo = {
            "id": 1,
            "project": config.project,
            "title": f"HTTP API quickstart {config.run_id}",
            "status": "in_progress",
            "rev": 4,
            "content_hash": "sha256:in-progress",
            "claimed_by": config.agent_id,
            "lease_expires_at": FUTURE_LEASE,
            "sections": {},
        }
        base = quickstart.wo_path(config, 1)
        valid = {
            "status": "done",
            "expected_rev": 4,
            "expected_content_hash": "sha256:in-progress",
            "claim_actor": config.agent_id,
            "closure_no_code": True,
        }
        invalid_requests = {
            "self close": (config.agent_token, valid),
            "missing hash": (
                config.reviewer_token,
                {key: value for key, value in valid.items() if key != "expected_content_hash"},
            ),
            "wrong actor": (
                config.reviewer_token,
                {**valid, "claim_actor": "other-agent"},
            ),
            "missing no-code evidence": (
                config.reviewer_token,
                {key: value for key, value in valid.items() if key != "closure_no_code"},
            ),
        }

        for name, (token, body) in invalid_requests.items():
            with self.subTest(name=name):
                with self.assertRaises(AssertionError):
                    api(config, "PATCH", base, token, body=body)


# public diagnostics and process streams must never repeat bearer material.
class DiagnosticSafetyTests(unittest.TestCase):
    # redact complete overlapping credentials before shorter substrings.
    def test_overlapping_credentials_are_redacted_longest_first(self) -> None:
        config = quickstart.Config(
            base_url="https://workledger.invalid",
            project="quickstart-project",
            agent_id="quickstart-agent",
            agent_token="shared-token",
            reviewer_token="shared-token-with-tail",
            run_id="repeatable-run",
        )

        diagnostic = quickstart.redact_diagnostic(config.reviewer_token, config)

        self.assertEqual(diagnostic, "<redacted>")

    # successful response fields cannot become credential-bearing diagnostics.
    def test_successful_response_status_is_not_echoed_in_errors(self) -> None:
        config = test_config()
        unsafe_status = f"pending-{config.agent_token}-{config.reviewer_token}"
        with patch.object(
            quickstart,
            "get_wo",
            return_value={"id": 42, "project": config.project, "status": unsafe_status},
        ):
            with self.assertRaises(RuntimeError) as raised:
                quickstart.read_completion_evidence(
                    config,
                    42,
                    "note-key",
                    {"created": False, "deduplicated": True},
                )

        diagnostic = str(raised.exception)
        self.assertNotIn(config.agent_token, diagnostic)
        self.assertNotIn(config.reviewer_token, diagnostic)

    # an error under either credential must redact both configured tokens.
    def test_http_failure_redacts_the_other_configured_token(self) -> None:
        config = test_config()
        error = HTTPError(
            config.base_url + "/api/v1/wo/quickstart-project/42",
            400,
            "bad request",
            {},
            io.BytesIO(
                json.dumps(
                    {"error": f"Authorization: Bearer {config.agent_token}"}
                ).encode()
            ),
        )

        with patch.object(quickstart.URL_OPENER, "open", side_effect=error):
            with self.assertRaises(quickstart.APIError) as raised:
                quickstart.request_json(
                    config,
                    "GET",
                    "/api/v1/wo/quickstart-project/42",
                    config.reviewer_token,
                )

        diagnostic = str(raised.exception)
        self.assertNotIn(config.agent_token, diagnostic)
        self.assertNotIn(config.reviewer_token, diagnostic)
        self.assertNotIn("Authorization", diagnostic)

    # sanitize both server-controlled fields before main writes stderr.
    def test_http_failure_does_not_emit_tokens_or_headers(self) -> None:
        config = test_config()
        error = HTTPError(
            config.base_url + "/api/v1/wo",
            400,
            "bad request",
            {},
            io.BytesIO(
                json.dumps(
                    {
                        "code": config.agent_token,
                        "error": f"Authorization: Bearer {config.agent_token}",
                    }
                ).encode()
            ),
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(quickstart.Config, "from_environment", return_value=config),
            patch.object(quickstart.URL_OPENER, "open", side_effect=error),
            patch.object(sys, "argv", ["quickstart.py"]),
            patch.object(sys, "stdout", stdout),
            patch.object(sys, "stderr", stderr),
        ):
            result = quickstart.main()

        output = stdout.getvalue() + stderr.getvalue()
        self.assertEqual(result, 1)
        self.assertNotIn(config.agent_token, output)
        self.assertNotIn(config.reviewer_token, output)
        self.assertNotIn("Authorization", output)


if __name__ == "__main__":
    unittest.main()
