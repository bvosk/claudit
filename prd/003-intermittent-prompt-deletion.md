## Overview

There is an issue where, occasionally, a Github Action will run and detect NO system prompt.

## My thoughts

I have noticed that in the bad runs, there are 4 captured requests. In the good runs, there are only 2. I suspect the issue has to do with the shoddy logic in the `ClaudeCodeStrategy`'s `extract_prompt` which simply assumes the system prompt we are after is in the first captured request. I suspect that in this case with 4 requests, that logic does not pick up the request we are after.

## Bad run

### Link: https://github.com/bvosk/claudit/actions/runs/18440729337/job/52540703797

### Logs

```
mitmproxy-capture  | 2025-10-12 07:12:38 - claudit.application.capture_service - INFO - Starting capture workflow for strategy 'claudecode'
mitmproxy-capture  | 2025-10-12 07:12:38 - claudit.application.capture_service - INFO - Configuring mitmproxy in reverse mode (listen_port=8080)
mitmproxy-capture  | 2025-10-12 07:12:38 - claudit.application.capture_service - DEBUG - Waiting for mitmproxy listener readiness
mitmproxy-capture  | 2025-10-12 07:12:38 - mitmproxy_rs.server.base - DEBUG - Initializing UDP server ...
mitmproxy-capture  | 2025-10-12 07:12:38 - mitmproxy_rs.server.base - DEBUG - UDP server successfully initialized.
mitmproxy-capture  | 2025-10-12 07:12:38 - mitmproxy_rs.server.base - DEBUG - Initializing UDP server ...
mitmproxy-capture  | 2025-10-12 07:12:38 - mitmproxy_rs.server.base - DEBUG - UDP server successfully initialized.
mitmproxy-capture  | 2025-10-12 07:12:38 - claudit.application.capture_service - INFO - mitmproxy listener ready (port=8080) after 0.071s in 2 attempt(s)
mitmproxy-capture  | 2025-10-12 07:12:38 - claudit.application.capture_service - DEBUG - Proxy running; invoking agent command
mitmproxy-capture  | 2025-10-12 07:12:38 - claudit.infrastructure.agent_command_runner - INFO - Preparing to invoke agent command
mitmproxy-capture  | 2025-10-12 07:12:38 - claudit.infrastructure.agent_command_runner - INFO - Agent command resolved: claude -p hello --model haiku (shell=True timeout=15.0)
mitmproxy-capture  | 2025-10-12 07:12:39 - claudit.infrastructure.agent_command_runner - INFO - Agent tool version: 2.0.14 (Claude Code)
mitmproxy-capture  | 2025-10-12 07:12:39 - claudit.infrastructure.agent_command_runner - INFO - Starting agent command: claude -p hello --model haiku
mitmproxy-capture  | 2025-10-12 07:12:40 - claudit.capture_addon - DEBUG - Response headers: {'Date': 'Sun, 12 Oct 2025 07:12:40 GMT', 'Content-Type': 'application/json', 'Content-Length': '130', 'Connection': 'keep-alive', 'CF-RAY': '98d4ca4c2867d6f5-IAD', 'x-should-retry': 'false', 'request-id': 'req_011CU2tXdLX1F4mnE8czx2jY', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'x-envoy-upstream-service-time': '5', 'via': '1.1 google', 'cf-cache-status': 'DYNAMIC', 'X-Robots-Tag': 'none', 'Server': 'cloudflare'}
mitmproxy-capture  | Response content length: 130 bytes
mitmproxy-capture  | 2025-10-12 07:12:40 - claudit.capture_addon - DEBUG - Response headers: {'Date': 'Sun, 12 Oct 2025 07:12:40 GMT', 'Content-Type': 'application/json', 'Content-Length': '130', 'Connection': 'keep-alive', 'CF-RAY': '98d4ca4c78f2d6f5-IAD', 'x-should-retry': 'false', 'request-id': 'req_011CU2tXdYAmcUFGcjPqNasd', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'x-envoy-upstream-service-time': '8', 'via': '1.1 google', 'cf-cache-status': 'DYNAMIC', 'X-Robots-Tag': 'none', 'Server': 'cloudflare'}
mitmproxy-capture  | Response content length: 130 bytes
mitmproxy-capture  | 2025-10-12 07:12:41 - claudit.capture_addon - DEBUG - Response headers: {'Date': 'Sun, 12 Oct 2025 07:12:41 GMT', 'Content-Type': 'text/plain', 'Content-Length': '95', 'Connection': 'keep-alive', 'CF-RAY': '98d4ca4a4c59c9af-IAD', 'via': '1.1 google', 'cf-cache-status': 'DYNAMIC', 'X-Robots-Tag': 'none', 'Server': 'cloudflare'}
mitmproxy-capture  | Response content length: 95 bytes
mitmproxy-capture  | 2025-10-12 07:12:41 - claudit.capture_addon - DEBUG - Response headers: {'Date': 'Sun, 12 Oct 2025 07:12:41 GMT', 'Content-Type': 'application/json', 'Content-Length': '130', 'Connection': 'keep-alive', 'CF-RAY': '98d4ca514973d6f5-IAD', 'x-should-retry': 'false', 'request-id': 'req_011CU2tXgr6y5RrueE6BQVzM', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'x-envoy-upstream-service-time': '122', 'via': '1.1 google', 'cf-cache-status': 'DYNAMIC', 'X-Robots-Tag': 'none', 'Server': 'cloudflare'}
mitmproxy-capture  | Response content length: 130 bytes
mitmproxy-capture  | 2025-10-12 07:12:41 - claudit.application.capture_service - DEBUG - Initiating mitmproxy shutdown
mitmproxy-capture  | 2025-10-12 07:12:41 - claudit.application.capture_service - DEBUG - mitmproxy shutdown completed within timeout
mitmproxy-capture  | 2025-10-12 07:12:41 - claudit.application.capture_service - INFO - mitmproxy runner stopped (port=8080)
mitmproxy-capture  | 2025-10-12 07:12:41 - claudit.application.capture_service - DEBUG - Capture workflow proxy context exited
mitmproxy-capture  | 2025-10-12 07:12:41 - claudit.application.capture_service - INFO - Captured 4 request(s)
mitmproxy-capture  | 2025-10-12 07:12:41 - claudit.application.capture_service - INFO - Prompt written to prompts/claudecode.md
mitmproxy-capture  | Captured 4 requests
mitmproxy-capture  | Markdown written to prompts/claudecode.md
```

