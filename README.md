# Yale Books 📚💙

Yale Books is a Goodreads-style web app built **for Yale students only**.  
Log in with Yale CAS, track what you’re reading, rate & review books, follow other students, and discover new reads recommended just for you.

The app focuses on:

- A clean, Yale-inspired UI (whites + Yale Blue)
- Simple flows for **adding**, **finding**, and **tracking** books
- Social features limited to the Yale community (netid-based)

## Deployment (Coolify)

One deployment path, so nothing can disagree with anything else: a single
container built from `backend/Dockerfile` serves both the API and the frontend
from the same origin.

Coolify settings:

| Field | Value |
| --- | --- |
| Build Pack | Dockerfile |
| Base Directory | `backend` |
| Dockerfile Location | `Dockerfile` |
| Build / Start Command | *(empty - the Dockerfile supplies both)* |
| Ports Exposes | `3000` |
| Health Check Path | `/healthz` |

Environment variables: `DATABASE_URL`, `SESSION_SECRET`, `ORIGIN=https://your-domain`,
`FILEBASE_ACCESS_KEY`, `FILEBASE_SECRET_KEY`. `DEMO_LOGIN` defaults to `true` in the
image while CAS is down; set it to `false` in Coolify to restore CAS-only login.

Because the build context is `backend/`, the frontend cannot be built inside the
image. **Rebuild it before any deploy carrying UI changes:**

```
cd frontend && npm run build:backend      # writes ../backend/static
```

Then commit `backend/static/` along with your changes.

### Same-origin serving

Flask serves `backend/static` for any path its own routes do not claim, falling
back to `index.html` so client-side routes work on refresh. Because the app and
API share an origin, the session cookie is first-party (`SameSite=Lax`) and no
CORS configuration is needed. All post-login redirects are relative.

### Database

New databases: `create_all()` builds the schema, and the `vector` extension is
enabled at startup, so the Postgres role needs permission to run
`CREATE EXTENSION vector`.

Existing databases predating the pgvector change: `create_all()` does **not**
migrate existing tables. Back up, then run `backend/migrations/001_vector_embeddings.sql`
once before deploying. Existing book embeddings must contain exactly 384 values;
the migration runs in a transaction and rolls back if they do not.

### Notes

- The embedding model loads lazily and needs roughly 800 MB resident once a
  recommendation, review, or bio request touches it. Size the host accordingly.
- CAS still points at Yale's **test** endpoints (`secure-tst.its.yale.edu`). The
  service URL is derived from `ORIGIN` and must match exactly what Yale ITS has
  registered. A CAS failure redirects to `/?login_error=...` rather than 500ing.
- Offline startup checks: `cd backend && python -m unittest test_deployment`.

## Local development

```
cd backend  && python app.py          # http://localhost:5000
cd frontend && npm run dev            # http://localhost:5173, proxies to :5000
```
