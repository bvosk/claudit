FROM mitmproxy/mitmproxy:latest

USER root

RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install requests

RUN mkdir -p /root/.mitmproxy

COPY capture_main.py /usr/local/bin/capture_main.py
COPY capture_addon.py /usr/local/bin/capture_addon.py
RUN chmod +x /usr/local/bin/capture_main.py

WORKDIR /app

EXPOSE 8080

CMD ["python3", "/usr/local/bin/capture_main.py"]