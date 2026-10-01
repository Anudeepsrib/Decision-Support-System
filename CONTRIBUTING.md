# Contributing to Compass

Thanks for helping teams preserve better decision records.

## Before you start

- Open an issue for substantial product changes.
- Keep pull requests focused on one workflow or problem.
- Explain the user need, not only the implementation.
- Do not add dependencies when the browser or existing stack already solves the problem.

## Local checks

```bash
cd frontend
npm install
npm test
npm run build

cd ..
py -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt
.venv/Scripts/python -m unittest backend.test_app
```

## Template contributions

A useful template has a clear decision type, 3–6 criteria, weights totaling roughly 100, and wording that applies across organizations. Add the template to `frontend/src/decision.ts` and include a short example in the pull request.

## Pull requests

Include what changed, why it helps, and how you verified it. Screenshots are welcome for visible UI changes.
