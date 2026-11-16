# ResolveAI Backend

This directory contains the FastAPI application and Phase 2 relational
database setup.

## Supabase setup

Create a free Supabase project manually before running migrations:

1. Create the project and keep the database password private.
2. Enable the `vector`/`pgvector` extension under Database > Extensions.
3. Open **Connect** in the Supabase dashboard.
4. Choose **Session pooler** for the persistent synchronous backend
   connection. It is the IPv4-compatible pooled option.
5. Copy the complete PostgreSQL connection string and replace the
   password placeholder locally. URL-encode reserved password
   characters.
6. Create `backend/.env` from `backend/.env.example`.
7. Set `DATABASE_URL` to the connection string and keep SSL enabled.

Do not paste credentials into chat, print them in logs, or commit
`backend/.env`.

For local Alembic migrations, Supabase documents the direct connection
as the native PostgreSQL option. If the local network cannot use IPv6,
the session pooler may be used instead. The Phase 2 database engine uses
small pool settings, `pool_pre_ping`, and connection recycling.

## Apply the Phase 2 schema

Only run these commands after `backend/.env` is configured and the
Supabase project is ready:

```powershell
.\.venv\Scripts\Activate.ps1
python -m alembic -c backend\alembic.ini upgrade head
python -m backend.scripts.seed_database
```

The migration creates the relational schema and enables pgvector, but
does not create an embedding vector column. The vector dimension is
intentionally deferred until the Phase 3 embedding decision.

The seed script creates deterministic synthetic customers and orders,
including `SE1025`, `SE1026`, and `SE1027`. Existing matching records
are preserved and are not overwritten.

## Run locally

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`, and the health check is
available at `http://127.0.0.1:8000/health`.

Database, Gemini, authentication, RAG, and ticket functionality are
intentionally not included in this local API stage. Ticket tables and
historical evidence storage are defined in the Phase 2 schema, but
ticket workflows remain a later phase.
