#!/bin/bash

set -e

echo "Starting mitmproxy capture setup..."

mkdir -p /app/captures

echo "Installing mitmproxy CA certificate..."
mitmdump --set confdir=/root/.mitmproxy &
MITM_PID=$!
sleep 3
kill $MITM_PID 2>/dev/null || true
wait $MITM_PID 2>/dev/null || true

if [ -f /root/.mitmproxy/mitmproxy-ca-cert.pem ]; then
    cp /root/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy-ca-cert.crt
    update-ca-certificates
    echo "CA certificate installed successfully"
else
    echo "Warning: CA certificate not found, creating initial cert..."
    mitmproxy --version
fi

TARGET_URL=${TARGET_URL:-"https://httpbin.org/get"}
CAPTURE_FILE=${CAPTURE_FILE:-"/app/captures/requests.txt"}
PROXY_PORT=${PROXY_PORT:-"8080"}

echo "Starting mitmdump on port $PROXY_PORT..."
mitmdump -p $PROXY_PORT -s /dev/stdin --set confdir=/root/.mitmproxy > "$CAPTURE_FILE" 2>&1 &
MITM_PID=$!

cat > /tmp/capture_script.py << 'EOF'
from mitmproxy import http
import json
import sys

def response(flow: http.HTTPFlow) -> None:
    request_info = {
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "headers": dict(flow.request.headers),
        "content": flow.request.content.decode('utf-8', errors='ignore') if flow.request.content else ""
    }
    response_info = {
        "status_code": flow.response.status_code,
        "headers": dict(flow.response.headers),
        "content": flow.response.content.decode('utf-8', errors='ignore') if flow.response.content else ""
    }
    
    capture_data = {
        "timestamp": flow.response.timestamp_start,
        "request": request_info,
        "response": response_info
    }
    
    print(f"CAPTURE: {json.dumps(capture_data)}", flush=True)
EOF

sleep 2

mitmdump -p $PROXY_PORT -s /tmp/capture_script.py --set confdir=/root/.mitmproxy > "$CAPTURE_FILE" 2>&1 &
MITM_PID=$!

sleep 3

echo "Executing curl command through proxy..."
export http_proxy="http://localhost:$PROXY_PORT"
export https_proxy="http://localhost:$PROXY_PORT"
export HTTP_PROXY="http://localhost:$PROXY_PORT"
export HTTPS_PROXY="http://localhost:$PROXY_PORT"

if [ ! -z "$CURL_HEADERS" ]; then
    IFS=',' read -ra HEADERS <<< "$CURL_HEADERS"
    HEADER_ARGS=""
    for header in "${HEADERS[@]}"; do
        HEADER_ARGS="$HEADER_ARGS -H \"$header\""
    done
    eval "curl -k -v $HEADER_ARGS \"$TARGET_URL\"" >> "$CAPTURE_FILE" 2>&1 || echo "Curl completed with proxy"
else
    curl -k -v "$TARGET_URL" >> "$CAPTURE_FILE" 2>&1 || echo "Curl completed with proxy"
fi

sleep 2

echo "Stopping mitmdump..."
kill $MITM_PID 2>/dev/null || true
wait $MITM_PID 2>/dev/null || true

echo "Capture completed. Results saved to $CAPTURE_FILE"
echo "Contents of capture file:"
cat "$CAPTURE_FILE"

if [ "$KEEP_RUNNING" = "true" ]; then
    echo "Keeping container running for inspection..."
    tail -f /dev/null
fi