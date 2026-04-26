FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/opt/jpstock

RUN groupadd --gid 10001 hermes \
    && useradd --uid 10001 --gid hermes --home-dir /home/hermes --create-home --shell /usr/sbin/nologin hermes \
    && mkdir -p ${APP_HOME} /workspace /data /tmp/hermes \
    && chown -R hermes:hermes ${APP_HOME} /workspace /data /tmp/hermes /home/hermes

WORKDIR ${APP_HOME}

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app

USER hermes

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
