# syntax=docker/dockerfile:1
ARG MITMPROXY_TAG=latest
# Stage 0: Official Node.js image (provides latest current/LTS toolchain)
FROM node:22-bookworm-slim AS nodejs

# Stage 1: mitmproxy runtime
# Pin-ready base image; override at build time with:
#   docker build --build-arg MITMPROXY_TAG=9.0.1 -t mitm-capture .
FROM mitmproxy/mitmproxy:${MITMPROXY_TAG}

USER root
WORKDIR /app

# Install tools needed to set up uv and a Python venv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install uv (https://docs.astral.sh/uv/) and place on PATH
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv

# Copy Node.js toolchain from official image and enable corepack (optional package managers)
COPY --from=nodejs /usr/local/bin/ /usr/local/bin/
COPY --from=nodejs /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN corepack enable || true

# Install Claude Code CLI via official installer script (version pinned for reproducibility)
ARG CLAUDE_CODE_VERSION=1.0.106
RUN curl -fsSL https://claude.ai/install.sh -o /tmp/claude-install.sh \
    && bash /tmp/claude-install.sh "${CLAUDE_CODE_VERSION}" \
    && mv /root/.local/bin/claude /usr/local/bin/claude \
    && rm -f /tmp/claude-install.sh

# Create a dedicated virtual environment for the app and prefer it on PATH
ENV VENV_PATH=/opt/venv
RUN python3 -m venv "${VENV_PATH}"
ENV PATH="${VENV_PATH}/bin:${PATH}"

# Copy dependency manifest first for better layer caching
COPY pyproject.toml /app/

# Resolve and install runtime dependencies into the venv
# This uses uv's fast resolver/installer. If/when you add a uv.lock,
# consider switching to a locked install flow.
RUN uv pip compile pyproject.toml -o /tmp/requirements.txt \
    && uv pip install --python "${VENV_PATH}/bin/python" -r /tmp/requirements.txt

# Copy the application source
COPY . /app

# Install the project itself into the venv without re-resolving dependencies
RUN uv pip install --python "${VENV_PATH}/bin/python" --no-deps /app

# Ensure mitmproxy's default confdir exists (code currently uses /root/.mitmproxy)
RUN mkdir -p /root/.mitmproxy

EXPOSE 8080

# Run via console script entrypoint (defined in pyproject.toml [project.scripts])
ENTRYPOINT ["mitm-capture"]
