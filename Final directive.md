# ResolveAI --- Final Project Directive

**Status:** Approved architecture\
**Project:** ResolveAI\
**Demo business:** ShopEase (fictional e-commerce company)\
**Primary goal:** Build a portfolio-grade, AI-powered customer-support
resolution system in a five-day development quest, using free-tier
services only.

------------------------------------------------------------------------

## 1. Purpose and authority of this document

This document is the authoritative technical and implementation
specification for ResolveAI.

-   `intent.md` explains the problem, users, product vision, scope, and
    success criteria.
-   `Final directive.md` defines how the project must be implemented.
-   If a proposed implementation conflicts with this directive, stop and
    explain the conflict before changing the design.
-   Do not silently introduce new technologies, features, architectural
    patterns, or paid services.
-   Do not generate the entire application in one response. Work phase
    by phase and file by file.
-   Do not proceed to the next phase until the user has reviewed and
    explicitly approved the current phase.

The approved Phase 0 architecture is frozen except for
provider-dependent decisions that must be verified during
implementation: the exact Gemini generation model, the exact Gemini
embedding model and dimension, and whether a local embedding fallback is
necessary.

## 2. Product definition

ResolveAI is not a generic FAQ chatbot. It is an AI-powered
customer-support operations system that investigates customer issues,
identifies knowledge gaps, prepares evidence-backed resolutions, and
manages human escalation.

It has two interfaces:

### 2.1 Customer support interface

A synthetic demo customer can:

-   Select a fictional customer identity.
-   Start or continue a support conversation.
-   Ask policy questions.
-   Ask about their own synthetic orders.
-   Provide missing information through follow-up questions.
-   Receive answers grounded in retrieved policy evidence or verified
    backend data.
-   Request human support.
-   See ticket or escalation status where appropriate.

### 2.2 Admin/support dashboard

A single configured admin can:

-   View and filter support tickets.
-   Inspect conversation history and AI investigation details.
-   Review extracted fields and verified order information.
-   Inspect retrieved policy evidence.
-   Review escalation reasons and suggested resolutions.
-   Edit, approve, or reject AI-drafted responses.
-   Assign tickets, add internal notes, and update ticket status.
-   Manage knowledge documents and versions.
-   Review recurring knowledge gaps.
-   Approve a knowledge-gap answer and publish it as an official
    knowledge document.

## 3. Non-negotiable product and safety rules

1.  Use fictional ShopEase data and synthetic customers/orders only.
    Never use real customer or patient data.
2.  Never invent an order, payment state, policy, eligibility result,
    refund, delivery event, or customer detail.
3.  Never allow the language model to execute SQL or access the database
    directly.
4.  All tools are explicit backend functions with validated inputs and
    controlled outputs.
5.  Deterministic backend logic, not the LLM, decides order ownership,
    return eligibility, warranty eligibility, ticket reuse, and
    escalation conditions.
6.  The LLM may extract, classify, summarize, and draft. Its outputs
    must be validated before they affect business operations.
7.  If required information is missing, ask a relevant follow-up
    question.
8.  If policy evidence is insufficient, do not guess. Record a knowledge
    gap and escalate when appropriate.
9.  An AI-generated guess must never become official knowledge
    automatically. An admin must approve the answer first.
10. No actual refunds, payments, cancellations that alter external
    systems, or financial transactions will be performed.
11. No real e-commerce, payment gateway, CRM, or external helpdesk
    integration is included in the MVP.
12. Never silently fall back to a paid model or provider.

## 4. Approved technology stack

### Backend

-   Python 3.11 or a compatible version supported by the selected
    hosting environment.
-   FastAPI.
-   Pydantic v2.
-   SQLAlchemy 2.x, synchronous style.
-   `psycopg` PostgreSQL driver.
-   Alembic migrations.
-   Uvicorn.
-   `python-dotenv` or an equivalent environment-based settings
    approach.
-   `pwdlib[argon2]` for admin password verification.
-   PyJWT for signed, expiring admin tokens.

### Database and retrieval

-   Supabase PostgreSQL is the only persistent application database.
-   PostgreSQL `pgvector` extension for vector retrieval.
-   SQLAlchemy models and Alembic migrations.
-   Do not add a second database or a separate vector database.

### AI

-   Official Google Gen AI Python SDK.
-   Gemini for structured extraction, response generation, and
    controlled function calling, subject to verified free-tier
    availability.
-   A small custom Python RAG implementation.
-   No LangChain, LangGraph, autonomous multi-agent framework, or
    additional orchestration framework in the MVP.

### Frontend

