FROM python:3.11-slim

COPY pyproject.toml README.md LICENSE /freq_io/
COPY ftio /freq_io/ftio

WORKDIR /freq_io

RUN python3 -m pip install --no-cache-dir .

ENTRYPOINT ["ftio"]
