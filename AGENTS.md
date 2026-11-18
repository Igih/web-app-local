# Repository Guidelines

## Project Structure & Module Organization

- `backend/` — FastAPI application. Routers live in `routers/`, database/validation logic in `models/` and `services/`, and shared helpers in `utils/`. The entrypoint is `main.py`.
- `frontend/` — Vue 3 + Vite single-page app. Reusable views are in `src/components/`, state in `src/stores/`, API calls in `src/services/`, and routing in `src/router/`.
- `nginx/` and `frontend/nginx.conf` — reverse-proxy and static-file configuration.
- `compose.yaml` — local Docker orchestration for PostgreSQL, FastAPI, and Nginx.
- `data/` — runtime PostgreSQL and dataset storage; do not commit generated contents.

## Build, Test, and Development Commands

- `docker compose up --build -d` — start the full stack.
- `cd frontend && npm install` — install frontend dependencies.
- `cd frontend && npm run dev` — start the Vite development server.
- `cd frontend && npm run build` — produce the production bundle in `frontend/dist`.
- `cd backend && python init_db.py` — create/refresh database tables and default users.
- `cd backend && uvicorn main:app --reload` — run the API locally for development.

## Coding Style & Naming Conventions

- Python: PEP 8, 4-space indentation, `snake_case` for modules, functions, and variables; `PascalCase` for Pydantic models.
- Vue/JavaScript: 2-space indentation, `camelCase` for variables and functions, `PascalCase` for `.vue` component files. Use `@` for imports from `src`.
- Keep API routes thin; place reusable database and business logic in `services/`.

## Testing Guidelines

No automated test suite is currently configured. If adding coverage, use `pytest` plus FastAPI's `TestClient` for backend tests and Vitest for Vue components. Place tests under `backend/tests/` and `frontend/src/**/*.test.js`, and name them after the module or behavior they verify.

## Commit & Pull Request Guidelines

- Write concise, imperative commit messages such as `fix: correct XML preview` or `feat: add folder switching`. Existing history mixes Chinese and English; new commits should be readable either way.
- Pull requests should explain what changed and why, link related issues when present, and include manual test steps.
- Include screenshots or short recordings for visible UI changes.

## Security & Configuration Tips

- Keep real secrets out of version control; rotate the example `SECRET_KEY` and database credentials before deployment.
- Prefer environment variables over hard-coded paths such as `/home/linux/Downloads`.
- Avoid committing `frontend/dist`, `backend/dist`, `__pycache__/`, or `data/`.
