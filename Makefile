# `make check` runs what CI runs. Needs: python3 (3.11+), and `pip install -e "reqin[test]"` once.
CTR ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
PY  ?= python3
IMG ?= requirements-consolidator/reqin:dev

.PHONY: help check guard test boards image image-test render
help:
	@echo "check       guard + test + boards (what CI runs)"
	@echo "guard       refuse real-data files (tools/check_no_real_data.py)"
	@echo "test        reqin tests"
	@echo "boards      rebuild all Excalidraw boards and confirm they match the committed ones"
	@echo "image       build the runtime image with podman (or docker)"
	@echo "image-test  build the test stage (runs the tests inside the container)"
	@echo "render      boards -> PNG in excalidraw_generator/out (needs node + Playwright; see EXCALIDRAW_GUIDE.md)"

check: guard test boards

guard:
	$(PY) -m pytest -q tools
	$(PY) tools/check_no_real_data.py

test:
	cd reqin && $(PY) -m pytest -q -rs

boards:
	cd excalidraw_generator && $(PY) build_all.py --check --out ../excalidraw && $(PY) validate.py ../excalidraw/*.excalidraw

image:
	$(CTR) build -t $(IMG) -f Containerfile .

image-test:
	$(CTR) build --target test -t $(IMG)-test -f Containerfile .

render:
	cd excalidraw_generator && npm ci && sh make_bundle.sh && mkdir -p out && for f in ../excalidraw/*.excalidraw; do $(PY) render.py "$$f" "out/$$(basename "$$f" .excalidraw).png"; done
