# PYTHON := ~/venv/bin/python3
PYTHON := python3
INSTALL_DIR := ~/.local/bin/

ftio: ftio_core test

ftio_core:
	pip install . 


test:
	ftio -e no

clean:
	pip uninstall ftio-hpc


install: PYTHON = .venv/bin/python3
install: req ftio test 

req: .venv
	$(PYTHON) ./install/install_packages.py
	

.venv: install/install_packages.py
	python3 -m venv .venv


clean_install: 
	rm -rf .venv


docker:
	cd docker && docker build -t freq_io:1.0 .


docker_run:
	cd docker && docker run -v "$$PWD/8.jsonl:/freq_io/8.jsonl" -t freq_io:1.0 ftio 8.jsonl -e no 


docker_interactive:
	cd docker && docker run -ti   freq_io:1.0

debug:
	mv old_setup setup.py
	mv pyproject.toml pyproject
	pip install -e .
	mv pyproject pyproject.toml
	mv setup.py old_setup