# ResolveAI

ResolveAI is a portfolio demonstration of an evidence-first customer-support
system for a fictional ShopEase store. It combines a FastAPI service, a
Streamlit presentation layer, PostgreSQL/Supabase, pgvector retrieval, and
Gemini-powered classification and response generation.

This repository is a synthetic demo. It does not provide real customer
authentication, live commerce integrations, or an enterprise production
readiness claim.

## What the demo shows

The application supports three customer scenarios:

1. **Policy/RAG** - retrieve approved policy chunks, generate a grounded
   answer, and return validated source citations.
2. **Verified order lookup** - select a synthetic customer, provide an order
   number, and return only fields from an order owned by that customer.
3. **Human escalation** - route unsupported or insufficiently grounded requests
   to an active support ticket without inventing compensation or policy rules.

The admin view supports login, ticket filtering and inspection, conversation and
evidence review, status changes, internal notes, and resolutions.

## Repository layout

```text
backend/
  app/
    ai/                 Gemini generation, embeddings, orchestration, schemas
    api/                FastAPI routers, dependencies, request/response schemas
    core/               settings, database engine, admin authentication
    models/             SQLAlchemy models and relationships
    rag/                chunking, loading, ingestion, retrieval, grounding
    services/           support workflow, order lookup, ticket operations
    tools/              tool declarations, validation, order lookup tool
  alembic/              database migrations
  knowledge_base/       approved policy Markdown documents
  scripts/              synthetic seed and knowledge ingestion commands
  tests/                backend tests
  .env.example          backend configuration template
frontend/
  app.py                Streamlit customer and admin interface
  api_client.py         HTTP-only client for the FastAPI API
  tests/                 frontend API-client tests
  .env.example          frontend configuration template
```

The repository contains virtual-environment directories in some working
copies. Use one fresh environment consistently; `.venv` is used in the
commands below.

## Prerequisites

- Python 3.11
- Git
- PostgreSQL with the `vector` extension. Supabase PostgreSQL is the intended
  persistent database.
- A Gemini API key with access to the configured generation and embedding
  models for live AI flows.
- PowerShell on Windows, or equivalent shell commands on another platform.

The backend dependency set is in
[backend/requirements.txt](backend/requirements.txt). It includes FastAPI,
Uvicorn, SQLAlchemy, psycopg, Alembic, pgvector, `google-genai`, Pydantic
through FastAPI, `pwdlib[argon2]`, PyJWT, pytest, and python-dotenv.

## Local setup

Run the following from the repository root.

### 1. Create a virtual environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Alternatively, invoke `.\.venv\Scripts\python.exe` directly without activating
the environment.

### 2. Configure the backend

Create a private backend environment file:

```powershell
Copy-Item backend\.env.example backend\.env
```

Set the values locally in `backend\.env`. Do not commit this file or paste
secret values into issue reports, logs, or documentation.

Required for database-backed operation:

```text
DATABASE_URL=postgresql+psycopg://user:password@host:5432/postgres?sslmode=require
```

Required for live AI operations:

```text
GEMINI_API_KEY=<your-key>
```

The template also defines:

| Variable | Purpose | Default |
| --- | --- | --- |
| `APP_ENV` | application environment label | `development` |
| `APP_NAME` | API application name | `ResolveAI API` |
| `API_PREFIX` | documented API prefix setting | `/api/v1` |
| `LOG_LEVEL` | logging preference | `INFO` |
| `DB_POOL_SIZE` | SQLAlchemy pool size | `2` |
| `DB_MAX_OVERFLOW` | additional connections | `1` |
| `DB_POOL_RECYCLE_SECONDS` | connection recycle interval | `1800` |
| `GEMINI_GENERATION_MODEL` | Gemini text-generation model | `gemini-3.5-flash-lite` |
| `GEMINI_EMBEDDING_MODEL` | Gemini embedding model | `gemini-embedding-001` |
| `EMBEDDING_DIMENSION` | pgvector/Gemini embedding dimension | `768` |
| `RAG_CHUNK_TOKEN_LIMIT` | maximum tokens per chunk | `1800` |
| `RAG_CHUNK_OVERLAP_TOKENS` | chunk overlap | `150` |
| `RAG_TOP_K` | retrieved chunk limit | `5` |
| `RAG_SIMILARITY_THRESHOLD` | optional minimum similarity | unset |

Admin authentication requires these additional values:

```text
ADMIN_USERNAME=<configured-admin-name>
ADMIN_PASSWORD_HASH=<Argon2 hash>
JWT_SECRET=<at-least-32-byte-secret>
JWT_EXPIRY_MINUTES=<positive-integer>
```

