FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY f1buddy ./f1buddy
COPY scripts ./scripts

RUN useradd --create-home --uid 1000 bot && mkdir /data && chown bot /data
USER bot
VOLUME /data

CMD ["python", "-m", "f1buddy"]
