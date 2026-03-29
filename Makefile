.PHONY: clean-pyc test clean-build lint format lock install dev-install mypy type-check check
TEST_PATH=tests

clean-pyc:
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '*.pyo' -exec rm --force {} +
	find . -name '*~' -exec rm --force  {} +

clean-build:
	rm --force --recursive build/
	rm --force --recursive dist/
	rm --force --recursive *.egg-info


clean: clean-pyc clean-build

build:
	uv build

upload: build
	uv publish

dist: clean test build upload

format:
	uv run ruff format .

lint:
	uv run ruff check .

test: clean-pyc
	uv run pytest $(TEST_PATH)

install:
	uv sync

dev-install:
	uv sync --group dev

lock:
	uv lock

mypy:
	uv run mypy pytest_docker_db

type-check: mypy

check: lint type-check

