FROM mitmproxy/mitmproxy:latest

USER root

RUN apt-get update && apt-get install -y \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /root/.mitmproxy

RUN mitmdump --version > /dev/null 2>&1 || echo "mitmproxy installed"

COPY capture.sh /usr/local/bin/capture.sh
RUN chmod +x /usr/local/bin/capture.sh

WORKDIR /app

EXPOSE 8080

CMD ["/usr/local/bin/capture.sh"]