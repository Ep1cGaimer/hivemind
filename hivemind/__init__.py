"""HiveMind's small, evidence-aware memory gateway.

The package deliberately defaults to the Python standard library.  The public
entry points are :func:`hivemind.fixture.seed_demo_store` and
``HiveMindGateway``; the optional FalkorDB adapter is imported lazily.
"""

from .domain import deterministic_id
from .demo import run_demo
from .fixture import seed_demo_store
from .gateway import HiveMindGateway

__all__ = ["HiveMindGateway", "deterministic_id", "run_demo", "seed_demo_store"]

__version__ = "0.1.0"
