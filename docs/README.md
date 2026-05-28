# ResistAI Documentation

The canonical project overview, quick start, pipeline architecture, SDK usage,
and model list live in the [top-level README](../README.md).

## Additional references

- **Interactive API docs:** start the REST API (`uvicorn src.api:app`) and open
  `http://localhost:8000/docs` for Swagger / OpenAPI documentation of every
  `/v1` endpoint.
- **SDK walkthrough:** see [`examples/quickstart.ipynb`](../examples/quickstart.ipynb)
  for an end-to-end notebook (fold → screen → dock → generate → optimize).
- **Configuration:** runtime settings live in [`config/settings.yaml`](../config/settings.yaml);
  secrets are supplied via environment variables (see [`.env.example`](../.env.example)).
- **CLI:** run `python -m src.cli --help` (or `./scripts/resistai --help`) for the
  command-line interface.
