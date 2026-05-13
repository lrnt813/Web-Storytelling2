# Project Structure

```text
Web-Storytelling/
  backend/          FastAPI app, computation engine, shared config/state/schemas
  backend/core/     Domain facades for engine functions
  frontend/         Browser app
  frontend/css/     Stylesheets
  frontend/js/      Browser JavaScript split by concern
  scripts/          Data preparation and diagnostic utilities
  legacy/           Original/archived notebooks or monolithic scripts
  scratch/          Temporary diagnostics and runtime logs
  data/             GeoPackage inputs and derived datasets
  static/           Static API-served assets
```

Root-level `main.py` and `engine.py` are compatibility shims. Prefer new imports from
`backend.main` and `backend.engine` for new code.
