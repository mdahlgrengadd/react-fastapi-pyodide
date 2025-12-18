# Repository Guidelines

## Project Structure & Module Organization
- `src/frontend/`: React + Vite app (components, pages, routing). `public/` holds static assets plus the copied backend payload used by Pyodide.
- `src/backend/app/`: FastAPI service adapted for the browser (domains, `api/v1`, `core` bridge, `db`). Manage Python deps in `src/backend/requirements.txt`.
- `scripts/`: utility scripts for syncing backend files (`npm run copy-api`) and GitHub Pages flows; build artifacts land in `dist/`.
- `apps/`: packaged backend/frontend variants; prefer editing under `src/` and letting scripts propagate.
- `docs/`: additional design and architecture notes.

## Build, Test, and Development Commands
- `npm run dev:pyodide`: start Vite with Pyodide enabled after copying backend files.
- `npm run dev:gh-pages`: GitHub Pages–friendly dev preview.
- `npm run build:pyodide` / `npm run build:gh-pages`: production bundles (postbuild duplicates `index.html` to `404.html` when `GITHUB_PAGES=true`).
- `npm run preview:pyodide`: preview built assets on port 3000.
- `npm run lint`: ESLint for TypeScript/React.
- `python -m pytest src/backend/app/tests`: backend test suite; add `-m unit` or `-m integration` to focus markers.

## Coding Style & Naming Conventions
- TypeScript: follow ESLint defaults; prefer function components and hooks; components `PascalCase`, hooks `useCamelCase`, files mirror main export (`UserList.tsx`).
- Styling: Tailwind utility classes; keep class groups readable and avoid scattered inline styles.
- Python: format with `black` and `isort`; static checks with `flake8` and `mypy`; keep routing under `api/v1` and domain logic in `domains/<area>/`.
- Do not commit generated artifacts (`dist/`, `public/backend/`); rerun `npm run copy-api` when backend Python changes.

## Testing Guidelines
- Place pytest cases under `src/backend/app/tests`; mark scope with `@pytest.mark.unit` / `integration` / `e2e` as defined in `pytest.ini`.
- For new endpoints, cover request/response paths, auth/permission branches, and database interactions (mock external I/O).
- Run `npm run lint` before pushes; add lightweight React interaction checks or document manual steps when automated coverage is impractical.

## Commit & Pull Request Guidelines
- Commits: short imperative summaries (e.g., `Add service worker preload`); group related changes and keep noise low.
- PRs: include what/why, linked issues, commands executed, and screenshots/GIFs for UI updates; mention Pyodide steps (e.g., `npm run copy-api`) in the description when relevant.
