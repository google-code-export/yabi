#!/bin/sh
#
source virt_yabibe/bin/activate

nosetests -v yabibe/tests/
#nosetests --with-coverage --cover-erase --cover-package=yabibe --cover-html --cover-branche
s ./tests/*.py
