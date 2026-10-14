# `make check` runs what CI runs. Needs: python3 (3.11+), and `pip install -e "reqin[test]"` once.
CTR ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
PY  ?= python3
IMG ?= requirements-consolidator/reqin:dev

.PHONY: help check guard test template boards proto proto-test image image-test render
help:
	@echo "check       guard + test + boards (what CI runs)"
	@echo "guard       refuse real-data files (tools/check_no_real_data.py)"
	@echo "test        reqin tests (file adapters, live connectors against fakes, HTTP kit, watch mode)"
	@echo "template    the connector template's own tests, in a throwaway virtualenv (.cache/tpl-venv)"
	@echo "boards      rebuild all Excalidraw boards and confirm they match the committed ones"
	@echo "proto       rebuild the prototype page, confirm it matches the committed one, run the static check"
	@echo "proto-test  prototype browser tests (needs npm, Playwright for Python, Chromium)"
	@echo "image       build the runtime image with podman (or docker)"
	@echo "image-test  build the test stage (runs the tests inside the container)"
	@echo "render      boards -> PNG in excalidraw_generator/out (needs node + Playwright; see EXCALIDRAW_GUIDE.md)"

check: guard test template boards proto

guard:
	$(PY) -m pytest -q tools
	$(PY) tools/check_no_real_data.py

test:
	cd reqin && $(PY) -m pytest -q -rs

# Runs in a throwaway virtualenv under .cache/ so the template's entry point never lands in your own environment.
template:
	rm -rf .cache/tpl-venv && $(PY) -m venv .cache/tpl-venv
	.cache/tpl-venv/bin/pip install -q -e "reqin[test]" -e connector_template
	.cache/tpl-venv/bin/python -m pytest -q connector_template/tests
	.cache/tpl-venv/bin/reqin connectors | grep -E "^acme "

boards:
	cd excalidraw_generator && $(PY) build_all.py --check --out ../excalidraw && $(PY) validate.py ../excalidraw/*.excalidraw

proto:
	cd prototype && $(PY) build.py /tmp/Main.built.dc.html >/dev/null && cmp /tmp/Main.built.dc.html project/Main.dc.html && node verify.js project/Main.dc.html | grep -E "^ISSUES 0$$"

proto-test:
	cd prototype && (cd vendor && npm ci) && $(PY) b11.py 1440 && $(PY) b11.py 390 && $(PY) b12.py 1440 && $(PY) b12.py 390

image:
	$(CTR) build -t $(IMG) -f Containerfile .

image-test:
	$(CTR) build --target test -t $(IMG)-test -f Containerfile .

render:
	cd excalidraw_generator && npm ci && sh make_bundle.sh && mkdir -p out && for f in ../excalidraw/*.excalidraw; do $(PY) render.py "$$f" "out/$$(basename "$$f" .excalidraw).png"; done
