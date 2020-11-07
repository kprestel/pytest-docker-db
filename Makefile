.PHONY: clean-pyc test clean-build
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
	python setup.py sdist bdist_wheel
	twine check dist/*

upload: build
	twine upload dist/*

dist: clean test build upload

isort:
	sh -c "isort --skip-glob=.tox --recursive . "

lint:
	flake8 --exclude=.tox

test: clean-pyc
	tox
