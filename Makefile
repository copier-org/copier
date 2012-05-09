.PHONY: clean clean-pyc test upload docs

all: clean clean-pyc test

clean: clean-pyc
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	rm -rf tests/res/t

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

test:
	rm -rf tests/res/t
	python runtests.py
	rm -rf tests/__pycache__

upload: clean
	python setup.py sdist upload

docs:
	cd docs; rm -rf build; clay build
	cp -r docs/build/html/* _pages
	cd _pages; git add .; git commit -m "Update pages"; git push origin gh-pages
	git add _pages; git commit -m "Update pages"; git push origin master
