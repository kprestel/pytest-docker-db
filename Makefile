.PHONY: clean-pyc test clean-build lint format isort lock install install-compose dev-install
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
	poetry build

upload: build
	poetry publish

dist: clean test build upload

format:
	poetry run black .

lint:
	poetry run ruff check .

test: clean-pyc
	poetry run pytest $(TEST_PATH)

test-all:
	poetry run tox

install:
	poetry install

install-compose:
	poetry install -E compose

dev-install:
	poetry install --with dev

lock:
	poetry lock
