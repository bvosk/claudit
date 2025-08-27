# Mitmproxy HTTP Capture Setup

This setup uses a slim Alpine Docker container to capture HTTP requests using mitmproxy.

## Quick Start

1. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

2. **View captured requests:**
   ```bash
   cat captures/requests.txt
   ```

## Configuration

Edit the `.env` file to customize:

- `TARGET_URL` - The URL to send requests to (default: https://httpbin.org/get)
- `CURL_HEADERS` - Additional headers for curl (comma-separated)
- `PROXY_PORT` - Proxy port (default: 8080)
- `KEEP_RUNNING` - Set to `true` to keep container running for inspection

## Examples

**Capture requests to a custom API:**
```bash
# In .env file:
TARGET_URL=https://api.example.com/endpoint
CURL_HEADERS=Authorization: Bearer your-token,Content-Type: application/json
```

**Keep container running for manual testing:**
```bash
# In .env file:
KEEP_RUNNING=true
```

Then connect to the running container:
```bash
docker exec -it mitmproxy-capture /bin/bash
```

## Output

- Captured requests are saved to `./captures/requests.txt`
- Contains both request and response data in JSON format
- Includes headers, content, timestamps, and status codes

## Cleanup

```bash
docker-compose down
rm -rf captures/
```