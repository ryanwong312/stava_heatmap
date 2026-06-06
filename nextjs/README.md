Next.js + Tailwind + SQLite scaffold

This is a minimal scaffold demonstrating API endpoints for importing GPX files and listing activities stored in a local SQLite DB (`next_data.sqlite`).

Install:

```bash
cd nextjs
npm install
npm run dev
```

Notes:
- The `/api/import` route supports simple GPX parsing only (no FIT support in this scaffold).
- Uses `better-sqlite3` for a small embedded DB.
- Frontend is a minimal Leaflet map initialized in `pages/index.js`.
