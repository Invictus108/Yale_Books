# Yale Books 📚💙

Yale Books is a Goodreads-style web app built **for Yale students only**.  
Log in with Yale CAS, track what you’re reading, rate & review books, follow other students, and discover new reads recommended just for you.

The app focuses on:

- A clean, Yale-inspired UI (whites + Yale Blue)
- Simple flows for **adding**, **finding**, and **tracking** books
- Social features limited to the Yale community (netid-based)

## Deploy the backend to Render

The repository includes `render.yaml` for the Python API; the frontend is hosted separately on Firebase. For an existing manually configured Render service, set:

- Root directory: `backend`
- Python: `3.12` via `.python-version`. Remove any conflicting `PYTHON_VERSION` environment override (or set it to a released 3.12 patch version).
- Build command: `pip install -r requirements.txt && python -c "from embeddings import get_model; get_model()"`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 180`
- Health check: `/healthz`
- Environment: `DATABASE_URL` (PostgreSQL), `SESSION_SECRET` (a random secret), `FRONTEND_URL=https://yalebooks-be079.web.app`, `FILEBASE_ACCESS_KEY`, and `FILEBASE_SECRET_KEY`.
- Set `HF_HOME=/opt/render/project/src/backend/.cache/huggingface` in both build and runtime so downloaded model files are included in the deployment. `ORIGIN` can override the backend public URL; otherwise Render's `RENDER_EXTERNAL_URL` is used.

Python 3.12 supports the pinned CPU PyTorch wheels. The model downloads during the build and loads on the first embedding request, so health checks do not wait for ML initialization. One worker avoids duplicate model copies; the service still needs enough RAM to load PyTorch and the model when recommendation requests arrive.

For a database created before the pgvector changes, back it up and run `backend/migrations/001_vector_embeddings.sql` once before deploying. This preserves embeddings while converting the old array column and adding the user vector column. Existing vectors must contain 384 elements. New databases enable the `vector` extension before creating tables; the database role must have permission to enable it. `create_all()` does not migrate existing columns.

For the frontend, run `npm ci` then `npm run build` from `frontend`. Production builds default to `https://yale-books.onrender.com`; set `VITE_API_URL` at build time for another backend. Local development defaults to `http://localhost:5000`. Login/logout links use the same backend URL. The CAS endpoints still point to Yale's test CAS service; use the institution-approved production CAS configuration when going live.

Run offline backend startup checks from `backend` with `python -m unittest test_deployment`. These use SQLite with schema creation mocked; they do not validate the production PostgreSQL schema or download the ML model.

Render references: [Python versions](https://render.com/docs/python-version), [Blueprint settings](https://render.com/docs/blueprint-spec), and [Postgres extensions](https://render.com/docs/postgresql-extensions).
