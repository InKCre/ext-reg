# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder
ENV PDM_CHECK_UPDATE=false PDM_IGNORE_SAVED_PYTHON=1 PDM_VENV_IN_PROJECT=1
WORKDIR /app
RUN pip install --no-cache-dir pdm==2.28.0
COPY pyproject.toml pdm.lock README.md ./
COPY src/ src/
COPY toolkit/ toolkit/
COPY runtimes/core-py/ runtimes/core-py/
RUN pdm install --prod --no-editable --frozen-lockfile

FROM python:3.13-slim
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV PATH="/app/.venv/bin:${PATH}" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    REGISTRY_SOURCE_REVISION="${SOURCE_REVISION}"
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
RUN useradd --uid 10001 --create-home registry
USER registry
EXPOSE 8000
CMD ["python", "-m", "inkcre_extension_registry"]
