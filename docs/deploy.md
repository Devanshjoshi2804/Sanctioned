# Deploying `sanctioned`

Two services ship independently:

| Service | What | Where |
|---|---|---|
| API | FastAPI engine (`packages/api`) | Any container host — Fly.io / Railway / Render |
| Dashboard | Next.js ops UI (`apps/dashboard`) | Vercel |

The dashboard talks to the API over HTTPS via the build-time env var
`NEXT_PUBLIC_API_URL`. **Deploy the API first**, note its URL, then point the
dashboard at it.

---

## 1. API — Fly.io (container)

The image is defined in [`deploy/Dockerfile.api`](../deploy/Dockerfile.api) and built
from the repo root. From `deploy/`:

```bash
fly auth login                       # run yourself: ! fly auth login
fly launch --copy-config --no-deploy # claim an app name + region (uses fly.toml)
fly deploy                           # builds Dockerfile.api, ships it
fly open /health                     # should return {"status":"ok","lenders":"4"}
```

Note the resulting URL, e.g. `https://sanctioned-api.fly.dev`.

### API — Railway (alternative)

```bash
railway login                        # run yourself: ! railway login
railway init
railway up --dockerfile deploy/Dockerfile.api
```

Railway injects `$PORT`; the Dockerfile already honours it.

---

## 2. Dashboard — Vercel

The dashboard is a standard Next.js app under `apps/dashboard`.

```bash
cd apps/dashboard
vercel login                         # run yourself: ! vercel login
vercel link                          # set "Root Directory" = apps/dashboard
vercel env add NEXT_PUBLIC_API_URL   # paste the API URL from step 1 (Production)
vercel --prod
```

In the Vercel dashboard, confirm the project **Root Directory** is `apps/dashboard`
and the env var `NEXT_PUBLIC_API_URL` is set for Production. Re-deploy after adding
the env var so it is baked into the client bundle.

---

## 3. Verify the live link

1. Open the Vercel URL.
2. Run the default borrower → the match grid and reason traces render.
3. Expand a lender → the audit ledger lists each rule's pass/fail.
4. Visit `/policy-diff`, run an impact replay.

The API's interactive OpenAPI docs are at `<api-url>/docs`.

> CORS on the API is currently open (`*`) for convenience. Before any non-demo use,
> restrict `allow_origins` in `packages/api/sanctioned_api/main.py` to the dashboard
> origin.
