#!/usr/bin/env python3
"""Run the authenticated Workledger HTTP lifecycle without third-party packages."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import io
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from http.client import HTTPConnection, HTTPException, HTTPResponse, HTTPSConnection
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import (
    HTTPHandler,
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)


# keep the copy-and-run default local unless the operator names a tenant.
DEFAULT_BASE_URL = "http://localhost:8080"
# bound the example claim instead of creating an indefinite lease.
DEFAULT_LEASE_MINUTES = 30
# every network wait in the quickstart has a finite client budget.
REQUEST_TIMEOUT_SECONDS = 10
# successful envelopes have a finite memory and wire budget.
MAX_SUCCESS_BODY_BYTES = 1_048_576
# diagnostics need less space and must not become an unbounded error sink.
MAX_ERROR_BODY_BYTES = 65_536
# small incremental reads let the absolute deadline interrupt trickle bodies.
RESPONSE_READ_CHUNK_BYTES = 16_384
# reject pathological resolver output instead of trusting an unbounded address set.
MAX_RESOLVED_ADDRESSES = 16
# one quarter of a short budget, capped at 250ms, is reserved for kill/reap.
RESOLVER_REAP_BUDGET_FRACTION = 0.25
# cap resolver cleanup so it cannot consume the request deadline.
RESOLVER_REAP_BUDGET_MAX_SECONDS = 0.25
# IPv6 flow labels are 20-bit and interface scope IDs are unsigned 32-bit.
MAX_IPV6_FLOWINFO = (1 << 20) - 1
# reject IPv6 scope IDs outside the kernel's unsigned range.
MAX_IPV6_SCOPE_ID = (1 << 32) - 1
# resolution runs without credentials and is killed and reaped at the deadline.
RESOLVER_CODE = """
import json
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
rows = []
for family, socktype, proto, _, sockaddr in socket.getaddrinfo(
    host, port, type=socket.SOCK_STREAM
):
    if family == socket.AF_INET:
        rows.append([family, socktype, proto, [sockaddr[0], sockaddr[1]]])
    elif family == socket.AF_INET6:
        rows.append(
            [family, socktype, proto, [sockaddr[0], sockaddr[1], sockaddr[2], sockaddr[3]]]
        )