-   Streamlit.
-   Python API client calling the FastAPI backend over HTTP/HTTPS.
-   Keep the frontend lightweight. It must not connect directly to
    Supabase or Gemini.

### Testing and utilities

-   pytest.
-   FastAPI TestClient.
-   Mock Gemini calls in automated tests.
-   `httpx` for HTTP client/testing where needed.
-   Standard Python logging.

### Hosting and source control

-   GitHub free plan.
-   Render free web service for FastAPI.
-   Streamlit Community Cloud for Streamlit.
-   Supabase free tier for PostgreSQL.
-   Google AI Studio/Gemini free tier, only where current eligibility
    and quotas are verified.

### Explicitly excluded

Do not introduce React, Node.js, Docker, Redis, Celery, Kafka,
Kubernetes, Qdrant, Pinecone, Weaviate, Airflow, dbt, LangChain,
LangGraph, paid hosting, paid APIs, or a local PostgreSQL runtime unless
the user explicitly approves a documented change.

## 5. High-level architecture

``` text
Synthetic Customer Selector
          |
          v
   Streamlit Frontend
          |
       HTTP/HTTPS
          |
          v
     FastAPI Backend
       /        \
      v          v
 AI / RAG     Business Services
   Layer      Orders, tickets,
      |       conversations,
      v       policy decisions
  Gemini          |
      \           /
       \         /
        v       v
    Supabase PostgreSQL
      |              |
 Relational data   pgvector
```

The frontend is a presentation layer only. The backend owns validation,
authorization boundaries, business rules, AI orchestration, database
access, and ticket lifecycle.

## 6. Identity and authentication

### 6.1 Synthetic customer identity

-   The customer selector is a public demo identity mechanism, not
    authentication or authorization.
-   No customer registration or login is implemented.
-   Customer IDs sent by Streamlit are untrusted input.
-   The backend must verify that a selected customer exists.
-   Every conversation is associated with the selected synthetic
    customer.
-   Every order-related backend operation must receive both
    `customer_id` and `order_id`.
-   Query the order using both identifiers or otherwise explicitly
    verify ownership before returning any order details.
-   An order belonging to another customer must be treated as
    unavailable.
-   Apply ownership checks to order lookup, order status, return
    eligibility, warranty checks, customer history, and every future
    order-related tool.
-   Never rely on the frontend selector to enforce ownership.

Document prominently in the README and demo that this is not suitable
for real customer data or production customer authentication.

### 6.2 Admin authentication

-   Configure exactly one admin account through environment variables.
-   Do not create an `admin_users` table.
-   Store an Argon2 password hash, not a plaintext password.
-   Generate the password hash locally through a script or documented
    command.
-   Use PyJWT to issue signed tokens with an explicit expiry.
-   Restrict accepted signing algorithms; do not trust an algorithm
    supplied by the token header.
-   Keep the JWT secret and admin credentials outside source control.
-   Protect every admin API endpoint independently in FastAPI. Do not
    treat a hidden Streamlit page as security.
-   Do not log passwords, tokens, API keys, or secrets.
-   This is a small portfolio-demo authentication implementation, not
    enterprise identity management.

## 7. Database design

Use UUID primary keys unless a strong implementation reason supports
another consistent choice. Use timezone-aware timestamps. Define
explicit foreign keys, indexes, uniqueness constraints, nullability, and
deletion behavior. Use SQLAlchemy relationships deliberately; avoid
circular import problems through a clear model registration pattern.

### 7.1 Core tables

#### `customers`

Synthetic customer records.

Suggested fields:

-   `id`
-   `name`
-   `email` (unique synthetic email)
-   `created_at`
-   `updated_at`

#### `orders`

Synthetic orders.

Suggested fields:

-   `id`
-   `order_number` (unique public identifier such as `SE1025`)
-   `customer_id` FK
-   `product`
-   `category`
-   `quantity`
-   `total_amount`
-   `currency`
-   `order_status`
-   `payment_status`
-   `payment_method`
-   `payment_reference` (synthetic only)
-   `order_date`
-   `shipping_date`
-   `delivery_date`
-   `created_at`
-   `updated_at`

Use controlled values for order and payment statuses. Do not infer an
order status from free text.

#### `conversations`

-   `id`
-   `customer_id` FK
-   `status`
-   `created_at`
-   `updated_at`

A conversation belongs to one synthetic customer.

#### `messages`

-   `id`
-   `conversation_id` FK
-   `sender_type` (controlled values such as customer, assistant,
    system)
-   `content`
-   `created_at`

Preserve conversation order using timestamps and a stable identifier.

#### `tickets`

Suggested fields:

