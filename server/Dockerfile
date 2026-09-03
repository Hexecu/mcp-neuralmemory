FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 10001 neuralmemory
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip && python -m pip install .

USER neuralmemory
EXPOSE 8765
CMD ["sh", "-c", "python -m kg_mcp.kg.apply_schema && kg-mcp --transport http"]
