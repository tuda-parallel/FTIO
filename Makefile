PYTHON = .venv/bin/python3

testpypi: build
	${PYTHON} -m pip install --upgrade twine
	${PYTHON} -m twine upload --repository testpypi dist/*

testpypi-install:	
	${PYTHON} -m pip install --index-url https://test.pypi.org/simple/ --no-deps ftio_hpc

pypi: build
	${PYTHON} -m pip install --upgrade twine
	${PYTHON} -m twine upload --repository testpypi dist/*
	${PYTHON} -m pip install ftio_hpc

build: pack

pack:
	${PYTHON} -m  pip install --upgrade pip
	${PYTHON} -m  pip install --upgrade build 
	${PYTHON} -m build

ftio: 
	${PYTHON} -m pip install . 

quick_test:
	$(PWD)/.venv/bin/ftio -e no -h 

clean:
	pip uninstall ftio-hpc


install: venv ftio 
	source $(PWD)/.venv/bin/activate
	@echo "\nftio was installed in an environment" 
	@echo "To activate it call:\nsource $(PWD)/.venv/bin/activate\n"
	@echo "Afterwards, you can just call 'ftio [filename]'"


venv: 
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

profile:
	rm -f test.pstats
	${PYTHON} -m cProfile -o test.pstats ftio/cli/ftio_core.py -h
	snakeviz test.pstats

profile2:
	${PYTHON} -m pyinstrument ftio/cli/ftio_core.py  -h

test_all:
	mkdir quicktest
	cp examples/8.jsonl quicktest
	@cd quicktest && ftio 8.jsonl -e no && echo "--- passed ftio ---" || echo "--- failed ftio ---"
	@cd quicktest && ftio 8.jsonl -e no -o dbscan && echo "--- passed ftio ---" || echo "--- failed ftio ---"
	@cd quicktest && ftio 8.jsonl -e no -o lof && echo "--- passed ftio ---" || echo "--- failed ftio ---"
	@cd quicktest && ioparse 8.jsonl && echo "--- passed ioparse ---" || echo "--- failed ioparse ---"
	@cd quicktest && ioplot 8.jsonl --no_disp && echo "--- passed ioplot ---" || echo "--- failed ioplot ---"
	@rm -rf ./quicktest/*

test:
	cd test && python3 -m unittest