from app import MitmproxyCapture
from capture_addon import CaptureAddon


def test_capture_addon_initialization():
    addon = CaptureAddon()
    assert addon is not None


def test_capture_addon_captured_data():
    addon = CaptureAddon()
    assert hasattr(addon, "captured_data")
    assert isinstance(addon.captured_data, list)


def test_mitmproxy_capture_initialization():
    capture = MitmproxyCapture()
    assert capture is not None
    assert capture.capture_addon is not None
