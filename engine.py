"""Compatibility re-export for the computation engine.

The implementation lives in backend.engine. Existing scripts that import
`engine` can keep working while the project structure stays organized.
"""

from backend.engine import *  # noqa: F401,F403