Generate the password hash and JWT secret locally. Do not put a plaintext
password in the repository:

```powershell
.\.venv\Scripts\python.exe -c "from pwdlib import PasswordHash; print(PasswordHash.recommended().hash(input('Password: ')))"
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

The backend loads `backend\.env` automatically through
`backend/app/core/config.py`.

### 3. Configure the frontend

The frontend template contains:

```text
BACKEND_API_URL=http://127.0.0.1:8000
```

Set it in the shell that will run Streamlit:

```powershell
$env:BACKEND_API_URL = "http://127.0.0.1:8000"
```

The Streamlit app stores the admin JWT only in Streamlit session state and
clears it on logout. It does not write credentials or tokens to disk.

### 4. Apply database migrations

From the repository root, inspect or apply Alembic migrations as appropriate
for the target database:

```powershell
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current
.\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
```

The current migration chain is:

```text
0001_initial_relational_schema
  -> 0002_add_embedding_vector (head)
```

The migrations create the relational schema, enable pgvector, and add the
768-dimensional embedding column. They are the only supported way to create or
upgrade the application schema.

### 5. Seed synthetic demo data

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.seed_database
```

The seed command creates 20 deterministic synthetic customers and deterministic
demo orders, including orders `SE1025`, `SE1026`, and `SE1027`. It is
idempotent for the seeded customer IDs and order numbers.

### 6. Ingest approved policy documents

Knowledge ingestion is deliberately separate from ordinary customer chat:

```powershell
.\.venv\Scripts\python.exe -m backend.scripts.ingest_knowledge
```

The script loads the five documents in `backend/knowledge_base/`:

- `return_policy.md`
- `refund_policy.md`
- `shipping_policy.md`
- `warranty_policy.md`
- `faq.md`

Ingestion chunks documents, creates normalized Gemini embeddings, persists
versioned documents and chunks, and marks the active version. Unchanged
documents are skipped based on content hash, embedding model/dimension, and
chunking configuration.

### 7. Start FastAPI

In one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

For diagnostic output from a single foreground process:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --log-level warning
```

Verify liveness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected result:

```text
status
------
ok
```

### 8. Start Streamlit

In a second terminal:

```powershell
$env:BACKEND_API_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m streamlit run frontend\app.py
```

Open the URL printed by Streamlit, normally
`http://localhost:8501`.

## API overview

The FastAPI application is registered in
[backend/app/main.py](backend/app/main.py) with the `/api/v1` prefix.

### Customer endpoints

Customer selection is a synthetic demo identity mechanism, not authentication.
Every conversation and message request is scoped to the selected customer.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/customers` | list synthetic demo customers |
| `POST` | `/api/v1/conversations` | create a conversation for an existing customer |
| `GET` | `/api/v1/customers/{customer_id}/conversations` | list that customer’s conversations |
| `GET` | `/api/v1/customers/{customer_id}/conversations/{conversation_id}` | retrieve owned messages and latest ticket status |
| `POST` | `/api/v1/customers/{customer_id}/conversations/{conversation_id}/messages` | persist a message and run the support workflow |

Conversation creation and message schemas use UUID fields with `extra="forbid"`.
The backend verifies both customer and conversation ownership before returning
private conversation data or processing a message.

### Admin endpoints

Admin routes require a valid expiring JWT independently of Streamlit:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/admin/login` | authenticate the configured admin account |
| `GET` | `/api/v1/admin/me` | validate the current admin token |
| `GET` | `/api/v1/admin/tickets` | list tickets, optionally filtered by `status` |
| `GET` | `/api/v1/admin/tickets/{ticket_id}` | inspect ticket, conversation, events, and evidence |
| `PATCH` | `/api/v1/admin/tickets/{ticket_id}` | change status, add an internal note, or set a resolution |

Status changes, notes, and resolutions are recorded through `TicketEvent`.
Ticket status timestamps are maintained by the ticket service:

- `resolved` sets `resolved_at` and clears `closed_at`.
- `closed` preserves or sets `resolved_at` and sets `closed_at`.
- Other statuses clear both timestamps.

## Technical architecture

```text
Streamlit
  |
  | HTTP/JSON
  v
FastAPI routers
  |
  +-- customer ownership and request validation
  +-- admin JWT dependency
  +-- short database transactions
  |
  +--> Support workflow
  |      +--> Gemini intent extraction
  |      +--> Gemini query embedding
  |      +--> pgvector retrieval
  |      +--> grounded Gemini response and citation validation
  |      +--> verified order tool, when applicable
  |      +--> ticket and evidence persistence
  |
  +--> SQLAlchemy 2.x / psycopg
           |
           v
       PostgreSQL/Supabase + pgvector
```

