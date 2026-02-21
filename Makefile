SCRIPT=git_fast_import_merge.py
PYTHON3=python3
PYTHON=$(PYTHON3)
TWINE=twine
GIT = git
PYTHONVERSION = 3.9
COVERAGE3 = $(PYTHON3) -m coverage
TESTS=$(SCRIPT:.py=.tests.py)
V=-v

BASEYEAR=2023
FOR=today

-include Makefile.tmp

help:
	$(PYTHON3) $(SCRIPT) --help
check:
	$(MAKE) checkcode
	$(MAKE) tests
checkcode cc:
	$(PYTHON3) _checkcode.py $(SCRIPT) $(TESTS)

test: ; $(PYTHON3) $(TESTS) $V
tests: ; $(PYTHON3) $(TESTS) $V --showgraph
test_%: ; $(PYTHON3) $(TESTS) --failfast --showgraph $V $@ 
t_%: ; $(PYTHON3) $(TESTS) --failfast --showgraph $V tes$@ 

cover coverage: ; $(PYTHON3) $(TESTS) $V --cover

clean:
	- rm *.pyc 
	- rm -rf *.tmp
	- rm -rf tmp tmp.files
	- rm TEST-*.xml
	- rm setup.py README
	- rm -rf build dist *.egg-info
	- rm *.cover *,cover

############## version
FILES = *.py *.cfg

version:
	@ grep -l __version__ $(FILES) | { while read f; do : \
	; THISYEAR=`date +%Y -d "$(FOR)"` ; YEARS=$$(expr $$THISYEAR - $(BASEYEAR)) \
        ; WEEKnDAY=`date +%W%u -d "$(FOR)"` ; sed -i \
	-e "/^version /s/[.]-*[0123456789][0123456789][0123456789]*/.$$YEARS$$WEEKnDAY/" \
	-e "/^ *__version__/s/[.]-*[0123456789][0123456789][0123456789]*\"/.$$YEARS$$WEEKnDAY\"/" \
	-e "/^ *__version__/s/[.]\\([0123456789]\\)\"/.\\1.$$YEARS$$WEEKnDAY\"/" \
	-e "/^ *__copyright__/s/(C) \\([123456789][0123456789]*\\)-[0123456789]*/(C) \\1-$$THISYEAR/" \
	-e "/^ *__copyright__/s/(C) [123456789][0123456789]* /(C) $$THISYEAR /" \
	$$f; done; }
	@ grep ^__version__ $(FILES) | grep -v .tests.py
	@ $(MAKE) commit
commit:
	@ ver=`grep "version.*=" setup.cfg | sed -e "s/version *= */v/"` \
	; echo ": $(GIT) commit -m $$ver"
tag:
	@ ver=`grep "version.*=" setup.cfg | sed -e "s/version *= */v/"` \
	; rev=`${GIT} rev-parse --short HEAD` \
	; if test -r tmp.changes.txt \
	; then echo ": ${GIT} tag -F tmp.changes.txt $$ver $$rev" \
	; else echo ": ${GIT} tag $$ver $$rev" ; fi

############## https://pypi.org/...

README: README.md Makefile
	cat README.md | sed -e "/\\/badge/d" -e /^---/q > README
setup.py: Makefile
	{ echo '#!/usr/bin/env python3' \
	; echo 'import setuptools' \
	; echo 'setuptools.setup()' ; } > setup.py
	chmod +x setup.py
setup.py.tmp: Makefile
	echo "import setuptools ; setuptools.setup()" > setup.py

.PHONY: build
build:
	rm -rf build dist *.egg-info
	$(MAKE) $(PARALLEL) README setup.py
	# pip install --root=~/local . -v
	$(PYTHON3) setup.py sdist
	- rm -v setup.py README
	$(TWINE) check dist/*
	: $(TWINE) upload dist/*

ins install:
	$(MAKE) setup.py
	export DISTUTILS_DEBUG=1; \
	$(PYTHON3) -m pip install --no-compile --user .
	rm -v setup.py
	$(MAKE) show | sed -e "s|[.][.]/[.][.]/[.][.]/bin|$$HOME/.local/bin|"
show:
	test -d tmp || mkdir -v tmp
	cd tmp && $(PYTHON3) -m pip show -f $$(sed -e '/^name *=/!d' -e 's/.*= *//' ../setup.cfg)
uns uninstall: setup.py
	test -d tmp || mkdir -v tmp
	cd tmp && $(PYTHON3) -m pip uninstall -v --yes $$(sed -e '/^name *=/!d' -e 's/.*= *//' ../setup.cfg)
rem remove:
	- rm -v ~/.local/bin/$(SCRIPT)
	- rm -v ~/.local/data/$(SCRIPT:.py=.tests.py)
	- find ~/.local/lib -name site-packages | \
	  { while read site; do rm -rv $$site/$$(sed -e '/^name *=/!d' -e 's/.*= *//' setup.cfg)-*; done }
	- rm -rv ~/.local/data/$$(sed -e '/^name *=/!d' -e 's/.*= *//' setup.cfg)/
	- rm -v ~/.local/data/README.md

mypy:
	zypper install -y mypy
	zypper install -y python3-click python3-pathspec

MYPY = mypy
MYPY_STRICT = --strict --show-error-codes --show-error-context --no-warn-unused-ignores --python-version $(PYTHONVERSION) --implicit-reexport
AUTOPEP8=autopep8
AUTOPEP8_INPLACE= --in-place

%.type: ; $(MYPY) $(MYPY_STRICT) $(MYPY_OPTIONS) $(@:.type=)
%.pep8:
	$(AUTOPEP8) $(AUTOPEP8_INPLACE) $(AUTOPEP8_OPTIONS) $(@:.pep8=)
	$(GIT) --no-pager diff $(@:.pep8=)

type: ;	 $(MAKE) $(SCRIPT).type $(SCRIPT:.py=.tests.py).type
style: ; $(MAKE) $(SCRIPT).pep8 $(SCRIPT:.py=.tests.py).pep8
