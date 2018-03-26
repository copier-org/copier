.PHONY: clean-pyc clean-build docs

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "testall - run tests on every Python version with tox"
	@echo "coverage - check code coverage with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "publish - package and upload a release"
	@echo "sdist - package"

clean: clean-build clean-pyc

clean-build:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

lint:
	flake8 voodoo tests

test:
	find . -name '__pycache__' -exec rm -rf {} +
	py.test -x tests/

test-all:
	tox

coverage:
	py.test --cov-config .coveragerc --cov-report html --cov voodoo tests/
	open htmlcov/index.html

docs:
	@(cd docs; make html)
	open docs/_build/html/index.html

publish: build
	python setup.py sdist bdist_wheel upload

build: clean
	python setup.py sdist
	python setup.py bdist_wheel --universal