### Backend and frontend split

FastAPI owns all business logic, validation, authorization boundaries,
database access, AI orchestration, retrieval, order verification, and ticket
updates. Streamlit is a presentation layer and uses only the API client in
`frontend/api_client.py`.

This split keeps the demo UI replaceable and prevents the frontend from
duplicating customer ownership checks, order filtering, citation validation, or
admin authorization.

### Gemini generation

The backend uses `google-genai` 3.3.0 through
[generation.py](backend/app/ai/generation.py). Structured generation uses:

```python
response_mime_type="application/json"
response_json_schema=response_model.model_json_schema()
```

The native `response_json_schema` path avoids the SDK typed-schema conversion
that can serialize unsupported `additional_properties` fields. The returned
JSON is still validated locally with:

```python
response_model.model_validate_json(text)
```

The response models use Pydantic `extra="forbid"` and, where defined, strict
validation. Gemini failures are wrapped as controlled `GenerationError`
instances; the API exposes only a generic safe failure response. Server-side
diagnostic logging records bounded provider metadata and does not expose
credentials or prompts.

### Retrieval-augmented generation

The implemented RAG pipeline is:

1. Load approved Markdown policy documents.
2. Tokenize and chunk them with the configured limit and overlap.
3. Generate and normalize Gemini embeddings.
4. Store versioned documents and chunks in PostgreSQL with pgvector vectors.
5. Embed a customer policy query only when policy retrieval is needed.
6. Query active chunks using pgvector cosine distance and `RAG_TOP_K`.
7. Classify evidence against `RAG_SIMILARITY_THRESHOLD`.
8. Stop safely when evidence is insufficient.
9. Include retrieved chunk IDs and excerpts in the grounded response prompt.
10. Validate every generated citation against the retrieved UUIDs.

`validate_grounded_response()` in
[orchestration.py](backend/app/ai/orchestration.py) rejects:

- missing or empty citations;
- malformed UUID citation IDs;
- IDs that were not in the current retrieval result;
- citation metadata that does not validate against the trusted retrieved data.

The current implementation is vector similarity retrieval through pgvector. It
does **not** implement a separate lexical keyword index or true hybrid
keyword-plus-vector search; this README does not claim that it does.

### Data ingestion and database

SQLAlchemy 2.x uses synchronous psycopg connections to PostgreSQL/Supabase.
The engine enables:

- `pool_pre_ping=True` for stale connection detection;
- connection recycling;
- small configurable pool and overflow limits suitable for a free tier.

Alembic manages schema changes. The database contains customers, orders,
conversations, messages, tickets, ticket events, knowledge documents, document
chunks, ticket evidence, knowledge gaps, and the knowledge-gap/ticket
many-to-many table.

Ingestion uses content hashes, document versions, embedding configuration
metadata, active-document uniqueness, chunk uniqueness, foreign keys, and
transactional persistence. AI and embedding calls are not performed during
ordinary customer chat except for the required query embedding.

Customer message processing uses separate transaction boundaries:

1. Validate ownership.
2. Persist and commit the customer message.
3. Construct AI clients.
4. Run Gemini, embedding, retrieval, and business logic.
5. Persist the assistant response, ticket, events, and evidence.

This preserves the customer message if an external AI call fails.

### Tool calling

The order tool is registered by
[order_lookup.py](backend/app/tools/order_lookup.py) and dispatched through
[registry.py](backend/app/tools/registry.py).

Tool declarations use:

```python
parameters_json_schema=arguments_model.model_json_schema()
```

This is the Gemini SDK’s native JSON Schema parameter path. The model may
provide an `order_number`, but the backend injects the trusted selected
`customer_id` into `get_customer_order()`. The model cannot choose the
customer identity. Missing or cross-customer orders return a safe not-found
result rather than another customer’s data.

## Evidence-first and escalation design

### Evidence-first answers

Policy answers are grounded in the approved knowledge corpus. Source titles,
chunk text, document IDs, and chunk IDs come from trusted retrieval data, not
from model-generated citation metadata. If evidence does not meet the
configured threshold, the system declines to make a policy claim and offers
human support.

### Knowledge gaps

The schema includes `knowledge_gaps` and the
`knowledge_gap_tickets` many-to-many relationship for future operational
tracking. The current customer workflow creates and reuses deterministic
support tickets for unsupported or insufficiently grounded requests, but this
MVP does not implement a knowledge-gap management UI or an approved-answer
publication workflow.

### Investigation-first escalation

Escalated tickets preserve the available handoff context:

- escalation reason;
- conversation and customer association;
- retrieved policy evidence snapshots when applicable;
- ticket status history;
- admin notes and resolution events.