print(json.dumps(rows, separators=(",", ":")))
"""
# only writes can leave an uncertain committed outcome after response failure.
MUTATION_METHODS = frozenset({"DELETE", "PATCH", "POST", "PUT"})
# negotiate the fail-closed note route before creating lifecycle state.
IDEMPOTENT_NOTE_ENDPOINT = "POST /api/v1/wo/{project}/{id}/note/idempotent"
# match the server's bounded visible-ASCII retry-identity contract.
MAX_IDEMPOTENCY_KEY_BYTES = 128
# create retry identities use the server's shared visible-ASCII byte ceiling.
MAX_CREATE_IDEMPOTENCY_KEY_BYTES = MAX_IDEMPOTENCY_KEY_BYTES
# note retry identities use the same bounded wire contract.
MAX_NOTE_IDEMPOTENCY_KEY_BYTES = MAX_IDEMPOTENCY_KEY_BYTES
# plaintext bearer transport is local-loopback only.
PLAINTEXT_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
# bind note acknowledgements and completion reads to one exact payload.
EVIDENCE_NOTE_CONTENT = "Python quickstart completed execution; reviewer may close."
# reconcile the persisted evidence produced by closure_no_code.
NO_CODE_TERMINAL_REASON = "closed as no-code work with explicit acknowledgement"
# accept the RFC3339 forms emitted by Go while rejecting timezone-free values.
RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


# keep HTTP refusals distinct from transport-ambiguous outcomes.
class APIError(RuntimeError):
    """Represent a known HTTP refusal without retaining credential-bearing headers."""

    # expose the canonical error code while keeping bearer tokens out of diagnostics.
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        self.message = message
        super().__init__(f"HTTP {status} {code or 'error'}: {message}")


# only this failure class may enter operation-specific reconciliation.
class TransportFailure(RuntimeError):
    """Mark a request whose commit outcome may be unknown to the caller."""


# refuse every redirect before urllib can forward a bearer credential.
class RedirectRefused(RuntimeError):
    """Mark a redirect that the credential-bearing example will not follow."""


# body-limit failures carry no server-controlled bytes into diagnostics.
class ResponseBodyTooLarge(RuntimeError):
    """Mark a response that exceeded its configured byte budget."""


# every socket read recomputes the one request-wide remaining budget.
def remaining_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("request deadline exceeded")
    return remaining


# numeric and localhost origins never enter a blocking system resolver.
def direct_addresses(host: str, port: int) -> list[tuple[int, int, int, tuple[Any, ...]]]:
    if host.lower() == "localhost":
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, ("127.0.0.1", port)),
            (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, ("::1", port, 0, 0)),
        ]
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return []
    if address.version == 4:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, (str(address), port))
        ]
    return [
        (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, (str(address), port, 0, 0))
    ]


# accept only numeric stream addresses emitted by the isolated resolver.
def parse_resolved_addresses(
    raw: bytes,
    expected_port: int,
) -> list[tuple[int, int, int, tuple[Any, ...]]]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise OSError("name resolution returned invalid data") from error
    if not isinstance(value, list) or not value or len(value) > MAX_RESOLVED_ADDRESSES:
        raise OSError("name resolution returned an invalid address set")

    addresses: list[tuple[int, int, int, tuple[Any, ...]]] = []
    for row in value:
        if not isinstance(row, list) or len(row) != 4:
            raise OSError("name resolution returned an invalid address")
        family, socktype, proto, sockaddr = row
        if (
            type(family) is not int
            or type(socktype) is not int
            or type(proto) is not int
            or socktype != socket.SOCK_STREAM
            or proto not in {0, socket.IPPROTO_TCP}
            or family not in {socket.AF_INET, socket.AF_INET6}
            or not isinstance(sockaddr, list)
        ):
            raise OSError("name resolution returned an invalid address")
        expected_parts = 2 if family == socket.AF_INET else 4
        if len(sockaddr) != expected_parts or type(sockaddr[0]) is not str:
            raise OSError("name resolution returned an invalid socket address")
        try:
            parsed = ipaddress.ip_address(sockaddr[0])
        except ValueError as error:
            raise OSError("name resolution returned a non-numeric address") from error
        if (family == socket.AF_INET) != (parsed.version == 4):
            raise OSError("name resolution returned a mismatched address family")
        if type(sockaddr[1]) is not int or sockaddr[1] != expected_port:
            raise OSError("name resolution returned the wrong port")
        if family == socket.AF_INET6:
            flowinfo, scope_id = sockaddr[2:]
            if (
                type(flowinfo) is not int
                or not 0 <= flowinfo <= MAX_IPV6_FLOWINFO
                or type(scope_id) is not int
                or not 0 <= scope_id <= MAX_IPV6_SCOPE_ID
            ):
                raise OSError("name resolution returned invalid IPv6 metadata")
        normalized = tuple(sockaddr)
        address = (family, socktype, proto, normalized)
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise OSError("name resolution returned no usable addresses")
    return addresses


# resolution cannot consume the cleanup time needed to kill and reap its child.
def resolver_execution_timeout(deadline: float) -> float:
    remaining = remaining_timeout(deadline)
    reap_budget = min(
        RESOLVER_REAP_BUDGET_MAX_SECONDS,
        remaining * RESOLVER_REAP_BUDGET_FRACTION,
    )
    execution_budget = remaining - reap_budget
    if execution_budget <= 0:
        raise TimeoutError("request deadline cannot admit name resolution")
    return execution_budget


# the resolver receives no credentials and only Windows process-start authority.
def resolver_environment() -> dict[str, str]:
    if os.name != "nt":
        return {}
    system_root = os.environ.get("SystemRoot") or os.environ.get("SYSTEMROOT")
    if not system_root:
        raise OSError("Windows SystemRoot is required for bounded name resolution")
    return {"SystemRoot": system_root}


# the daemon resumes communicate so Windows joins its output reader thread.
def start_killed_resolver_reaper(process: subprocess.Popen[bytes]) -> None:
    def reap() -> None:
        process.communicate()

    threading.Thread(
        target=reap,
        name="workledger-resolver-reaper",
        daemon=True,
    ).start()


# reap synchronously only inside the request budget, otherwise in the daemon.
def reap_killed_resolver(process: subprocess.Popen[bytes], deadline: float) -> None:
    try:
        reap_timeout = remaining_timeout(deadline)
    except TimeoutError:
        start_killed_resolver_reaper(process)
        return
    try:
        process.communicate(timeout=reap_timeout)
    except subprocess.TimeoutExpired:
        start_killed_resolver_reaper(process)


# an isolated credential-free resolver is killed and always assigned a reaper.
def resolve_addresses(
    host: str,
    port: int,
    deadline: float,
) -> list[tuple[int, int, int, tuple[Any, ...]]]:
    addresses = direct_addresses(host, port)
    if addresses:
        return addresses

    process = subprocess.Popen(
        [sys.executable, "-I", "-c", RESOLVER_CODE, host, str(port)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=resolver_environment(),
        close_fds=True,
    )
    try:
        output, _ = process.communicate(timeout=resolver_execution_timeout(deadline))
    except (subprocess.TimeoutExpired, TimeoutError) as error:
        process.kill()
        reap_killed_resolver(process, deadline)
        raise TimeoutError("name resolution exceeded the request deadline") from error
    if process.returncode != 0 or output is None:
        raise OSError("name resolution failed")
    remaining_timeout(deadline)
    return parse_resolved_addresses(output, port)


# raw socket reads cannot reset the timeout while a peer trickles bytes.
class DeadlineRawReader(io.RawIOBase):
    def __init__(self, raw: Any, sock: Any, deadline: float) -> None:
        super().__init__()
        self.raw = raw
        self.sock = sock
        self.deadline = deadline

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Any) -> int | None:
        self.sock.settimeout(remaining_timeout(self.deadline))
        return self.raw.readinto(buffer)

    def fileno(self) -> int:
        return self.raw.fileno()

    def close(self) -> None:
        if not self.closed:
            self.raw.close()
        super().close()


# status, headers, and bodies share a deadline-aware buffered reader.
class DeadlineHTTPResponse(HTTPResponse):
    def __init__(
        self,
        sock: Any,
        debuglevel: int = 0,
        method: str | None = None,
        url: str | None = None,
        *,
        deadline: float,
    ) -> None:
        class DeadlineSocketView:
            # HTTPResponse receives a bounded stream without owning a second socket.
            def makefile(self, mode: str, *_: Any, **__: Any) -> io.BufferedReader:
                if mode != "rb":
                    raise ValueError("deadline socket supports response reads only")
                raw = sock.makefile(mode, buffering=0)
                return io.BufferedReader(DeadlineRawReader(raw, sock, deadline))

        super().__init__(DeadlineSocketView(), debuglevel, method, url)


# every resolved address consumes, rather than resets, one connection budget.
class DeadlineConnectionMixin:
    def __init__(
        self,
        *args: Any,
        deadline: float,
        addresses: list[tuple[int, int, int, tuple[Any, ...]]],
        **kwargs: Any,
    ) -> None:
        self.deadline = deadline
        self.addresses = addresses
        super().__init__(*args, **kwargs)
        self._create_connection = self.create_resolved_connection
        self.response_class = partial(DeadlineHTTPResponse, deadline=deadline)

    def create_resolved_connection(
        self,
        address: tuple[str, int],
        _: float | object,
        source_address: tuple[str, int] | None,
    ) -> socket.socket:
        if address != (self.host, self.port):
            raise OSError("HTTP connection requested an unapproved address")
        last_error: OSError | None = None
        for family, socktype, proto, sockaddr in self.addresses:
            candidate = socket.socket(family, socktype, proto)
            try:
                candidate.settimeout(remaining_timeout(self.deadline))
                if source_address is not None:
                    candidate.bind(source_address)
                candidate.connect(sockaddr)
                return candidate
            except TimeoutError:
                candidate.close()
                raise
            except OSError as error:
                candidate.close()
                last_error = error
        if last_error is None:
            raise OSError("name resolution returned no connection candidates")
        raise last_error

    def connect(self) -> None:
        self.timeout = remaining_timeout(self.deadline)
        super().connect()
        if self.sock is not None:
            self.sock.settimeout(remaining_timeout(self.deadline))

    def send(self, data: Any) -> None:
        if self.sock is None:
            self.connect()
        if self.sock is not None:
            self.sock.settimeout(remaining_timeout(self.deadline))
        super().send(data)


# urllib uses only the admitted, deadline-shared plaintext addresses.
class DeadlineHTTPConnection(DeadlineConnectionMixin, HTTPConnection):
    pass


# TLS handshake receives only the remainder after resolution and TCP connect.
class DeadlineHTTPSConnection(DeadlineConnectionMixin, HTTPSConnection):
    def connect(self) -> None:
        self.timeout = remaining_timeout(self.deadline)
        HTTPConnection.connect(self)
        server_hostname = self._tunnel_host or self.host
        if self.sock is None:
            raise OSError("HTTPS connection did not create a socket")
        self.sock.settimeout(remaining_timeout(self.deadline))
        self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)
        self.sock.settimeout(remaining_timeout(self.deadline))


# handlers carry admitted addresses and the deadline into the connection factory.
class DeadlineHTTPHandler(HTTPHandler):
    def http_open(self, request: Request) -> Any:
        deadline = request.workledger_deadline
        connection = partial(
            DeadlineHTTPConnection,
            deadline=deadline,
            addresses=request.workledger_addresses,
        )
        return self.do_open(connection, request)


# HTTPS connects and reads use the same admitted address set and budget.
class DeadlineHTTPSHandler(HTTPSHandler):
    def https_open(self, request: Request) -> Any:
        deadline = request.workledger_deadline
        connection = partial(
            DeadlineHTTPSConnection,
            deadline=deadline,
            addresses=request.workledger_addresses,
        )
        return self.do_open(connection, request, context=self._context)


# the example has one configured API origin and never follows redirects.
class RefuseRedirectHandler(HTTPRedirectHandler):
    # close the source response before refusing its untrusted Location value.
    def http_error_302(self, req: Request, response: Any, *_: Any, **__: Any) -> None:
        try:
            response.close()
        finally:
            raise RedirectRefused(f"redirect refused for {req.get_method()} {req.selector}")

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302

    # abort before urllib constructs or sends any redirected request.
    def redirect_request(self, req: Request, *_: Any, **__: Any) -> None:
        raise RedirectRefused(f"redirect refused for {req.get_method()} {req.selector}")


# disable inherited proxies, bound I/O, and refuse credential redirects.
URL_OPENER = build_opener(
    ProxyHandler({}),
    DeadlineHTTPHandler(),
    DeadlineHTTPSHandler(),
    RefuseRedirectHandler(),
)


# accept one HTTP(S) origin and refuse credential-bearing URL ambiguity.
def validate_base_url(value: str) -> str:
    base_url = value.strip()
    if not base_url:
        raise RuntimeError("WORKLEDGER_URL must not be empty")
    try:
        parsed = urlsplit(base_url)
        hostname = parsed.hostname
        parsed_port = parsed.port
    except ValueError:
        raise RuntimeError("WORKLEDGER_URL must be a valid HTTP(S) origin") from None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not hostname:
        raise RuntimeError("WORKLEDGER_URL must be a valid HTTP(S) origin")
    if parsed_port == 0:
        raise RuntimeError("WORKLEDGER_URL must not use port 0")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError("WORKLEDGER_URL must not contain user information")
    if parsed.path not in {"", "/"}:
        raise RuntimeError("WORKLEDGER_URL must not contain a path")
    if "?" in base_url or "#" in base_url:
        raise RuntimeError("WORKLEDGER_URL must not contain a query or fragment")
    if parsed.scheme == "http" and hostname.lower() not in PLAINTEXT_LOOPBACK_HOSTS:
        raise RuntimeError("WORKLEDGER_URL must use HTTPS outside localhost")
    return base_url[:-1] if parsed.path == "/" else base_url


# reject header-unsafe credentials locally without echoing their bytes.
def validate_bearer_token(token: str, context: str) -> None:
    encoded = token.encode("utf-8")
    if not encoded:
        raise RuntimeError(f"{context} must not be blank")
    if any(byte < 0x21 or byte > 0x7E for byte in encoded):
        raise RuntimeError(f"{context} must contain visible ASCII only")


# two credentials make execution and closure identities structurally distinct.
@dataclass(frozen=True)
class Config:
    base_url: str
    project: str
    agent_id: str
    agent_token: str
    reviewer_token: str
    run_id: str

    # require durable retry identity and separate execution/review credentials.
    @classmethod
    # construct configuration only after the full credential contract validates.
    def from_environment(cls) -> Config:
        values = {
            "WORKLEDGER_PROJECT": os.environ.get("WORKLEDGER_PROJECT", "").strip(),
            "WORKLEDGER_AGENT_ID": os.environ.get("WORKLEDGER_AGENT_ID", "").strip(),
            "WORKLEDGER_AGENT_API_KEY": os.environ.get("WORKLEDGER_AGENT_API_KEY", ""),
            "WORKLEDGER_REVIEWER_API_KEY": os.environ.get(
                "WORKLEDGER_REVIEWER_API_KEY", ""
            ),
            "WORKLEDGER_RUN_ID": os.environ.get("WORKLEDGER_RUN_ID", "").strip(),
        }
        missing = sorted(name for name, value in values.items() if not value)
        if missing:
            raise RuntimeError("missing required environment variables: " + ", ".join(missing))
        if values["WORKLEDGER_AGENT_API_KEY"] == values["WORKLEDGER_REVIEWER_API_KEY"]:
            raise RuntimeError("agent and reviewer API keys must be distinct")
        validate_bearer_token(values["WORKLEDGER_AGENT_API_KEY"], "agent API key")
        validate_bearer_token(values["WORKLEDGER_REVIEWER_API_KEY"], "reviewer API key")

        base_url = validate_base_url(os.environ.get("WORKLEDGER_URL", DEFAULT_BASE_URL))
        return cls(
            base_url=base_url,
            project=values["WORKLEDGER_PROJECT"],
            agent_id=values["WORKLEDGER_AGENT_ID"],
            agent_token=values["WORKLEDGER_AGENT_API_KEY"],
            reviewer_token=values["WORKLEDGER_REVIEWER_API_KEY"],
            run_id=values["WORKLEDGER_RUN_ID"],
        )


# parser-limit failures are undecodable bodies, not escaped mutation outcomes.
def decode_response_body(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, RecursionError):
        return raw.decode("utf-8", errors="replace")


# read at most one byte beyond the named cap under the request deadline.
def read_bounded_body(response: Any, limit: int, deadline: float) -> bytes:
    chunks: list[bytes] = []
    remaining = limit + 1
    while remaining > 0:
        remaining_timeout(deadline)
        chunk = response.read(min(RESPONSE_READ_CHUNK_BYTES, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    body = b"".join(chunks)
    if len(body) > limit:
        raise ResponseBodyTooLarge("response body exceeded its byte limit")
    return body


# longest-first replacement prevents overlapping credentials from leaking suffixes.
def redact_diagnostic(value: str, config: Config) -> str:
    redacted = value
    tokens = sorted({config.agent_token, config.reviewer_token}, key=len, reverse=True)
    for token in tokens:
        if token:
            redacted = redacted.replace(token, "<redacted>")
    return re.sub(r"authorization", "<redacted-header>", redacted, flags=re.IGNORECASE)


# refuse redirects and classify uncertain mutation acknowledgements centrally.
def request_json(
    config: Config,
    method: str,
    path: str,
    token: str,
    *,
    body: dict[str, Any] | None = None,
    expected_statuses: tuple[int, ...] = (200,),
) -> Any:
    base_url = validate_base_url(config.base_url)
    validate_bearer_token(config.agent_token, "agent API key")
    validate_bearer_token(config.reviewer_token, "reviewer API key")
    validate_bearer_token(token, "request API key")
    payload = None if body is None else json.dumps(body).encode("utf-8")
    headers = {
        "Accept": "application/json",
    }
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = Request(base_url + path, data=payload, headers=headers, method=method)
    request.add_unredirected_header("Authorization", f"Bearer {token}")

    # one monotonic deadline begins before network dispatch.
    deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
    request.workledger_deadline = deadline

    try:
        origin = urlsplit(base_url)
        if origin.hostname is None:
            raise OSError("request origin has no hostname")
        port = origin.port if origin.port is not None else (443 if origin.scheme == "https" else 80)
        # resolution finishes inside the budget before urllib can dispatch.
        request.workledger_addresses = resolve_addresses(origin.hostname, port, deadline)
        with URL_OPENER.open(request, timeout=remaining_timeout(deadline)) as response:
            status = response.status
            decoded = decode_response_body(
                read_bounded_body(response, MAX_SUCCESS_BODY_BYTES, deadline)
            )
    except ResponseBodyTooLarge:
        if method in MUTATION_METHODS:
            raise TransportFailure(
                f"oversized successful response for {method} {path}"
            ) from None
        raise RuntimeError(f"oversized successful response for {method} {path}") from None
    except RedirectRefused:
        if method in MUTATION_METHODS:
            raise TransportFailure(
                f"redirect refused after dispatch for {method} {path}"
            ) from None
        raise
    except HTTPError as error:
        try:
            decoded = decode_response_body(
                read_bounded_body(error, MAX_ERROR_BODY_BYTES, deadline)
            )
        except (HTTPException, OSError, ResponseBodyTooLarge):
            error.close()
            if method in MUTATION_METHODS:
                raise TransportFailure(
                    f"ambiguous HTTP error response for {method} {path}"
                ) from None
            raise APIError(
                error.code,
                "response_read_failed",
                f"could not read HTTP error response for {method} {path}",
            ) from None
        # release the response stream before interpreting untrusted error fields.
        error.close()
        # malformed redirects can bypass redirect_request after dispatch.
        if method in MUTATION_METHODS and (
            300 <= error.code <= 399 or 500 <= error.code <= 599
        ):
            raise TransportFailure(f"ambiguous HTTP {error.code} for {method} {path}") from None
        if isinstance(decoded, dict):
            code = redact_diagnostic(str(decoded.get("code", "")), config)
            message = redact_diagnostic(str(decoded.get("error", decoded)), config)
        else:
            code = ""
            message = redact_diagnostic(str(decoded), config)
        raise APIError(error.code, code, message) from None
    except HTTPException:
        if method in MUTATION_METHODS:
            raise TransportFailure(f"ambiguous HTTP response for {method} {path}") from None
        raise RuntimeError(f"invalid HTTP response for {method} {path}") from None
    except OSError as error:
        reason = error.reason if isinstance(error, URLError) else str(error)
        diagnostic = redact_diagnostic(str(reason), config)
        raise TransportFailure(
            f"transport failed for {method} {path}: {diagnostic}"
        ) from None

    if status not in expected_statuses:
        if method in MUTATION_METHODS and 200 <= status <= 299:
            raise TransportFailure(f"unexpected successful status {status} for {method} {path}")
        diagnostic = redact_diagnostic(f"unexpected response body: {decoded!r}", config)
        raise APIError(status, "unexpected_status", diagnostic)
    if method in MUTATION_METHODS and not isinstance(decoded, dict):
        raise TransportFailure(f"invalid successful acknowledgement for {method} {path}")
    return decoded


# reject response-shape drift before a mutation consumes missing authority.
def require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{context} returned {type(value).__name__}, expected an object")
    return value


# evidence reads are arrays, never silently accepted envelopes.
def require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError(f"{context} returned {type(value).__name__}, expected an array")
    return value


# quote caller-supplied project identity before constructing route paths.
def wo_path(config: Config, wo_id: int) -> str:
    project = quote(config.project, safe="")
    return f"/api/v1/wo/{project}/{wo_id}"


# reconciliation always returns to the authoritative WO read.
def get_wo(config: Config, wo_id: int, token: str) -> dict[str, Any]:
    wo = require_object(request_json(config, "GET", wo_path(config, wo_id), token), "get WO")
    require_wo_identity(wo, config.project, wo_id, "get WO")
    return wo


# revision and content identity travel together for deterministic mutation admission.
def mutation_authority(wo: dict[str, Any]) -> tuple[int, str]:
    rev = wo.get("rev")
    content_hash = wo.get("content_hash")
    if type(rev) is not int or rev <= 0:
        raise RuntimeError("WO response is missing a positive rev")
    if not isinstance(content_hash, str) or not content_hash:
        raise RuntimeError("WO response is missing content_hash")
    return rev, content_hash


# inject one timezone-aware clock into lease admission and deterministic tests.
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# accept only timezone-aware RFC3339 timestamps emitted by the HTTP contract.
def parse_rfc3339(value: Any, context: str) -> datetime:
    if not isinstance(value, str) or RFC3339_PATTERN.fullmatch(value) is None:
        raise RuntimeError(f"{context} is not a timezone-aware RFC3339 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise RuntimeError(f"{context} is not a valid RFC3339 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise RuntimeError(f"{context} has no timezone offset")
    return parsed.astimezone(timezone.utc)


# validate durable WO identity before consuming response authority.
def require_wo_identity(
    wo: dict[str, Any], expected_project: str, expected_id: int, context: str
) -> None:
    if wo.get("project") != expected_project or wo.get("id") != expected_id:
        raise RuntimeError(f"{context} names the wrong project or WO")


# every retry identity uses one bounded visible-ASCII contract.
def validate_idempotency_key(key: str, context: str, max_bytes: int) -> None:
    encoded = key.encode("utf-8")
    if not encoded:
        raise RuntimeError(f"{context} must not be empty")
    if len(encoded) > max_bytes:
        raise RuntimeError(f"{context} exceeds {max_bytes} bytes")
    if any(byte < 0x21 or byte > 0x7E for byte in encoded):
        raise RuntimeError(f"{context} must contain visible ASCII only")


# expose create-key validation at the lifecycle preflight boundary.
def validate_create_idempotency_key(key: str) -> None:
    validate_idempotency_key(
        key,
        "create idempotency key",
        MAX_CREATE_IDEMPOTENCY_KEY_BYTES,
    )


# preserve the dedicated note-key validator used by callers and tests.
def validate_note_idempotency_key(key: str) -> None:
    validate_idempotency_key(
        key,
        "note idempotency key",
        MAX_NOTE_IDEMPOTENCY_KEY_BYTES,
    )


# unsafe create identity maps to one stable bounded caller key.
def derive_create_key(project: str, run_id: str) -> str:
    candidate = f"{project}:{run_id}:create"
    try:
        validate_create_idempotency_key(candidate)
        return candidate
    except RuntimeError:
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        derived = f"quickstart-create:{digest}"
        validate_create_idempotency_key(derived)
        return derived


# derive one stable bounded note identity before any lifecycle mutation.
def derive_note_key(project: str, run_id: str) -> str:
    candidate = f"{project}:{run_id}:note"
    try:
        validate_note_idempotency_key(candidate)
        return candidate
    except RuntimeError:
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        derived = f"quickstart-note:{digest}"
        validate_note_idempotency_key(derived)
        return derived


# fail before create when an old server cannot guarantee keyed note replay.
def preflight_idempotent_note_route(config: Config) -> None:
    discovery = require_object(
        request_json(config, "GET", "/api/v1/discover", config.agent_token),
        "discover capabilities",
    )
    endpoints = require_list(discovery.get("endpoints"), "discover endpoints")
    if IDEMPOTENT_NOTE_ENDPOINT not in endpoints:
        raise RuntimeError(
            "server does not advertise the fail-closed idempotent note endpoint"
        )


# invalid mutation bodies are ambiguous outcomes, not successful authority.
def require_mutation_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TransportFailure(f"{context} returned an invalid successful acknowledgement")
    return value


# a create replay must acknowledge the exact requested project and title.
def require_create_ack(
    value: Any, expected_project: str, expected_title: str
) -> dict[str, Any]:
    result = require_mutation_object(value, "create WO")
    wo = require_mutation_object(result.get("wo"), "create WO")
    if not isinstance(result.get("created"), bool):
        raise TransportFailure("create WO acknowledgement is missing created")
    if "deduplicated" in result and not isinstance(result["deduplicated"], bool):
        raise TransportFailure("create WO acknowledgement has invalid deduplicated")
    if type(wo.get("id")) is not int or wo["id"] <= 0:
        raise TransportFailure("create WO acknowledgement is missing a positive WO id")
    try:
        require_wo_identity(wo, expected_project, int(wo["id"]), "create WO")
    except RuntimeError as error:
        raise TransportFailure(f"create WO acknowledgement is invalid: {error}") from None
    if wo.get("title") != expected_title:
        raise TransportFailure("create WO acknowledgement has the wrong title")
    if not isinstance(wo.get("status"), str) or not wo["status"]:
        raise TransportFailure("create WO acknowledgement is missing WO status")
    try:
        mutation_authority(wo)
    except RuntimeError as error:
        raise TransportFailure(f"create WO acknowledgement is invalid: {error}") from None
    return result


# claim and status acknowledgements must name exact durable authority.
def require_wo_ack(
    value: Any,
    context: str,
    project: str,
    wo_id: int,
    *,
    status: str | None = None,
    claimed_by: str | None = None,
    claim_now: datetime | None = None,
    terminal_reason: str | None = None,
) -> dict[str, Any]:
    wo = require_mutation_object(value, context)
    try:
        require_wo_identity(wo, project, wo_id, context)
    except RuntimeError as error:
        raise TransportFailure(f"{context} acknowledgement is invalid: {error}") from None
    if status is not None and wo.get("status") != status:
        raise TransportFailure(f"{context} acknowledgement has the wrong status")
    if claimed_by is not None:
        if wo.get("claimed_by") != claimed_by:
            raise TransportFailure(f"{context} acknowledgement has no matching active claim")
        now = claim_now or utc_now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise RuntimeError("claim reconciliation clock must be timezone-aware")
        try:
            lease_expires_at = parse_rfc3339(
                wo.get("lease_expires_at"), f"{context} lease_expires_at"
            )
        except RuntimeError as error:
            raise TransportFailure(f"{context} acknowledgement is invalid: {error}") from None
        if lease_expires_at <= now.astimezone(timezone.utc):
            raise TransportFailure(f"{context} acknowledgement has an expired claim")
    if terminal_reason is not None:
        sections = wo.get("sections")
        if not isinstance(sections, dict) or sections.get("terminal_reason") != terminal_reason:
            raise TransportFailure(f"{context} acknowledgement has the wrong terminal reason")
    try:
        mutation_authority(wo)
    except RuntimeError as error:
        raise TransportFailure(f"{context} acknowledgement is invalid: {error}") from None
    return wo


# require the canonical note shape and the exact requested durable row.
def require_exact_note(
    value: Any,
    context: str,
    project: str,
    wo_id: int,
    content: str,
    idempotency_key: str,
) -> dict[str, Any]:
    note = require_object(value, context)
    if type(note.get("id")) is not int or note["id"] <= 0:
        raise RuntimeError(f"{context} is missing a positive note id")
    if note.get("project") != project or note.get("wo_id") != wo_id:
        raise RuntimeError(f"{context} names the wrong project or WO")
    if type(note.get("rev")) is not int or note["rev"] <= 0:
        raise RuntimeError(f"{context} is missing a positive rev")
    if note.get("content") != content:
        raise RuntimeError(f"{context} has the wrong content")
    if note.get("idempotency_key") != idempotency_key:
        raise RuntimeError(f"{context} has the wrong retry identity")
    parse_rfc3339(note.get("created_at"), f"{context} created_at")
    return note


# invalid exact note acknowledgements receive only one keyed replay.
def require_note_ack(
    value: Any, project: str, wo_id: int, content: str, idempotency_key: str
) -> dict[str, Any]:
    try:
        return require_exact_note(
            require_mutation_object(value, "add note"),
            "add note acknowledgement",
            project,
            wo_id,
            content,
            idempotency_key,
        )
    except RuntimeError as error:
        raise TransportFailure(f"add note acknowledgement is invalid: {error}") from None


# only validated caller-keyed writes receive one identical replay.
def keyed_write(
    config: Config,
    method: str,
    path: str,
    token: str,
    body: dict[str, Any],
    expected_statuses: tuple[int, ...],
    acknowledge: Callable[[Any], dict[str, Any]],
) -> dict[str, Any]:
    # both attempts share exact request construction and acknowledgement checks.
    def attempt() -> dict[str, Any]:
        response = request_json(
            config,
            method,
            path,
            token,
            body=body,
            expected_statuses=expected_statuses,
        )
        return acknowledge(response)

    try:
        return attempt()
    except TransportFailure:
        return attempt()


# a claim has no caller dedupe key, so inspect authority after an ambiguous response.
def claim_or_reconcile(
    config: Config,
    wo: dict[str, Any],
    *,
    clock: Callable[[], datetime] = utc_now,
) -> dict[str, Any]:
    wo_id = int(wo["id"])
    rev, content_hash = mutation_authority(wo)
    body = {
        "claimed_by": config.agent_id,
        "lease_minutes": DEFAULT_LEASE_MINUTES,
        "expected_rev": rev,
        "expected_content_hash": content_hash,
    }
    try:
        return require_wo_ack(
            request_json(
                config,
                "POST",
                wo_path(config, wo_id) + "/claim",
                config.agent_token,
                body=body,
            ),
            "claim WO",
            config.project,
            wo_id,
            claimed_by=config.agent_id,
            claim_now=clock(),
        )
    except TransportFailure:
        current = get_wo(config, wo_id, config.agent_token)
        try:
            return require_wo_ack(
                current,
                "claim reconciliation",
                config.project,
                wo_id,
                claimed_by=config.agent_id,
                claim_now=clock(),
            )
        except TransportFailure:
            pass
        raise RuntimeError(
            "claim outcome is ambiguous; inspect the WO before retrying the claim"
        ) from None


# updates have CAS but no dedupe key; accept only the observed target state.
def update_status_or_reconcile(
    config: Config,
    wo: dict[str, Any],
    status: str,
    token: str,
    *,
    no_code: bool = False,
) -> dict[str, Any]:
    wo_id = int(wo["id"])
    rev, content_hash = mutation_authority(wo)
    body: dict[str, Any] = {
        "status": status,
        "expected_rev": rev,
        "expected_content_hash": content_hash,
        "claim_actor": config.agent_id,
    }
    if no_code:
        body["closure_no_code"] = True
    terminal_reason = NO_CODE_TERMINAL_REASON if no_code else None
    try:
        return require_wo_ack(
            request_json(
                config,
                "PATCH",
                wo_path(config, wo_id),
                token,
                body=body,
            ),
            f"update WO to {status}",
            config.project,
            wo_id,
            status=status,
            terminal_reason=terminal_reason,
        )
    except TransportFailure:
        current = get_wo(config, wo_id, token)
        try:
            return require_wo_ack(
                current,
                f"update to {status} reconciliation",
                config.project,
                wo_id,
                status=status,
                terminal_reason=terminal_reason,
            )
        except TransportFailure:
            pass
        # do not echo a server-controlled status in operator diagnostics.
        raise RuntimeError(
            f"update to {status} is ambiguous; current authority does not confirm it; "
            "inspect before retrying"
        ) from None


# the preflighted route binds one exact canonical evidence note.
def add_evidence_note(config: Config, wo_id: int, note_key: str) -> dict[str, Any]:
    body = {
        "content": EVIDENCE_NOTE_CONTENT,
        "idempotency_key": note_key,
        "claim_actor": config.agent_id,
    }
    return keyed_write(
        config,
        "POST",
        wo_path(config, wo_id) + "/note/idempotent",
        config.agent_token,
        body,
        (201,),
        lambda value: require_note_ack(
            value,
            config.project,
            wo_id,
            EVIDENCE_NOTE_CONTENT,
            note_key,
        ),
    )


# a terminal replay proves completion exclusively through authoritative reads.
def read_completion_evidence(
    config: Config,
    wo_id: int,
    note_key: str,
    create_result: dict[str, Any],
    expected_note_id: int | None = None,
) -> dict[str, Any]:
    current = get_wo(config, wo_id, config.reviewer_token)
    if current.get("status") != "done":
        # successful response fields remain untrusted diagnostic input.
        raise RuntimeError("completion evidence does not report done status")
    sections = require_object(current.get("sections"), "completion evidence sections")
    if sections.get("terminal_reason") != NO_CODE_TERMINAL_REASON:
        raise RuntimeError("completion evidence has the wrong terminal reason")

    notes_query = urlencode({"limit": 100, "order": "asc"})
    notes = require_list(
        request_json(
            config,
            "GET",
            wo_path(config, wo_id) + "/notes?" + notes_query,
            config.reviewer_token,
        ),
        "list notes",
    )
    history = require_list(
        request_json(
            config,
            "GET",
            wo_path(config, wo_id) + "/history",
            config.reviewer_token,
        ),
        "get history",
    )
    binding_query = urlencode({"idempotency_key": note_key})
    binding = require_object(
        request_json(
            config,
            "GET",
            wo_path(config, wo_id) + "/note/idempotency?" + binding_query,
            config.reviewer_token,
        ),
        "get note idempotency binding",
    )
    bound_note = require_exact_note(
        binding.get("note"),
        "note idempotency binding note",
        config.project,
        wo_id,
        EVIDENCE_NOTE_CONTENT,
        note_key,
    )
    note_id = int(bound_note["id"])
    if not isinstance(binding.get("authority_hash"), str) or not binding["authority_hash"]:
        raise RuntimeError("note idempotency binding is missing authority_hash")
    if expected_note_id is not None and note_id != expected_note_id:
        raise RuntimeError("note idempotency binding does not reference the created note")
    listed_value = next(
        (
            note
            for note in notes
            if isinstance(note, dict) and note.get("id") == note_id
        ),
        None,
    )
    if listed_value is None:
        raise RuntimeError("bound note is absent from the authoritative note list")
    listed_note = require_exact_note(
        listed_value,
        "authoritative note list row",
        config.project,
        wo_id,
        EVIDENCE_NOTE_CONTENT,
        note_key,
    )
    for field in ("rev", "created_at"):
        if listed_note[field] != bound_note[field]:
            raise RuntimeError(f"note binding disagrees with the note list on {field}")

    return {
        "wo_id": wo_id,
        "created": bool(create_result.get("created")),
        "deduplicated": bool(create_result.get("deduplicated")),
        "status": current["status"],
        "note_id": note_id,
        "notes_returned": len(notes),
        "history_entries": len(history),
        "note_binding_verified": True,
    }


# demonstrate replay-safe lifecycle recovery without re-opening terminal work.
def run_lifecycle(
    config: Config, *, clock: Callable[[], datetime] = utc_now
) -> dict[str, Any]:
    create_key = derive_create_key(config.project, config.run_id)
    note_key = derive_note_key(config.project, config.run_id)
    validate_create_idempotency_key(create_key)
    validate_note_idempotency_key(note_key)
    preflight_idempotent_note_route(config)
    title = f"HTTP API quickstart {config.run_id}"
    create_body = {
        "project": config.project,
        "title": title,
        "priority": "P2",
        "sections": {
            "problem": "Verify an embedded HTTP client lifecycle.",
            "scope": "Create only this quickstart record.",
            "acceptance_criteria": "The reviewer closes the record and evidence remains queryable.",
            "expected_output": "A done WO with one keyed evidence note.",
        },
        "idempotency_key": create_key,
    }
    create_result = keyed_write(
        config,
        "POST",
        "/api/v1/wo",
        config.agent_token,
        create_body,
        (200, 201),
        lambda value: require_create_ack(value, config.project, title),
    )
    wo = require_object(create_result.get("wo"), "create result wo")
    wo_id = int(wo["id"])
    if wo.get("status") == "done":
        return read_completion_evidence(config, wo_id, note_key, create_result)

    claimed = claim_or_reconcile(config, wo, clock=clock)
    update_status_or_reconcile(config, claimed, "in_progress", config.agent_token)
    note = add_evidence_note(config, wo_id, note_key)

    current = get_wo(config, wo_id, config.reviewer_token)
    update_status_or_reconcile(
        config,
        current,
        "done",
        config.reviewer_token,
        no_code=True,
    )
    return read_completion_evidence(config, wo_id, note_key, create_result, int(note["id"]))


# emit only non-secret lifecycle evidence for copy-and-run diagnostics.
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Workledger HTTP API Python quickstart lifecycle."
    )
    parser.parse_args()
    try:
        summary = run_lifecycle(Config.from_environment())
    except (APIError, RuntimeError) as error:
        print(f"quickstart failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
