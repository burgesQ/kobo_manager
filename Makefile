.PHONY: test test-coverage lint lint-fix type-check

test:
	uv run pytest .

test-coverage:
	uv run pytest --cov=kobocore --cov=vault --cov=unmod --cov=flasher --cov=modder --cov-report=html . -q

lint:
	uv run ruff check .
	uv run black --check --diff .
	uv run isort --profile black --check-only .

lint-fix:
	uv run ruff check --fix .
	uv run black .
	uv run isort --profile black .

type-check:
	uv run mypy kobocore/src vault/src unmod/src flasher/src modder/src
