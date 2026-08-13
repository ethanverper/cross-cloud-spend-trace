#!/usr/bin/env bash
# macOS-only. uv writes editable-install .pth files with the UF_HIDDEN
# filesystem flag set, which CPython 3.11's site.py silently skips -- causing
# `ModuleNotFoundError` for every workspace package even right after a clean
# `uv sync`. Not a project bug: Linux (this project's Docker images) is
# unaffected, since st_flags doesn't carry this meaning there. See
# docs/decisions/0002-phase2-raw-store-and-collector-architecture.md, item 9,
# for the full root-cause trace.
#
# uv re-hides these files on every `uv sync`/`uv run`, so re-run this after
# each one if imports mysteriously break again on macOS.

set -euo pipefail

if [[ "$(uname)" != "Darwin" ]]; then
  echo "fix-macos-venv.sh: not on macOS, nothing to do."
  exit 0
fi

shopt -s nullglob
pth_files=(.venv/lib/python3.*/site-packages/_editable_impl_*.pth)

if [[ ${#pth_files[@]} -eq 0 ]]; then
  echo "fix-macos-venv.sh: no _editable_impl_*.pth files found (no .venv yet? run 'uv sync' first)."
  exit 0
fi

chflags nohidden "${pth_files[@]}"
echo "fix-macos-venv.sh: un-hid ${#pth_files[@]} editable-install .pth file(s)."
