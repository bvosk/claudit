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