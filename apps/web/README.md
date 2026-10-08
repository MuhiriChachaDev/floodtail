# FLOODTAIL Web

Kenya Re flood-risk intelligence UI for the Nairobi Urban Flood prototype.

## Run

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Sign in with any email/password (demo auth).

Optional: set `NEXT_PUBLIC_API_URL=http://localhost:8000` to read API health / AI status.

## Production (Vercel)

1. Import the monorepo in Vercel.
2. Set **Root Directory** to `apps/web`.
3. Env: `NEXT_PUBLIC_API_URL=https://api.YOUR_DOMAIN` (Contabo API).
4. Ensure that origin is listed in the VPS `CORS_ORIGINS`.

Full plan: [../../DEPLOYMENT.md](../../DEPLOYMENT.md).

## Journey

Login → Home (command centre) → Data → Risk Modelling → Finance → Decisions → AI, with cross-cutting controls in the footer.

Copy stays in plain language for underwriters and risk teams (problem-statement stakeholders). Demo portfolio markers are synthetic Nairobi buildings.
