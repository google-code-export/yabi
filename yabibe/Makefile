init:
	python setup.py develop
	pip install -r requirements.txt

tests: test

test:
	nosetests ./tests/*.py

vtest:
	nosetests -v ./tests/*.py

coverage:
	nosetests --with-coverage --cover-erase --cover-package=yabibe --cover-html --cover-branches ./tests/*.py

egg: build
	python setup.py bdist_egg

build:
	python setup.py build

install:
	python setup.py install