-   `id`
-   `ticket_number` (unique human-readable identifier)
-   `conversation_id` FK
-   `customer_id` FK
-   `order_id` nullable FK
-   `category`
-   `issue_type`
-   `issue_key`
-   `priority`
-   `status`
-   `escalation_reason`
-   `assigned_team`
-   `ai_summary`
-   `extracted_information` (JSONB)
-   `ai_suggested_resolution`
-   `ai_draft_response`
-   `final_response`
-   `requires_human_review`
-   `created_at`
-   `updated_at`
-   `resolved_at`
-   `closed_at`

Use controlled values for statuses, priorities, categories, and issue
types. Keep ticket status transitions explicit and validated.

#### `ticket_events`

Audit significant ticket changes.

Suggested fields:

-   `id`
-   `ticket_id` FK
-   `event_type`
-   `old_value` (nullable)
-   `new_value` (nullable)
-   `internal_note` (nullable)
-   `created_at`

#### `knowledge_documents`

Each row represents one immutable version of a logical knowledge
document.

Suggested fields:

-   `id`
-   `document_key` (stable logical identifier, e.g. `shipping_policy`)
-   `title`
-   `filename`
-   `category`
-   `content`
-   `content_hash`
-   `version`
-   `embedding_model`
-   `embedding_dimension`
-   `embedding_configuration` (JSONB or equivalent)
-   `is_active`
-   `created_at`
-   `updated_at`

Constraints:

-   `UNIQUE(document_key, version)`.
-   A partial unique index allows only one active row per logical
    document: `UNIQUE(document_key) WHERE is_active = true`.
-   New versions receive new IDs.
-   Old versions are archived with `is_active = false`; do not routinely
    delete historical documents.
-   A document version's content and embedding configuration must not be
    silently mutated after publication. Create a new version instead.

#### `document_chunks`

Suggested fields:

-   `id`
-   `document_id` FK to the exact `knowledge_documents` version
-   `chunk_index`
-   `chunk_text`
-   `metadata` (JSONB)
-   `embedding` (pgvector column, added only after model/dimension
    verification)
-   `created_at`

Use a uniqueness constraint such as `(document_id, chunk_index)`. Index
the document foreign key and add the appropriate vector index only after
choosing a compatible distance operator and index strategy. Do not guess
vector dimensions.

#### `ticket_policy_evidence`

Immutable historical snapshots of evidence used in an investigation.

Required fields:

-   `id`
-   `ticket_id` FK, required
-   `document_id` nullable FK to the exact document version,
    `ON DELETE SET NULL`
-   `chunk_id` nullable FK, `ON DELETE SET NULL`
-   `document_title` required snapshot
-   `chunk_text` required snapshot
-   `similarity_score` nullable
-   `evidence_classification` required
-   `created_at`

The title and text snapshot must remain readable even if the original
document or chunk is later removed. Do not depend solely on foreign-key
references for historical evidence.

#### `knowledge_gaps`

Suggested fields:

-   `id`
-   `normalized_question`
-   `example_question`
-   `category`
-   `occurrence_count`
-   `status` (e.g. open, under_review, resolved)
-   `approved_answer` nullable
-   `created_at`
-   `updated_at`

#### `knowledge_gap_tickets`

Many-to-many association table:

-   `knowledge_gap_id` FK
-   `ticket_id` FK
-   `created_at`

Use composite primary key `(knowledge_gap_id, ticket_id)` and cascade
deletion of association rows when either parent is deleted. This does
not imply deleting the underlying ticket or knowledge gap when the other
is deleted.

### 7.2 Relationships and indexes

-   Define foreign keys and deletion rules explicitly.
-   Add indexes for common lookups: customer/order number, customer
    orders, conversation messages, ticket status/created date, ticket
    issue key, document key/active state, and evidence references.
-   Ensure `ticket_policy_evidence.ticket_id` has an index.
-   Add the required partial unique indexes for active documents and
    active tickets.
-   Do not create redundant indexes without a query/use-case reason.
-   Avoid cascading deletion of historical tickets, messages, or
    evidence as a convenience.

## 8. Ticket matching and duplicate prevention

### 8.1 Controlled classifications

Categories:

-   `shipping`
-   `returns`
-   `refunds`
-   `warranty`
-   `defective_product`
-   `payment`
-   `cancellation`
-   `other`

Issue types:

-   `delayed_delivery`
-   `missing_package`
-   `defective_product`
-   `damaged_product`
-   `incorrect_item`
-   `duplicate_payment`
-   `refund_delay`
-   `cancellation`
-   `unknown`

Validate extracted values against these allowlists. Normalize values to
lowercase snake_case. Invalid or missing values must map to safe
deterministic values such as `other` and `unknown`.

