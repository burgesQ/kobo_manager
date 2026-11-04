# Single image used both to run the CLIs and as the Codespaces dev container.
#
#   docker run --rm -it \
#     -v /media/$USER/KOBOeReader:/kobo \
#     -v ~/kobo-backups:/root/kobo-backups \
#     ghcr.io/burgesq/kobo_manager vault snapshot --mount /kobo --dry-run
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# git + make: needed by the dev container (Codespaces) and `make lint/test`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git make \
    && rm -rf /var/lib/apt/lists/*

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY . .
RUN uv sync --frozen --no-editable

ENV PATH="/app/.venv/bin:$PATH"

CMD ["bash"]
