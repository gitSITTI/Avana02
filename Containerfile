# Requirements Consolidator: container image for the input layer (reqin).
# Works with Podman and Docker:   podman build -t reqin:dev .      docker build -f Containerfile -t reqin:dev .
#
# Stages (pick with --target):
#   test     installs reqin + test extras and RUNS the tests; the build fails if a test fails
#   boards   rebuilds the Excalidraw boards and checks they are byte-identical to the committed ones (stdlib only)
#   runtime  the `reqin` command only. This is the LAST stage, so a plain build produces it.
#
# Behind a firewall: point BASE_IMAGE at your internal registry mirror and PIP_INDEX_URL at your PyPI mirror, e.g.
#   podman build --build-arg BASE_IMAGE=registry.example.internal/python:3.12-slim --build-arg PIP_INDEX_URL=https://pypi.example.internal/simple .
# Database drivers are NOT included. Add what you need, e.g.  --build-arg EXTRA_PIP="psycopg[binary]"  (Postgres)  or  pyodbc  (SQL Server).

ARG BASE_IMAGE=docker.io/library/python:3.12-slim

FROM ${BASE_IMAGE} AS base
ARG PIP_INDEX_URL
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /opt/reqin
COPY reqin/pyproject.toml ./pyproject.toml
COPY reqin/src ./src
COPY reqin/profiles ./profiles
COPY reqin/connectors ./connectors
COPY reqin/CONNECTORS.md ./CONNECTORS.md
COPY reqin/GUI_CONTRACT.md ./GUI_CONTRACT.md
COPY reqin/LICENSE reqin/NOTICE ./

FROM base AS test
COPY reqin/tests ./tests
RUN pip install ".[test]" && python -m pytest -q -rs

FROM ${BASE_IMAGE} AS boards
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /opt/boards
COPY excalidraw_generator ./excalidraw_generator
COPY excalidraw ./excalidraw
WORKDIR /opt/boards/excalidraw_generator
RUN python build_all.py --check --out ../excalidraw && python validate.py ../excalidraw/*.excalidraw

FROM base AS runtime
ARG EXTRA_PIP=""
RUN pip install ".[oslc]" && if [ -n "$EXTRA_PIP" ]; then pip install $EXTRA_PIP; fi \
 && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin reqin \
 && mkdir /data && chown 10001 /data
LABEL org.opencontainers.image.title="reqin" \
      org.opencontainers.image.description="Reads requirements from SysML v2, ReqIF, DOORS Next (OSLC), Agility, Excel/CSV, SQL, Word and PDF into one canonical model. Read-only; makes no network calls unless the source itself is a URL or a remote database."
USER 10001
WORKDIR /data
ENTRYPOINT ["reqin"]
CMD ["--help"]
