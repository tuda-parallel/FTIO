PYTHON = .venv/bin/python3
SHELL := /bin/bash


#check if python exist in venv, otherwise fallback to default
ifeq ("$(PYTHON)",".venv/bin/python3")
ifeq ("$(wildcard ${PYTHON})","")
$(warning Python not found in .venv, falling back to default)
PYTHON=python3
endif
else 
$(info Using python: $(PYTHON))
endif

REQUIRED_PYTHON_VERSION := 3.8
PYTHON_VERSION := $(shell python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

version_check = $(shell python3 -c 'import sys; required_version = tuple(map(int, "$(REQUIRED_PYTHON_VERSION)".split("."))); \
    sys.exit((sys.version_info.major, sys.version_info.minor) < required_version)')

# Terminate the make process if the version is below the required version
ifeq ($(version_check),1)
$(error Python $(REQUIRED_PYTHON_VERSION) or higher is required. Installed version: $(PYTHON_VERSION))
else
$(info Python version is satisfied: $(PYTHON_VERSION))
endif


all: install  

install: venv clean ftio_venv msg 

debug: venv ftio_debug_venv msg 

ftio_venv: override PYTHON = .venv/bin/python3
ftio_venv: ftio

ftio_debug_venv: override PYTHON = .venv/bin/python3
ftio_debug_venv: ftio_debug

ftio_debug: 
	$(PYTHON) -m pip install -e .
	# mv old_setup setup.py
	# mv pyproject.toml old_pyproject
	# $(PYTHON) -m pip install -e . || (mv old_pyproject pyproject.toml && mv setup.py old_setup)
	# mv old_pyproject pyproject.toml
	# mv setup.py old_setup

ftio: 
	$(PYTHON) -m pip install . 

venv: 
	$(PYTHON) -m venv .venv 
	@echo -e "Environment created. Using python from .venv/bin/python3" 

msg: 
	@echo -e "\nftio was installed in an python environment in .venv" 
	@echo -e "To activate python from this venv, call:\nsource $(PWD)/.venv/bin/activate\n"
	@echo -e "Afterwards, you can just call 'ftio [filename]'"
#########



clean_project:
	echo "Cleaning old installation"
	$(PYTHON) -m pip uninstall --yes ftio-hpc || echo "no installation of ftio found"
	# @mv old_pyproject pyproject.toml && mv setup.py old_setup || true

clean: clean_project
	rm -rf .venv


docker:
	cd docker && docker build -t freq_io:1.0 .


docker_run:
	cd docker && docker run -v "$$PWD/examples/tmio/JSONL/8.jsonl:/freq_io/8.jsonl" -t freq_io:1.0 ftio 8.jsonl -e no 


docker_interactive:
	cd docker && docker run -ti   freq_io:1.0



# profile 
profile:
	rm -f test.pstats
	$(PYTHON) -m cProfile -o test.pstats ftio/cli/ftio_core.py -h
	$(PYTHON) -m pip install snakeviz
	snakeviz test.pstats

profile2:
	$(PYTHON) -m pip install pyinstrument
	$(PYTHON) -m pyinstrument ftio/cli/ftio_core.py  -h

# test
test_all:
	mkdir quicktest
	cp examples/tmio/JSONL/8.jsonl quicktest
	@cd quicktest && ftio 8.jsonl -e no && echo "--- passed ftio ---" || echo "--- failed ftio ---"
	@cd quicktest && ftio 8.jsonl -e no -o dbscan && echo "--- passed ftio ---" || echo "--- failed ftio ---"
	@cd quicktest && ftio 8.jsonl -e no -o lof && echo "--- passed ftio ---" || echo "--- failed ftio ---"
	@cd quicktest && ioparse 8.jsonl && echo "--- passed ioparse ---" || echo "--- failed ioparse ---"
	@cd quicktest && ioplot 8.jsonl --no_disp && echo "--- passed ioplot ---" || echo "--- failed ioplot ---"
	@rm -rf ./quicktest/*

test:
	cd test && python3 -m pytest && make clean

quick_test:
	$(PWD)/.venv/bin/ftio -e no -h 


# publish
testpypi: build
	$(PYTHON) -m pip install --upgrade twine
	$(PYTHON) -m twine upload --repository testpypi dist/*

testpypi-install:	
	$(PYTHON) -m pip install --index-url https://test.pypi.org/simple/ --no-deps ftio_hpc

pypi: build
	$(PYTHON) -m pip install --upgrade twine
	$(PYTHON) -m twine upload --repository testpypi dist/*
	$(PYTHON) -m pip install ftio_hpc

build: pack

pack:
	$(PYTHON) -m  pip install --upgrade pip
	$(PYTHON) -m  pip install --upgrade build 
	$(PYTHON) -m build



.PHONY: all test test_all clean clean_all build pack testpypi ftio