### 8.2 Canonical issue key

Build a canonical payload from these fields in a fixed order:

1.  `conversation_id`
2.  Verified `order_id`, or the literal `no_order`
3.  Normalized category
4.  Normalized issue type

Serialize deterministically and hash with SHA-256 to produce
`issue_key`. Do not use an unverified order ID from the LLM or frontend.

### 8.3 Active-ticket rule

Active statuses:

-   `open`
-   `pending_human_review`
-   `assigned`
-   `in_progress`

A PostgreSQL partial unique index on `issue_key` for active statuses
must prevent two active tickets for the same canonical issue.

-   Lookup and creation must be transaction-safe.
-   Handle a uniqueness conflict by retrieving the already-existing
    active ticket.
-   Repeated human-support requests for the same unresolved issue reuse
    its ticket.
-   Different issue types or categories for the same order produce
    distinct keys.
-   Resolved or closed tickets do not block a new later issue.
-   Do not merge uncertain cases merely because both were classified
    `other`/`unknown`. Use a conservative fallback: ask a clarifying
    question or create a separately reviewed issue rather than
    confidently merging unrelated problems.
-   Do not introduce semantic similarity matching for the MVP.

## 9. ShopEase policy knowledge base and RAG

Create a small, internally consistent, explicitly fictional policy
corpus:

-   `return_policy.md`
-   `refund_policy.md`
-   `shipping_policy.md`
-   `warranty_policy.md`
-   `faq.md`

The policies must agree with each other. Do not invent policy details in
customer responses that are absent from the approved documents.

### 9.1 RAG pipeline

1.  Load active document versions.
2.  Split documents into manageable chunks while retaining document key,
    version, title, category, and chunk index metadata.
3.  Generate embeddings using the selected and verified embedding model.
4.  Store vectors in Supabase PostgreSQL with pgvector.
5.  Embed a customer query only when retrieval is needed.
6.  Retrieve the most relevant active chunks.
7.  Apply a relevance threshold or other explicit insufficient-evidence
    rule.
8.  Pass retrieved excerpts and source metadata to Gemini.
9.  Require the response to use the supplied evidence and identify
    source titles.
10. Persist evidence snapshots when an investigation/ticket requires
    historical traceability.

Do not return a source citation that was not actually retrieved. Do not
treat a high similarity score alone as proof that a policy supports a
claim.

### 9.2 Insufficient evidence

If no sufficiently relevant evidence is found:

-   Do not guess or fabricate a policy.
-   Ask a follow-up if the question is ambiguous or required information
    is missing.
-   Otherwise create or update a knowledge gap.
-   Escalate to human support when the case requires a human decision or
    the customer requests it.
-   Explain clearly that the system cannot verify the answer from the
    current policy information.

## 10. Knowledge document versioning and safe ingestion

Ingestion is a separate CLI/script operation, never part of ordinary
customer chat.

### 10.1 Version identity

Use a stable `document_key` for each logical document. Every version is
a separate `knowledge_documents` row with its own ID, content hash,
embedding model/configuration, dimension, and chunks.

### 10.2 Skip conditions

Skip ingestion only if all relevant values match:

-   Document content hash.
-   Embedding model and version.
-   Embedding dimension.
-   Relevant embedding configuration.
-   Chunking configuration/version, if it affects stored chunks.

If the embedding model, dimension, or relevant configuration changes,
re-embed all affected documents even if the text has not changed.

### 10.3 Atomic replacement

1.  Read the source document and compute its hash.
2.  Determine the exact embedding configuration.
3.  Skip only if content and all relevant processing configuration are
    unchanged.
4.  Generate new chunks and embeddings outside the replacement
    transaction.
5.  Validate embedding results, vector dimensions, and chunk counts.
6.  Begin a database transaction.
7.  Insert the new document version and its chunks.
8.  Mark the previous version inactive.
9.  Mark the new version active.
10. Commit atomically.

If generation, validation, or database work fails, roll back the new
records and keep the previous active version searchable. Do not delete
old searchable chunks before replacements are ready.

For a database transaction failure, ensure the old active version
remains active. Preserve historical versions and ticket evidence. Do not
routinely delete archived document versions.

An approved knowledge-gap answer must first be saved as an official
knowledge document, then ingested through this process. Only after
successful publication should the gap be marked resolved.

## 11. Gemini integration and cost controls

Before selecting a Gemini model, verify current official documentation
and actual API behavior for:

-   Generation model availability.
-   Structured output/function-calling support.
-   Free-tier eligibility in the user's region/account.
-   Current request and token quotas.
-   Embedding model availability.
-   Embedding dimensions and supported configuration.
-   SDK request/response format.

