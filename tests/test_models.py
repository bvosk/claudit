import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from models import (
    ProxyConfig,
    CaptureConfig,
    CapturedRequest,
    ValidationError,
)


# ---------------------------------------------------------------------------
# ProxyConfig Tests
# ---------------------------------------------------------------------------


def test_proxy_config_defaults():
    pc = ProxyConfig()
    assert pc.listen_host == "localhost"
    assert pc.listen_port == 8080
    assert pc.target_url == "https://api.anthropic.com"
    assert pc.mode == "reverse"
    assert pc.mitm_modes == ["reverse:https://api.anthropic.com"]
    opts = pc.to_options_dict()
    assert opts["listen_port"] == 8080
    assert opts["mode"][0].startswith("reverse:")


def test_proxy_config_custom_valid():
    pc = ProxyConfig(
        listen_host="0.0.0.0", listen_port=1234, target_url="https://example.com"
    )
    assert pc.listen_port == 1234
    assert pc.mitm_modes == ["reverse:https://example.com"]


def test_proxy_config_invalid_port():
    with pytest.raises(ValidationError):
        ProxyConfig(listen_port=70000)


def test_proxy_config_invalid_mode():
    with pytest.raises(ValidationError):
        ProxyConfig(mode="invalid_mode")


def test_proxy_config_invalid_url():
    with pytest.raises(ValidationError):
        ProxyConfig(target_url="ftp://example.com")


# ---------------------------------------------------------------------------
# CaptureConfig Tests
# ---------------------------------------------------------------------------


def test_capture_config_defaults():
    cc = CaptureConfig()
    # With no include patterns everything is included unless excluded
    assert cc.url_is_included("https://whatever.test/path")
    assert "authorization" in cc.sensitive_headers


def test_capture_config_include_exclude_substring():
    cc = CaptureConfig(
        url_include_patterns=["/v1/messages"],
        url_exclude_patterns=["/health"],
    )
    assert cc.url_is_included("https://api.test/v1/messages") is True
    assert cc.url_is_included("https://api.test/v1/messages/health") is False
    assert cc.url_is_included("https://api.test/other") is False  # not included


def test_capture_config_regex_mode():
    cc = CaptureConfig(
        url_include_patterns=[r"https://api\.example\.com/.+"],
        url_exclude_patterns=[r"/health$"],
        treat_patterns_as_regex=True,
    )
    assert cc.url_is_included("https://api.example.com/v1/messages")
    assert not cc.url_is_included("https://api.example.com/health")
    assert not cc.url_is_included("https://other.example.com/v1/messages")


def test_capture_config_invalid_regex():
    with pytest.raises(ValidationError):
        CaptureConfig(url_include_patterns=["*bad("], treat_patterns_as_regex=True)


def test_capture_config_header_masking():
    cc = CaptureConfig()
    headers = {
        "Authorization": "SuperSecretTokenValue",
        "X-API-Key": "sk-abcdefghijklmnop",
        "X-Auth-Token": "auth1234",
        "Content-Type": "application/json",
    }
    masked = cc.mask_headers(headers)
    assert masked["Authorization"].startswith("Supe") and masked[
        "Authorization"
    ].endswith("****")
    assert masked["X-API-Key"].startswith("sk-a") and masked["X-API-Key"].endswith(
        "****"
    )
    assert masked["X-Auth-Token"].endswith("****")
    assert masked["Content-Type"] == "application/json"


def test_capture_config_invalid_max_content():
    with pytest.raises(ValidationError):
        CaptureConfig(max_content_size=0)


# ---------------------------------------------------------------------------
# CapturedRequest.from_flow Tests
# ---------------------------------------------------------------------------


class DummyHeaders(dict):
    # mitmproxy headers support .items() etc; dict is fine
    pass


class DummyRequest:
    def __init__(
        self,
        method="POST",
        url="https://api.example.com/v1/messages",
        headers=None,
        content=b'{"key":"value"}',
        timestamp_start=None,
    ):
        self.method = method
        self.url = url
        self.pretty_url = url  # mimic mitmproxy attribute
        self.headers = DummyHeaders(
            headers or {"Authorization": "secret", "X-Id": "123"}
        )
        self.content = content
        self.timestamp_start = (
            timestamp_start
            if timestamp_start is not None
            else datetime.now(timezone.utc).timestamp()
        )


