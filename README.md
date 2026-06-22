# Switchboard — Multi-Tenant WhatsApp AI Agent

> **A cloud-native, end-to-end agentic WhatsApp Support & Sales SaaS** built with LangGraph, FastAPI, MongoDB, and React.

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange)](https://langchain-ai.github.io/langgraph/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-success)](https://www.mongodb.com/atlas)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ed)](https://docker.com)

---

## Overview

Switchboard allows **multiple companies (tenants)** to manage customer queries interactively over WhatsApp using a shared AI infrastructure. Each tenant has their own brand persona, media library, and conversation history — fully isolated inside MongoDB.

### Demo tenants
| Tenant | Industry | Media |
|--------|----------|-------|
| **Aurelia & Oak** | Luxury Furniture | Catalog PDF, sofa image, showroom image |
| **TorquePoint Automotive Care** | Automotive Service | Invoice PDF, repair diagram, brake image |

---

## Architecture

```
[Meta WhatsApp Cloud API]
         │  (POST /api/webhooks/whatsapp)
         ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI  (uvicorn)                      │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Webhook Handler  ←→  BackgroundTasks           │    │
│  │   Returns 200 OK immediately ─────────────────► │    │
│  └────────────────────────┬────────────────────────┘    │
│                           │ async (never blocks HTTP)    │
│  ┌────────────────────────▼────────────────────────┐    │
│  │            LangGraph StateGraph                  │    │
│  │                                                  │    │
│  │  ┌──────────┐   ┌──────────┐   ┌─────────────┐  │    │
│  │  │ Acknowledge│→ │ Context  │→ │LLM Reasoning│  │    │
│  │  │  Node    │   │ Retriever│   │    Node     │  │    │
│  │  └──────────┘   └──────────┘   └──────┬──────┘  │    │
│  │                                        │         │    │
│  │                           ┌────────────┴──────┐  │    │
│  │                           │  Conditional Edge │  │    │
│  │                     ┌─────┴──────┐   ┌────────┴─┐│    │
│  │                     │ Dispatcher │   │  Human   ││    │
│  │                     │   Node     │   │ Handover ││    │
│  │                     └─────┬──────┘   └────────┬─┘│    │
│  └───────────────────────────┼───────────────────┼──┘    │
│                              │                   │        │
│  ┌───────────────────────────▼───────────────────▼──┐    │
│  │  MongoDB (Motor async driver)                     │    │
│  │  collections: tenants · chat_sessions · messages  │    │
│  └───────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────────────────────────────┐                  │
│  │  WebSocket /ws  ←→  React Dashboard │                  │
│  │  (live pipeline strip, chat thread) │                  │
│  └─────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

### LangGraph State (`AgentState`)

| Key | Type | Description |
|-----|------|-------------|
| `tenant_id` | str | Which tenant this conversation belongs to |
| `session_id` | str | Chat session UUID |
| `customer_phone` | str | E.164 phone number of the customer |
| `phone_number_id` | str | Meta phone number ID for this tenant |
| `wa_message_id` | str | Inbound message ID (for read receipt) |
| `inbound_text` | str | Customer's message text |
| `inbound_media` | dict | Media metadata + resolved URL/description |
| `tenant` | dict | Full tenant document (prompt, media library) |
| `chat_history` | list | Last 5 messages for context |
| `response_type` | str | `"text"` / `"image"` / `"document"` |
| `response_text` | str | Bot's reply text / media caption |
| `response_media_url` | str | URL if sending media |
| `sentiment` | str | `"neutral"` / `"frustrated"` |
| `needs_human` | bool | Triggers handover node |
| `trace` | list[str] | Visited node names (for dashboard) |
| `status` | str | Current session status |

### LangGraph Nodes

| Node | Responsibility |
|------|---------------|
| `acknowledge_node` | ① Mark message read (read receipt) ② Start typing indicator (two separate Graph API calls) ③ Persist inbound message as `PENDING_RESPONSE` |
| `context_retriever_node` | Pull tenant prompt + media catalog from DB; fetch last 5 chat messages; optionally resolve + describe inbound media via vision LLM |
| `llm_reasoning_node` | Invoke LLM with structured output → `AgentDecision` (reply text, action, media keyword, sentiment) |
| `dispatcher_node` | Build WhatsApp payload (text / image / document); send via Graph API; persist outbound message; flip session to `RESOLVED` |
| `human_handover_node` | Send holding message; flip session to `NEEDS_HUMAN`; halts automation (bonus feature) |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- A MongoDB Atlas cluster (M0 free tier works) — **or** let Docker spin up local Mongo

### 1. Clone & configure

```bash
git clone <repo-url>
cd whatsapp-agent
cp .env.example .env
```

Edit `.env` — minimum fields for a local demo:

```env
# MongoDB (docker-compose overrides this automatically)
MONGO_URI=mongodb://localhost:27017

# LLM (at least one of these)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Keep true until you have a real Meta App
DRY_RUN_WHATSAPP=true
```

### 2. Start the stack

```bash
docker compose up
```

This starts:
- **MongoDB** on port 27017
- **FastAPI backend** on port 8000 (with hot-reload)
- **React dev server** on port 5173 (with Vite HMR)

### 3. Seed demo data

```bash
docker compose exec backend python -m app.seed
```

### 4. Open the dashboard

Visit **http://localhost:5173**

You'll see two demo tenants with pre-seeded conversations. Use the **"Simulate inbound"** panel in any chat thread to trigger the full LangGraph pipeline without a real WhatsApp number.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MONGO_URI` | ✅ | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGO_DB_NAME` | | `whatsapp_agent` | Database name |
| `WHATSAPP_ACCESS_TOKEN` | Prod | — | Meta Graph API bearer token |
| `WHATSAPP_PHONE_NUMBER_ID` | Prod | — | Meta phone number ID |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Prod | — | Meta WABA ID |
| `WHATSAPP_VERIFY_TOKEN` | Prod | `change-me-verify-token` | Webhook verification token |
| `WHATSAPP_APP_SECRET` | Prod | — | For HMAC-SHA256 signature validation |
| `DRY_RUN_WHATSAPP` | | `false` | Log instead of calling Meta API |
| `LLM_PROVIDER` | | `openai` | `"openai"` or `"anthropic"` |
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `OPENAI_MODEL` | | `gpt-4o-mini` | Model name |
| `ANTHROPIC_API_KEY` | | — | Anthropic API key (if using Anthropic) |
| `ANTHROPIC_MODEL` | | `claude-sonnet-4-6` | Anthropic model name |
| `CORS_ORIGINS` | | `*` | Allowed CORS origins (comma-separated) |
| `SENTIMENT_HANDOVER_ENABLED` | | `true` | Enable human handover on frustration |

---

## API Endpoints

### Webhooks
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/webhooks/whatsapp` | Meta webhook verification challenge |
| `POST` | `/api/webhooks/whatsapp` | Inbound message delivery (async) |

### Dashboard
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/tenants` | List all tenants |
| `GET` | `/api/tenants/{id}` | Tenant detail + media library |
| `GET` | `/api/tenants/{id}/stats` | Stats chips (active, needs_human, etc.) |
| `GET` | `/api/tenants/{id}/sessions` | Live chat session list |
| `GET` | `/api/tenants/{id}/sessions/{sid}/messages` | Full chat thread |
| `POST` | `/api/tenants/{id}/broadcast` | Broadcast campaign |
| `GET/POST` | `/api/simulate` | Simulate inbound message (dev/demo) |
| `WS` | `/ws` | Live updates WebSocket |
| `GET` | `/api/health` | Health check |

Interactive docs: **http://localhost:8000/docs**

---

## Deployment

### Option 1: Render.com *(recommended for quick demo)*

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → **New Blueprint**
3. Select the repo → Render reads `render.yaml` automatically
4. Set the required secrets in the Render dashboard (Environment section)
5. Deploy — your live URL will be `https://switchboard.onrender.com`
6. Set the Render URL as your Meta webhook URL:
   `https://switchboard.onrender.com/api/webhooks/whatsapp`

### Option 2: GCP Cloud Run *(preferred per assignment)*

```bash
# Build and push
PROJECT_ID=$(gcloud config get-value project)
docker build -t gcr.io/$PROJECT_ID/switchboard .
docker push gcr.io/$PROJECT_ID/switchboard

# Create secrets in Secret Manager
echo -n "mongodb+srv://..." | gcloud secrets create MONGO_URI --data-file=-
echo -n "EAABs..." | gcloud secrets create WHATSAPP_ACCESS_TOKEN --data-file=-
# ... repeat for all secrets

# Update image in manifest and deploy
sed -i "s|<PROJECT_ID>|$PROJECT_ID|g" gcp-cloudrun.yaml
gcloud run services replace gcp-cloudrun.yaml --region=us-central1

# Get the live URL
gcloud run services describe switchboard --region=us-central1 --format='value(status.url)'
```

Set the Cloud Run URL as your Meta webhook: `https://<url>/api/webhooks/whatsapp`

### Option 3: Fly.io

```bash
fly auth login
fly launch --no-deploy --name switchboard-agent
fly secrets set \
  MONGO_URI="mongodb+srv://..." \
  WHATSAPP_ACCESS_TOKEN="..." \
  WHATSAPP_VERIFY_TOKEN="your-token" \
  WHATSAPP_APP_SECRET="..." \
  OPENAI_API_KEY="sk-..."
fly deploy
```

### Option 4: Local Docker (production image)

```bash
docker build -t switchboard .
docker run -p 8080:8080 --env-file .env switchboard
```

---

## Production Dockerfile

The single `Dockerfile` in the repo root:
1. **Stage 1 (node:20-slim)**: Builds the React dashboard → `dist/`
2. **Stage 2 (python:3.12-slim)**: Installs Python deps, copies the built dashboard into `./static/`, and serves everything from uvicorn

The backend auto-detects the `static/` directory and mounts it at `/`, so the production image serves both the API and the dashboard from a single container — ideal for GCP Cloud Run.

---

## Security

- **HMAC-SHA256 Webhook Validation**: Every inbound POST is validated against the `X-Hub-Signature-256` header using your `WHATSAPP_APP_SECRET`. Set in production to prevent spoofed webhook deliveries.
- **Async-first**: The webhook handler returns `200 OK` immediately and runs the LangGraph pipeline in a `BackgroundTask` — Meta never times out, eliminating duplicate delivery retries.
- **Unprivileged container user**: The production image runs as `appuser` (UID 10001), not root.

---

## Frontend Features

| Feature | Description |
|---------|-------------|
| **Tenant Switcher** | Left rail — click to switch between Tenant A & B; entire session list and stats update |
| **Live Session Monitor** | Shows all conversations with status filters (All / Waiting / Needs Human / Resolved) |
| **Chat Thread** | Full message history with image thumbnails, PDF download badges, and typing bubbles |
| **Pipeline Strip** | Animated 4-node progress bar (Acknowledge → Context → Reasoning → Dispatch) that lights up in real time via WebSocket |
| **Typing Indicator** | `TypingBubble` component shown while bot is processing (mirrors what the customer sees on WhatsApp) |
| **Broadcast Drawer** | Send template campaigns to cohorts (all / needs_human / resolved / custom numbers) |
| **NEEDS_HUMAN Highlight** | Sessions flagged for human takeover are highlighted in red throughout the UI |

---

## Running Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Project Structure

```
whatsapp-agent/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── dashboard.py     # Dashboard REST endpoints
│   │   │   ├── simulator.py     # Dev simulator endpoint
│   │   │   └── webhooks.py      # Meta webhook handler (async)
│   │   ├── graph/
│   │   │   ├── builder.py       # LangGraph StateGraph wiring
│   │   │   ├── nodes.py         # 4 pipeline nodes + handover
│   │   │   ├── state.py         # AgentState TypedDict
│   │   │   └── tools.py         # Media library helpers
│   │   ├── services/
│   │   │   ├── llm_client.py    # OpenAI/Anthropic + AgentDecision schema
│   │   │   ├── security.py      # HMAC-SHA256 signature verification
│   │   │   ├── session_service.py  # Session get-or-create
│   │   │   └── whatsapp_client.py  # Meta Graph API client
│   │   ├── config.py            # Pydantic settings (env vars)
│   │   ├── database.py          # Motor MongoDB connection
│   │   ├── main.py              # FastAPI app + WebSocket
│   │   ├── models.py            # Pydantic models (Tenant, ChatSession, Message)
│   │   ├── realtime.py          # WebSocket connection manager
│   │   └── seed.py              # Demo data seeder
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/client.js        # Typed API client
│       ├── components/          # React components
│       ├── hooks/               # useLiveUpdates (WebSocket)
│       ├── lib/format.js        # Formatting utilities
│       └── App.jsx              # Main app shell
├── Dockerfile                   # Production: React build + FastAPI
├── docker-compose.yml           # Local dev: hot-reload on both sides
├── render.yaml                  # Render.com deployment blueprint
├── fly.toml                     # Fly.io deployment config
├── gcp-cloudrun.yaml            # GCP Cloud Run service manifest
└── .env.example                 # All env vars documented
```
