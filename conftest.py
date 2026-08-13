"""Loads .env before any test module's collection-time code runs (e.g. the
live-test `skipif` guards in `collectors/*/tests/test_*.py`, which check
`os.environ` directly at import time). Without this, credentials set only
in `.env` -- not exported as real shell env vars -- would never reach the
skipif checks, since `cross_cloud_spend_trace_common.config`'s own `load_dotenv()` call
only happens as a side effect of code that imports it, which is later than
pytest's collection-time skipif evaluation.
"""
from dotenv import load_dotenv

load_dotenv()
