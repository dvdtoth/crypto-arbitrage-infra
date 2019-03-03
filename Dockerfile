FROM python:3.6.8
ARG REQUIREMENTSFILE
WORKDIR /app

COPY $REQUIREMENTSFILE ./
RUN pip install --no-cache-dir -r $REQUIREMENTSFILE
COPY src/ ./src
COPY config/ ./config

COPY ./docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