class DummyResponse:
    def __init__(
        self,
        status_code=200,
        headers=None,
        content=b'{"reply":"ok"}',
        timestamp_start=None,
    ):
        self.status_code = status_code
        self.headers = DummyHeaders(headers or {"Content-Type": "application/json"})
        self.content = content
        self.timestamp_start = (
            timestamp_start
            if timestamp_start is not None
            else datetime.now(timezone.utc).timestamp()
        )


class DummyError:
    def __init__(self, msg="Boom"):
        self.msg = msg

    def __str__(self):
        return self.msg


def build_flow(
    with_response=True,
    with_error=False,
    method="POST",
    request_content=b'{"key":"value"}',
    response_content=b'{"reply":"ok"}',
):
    start = datetime.now(timezone.utc)
    req_ts = start.timestamp()
    resp_ts = (start + timedelta(milliseconds=120)).timestamp()
    request = DummyRequest(
        method=method, content=request_content, timestamp_start=req_ts
    )
    response = (
        DummyResponse(content=response_content, timestamp_start=resp_ts)
        if with_response
        else None
    )
    error = DummyError() if with_error else None
    return SimpleNamespace(request=request, response=response, error=error)


def test_captured_request_success_flow():
    flow = build_flow()
    cc = CaptureConfig()
    cr = CapturedRequest.from_flow(flow, id=1, capture_config=cc)
    assert cr.id == 1
    assert cr.method == "POST"
    assert cr.response_status == 200
    assert isinstance(cr.duration_ms, (int, float))
    record = cr.as_dict()
    assert record["request"]["headers"]["Authorization"].endswith("****")  # masked
    assert record["response"]["status_code"] == 200
    assert record["duration_ms"] >= 0


def test_captured_request_error_flow():
    flow = build_flow(with_response=False, with_error=True)
    cr = CapturedRequest.from_flow(flow, id=2)
    assert cr.error is not None
    assert cr.response_status is None
    record = cr.to_record()
    assert record["response"] is None or record["response"]["status_code"] is None


def test_captured_request_request_body_disabled():
    flow = build_flow()
    cc = CaptureConfig(capture_request_body=False)
    cr = CapturedRequest.from_flow(flow, id=3, capture_config=cc)
    assert cr.request_body == ""  # omitted
    assert cr.response_body != ""


def test_captured_request_response_body_disabled():
    flow = build_flow()
    cc = CaptureConfig(capture_response_body=False)
    cr = CapturedRequest.from_flow(flow, id=4, capture_config=cc)
    assert cr.response_body == ""


def test_captured_request_non_json_content():
    flow = build_flow(request_content=b"plain text", response_content=b"\xff\xfe\xfa")
    cr = CapturedRequest.from_flow(flow, id=5)
    assert cr.request_body == "plain text"
    # response body should fallback to binary descriptor or decoded latin1
    assert isinstance(cr.response_body, str)


def test_captured_request_invalid_method():
    # from_flow will accept and then __post_init__ should raise if method invalid (not uppercase letters)
    flow = build_flow()
    flow.request.method = "Post"  # invalid pattern for our validation
    with pytest.raises(ValidationError):
        CapturedRequest.from_flow(flow, id=10)


def test_captured_request_custom_timestamp_override():
    flow = build_flow()
    override_ts = datetime(2020, 1, 1, 12, 0, 0)
    cr = CapturedRequest.from_flow(flow, id=6, timestamp=override_ts)
    assert cr.timestamp == override_ts


def test_captured_request_minimal_flow_missing_response_timestamps():
    # Remove response timestamp to exercise fallback
    flow = build_flow()
    flow.response.timestamp_start = None
    cr = CapturedRequest.from_flow(flow, id=7)
    # duration may be None if timestamps invalid
    assert cr.method == "POST"
    assert cr.timestamp is not None


# ---------------------------------------------------------------------------
# Validation Edge Cases
# ---------------------------------------------------------------------------


def test_captured_request_negative_duration_rejected():
    # Build manually to hit validation
    with pytest.raises(ValidationError):
        CapturedRequest(
            id=1,
            timestamp=datetime.now(timezone.utc),
            method="GET",
            url="https://x",
            duration_ms=-5,
        )


def test_captured_request_invalid_status():
    with pytest.raises(ValidationError):
        CapturedRequest(
            id=1,
            timestamp=datetime.now(timezone.utc),
            method="GET",
            url="https://x",
            response_status=-1,
        )
