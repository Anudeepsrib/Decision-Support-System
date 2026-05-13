# KSERC DSS Frontend

Vite + React UI for the local MVP.

Install:

```bash
npm ci
```

Start:

```bash
npm start
```

Build:

```bash
npm run build
```

The frontend calls `http://127.0.0.1:8000/api` by default. To override it, create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```
