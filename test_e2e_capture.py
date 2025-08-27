
import json
import os
import tempfile
import pytest
from pathlib import Path
from aiohttp import web
from aiohttp.test_utils import TestServer


from capture_main import MitmproxyCapture


@pytest.fixture
async def mock_http_server():
    """Create a mock HTTP server for testing"""
    async def hello_handler(request):
        return web.json_response({
            "message": "Hello from test server",
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers)
        })

    app = web.Application()
    app.router.add_get("/test", hello_handler)

    server = TestServer(app)
    await server.start_server()

    yield server

    await server.close()


@pytest.fixture
def temp_capture_file():
    """Create a temporary file for capture output"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def temp_mitmproxy_dir():
    """Create a temporary directory for mitmproxy config"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir

    # Cleanup
    import shutil
    try:
        shutil.rmtree(temp_dir)
    except FileNotFoundError:
        pass


@pytest.fixture
def available_port():
    """Find an available port for the proxy"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class TestMitmproxyCapture:
    async def test_end_to_end_capture(self, mock_http_server, temp_capture_file, available_port, temp_mitmproxy_dir):
        """Test complete HTTP capture workflow"""

        # Setup environment variables for the test
        test_env = {
            'TARGET_URL': f'http://localhost:{mock_http_server.port}/test',
            'CAPTURE_FILE': temp_capture_file,
            'PROXY_PORT': str(available_port),
            'KEEP_RUNNING': 'false'
        }

        # Backup original environment
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]

        try:
            # Create and configure the capture instance
            capture = MitmproxyCapture()

            # Verify configuration is loaded correctly
            assert capture.target_url == test_env['TARGET_URL']
            assert capture.capture_file == test_env['CAPTURE_FILE']
            assert capture.proxy_port == available_port
            assert not capture.keep_running

            # Setup mitmproxy with temporary config directory
            from mitmproxy import options
            from mitmproxy.tools.dump import DumpMaster

            opts = options.Options(
                listen_port=capture.proxy_port,
                confdir=temp_mitmproxy_dir  # Use temp directory instead of /root/.mitmproxy
            )
            capture.master = DumpMaster(opts)
            capture.master.addons.add(capture.capture_addon)

            assert capture.master is not None

            # Run the capture session
            # Note: This will start proxy, make request, and capture the traffic
            await capture.run_capture_session()

            # Verify capture file was created and has content
            assert Path(temp_capture_file).exists()

            with open(temp_capture_file, 'r') as f:
                content = f.read().strip()
                assert content, "Capture file should not be empty"

                # Parse JSON lines format
                lines = content.strip().split('\n')
                assert len(lines) > 0, "Should have at least one captured request"

                # Verify first captured record
                first_record = json.loads(lines[0])

                # Validate structure
                assert 'id' in first_record
                assert 'timestamp' in first_record
                assert 'request' in first_record
                assert 'response' in first_record
                assert 'duration_ms' in first_record

                # Validate request data
                request_data = first_record['request']
                assert request_data['method'] == 'GET'
                assert '/test' in request_data['url']
                assert 'headers' in request_data

                # Validate response data
                response_data = first_record['response']
                assert response_data['status_code'] == 200
                assert 'headers' in response_data
                assert 'content' in response_data

                # Check that response contains expected data
                response_content = json.loads(response_data['content'])
                assert response_content['message'] == "Hello from test server"
                assert response_content['method'] == 'GET'

        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    async def test_capture_with_headers(self, mock_http_server, temp_capture_file, available_port, temp_mitmproxy_dir):
        """Test capture with custom headers"""

        test_env = {
            'TARGET_URL': f'http://localhost:{mock_http_server.port}/test',
            'CAPTURE_FILE': temp_capture_file,
            'PROXY_PORT': str(available_port),
            'CURL_HEADERS': 'X-Test-Header: test-value, Authorization: Bearer token123',
            'KEEP_RUNNING': 'false'
        }

        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]

        try:
            capture = MitmproxyCapture()

            # Setup mitmproxy with temporary config directory
            from mitmproxy import options
            from mitmproxy.tools.dump import DumpMaster

            opts = options.Options(
                listen_port=capture.proxy_port,
                confdir=temp_mitmproxy_dir
            )
            capture.master = DumpMaster(opts)
            capture.master.addons.add(capture.capture_addon)

            # Run a single request to test headers
            await capture.run_capture_session()

            # Verify headers were captured
            with open(temp_capture_file, 'r') as f:
                content = f.read().strip()
                record = json.loads(content.split('\n')[0])

                request_headers = record['request']['headers']
                assert 'X-Test-Header' in request_headers
                assert request_headers['X-Test-Header'] == 'test-value'
                assert 'Authorization' in request_headers
                assert request_headers['Authorization'] == 'Bearer token123'

        finally:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_config_loading(self, temp_capture_file, available_port):
        """Test configuration loading from environment variables"""

        test_env = {
            'TARGET_URL': 'https://example.com/api',
            'CAPTURE_FILE': temp_capture_file,
            'PROXY_PORT': str(available_port),
            'CURL_HEADERS': 'Content-Type: application/json',
            'KEEP_RUNNING': 'true'
        }

        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]

        try:
            capture = MitmproxyCapture()

            assert capture.target_url == 'https://example.com/api'
            assert capture.capture_file == temp_capture_file
            assert capture.proxy_port == available_port
            assert capture.curl_headers == 'Content-Type: application/json'
            assert capture.keep_running is True

        finally:
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
