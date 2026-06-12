# SmartBiz Backend

FastAPI backend for SmartBiz invoice management.

The app supports:

- Clients
- Invoices and invoice items
- Payment records
- Invoice template metadata and previews
- Invoice PDF preview generation
- AI invoice draft creation
- Device-based anonymous data isolation
- Dashboard summary data

## Tech Stack

- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic
- Pydantic v2
- LangChain Ollama / Anthropic Claude
- WeasyPrint
- uv

## Setup

Install dependencies:

```bash
uv sync
```

Create a `.env` file:

```env
APP_NAME="SmartBiz API"
APP_VERSION="1.0.0"
DEBUG=true

DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/smartbiz"

# AI provider: claude or ollama
AI_PROVIDER=claude
AI_REQUEST_TIMEOUT_SECONDS=60

# Claude
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_MODEL_NAME=claude-sonnet-4-20250514

# Ollama, useful for local development
OLLAMA_MODEL_NAME=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
```

Run database migrations:

```bash
uv run alembic upgrade head
```

Start the development server:

```bash
uv run fastapi dev app/main.py
```

## Device-Based Data Isolation

Most business APIs require this header:

```text
X-Device-Id: <uuid>
```

Example:

```bash
curl http://localhost:8000/clients \
  -H "X-Device-Id: 11111111-1111-1111-1111-111111111111"
```

Rules:

- Missing `X-Device-Id` returns `400`.
- Invalid UUID returns `400`.
- `device_id` is always taken from the header.
- Body-provided `device_id` is ignored.
- Reads, updates, deletes, invoice PDFs, payments, AI drafts, and dashboard data are scoped to the current device.

Invoice template library endpoints are global metadata and are not device-scoped.

## Response Shape

API responses use a standard envelope:

```json
{
  "status": true,
  "message": "success",
  "result": {}
}
```

Errors use the same shape:

```json
{
  "status": false,
  "message": "Client not found",
  "result": null
}
```

## Main APIs

### Health

```text
GET /
GET /health
```

### Dashboard

Requires `X-Device-Id`.

```text
GET /dashboard
```

Returns counts, invoice status totals, sales totals, recent invoices, and recent payments for the current device.

### Clients

Requires `X-Device-Id`.

```text
POST   /clients
GET    /clients
GET    /clients/{client_id}
PATCH  /clients/{client_id}
DELETE /clients/{client_id}
```

### Invoices

Requires `X-Device-Id`.

```text
POST   /invoices
GET    /invoices
GET    /invoices/{invoice_id}
PATCH  /invoices/{invoice_id}
DELETE /invoices/{invoice_id}
```

Invoice creation calculates item line totals, subtotal, and total in the backend.

### Invoice Payments

Requires `X-Device-Id`.

```text
POST /invoices/{invoice_id}/payments
GET  /invoices/{invoice_id}/payments
```

Adding payments updates invoice status:

- payment total less than invoice total -> `partially_paid`
- payment total equal to or greater than invoice total -> `paid`

### Standalone Payments

Requires `X-Device-Id`.

```text
POST /payments
GET  /payments
GET  /payments/{payment_id}
```

`POST /payments` can create:

- invoice-linked payment when `invoice_id` is provided
- standalone personal payment record when `invoice_id` is omitted

### Invoice PDF Preview

Requires `X-Device-Id`.

```text
GET /invoices/{invoice_id}/preview-pdf?template_key=modern_1
```

The invoice must belong to the current device.

### Invoice Templates

Global template metadata.

```text
GET    /invoice-templates
GET    /invoice-templates/{template_id}
POST   /invoice-templates
PATCH  /invoice-templates/{template_id}
DELETE /invoice-templates/{template_id}
GET    /invoice-templates/preview/{template_key}
```

### AI Invoice Draft

Requires `X-Device-Id`.

```text
POST /ai/invoice/draft
```

Example:

```bash
curl -X POST http://localhost:8000/ai/invoice/draft \
  -H "Content-Type: application/json" \
  -H "X-Device-Id: 11111111-1111-1111-1111-111111111111" \
  -d '{"text":"sell 30 soap $5 each and 20 toys $10 each to toseef"}'
```

The AI extracts data only. The backend validates items, creates a draft invoice, creates/attaches a client when provided, and calculates totals.

Roman Urdu / Hinglish prompts are supported for common phrases, for example:

```text
aj me ne 30 shower set aik ki qemat 5000pkr the or 20 commod aik ki qemat 10000pkr the toseef ko bechy hain
```

## AI Provider

Use Claude in production:

```env
AI_PROVIDER=claude
ANTHROPIC_API_KEY=your_anthropic_api_key
CLAUDE_MODEL_NAME=claude-sonnet-4-20250514
```

Use Ollama locally:

```env
AI_PROVIDER=ollama
OLLAMA_MODEL_NAME=llama3.1
OLLAMA_BASE_URL=http://localhost:11434
```

## Database Migrations

Create a migration:

```bash
uv run alembic revision --autogenerate -m "message"
```

Apply migrations:

```bash
uv run alembic upgrade head
```

Check current migration head:

```bash
uv run alembic heads
```

## Quality Checks

Run tests:

```bash
uv run pytest -q
```

Run type checker:

```bash
uv run ty check
```

Run linter:

```bash
uv run ruff check app tests
```

Compile check:

```bash
uv run python -m compileall app tests alembic
```

## Notes

- Do not trust client-provided totals.
- Do not trust body-provided `device_id`.
- Keep routers thin and put database/business logic in services.
- Use sync SQLAlchemy sessions through `get_db`.
- Keep authentication out until the product is ready for accounts.
