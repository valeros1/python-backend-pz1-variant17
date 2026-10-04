PYTHON = .venv/bin/python

.PHONY: install repl repl-demo server demo test lint

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt

repl:
	$(PYTHON) -m src.repl

repl-demo:
	$(PYTHON) -m src.repl < examples/repl_demo.txt

server:
	$(PYTHON) -m src.server

demo:
	$(PYTHON) -m src.demo

test:
	$(PYTHON) -m coverage run --branch \
		--include='src/model.py,src/client.py,src/protocol.py,src/server.py' \
		-m pytest -q
	$(PYTHON) -m coverage report -m

lint:
	$(PYTHON) -m pycodestyle src tests --max-line-length=80
