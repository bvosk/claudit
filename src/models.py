"""
Core domain models and configuration dataclasses for the decoupled architecture.

This module intentionally contains ONLY pure data structures, light validation,
and deterministic helper methods. No side-effects (network, file I/O, logging)
should occur here to preserve testability and reusability.

Planned Usage (per refactor plan):
  - ProxyConfig: Passed into generic mitm proxy layer to configure listener & target
  - CaptureConfig: Passed into capture addon to drive filtering / masking behavior
  - CapturedRequest: Structured record produced by capture layer & consumed by
                     formatting / higher coordination logic.

All validation is performed eagerly in dataclass __post_init__ methods so that
invalid state cannot silently propagate. An explicit `.validate()` method is also
exposed for ergonomic re-validation in tests if mutated (though mutation of
frozen models is discouraged and not supported here except for `CapturedRequest`
which may be constructed incrementally in some workflows).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from datetime import datetime, timezone
from urllib.parse import urlparse
import json
import re


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #


class ValidationError(ValueError):
    """Raised when model initialization or explicit validation fails."""


# --------------------------------------------------------------------------- #
# Utility helpers (pure functions, test-friendly)
# --------------------------------------------------------------------------- #


def _validate_port(port: int) -> None:
    if not isinstance(port, int):
        raise ValidationError("Port must be an integer")
    if not (1 <= port <= 65535):
        raise ValidationError(f"Port {port} out of valid range 1-65535")


def _validate_url(url: str, field_name: str = "url") -> None:
    if not isinstance(url, str) or not url.strip():
        raise ValidationError(f"{field_name} must be a non-empty string")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValidationError(
            f"{field_name} must start with http:// or https:// (got: {url})"
        )
    if not parsed.netloc:
        raise ValidationError(
            f"{field_name} missing network location (host) portion: {url}"
        )


def _normalize_header_key(key: str) -> str:
    return key.strip()


def _mask_value(value: str) -> str:
    if not value:
        return "****"
    if len(value) <= 4:
        return "****"
    return value[:4] + "****"


def _safe_json_parse(blob: Optional[bytes | str]) -> Any:
    """
    Best-effort JSON parse utility:
      - If bytes, decode as UTF-8 with fallback to latin1.
      - If str, parse if JSON; otherwise return original string.
      - Returns parsed object on success, otherwise original primitive/string.
    """
    if blob is None:
        return ""
    if isinstance(blob, bytes):
        for encoding in ("utf-8", "latin1"):
            try:
                blob = blob.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        # If still bytes after attempts, represent as binary length.
        if isinstance(blob, bytes):
            return f"<binary:{len(blob)} bytes>"
    if isinstance(blob, str):
        stripped = blob.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return json.loads(blob)
            except json.JSONDecodeError:
                return blob
        return blob
    return blob


# --------------------------------------------------------------------------- #
# Data Models
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class ProxyConfig:
    """
    Configuration for the generic mitm proxy layer.

    Attributes:
        listen_host: Host interface to bind (usually 'localhost')
        listen_port: TCP port to listen on
        target_url: Base upstream service URL (e.g. 'https://api.anthropic.com')
        mode: mitmproxy mode specifier; for reverse proxy use 'reverse'
        extra_modes: Additional mode strings (rare; experimental flexibility)
    """

    listen_host: str = "localhost"
    listen_port: int = 8080
    target_url: str = "https://api.anthropic.com"
    mode: str = "reverse"
    extra_modes: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.listen_host, str) or not self.listen_host.strip():
            raise ValidationError("listen_host must be a non-empty string")
        _validate_port(self.listen_port)
        _validate_url(self.target_url, "target_url")
        if self.mode not in {"reverse", "transparent", "regular"}:
            raise ValidationError(
                f"Unsupported mode '{self.mode}'. Expected one of: reverse, transparent, regular"
            )
        for em in self.extra_modes:
            if not isinstance(em, str) or not em.strip():
                raise ValidationError("extra_modes must contain only non-empty strings")

    @property
    def mitm_modes(self) -> List[str]:
        """
        Return the list of mitmproxy 'mode' CLI-equivalent strings.

        For reverse mode the required syntax is 'reverse:<target_url>'.
        Additional modes appended as-is if provided.
        """
        base_mode = (
            f"{self.mode}:{self.target_url}" if self.mode == "reverse" else self.mode
        )
        return [base_mode, *self.extra_modes]

    def to_options_dict(self) -> Dict[str, Any]:
        """
        Adapter method returning dictionary structure suitable for constructing
        mitmproxy options programmatically (kept generic to avoid direct dependency).
        """
        return {
            "listen_host": self.listen_host,
            "listen_port": self.listen_port,
            "mode": self.mitm_modes,
        }

    def validate(self) -> None:
        """Explicit re-validation hook (normally unnecessary unless mutated)."""
        self.__post_init__()


@dataclass(slots=True)
class CaptureConfig:
    """
    Configuration controlling what traffic is captured and how it's sanitized.

    Attributes:
        url_include_patterns: List of substring or regex patterns to INCLUDE.
                              (If empty, all requests are considered candidates)
        url_exclude_patterns: List of substring or regex patterns to EXCLUDE.
        sensitive_headers: Headers whose values should be masked.
        max_content_size: Maximum raw byte size to attempt to decode (None = unlimited).
        capture_request_body: Whether to include the request body payload.
        capture_response_body: Whether to include the response body payload.
        treat_patterns_as_regex: If True, patterns are interpreted as compiled regex.
    """

    url_include_patterns: Sequence[str] = field(default_factory=tuple)
    url_exclude_patterns: Sequence[str] = field(default_factory=tuple)
    sensitive_headers: Iterable[str] = field(
        default_factory=lambda: {
            "authorization",
            "x-api-key",
            "cookie",
            "x-auth-token",
            "x-access-token",
        }
    )
    max_content_size: Optional[int] = 512_000  # ~500KB safety
    capture_request_body: bool = True
    capture_response_body: bool = True
    treat_patterns_as_regex: bool = False

    # Internal compiled regex caches (not part of external representation)
    _compiled_includes: List[re.Pattern] = field(
        init=False, repr=False, default_factory=list
    )
    _compiled_excludes: List[re.Pattern] = field(
        init=False, repr=False, default_factory=list
    )

    def __post_init__(self) -> None:
        if self.max_content_size is not None:
            if not isinstance(self.max_content_size, int) or self.max_content_size <= 0:
                raise ValidationError("max_content_size must be positive int or None")
        for lst_name, patterns in (
            ("url_include_patterns", self.url_include_patterns),
            ("url_exclude_patterns", self.url_exclude_patterns),
        ):
            for p in patterns:
                if not isinstance(p, str) or not p.strip():
                    raise ValidationError(
                        f"{lst_name} must contain non-empty string patterns"
                    )

        # Normalize sensitive header keys (case-insensitive matching)
        self.sensitive_headers = {
            h.lower().strip() for h in self.sensitive_headers if h.strip()
        }

        if self.treat_patterns_as_regex:
            # Compile includes/excludes for performance
            try:
                self._compiled_includes = [
                    re.compile(p) for p in self.url_include_patterns
                ]
                self._compiled_excludes = [
                    re.compile(p) for p in self.url_exclude_patterns
                ]
            except re.error as e:
                raise ValidationError(f"Invalid regex pattern: {e}") from e

    def validate(self) -> None:
        """Re-validate (e.g. after manual mutation in advanced scenarios)."""
        self.__post_init__()

    # ---------------- Filtering Logic (Pure) ---------------- #

    def url_is_included(self, url: str) -> bool:
        """Return True if the URL passes include/exclude criteria."""
        if self.treat_patterns_as_regex:
            if self._compiled_includes and not any(
                r.search(url) for r in self._compiled_includes
            ):
                return False
            if any(r.search(url) for r in self._compiled_excludes):
                return False
            return True
        else:
            if self.url_include_patterns and not any(
                p in url for p in self.url_include_patterns
            ):
                return False
            if any(p in url for p in self.url_exclude_patterns):
                return False
            return True

    def mask_headers(self, headers: Mapping[str, str]) -> Dict[str, str]:
        """Return a new headers dict with sensitive values masked."""
        masked: Dict[str, str] = {}
        for k, v in headers.items():
            lk = k.lower()
            masked[k] = _mask_value(v) if lk in self.sensitive_headers else v
        return masked


@dataclass
class CapturedRequest:
    """
    Structured record representing a single HTTP exchange.

    Fields intentionally align closely with the existing capture_addon output
    but provide stronger typing and normalization.

    Attributes:
        id: Sequence identifier (monotonic within a capture session)
        timestamp: UTC timestamp of when the response (or terminal error) was observed
        method: HTTP method (e.g. GET, POST)
        url: Full request URL
        request_headers: Dictionary of (possibly masked) request headers
        request_body: Parsed object OR raw string OR '' if unavailable
        response_status: Integer status code (None if error / not applicable)
        response_headers: Response headers (empty if not available)
        response_body: Parsed/decoded response payload ('' if absent/unavailable)
        duration_ms: Elapsed roundtrip time in milliseconds (float)
        error: Optional error message if flow failed
    """

    id: int
    timestamp: datetime
    method: str
    url: str
    request_headers: Dict[str, str] = field(default_factory=dict)
    request_body: Any = ""
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Any = ""
    duration_ms: Optional[float] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or self.id < 1:
            raise ValidationError("id must be positive integer")
        if not isinstance(self.timestamp, datetime):
            raise ValidationError("timestamp must be datetime instance")
        if not isinstance(self.method, str) or not self.method:
            raise ValidationError("method must be non-empty string")
        if not isinstance(self.url, str) or not self.url:
            raise ValidationError("url must be non-empty string")
        # Basic HTTP method sanity (per RFC; allow custom verbs gracefully)
        if not re.match(r"^[A-Z]+$", self.method):
            raise ValidationError(f"method appears invalid: {self.method}")
        if self.response_status is not None and (
            not isinstance(self.response_status, int) or self.response_status < 0
        ):
            raise ValidationError(
                "response_status must be a non-negative integer or None"
            )
        if self.duration_ms is not None and self.duration_ms < 0:
            raise ValidationError("duration_ms must be non-negative or None")

    # ---------------- Factory & Serialization ---------------- #

    @classmethod
    def from_flow(
        cls,
        flow: Any,
        *,
        id: int,
        capture_config: Optional[CaptureConfig] = None,
        timestamp: Optional[datetime] = None,
    ) -> "CapturedRequest":
        """
        Build a CapturedRequest from a mitmproxy HTTPFlow-like object WITHOUT
        importing mitmproxy directly (duck typing makes tests simpler).

        Expected minimal attributes on `flow`:
            flow.request.method (str)
            flow.request.pretty_url or flow.request.url (str)
            flow.request.headers (Mapping)
            flow.request.content (bytes | None)
            flow.request.timestamp_start (float, seconds since epoch)
            flow.response? (optional):
                .status_code (int)
                .headers (Mapping)
                .content (bytes | None)
                .timestamp_start (float)
            flow.error? (optional):
                .msg or __str__()

        Args:
            flow: The HTTP flow object
            id: Sequence identifier
            capture_config: CaptureConfig controlling masking / body inclusion
            timestamp: Optional override timestamp; defaults to response timestamp or now.
        """
        cc = capture_config or CaptureConfig()
        req_headers_raw = dict(getattr(flow.request, "headers", {}) or {})
        masked_headers = cc.mask_headers(req_headers_raw)

        # Resolve URL attribute gracefully
        url = getattr(flow.request, "pretty_url", None) or getattr(
            flow.request, "url", ""
        )

        # Request body
        request_body: Any = ""
        if cc.capture_request_body:
            request_body = _safe_json_parse(getattr(flow.request, "content", None))

        # Response handling
        response = getattr(flow, "response", None)
        resp_status: Optional[int] = None
        resp_headers: Dict[str, str] = {}
        resp_body: Any = ""
        duration_ms: Optional[float] = None

        if response is not None:
            resp_status = getattr(response, "status_code", None)
            resp_headers = dict(getattr(response, "headers", {}) or {})
            if cc.capture_response_body:
                resp_body = _safe_json_parse(getattr(response, "content", None))

            try:
                start_ts = float(getattr(flow.request, "timestamp_start"))
                end_ts = float(getattr(response, "timestamp_start"))
                duration_ms = round((end_ts - start_ts) * 1000, 2)
            except Exception:
                duration_ms = None

        err_obj = getattr(flow, "error", None)
        err_msg = None
        if err_obj:
            err_msg = getattr(err_obj, "msg", None) or str(err_obj)

        # Timestamp preference: supplied > response > request > now
        if timestamp is None:
            ts_epoch = None
            if response is not None:
                ts_epoch = getattr(response, "timestamp_start", None)
            if ts_epoch is None:
                ts_epoch = getattr(flow.request, "timestamp_start", None)
            if ts_epoch is not None:
                try:
                    timestamp = datetime.fromtimestamp(float(ts_epoch))
                except Exception:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)

        return cls(
            id=id,
            timestamp=timestamp,
            method=getattr(flow.request, "method", "UNKNOWN"),
            url=url,
            request_headers=masked_headers,
            request_body=request_body,
            response_status=resp_status,
            response_headers=resp_headers,
            response_body=resp_body,
            duration_ms=duration_ms,
            error=err_msg,
        )

    def as_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dict (stable field names), mirroring prior structure."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "request": {
                "method": self.method,
                "url": self.url,
                "headers": self.request_headers,
                "content": self.request_body,
            },
            "response": (
                None
                if self.error and self.response_status is None
                else {
                    "status_code": self.response_status,
                    "headers": self.response_headers,
                    "content": self.response_body,
                }
            ),
            "duration_ms": self.duration_ms,
            "error": self.error,
        }

    # Alias to harmonize with earlier code that appended capture dicts
    def to_record(self) -> Dict[str, Any]:
        return self.as_dict()
