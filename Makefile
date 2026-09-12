.PHONY: check setup list
check:
	python3 -m unittest discover -s tests
	python3 -m py_compile scripts/bench scripts/build-harness scripts/results.py
	bash -n docker/prepare-app

setup:
	scripts/bench doctor
	scripts/bench build

list:
	scripts/bench list