Do not assume model names, quotas, or free-tier availability based on
old examples.

### 11.1 Model decision and vector migration

-   Do not finalize the vector dimension until the embedding model has
    been verified.
-   Phase 2 may create the relational schema and `document_chunks` table
    without a vector column.
-   Enable the pgvector extension before creating a vector column.
-   Between Phase 2 and Phase 3, verify the embedding model, dimension,
    configuration, and a real API response.
-   Then create a dedicated Alembic migration adding the vector column
    with the verified dimension.
-   Only after that migration succeeds may knowledge ingestion begin.
-   Never mix vectors from different embedding models/configurations in
    the same vector index.

### 11.2 Free-tier restrictions

-   Do not enable paid billing for this project.
-   Do not call paid Gemini models.
-   Do not automatically switch to a paid model or another provider.
-   Do not silently fall back to paid usage.
-   Use bounded retries only for transient failures.
-   Stop promptly on quota/billing errors and show a clear
    service-unavailable message.
-   Do not retry indefinitely.
-   Avoid repeatedly retrying failed embedding operations.
-   Cache embeddings and skip unchanged content/configuration.
-   Keep the dataset and policy corpus small.
-   Mock Gemini in automated tests.

If Gemini embeddings are unavailable or unsuitable, pause and present a
local open-source embedding option with its model size, memory/startup
implications, hosting feasibility, and migration consequences. Do not
switch without the user's explicit approval. Do not assume the local
model will fit Render's free memory limits.

## 12. Business tools and deterministic rules

Implement explicit backend functions for only the tools required by the
MVP, such as:

-   Customer-scoped order lookup.
-   Customer-scoped order status.
-   Payment status lookup (read-only synthetic data).
-   Return eligibility evaluation.
-   Warranty eligibility evaluation.
-   Ticket creation/reuse.
-   Customer conversation/history lookup, scoped to the selected
    synthetic customer.

The LLM may request a tool call, but the backend must:

1.  Validate tool name and arguments.
2.  Validate IDs and types.
3.  Verify customer/order ownership.
4.  Execute only an allowlisted backend function.
5.  Apply deterministic business rules.
6.  Return a minimal, structured result to the AI layer.

Never expose arbitrary database queries, raw SQL execution, unrestricted
Python execution, or unrestricted function dispatch to the model.

Return eligibility and warranty decisions must be deterministic
functions based on verified order fields and the fictional policy rules.
The LLM can explain the result but cannot override it.

## 13. Escalation and customer-support workflow

Escalate or require human review for cases such as:

-   Explicit customer request for a human.
-   Payment dispute or suspicious/ambiguous payment issue.
-   Policy exception or discretionary compensation request.
-   Unsupported question that requires a business decision.
-   Insufficient policy evidence where a reliable answer cannot be
    given.
-   Repeated unresolved interaction or clear customer frustration.
-   Any action that would require human approval.

Low-risk policy questions may be answered automatically only when
retrieved evidence is sufficient and the response is grounded.

A ticket should preserve, as applicable:

-   Conversation and message history.
-   AI summary.
-   Validated extracted fields.
-   Verified order information.
-   Retrieved policy evidence snapshots.
-   Escalation reason.
-   Suggested resolution.
-   Draft customer response.
-   Human decisions and ticket events.

Do not perform an actual refund or payment action.

## 14. Knowledge-gap workflow

-   Normalize and group recurring unsupported questions conservatively.
-   Track occurrence count and related tickets.
-   Show open and under-review gaps in the admin dashboard.
-   Allow an admin to write or approve an answer.
-   Save the approved answer as an official versioned knowledge
    document.
-   Run the ingestion command.
-   Verify retrieval of the newly approved content.
-   Mark the gap resolved only after successful publication.
-   Never automatically promote an AI-generated guess to official
    policy.

## 15. API and frontend requirements

Use a versioned API prefix such as `/api/v1`.

The API should be organized into focused routers. Exact endpoint names
may be proposed during implementation, but the required capabilities
include:

### Customer endpoints

-   List/select synthetic demo customers.
-   Create or continue a customer-scoped conversation.
-   Submit a message and receive a response.
-   Retrieve conversation messages.
-   Retrieve customer-scoped ticket status where needed.

### Admin endpoints

-   Admin login.
-   Ticket list/filter/detail.
-   Ticket assignment and status updates.
-   Add internal notes.
-   Approve/edit/reject suggested resolutions.
-   Knowledge document list/version management.
-   Knowledge-gap list/detail/approval.

All admin endpoints must independently enforce authentication.

### Streamlit pages

