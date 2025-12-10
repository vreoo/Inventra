# Repository Guidelines

## Project Structure & Module Organization
`backend/` hosts FastAPI services: routes in `api/`, business logic in `services/`, Pydantic schemas in `models/`, uploads in `storage/`, and regression tests in `tests/`. `frontend/` is a Next.js workspace with routing in `src/app/`, shared UI in `src/components/`, and static assets in `public/`. CSV fixtures live in `sample_data/`; regenerate demos with `sample_data/generate_demand_planning_data.py`. Review `docs/` and `memory-bank/` before major flow updates.

## Build, Test, and Development Commands
- `cd backend && python run_server.py` — installs dependencies and starts FastAPI on `:8000`.
- `cd backend && uvicorn main:app --reload` — lean reload loop once deps exist.
- `cd backend && python -m unittest discover tests` — runs the backend suite.
- `cd frontend && npm install` (or `pnpm install`) — prepares the web workspace.
- `cd frontend && npm run dev` — serves Next.js on `:3000` with HMR.
- `cd frontend && npm run lint` — enforces the Next.js ESLint ruleset.

## Coding Style & Naming Conventions
Target Python 3.10+, 4-space indents, and type hints on public functions. Use `snake_case` for modules/functions, `PascalCase` for classes, and expose routers with `router = APIRouter()` in `api/*.py`. Prefer Pydantic models over raw dict responses. Frontend `.tsx` files use `PascalCase` components, `camelCase` hooks, and colocate reusable pieces in `src/components/`. Organize Tailwind utilities and run `npm run lint` (optional local Prettier) before commits.

## Testing Guidelines
Backend tests rely on the stdlib `unittest` harness (`backend/tests/test_*.py`); subclass `unittest.TestCase`, clean temporary files in `tearDown`, and cover edge cases with descriptive method names. Use `sample_data/` fixtures rather than ad-hoc uploads. Frontend tests are not wired—if you add them, favor `@testing-library/react` beside the component (`Widget.test.tsx`). Capture the output of `python -m unittest …` and `npm run lint` in PRs that impact behavior.

## Commit & Pull Request Guidelines
Adopt imperative ≤72-character summaries, ideally Conventional Commit `type: summary` (`feat`, `fix`, `refactor`, `docs`). Split backend and frontend changes when practical. PRs should link issues, call out cross-surface touchpoints, attach relevant screenshots or logs, and note new env vars or scripts for reviewer setup.

## Configuration & Feature Flags
Enable demand planning with `DEMAND_PLANNING_ENABLED` (API) and `NEXT_PUBLIC_DEMAND_PLANNING_ENABLED` (web) in local `.env` files. Manage CORS through `ALLOWED_ORIGINS` or `ALLOWED_ORIGIN_REGEX`; include localhost plus any staging domains. Keep secrets out of TypeScript bundles and generate regression inputs with `sample_data/generate_demand_planning_data.py`.

Enable AI forecast summaries by setting `ENABLE_AI_SUMMARY=true` and providing
`HF_API_TOKEN` plus optional `AI_SUMMARY_MODEL` (defaults to
`HuggingFaceH4/zephyr-7b-beta`). Requests target the Hugging Face router chat
completions endpoint (`https://router.huggingface.co/v1/chat/completions`). The
`/api/ai/status` endpoint reports current state; never expose the Hugging Face
token to the frontend.