## Good run

### Link: https://github.com/bvosk/claudit/actions/runs/18441353075

### Logs

```
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.application.capture_service - INFO - Starting capture workflow for strategy 'claudecode'
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.application.capture_service - INFO - Configuring mitmproxy in reverse mode (listen_port=8080)
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.application.capture_service - DEBUG - Waiting for mitmproxy listener readiness
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.application.capture_service - INFO - mitmproxy listener ready (port=8080) after 0.004s in 1 attempt(s)
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.application.capture_service - DEBUG - Proxy running; invoking agent command
mitmproxy-capture  | 2025-10-12 08:16:56 - mitmproxy_rs.server.base - DEBUG - Initializing UDP server ...
mitmproxy-capture  | 2025-10-12 08:16:56 - mitmproxy_rs.server.base - DEBUG - UDP server successfully initialized.
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.infrastructure.agent_command_runner - INFO - Preparing to invoke agent command
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.infrastructure.agent_command_runner - INFO - Agent command resolved: claude -p hello --model haiku (shell=True timeout=15.0)
mitmproxy-capture  | 2025-10-12 08:16:56 - mitmproxy_rs.server.base - DEBUG - Initializing UDP server ...
mitmproxy-capture  | 2025-10-12 08:16:56 - mitmproxy_rs.server.base - DEBUG - UDP server successfully initialized.
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.infrastructure.agent_command_runner - INFO - Agent tool version: 2.0.14 (Claude Code)
mitmproxy-capture  | 2025-10-12 08:16:56 - claudit.infrastructure.agent_command_runner - INFO - Starting agent command: claude -p hello --model haiku
mitmproxy-capture  | 2025-10-12 08:16:58 - claudit.capture_addon - DEBUG - Response headers: {'Date': 'Sun, 12 Oct 2025 08:16:58 GMT', 'Content-Type': 'application/json', 'Content-Length': '130', 'Connection': 'keep-alive', 'CF-RAY': '98d5287b4f0af05c-DFW', 'x-should-retry': 'false', 'request-id': 'req_011CU2yS1CpvsGpmHsAE7Vu8', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'x-envoy-upstream-service-time': '24', 'via': '1.1 google', 'cf-cache-status': 'DYNAMIC', 'X-Robots-Tag': 'none', 'Server': 'cloudflare'}
mitmproxy-capture  | Response content length: 130 bytes
mitmproxy-capture  | 2025-10-12 08:16:58 - claudit.capture_addon - DEBUG - Response headers: {'Date': 'Sun, 12 Oct 2025 08:16:58 GMT', 'Content-Type': 'application/json', 'Content-Length': '130', 'Connection': 'keep-alive', 'CF-RAY': '98d5287c4881f05c-DFW', 'x-should-retry': 'false', 'request-id': 'req_011CU2yS1hqgULomszoUNEi9', 'strict-transport-security': 'max-age=31536000; includeSubDomains; preload', 'x-envoy-upstream-service-time': '6', 'via': '1.1 google', 'cf-cache-status': 'DYNAMIC', 'X-Robots-Tag': 'none', 'Server': 'cloudflare'}
mitmproxy-capture  | Response content length: 130 bytes
mitmproxy-capture  | 2025-10-12 08:16:58 - claudit.application.capture_service - DEBUG - Initiating mitmproxy shutdown
mitmproxy-capture  | 2025-10-12 08:16:58 - claudit.application.capture_service - DEBUG - mitmproxy shutdown completed within timeout
mitmproxy-capture  | 2025-10-12 08:16:58 - claudit.application.capture_service - INFO - mitmproxy runner stopped (port=8080)
mitmproxy-capture  | 2025-10-12 08:16:58 - claudit.application.capture_service - DEBUG - Capture workflow proxy context exited
mitmproxy-capture  | 2025-10-12 08:16:58 - claudit.application.capture_service - INFO - Captured 2 request(s)
mitmproxy-capture  | 2025-10-12 08:16:58 - claudit.application.capture_service - INFO - Prompt written to prompts/claudecode.md
mitmproxy-capture  | Captured 2 requests
mitmproxy-capture  | Markdown written to prompts/claudecode.md
```