-   Customer support page with synthetic customer selector and chat.
-   Admin dashboard with login.
-   Ticket inbox and ticket investigation detail.
-   Knowledge base management.
-   Knowledge-gap management.

The frontend must call FastAPI through a small API client. It must not
contain database credentials or Gemini API keys. Use Streamlit
secrets/environment variables only for the backend API URL and admin
session/token handling required by the frontend. Do not store secrets in
source files.

Add loading states, clear API errors, bounded HTTP timeouts, and a
user-friendly message for a sleeping backend/cold start.

## 16. Testing requirements

Tests must not require live Gemini calls. Mock the AI client and test
deterministic behavior independently.

At minimum, test:

### Database and ownership

-   Customer exists/does not exist.
-   Customer can access their own order.
-   Customer cannot access another customer's order.
-   Every order-related tool enforces ownership.
-   Foreign keys and unique constraints behave as expected.

### Ticketing

-   Ticket creation for a new issue.
-   Reuse for repeated messages about the same issue.
-   Reuse for repeated human requests.
-   Different issue types for the same order create separate tickets.
-   Resolved/closed tickets do not block a new issue.
-   Concurrent creation cannot produce two active tickets for the same
    issue.
-   Uncertain `other`/`unknown` classifications do not blindly merge
    unrelated issues.

### RAG and ingestion

-   Chunking preserves metadata.
-   Embedding dimensions are validated.
-   Unchanged content/configuration is skipped.
-   Changed content creates a new version.
-   Changed embedding configuration triggers re-embedding.
-   Failed embedding generation leaves the old active version
    searchable.
-   Only one active version exists per document key.
-   Historical ticket evidence remains readable after document
    updates/archive.
-   Insufficient evidence does not produce a fabricated answer.
-   Approved knowledge-gap content is searchable after ingestion.

### Authentication and API

-   Valid admin login.
-   Invalid password rejection.
-   Expired/invalid token rejection.
-   Unauthorized admin endpoint access is rejected.
-   Customer endpoints cannot access admin functionality.

### AI orchestration

-   Invalid structured output is rejected or safely handled.
-   Unknown extraction values map to safe controlled values.
-   Tool calls are allowlisted and validated.
-   AI cannot override deterministic eligibility/escalation decisions.
-   Quota errors stop bounded retries and do not trigger paid fallback.

Use pytest and FastAPI TestClient. Use a test database/schema or
isolated test records; never run destructive tests against
production/demo data. Do not make tests depend on live free-tier quotas.

## 17. Environment variables and secrets

Maintain `.env.example` files containing variable names and safe
placeholders only. Never commit actual `.env` files.

Backend settings will likely include:

-   `DATABASE_URL`
-   `GEMINI_API_KEY`
-   `GEMINI_GENERATION_MODEL`
-   `GEMINI_EMBEDDING_MODEL`
-   `EMBEDDING_DIMENSION`
-   `ADMIN_USERNAME`
-   `ADMIN_PASSWORD_HASH`
-   `JWT_SECRET_KEY`
-   `JWT_ALGORITHM`
-   `JWT_EXPIRE_MINUTES`
-   Application environment/log level settings

Only add variables that are actually used. Do not put secrets in
frontend code or GitHub. Keep frontend settings separate and limited to
the backend API URL and session handling.

## 18. Supabase connection and migrations

-   Use Supabase PostgreSQL as the only persistent store.
-   For Render, evaluate the Supabase external pooler and prefer session
    pooling for this synchronous SQLAlchemy MVP where supported.
-   Verify current Supabase connection guidance, Render networking
    compatibility, and pooler connection details before configuration.
-   Use SSL, with the connection configuration required by the current
    Supabase guidance.
-   Keep SQLAlchemy pool size and overflow conservative.
-   Use `pool_pre_ping=True` and an appropriate connection recycle
    setting.
-   Do not create a large application connection pool.
-   Do not run Alembic migrations automatically on every application
    startup.
-   Run migrations explicitly as a controlled deployment/setup step.
-   Use direct connections for local tools only when the network
    supports them and the connection limits permit it.
-   Never commit database credentials.

## 19. Free deployment constraints

### Supabase

-   Free storage, compute, connection, and vector capacity are limited.
-   Projects may pause after inactivity.
-   Keep synthetic data and the knowledge corpus small.
-   Do not use the database for large binary files.

### Render

-   Free web services may sleep and have cold starts/resource limits.
-   The filesystem is ephemeral; never use it as persistent storage.
-   Keep all persistent application data in Supabase.
-   Handle timeouts and cold starts gracefully.
-   Do not promise production uptime.

### Streamlit Community Cloud

