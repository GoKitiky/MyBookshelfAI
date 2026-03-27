# Contributing

Thanks for your interest in MyBookshelfAI.

## Development setup

1. **Python 3.11+** and **Node.js 22+** (with npm).
2. Install backend deps: `pip install -r requirements.txt`
3. Install frontend deps: `cd frontend && npm ci`
4. Run API + Vite together: `make dev` from the repo root (or use `./scripts/run.sh local`).

Alternatively, use Docker: `./scripts/run.sh docker`.

## Tests

```bash
pytest
```

Tests that call an LLM are skipped when `LLM_API_KEY` is unset.

## Frontend build

```bash
cd frontend && npm ci && npm run build
```

## Pull requests

- Keep changes focused on one concern when possible.
- Run `pytest` and `npm run build` before submitting when your change touches backend or frontend respectively.
- Follow existing code style; comments in English.

## Maintainer checklist: GitHub topics

After publishing or updating the repo, consider adding topics such as: `books`, `reading`, `self-hosted`, `fastapi`, `react`, `vite`, `llm`, `openai`, `byok`, `markdown`.
