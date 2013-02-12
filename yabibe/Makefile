init:
	python setup.py develop
	pip install -r requirements.txt

tests: test

vtests: vtest

test: vptest
	vptest/bin/nosetests ./tests/*.py

vtest:
	nosetests -v ./tests/*.py

coverage:
	nosetests --with-coverage --cover-erase --cover-package=yabibe --cover-html --cover-branches ./tests/*.py

quicktest:
	nosetests --with-coverage --cover-erase --cover-package=yabibe --cover-html --cover-branches ./tests/test_SSHFilesystem.py

egg: build
	python setup.py bdist_egg

build:
	python setup.py build

install:
	python setup.py install

vptest:
	#build a virtual pyhton for running tests
	virtualenv vptest
	vptest/bin/pip install -r test-requirements.txt