-   CPU, memory, and runtime resources are limited.
-   Keep the frontend lightweight.
-   Separate frontend dependencies from backend dependencies.
-   Do not expose database or Gemini secrets to the frontend.

### Overall cost rule

The intended project cost is \$0. Free-tier terms, quotas, and
availability can change. Verify current terms at setup/deployment time.
If a required service cannot be used within the free tier, stop and
explain the limitation; do not activate billing or substitute a paid
service without explicit approval.

## 20. Approved repository structure

Use this as the initial target structure. Adjust only when there is a
concrete reason, and explain the change before applying it.

``` text
resolve-ai/
├── intent.md
├── Final directive.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   └── exceptions.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   └── routes/
│   │   ├── services/
│   │   ├── ai/
│   │   ├── rag/
│   │   ├── tools/
│   │   └── utils/
│   ├── alembic/
│   ├── tests/
│   ├── scripts/
│   ├── knowledge_base/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example
│   └── README.md
├── frontend/
│   ├── app.py
│   ├── pages/
│   ├── services/
│   ├── components/
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── deployment.md
├── .gitignore
└── README.md
```

Do not create empty placeholder files or folders without a purpose. Keep
dependencies minimal and separate backend/frontend requirements.

## 21. Phase-by-phase implementation plan

### Phase 0 --- Planning (approved)

Architecture and product decisions are approved. Do not redo Phase 0
unless a genuine contradiction or provider constraint is discovered.

### Phase 1 --- Local project setup

-   Inspect the existing repository before changing anything.
-   Confirm `intent.md` and this directive are present.
-   Create the approved backend/frontend structure.
-   Create and document Python virtual environments.
-   Add minimal dependency manifests and `.env.example` files.
-   Add `.gitignore`.
-   Initialize/configure Git only if not already initialized.
-   Create the FastAPI app and `/health` endpoint.
-   Run it locally and verify the health response.
-   Do not connect Gemini or Supabase yet unless a step explicitly
    requires it.
-   Do not create the full database schema in Phase 1.

**Phase 1 acceptance criteria:** clean local project structure,
reproducible setup instructions, FastAPI starts, `/health` works,
secrets are excluded from Git, and the user can run the app
independently.

### Phase 2 --- Supabase and relational database

-   Create/configure Supabase manually with the user.
-   Enable pgvector extension.
-   Configure environment-based database connection.
-   Implement SQLAlchemy models and Alembic.
-   Create relational tables, relationships, constraints, and indexes.
-   Create `document_chunks` without a vector column until the embedding
    dimension is verified.
-   Apply and verify migrations.
-   Seed a small synthetic dataset (approximately 20 customers and
    50--100 orders).
-   Make seeding safe to rerun without duplicates.
-   Verify customer-scoped order lookup.

**Phase 2 acceptance criteria:** migrations apply cleanly, schema
matches the directive, seed is repeatable, and ownership tests pass.

### Phase 3 --- Embedding decision, vector migration, and RAG

-   Verify current official Gemini embedding availability and free-tier
    eligibility.
-   Test the SDK request and returned vector shape.
-   Decide model/configuration/dimension with the user.
-   If unsuitable, present a local embedding alternative and obtain
    approval.
-   Create a dedicated Alembic migration adding the verified vector
    column.
-   Implement content hashing, versioned chunking, embedding caching,
    safe ingestion, and pgvector retrieval.
-   Implement relevance/insufficient-evidence behavior.
-   Test historical evidence and failed re-ingestion behavior.

**Phase 3 acceptance criteria:** verified vector dimension, migration
succeeds, ingestion is repeatable and failure-safe, retrieval returns
source metadata, and insufficient evidence does not hallucinate.

### Phase 4 --- Gemini extraction and response orchestration

-   Verify and select an available free-tier generation model.
-   Implement structured extraction and Pydantic validation.
-   Implement grounded response generation.
-   Implement controlled function calling.
-   Enforce allowlisted tools and deterministic backend decisions.
-   Add bounded quota/error handling.
-   Mock Gemini in tests.

**Phase 4 acceptance criteria:** validated extraction, grounded answers,
safe tool dispatch, deterministic business decisions, and no paid
fallback.

### Phase 5 --- Business workflows and ticketing

-   Implement customer conversations/messages.
-   Implement customer-scoped order tools.
-   Implement deterministic return/warranty checks.
-   Implement escalation rules.
-   Implement canonical issue keys and duplicate-ticket reuse.
-   Implement ticket evidence snapshots.
-   Implement ticket events and knowledge-gap associations.
-   Implement knowledge-gap approval and publication workflow.

**Phase 5 acceptance criteria:** three core scenarios work end-to-end at
the API/service level, ticket matching is safe, and audit/evidence
history is preserved.