This produces an inspectable handoff for the admin dashboard. It is a compact
demo workflow, not a full workforce-management or case-assignment system.

## Security and safety boundaries

- Customer identity is explicitly synthetic selection, not authentication.
- Every customer conversation query is scoped by both customer ID and
  conversation ID.
- Order lookup is customer-scoped in backend service logic.
- Admin routes independently require a signed, expiring JWT.
- Admin credentials are configured through environment variables; no admin
  table is used.
- Password hashes must use Argon2 through `pwdlib`.
- Request models reject unexpected fields where configured.
- Gemini structured outputs are validated by Pydantic before use.
- Citation IDs are checked against trusted retrieval results.
- Unsupported policy requests do not receive invented compensation or policy
  details.
- AI failures do not remove an already committed customer message.
- Streamlit does not log or persist passwords or JWTs.

## Testing

Run the backend tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Database-dependent tests use `TEST_DATABASE_URL` only and skip when that
isolated test database is unavailable. They must not fall back to
`DATABASE_URL`, Supabase, or production data.

Frontend API-client tests can be run with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q frontend\tests
```

The test suite covers customer ownership, conversation and message workflows,
policy grounding and citation validation, order ownership, ticket reuse and
evidence, admin authentication and ticket operations, schema rejection, AI
failure persistence, and frontend HTTP error handling.

## Free-tier and deployment notes

- Free database and hosting tiers can impose connection, storage, execution,
  and request-rate limits.
- Render-style deployments should use a PostgreSQL connection URL with SSL,
  conservative pool settings, `pool_pre_ping`, and recycling. The current
  defaults are intentionally small.
- Cold starts can delay the first FastAPI or Streamlit request.
- Gemini quotas and transient provider failures can interrupt live AI flows.
- Knowledge ingestion is an explicit operational command and should not run
  concurrently with customer traffic without an operational plan.
- The application has no background job queue, distributed lock, assignment
  system, analytics pipeline, or production secrets manager.
- Supabase/PostgreSQL and Gemini availability are external prerequisites for
  live demonstrations.

The deployment configuration is intentionally minimal. Before any hosted
deployment, configure secrets through the platform’s secret store, apply
Alembic migrations deliberately, verify the vector extension, and use an
isolated database for tests.



### Why split FastAPI and Streamlit?

FastAPI provides a stable API boundary for validation, authorization,
transactions, and integration tests. Streamlit makes the final demonstration
quick to operate without moving business logic into UI callbacks. The trade-off
is an additional HTTP hop and the need to keep frontend response handling
aligned with backend schemas.

### How is tool calling controlled?

Gemini receives an allowlisted function declaration for the order lookup tool.
Its parameters use the SDK-native `parameters_json_schema` field. The model
can identify an order number, but customer ownership is supplied by trusted
backend context. The handler calls the existing order service and returns only
approved order fields.

### How is hallucination reduced?

Retrieval supplies the policy context and exact chunk UUIDs. The model must
return citation IDs, and the backend verifies each one against the current
retrieval result before exposing citation data. Threshold failure bypasses
grounded generation and returns a safe insufficiency response.

### What is deterministic versus probabilistic?

Gemini handles intent extraction, structured response drafting, query
embeddings, and tool selection. Deterministic application code handles customer
ownership, order ownership, allowlisted tool dispatch, retrieval thresholds,
citation validation, ticket reuse, transaction boundaries, timestamps, and
API authorization.

### Where are the security boundaries?

Pydantic request schemas validate API inputs. Admin authentication is verified
in FastAPI dependencies rather than trusted from Streamlit. Customer and order
scope are enforced by backend queries. AI output is treated as untrusted until
validated against typed schemas, retrieved UUIDs, and deterministic business
rules. Unsupported paths are quarantined into human-review tickets instead of
being answered with speculative policy.

### What are the trade-offs?

The design favors traceability and predictable behavior over open-ended agent
autonomy. It uses synchronous database and AI calls for a small demonstration,
which simplifies reasoning but limits throughput. A single configured admin and
synthetic customer selector are appropriate for the portfolio demo but are not
substitutes for real identity, authorization administration, audit governance,
or production customer integrations.

## Scope and limitations

ResolveAI currently does not claim:

- real customer registration or login;
- live payment, shipping, warranty, or commerce-provider integrations;
- production-grade identity, tenant isolation, or secret management;
- lexical hybrid search;
- automated knowledge-gap publication;
- advanced assignment, analytics, queues, or concurrency architecture;
- guaranteed availability under provider or free-tier limits.

Use synthetic data only when demonstrating the application.
