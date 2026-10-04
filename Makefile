PYTHON = .venv/bin/python

.PHONY: install repl server demo test lint

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt

repl:
	$(PYTHON) -m src.repl

server:
	$(PYTHON) -m src.server

demo:
	$(PYTHON) -m src.demo

test:
	$(PYTHON) -m coverage run --branch -m pytest -q
	$(PYTHON) -m coverage report -m

lint:
	$(PYTHON) -m pycodestyle src tests --max-line-length=80