### Phase 6 --- Streamlit frontend

-   Build synthetic customer selector.
-   Build customer chat and conversation continuity.
-   Display grounded sources and escalation/ticket status.
-   Build admin login and token handling.
-   Build ticket inbox and investigation view.
-   Build knowledge document and knowledge-gap pages.
-   Use only the FastAPI API client for backend operations.

**Phase 6 acceptance criteria:** customer and admin flows work through
the UI without direct database or Gemini access from Streamlit.

### Phase 7 --- Testing and refinement

-   Run the full automated suite.
-   Test ownership, authentication, ticket concurrency, ingestion
    failure, RAG evidence, and all three demo scenarios.
-   Fix defects before deployment.
-   Review logs and error messages for secret leakage.
-   Do not claim tests pass unless they were actually run.

### Phase 8 --- Deployment

-   Verify current free-tier availability and terms.
-   Configure Supabase connection for Render.
-   Deploy FastAPI to Render.
-   Run migrations explicitly.
-   Run seed and ingestion commands deliberately.
-   Deploy Streamlit Community Cloud.
-   Configure secrets through hosting dashboards.
-   Verify end-to-end behavior, cold starts, and error handling.
-   Confirm no paid fallback/billing has been enabled.

### Phase 9 --- Documentation and portfolio readiness

-   Complete README and setup guide.
-   Document architecture, API, schema, RAG, ingestion, and deployment.
-   Document free-tier limitations and demo-only identity.
-   Include screenshots only if captured from the actual working
    application.
-   Prepare an interview explanation covering architecture, tool
    calling, RAG, deterministic business logic, security boundaries, and
    trade-offs.
-   Do not claim production readiness, real customer integrations, or
    capabilities that were not implemented.

## 22. Demonstration scenarios

The MVP must demonstrate these three scenarios:

### Scenario A --- Policy-grounded answer

A synthetic customer asks a return-policy question.

Expected behavior:

-   Retrieve relevant active policy chunks.
-   Answer using retrieved evidence.
-   Display the source document title.
-   Avoid unsupported claims.

### Scenario B --- Verified order lookup

A synthetic customer asks for the status of their own order, such as
`SE1025`.

Expected behavior:

-   Identify the selected synthetic customer.
-   Verify order ownership in the backend.
-   Retrieve order information through a controlled tool.
-   Explain only the verified status and relevant fields.

### Scenario C --- Unsupported compensation request

A customer asks for a compensation promise or policy exception not
covered by ShopEase's documents.

Expected behavior:

-   Do not invent a compensation policy.
-   Explain that the current policy does not establish the requested
    entitlement.
-   Create or reuse an appropriate ticket.
-   Record a knowledge gap.
-   Preserve retrieved evidence, if any.
-   Allow the admin to approve an official answer.
-   Ingest the approved answer as a new knowledge document version.

## 23. Working method and Copilot behavior

For every phase:

1.  State the phase objective and the exact tasks to be completed.
2.  Inspect existing files before creating or overwriting anything.
3.  Explain the planned files and important design choices.
4.  Implement only the current phase.
5.  Keep code readable and beginner-friendly, with useful comments where
    they clarify non-obvious behavior.
6.  Explain commands and where the user should run them (PowerShell/VS
    Code terminal).
7.  Run relevant tests or validation commands when possible.
8.  Report exactly what was created or changed.
9.  Report commands actually executed and their results.
10. List known limitations and unresolved decisions.
11. Provide manual verification steps for the user.
12. Stop and wait for explicit user approval before starting the next
    phase.

If you cannot execute a command or verify a result in the user's
environment, say so. Do not pretend that a migration, test, deployment,
or API call succeeded.

If a requirement is ambiguous, ask one focused question rather than
guessing. If a proposed change affects architecture, cost, security,
data integrity, or scope, explain the trade-off and obtain approval
first.

## 24. Current project state and immediate instruction

Phase 0 is approved. The next task is **Phase 1 --- Local Project
Setup**.

Before doing anything:

-   Inspect the current repository and its existing files.
-   Confirm whether `intent.md` and `Final directive.md` already exist.
-   Do not overwrite user-authored content without showing the proposed
    change.
-   Do not create Supabase resources, API keys, cloud services, or paid
    resources.
-   Do not begin Phase 2 or implement database models, Gemini
    integration, RAG, tickets, or the frontend workflows yet.

Start by reporting the repository state and proposing the exact Phase 1
file/folder changes. Then implement Phase 1 only, verify the FastAPI
health endpoint, document how the user can run it on Windows 11, and
stop for approval.
