# GitLab Hooks API

A FastAPI service that listens for GitLab webhook events and dispatches tasks to configurable triggers — GitLab CI pipelines or an OpenClaw agent.

## How It Works

```
GitLab comment
    │  (contains CODE_PHRASE, e.g. "trigger-bot do X")
    ▼
POST /gitlab/webhook
    │  validates X-Gitlab-Token
    │  extracts project_id, ref, flow_context
    ▼
Trigger dispatcher
    ├─ gitlab_pipeline → triggers GitLab CI pipeline with AI_FLOW_* variables
    └─ openclaw        → POSTs task + context to OpenClaw agent endpoint
```

### Registration flow

Before events can be received, webhooks must be registered across all projects in a GitLab group:

```
POST /gitlab/register-webhooks
    │  iterates all projects in group (including nested subgroups)
    │  creates/updates webhook on each project
    │  creates pipeline trigger token per project
    ▼
MongoDB stores { webhook_token, trigger_tokens: { project_id: token } }
```

### Webhook processing flow

When GitLab POSTs a webhook event:

1. `X-Gitlab-Token` is validated against MongoDB
2. Comment text is checked for `CODE_PHRASE`
3. If found, `flow_context` is assembled:
   - event type, user, project, merge request metadata, note text, last commit
4. Configured trigger(s) fire with: `project_id`, `ref`, `trigger_token`, `flow_context`, `AI_FLOW_INPUT`, `AI_FLOW_EVENT`

---

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITLAB_HOST` | yes | — | GitLab instance base URL |
| `MONGO_URL` | no | `mongodb://root:example@localhost:27017/` | MongoDB connection string |
| `CODE_PHRASE` | no | `trigger-bot` | Phrase that activates the trigger |
| `TRIGGER_TYPE` | no | `gitlab_pipeline` | Active trigger(s); comma-separated: `gitlab_pipeline`, `openclaw` |
| `OPENCLAW_HOST` | openclaw only | — | OpenClaw base URL, e.g. `http://openclaw-1:18789` |
| `OPENCLAW_OPERATOR_TOKEN` | openclaw only | — | Bearer token for OpenClaw |
| `OPENCLAW_WEBHOOK_SECRET` | openclaw only | — | `X-OpenClaw-Webhook-Secret` header value |
| `OPENCLAW_GENERAL_PROMPT` | no | *(built-in agent prompt)* | Prompt prepended to the flow context in OpenClaw messages |

### `.env` example

```env
GITLAB_HOST=https://gitlab.example.com
MONGO_URL=mongodb://root:example@localhost:27017/
CODE_PHRASE=trigger-bot

# Use both triggers simultaneously
TRIGGER_TYPE=gitlab_pipeline,openclaw

OPENCLAW_HOST=http://openclaw-1:18789
OPENCLAW_OPERATOR_TOKEN=your-operator-token
OPENCLAW_WEBHOOK_SECRET=your-webhook-secret
```

---

## Running

```bash
# Development
uv run dev

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker Compose (includes MongoDB)
docker-compose up -d
```

---

## API

### `GET /health`

```bash
curl http://localhost:8000/health
# {"status":"healthy"}
```

### `GET /gitlab/projects?group_id=123`

List all projects in a GitLab group. Basic Auth: any username, GitLab PAT as password.

```bash
curl -u "user:$GITLAB_PAT" \
  "http://localhost:8000/gitlab/projects?group_id=123"
```

### `POST /gitlab/register-webhooks`

Register or update webhooks across every project in a group. Re-running is safe — existing webhooks are compared and updated only if configuration changed.

```bash
curl -X POST http://localhost:8000/gitlab/register-webhooks \
  -u "user:$GITLAB_PAT" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 123,
    "webhook_url": "https://hooks.example.com/gitlab/webhook",
    "webhook_token": "my-secret-token",
    "target_trigger_url": "unused-kept-for-compat",
    "name": "autowebhook",
    "merge_requests_events": true,
    "note_events": true,
    "push_events": false
  }'
```

**Request fields:**

| Field | Required | Default | Description |
|---|---|---|---|
| `group_id` | yes | — | GitLab group ID |
| `webhook_url` | yes | — | Public URL of this service's `/gitlab/webhook` endpoint |
| `webhook_token` | yes | — | Secret sent in `X-Gitlab-Token` by GitLab |
| `name` | yes | — | Webhook name used to identify existing webhooks (e.g. `autowebhook`) |
| `target_trigger_url` | yes | — | Kept for schema compatibility |
| `enable_ssl_verification` | no | `true` | SSL verification on GitLab's outbound request |
| `merge_requests_events` | no | `false` | |
| `note_events` | no | `false` | Comments on MRs/issues |
| `push_events` | no | `false` | |
| `issues_events` | no | `false` | |
| `pipeline_events` | no | `false` | |
| `tag_push_events` | no | `false` | |
| `deployment_events` | no | `false` | |
| `releases_events` | no | `false` | |
| `wiki_page_events` | no | `false` | |
| `job_events` | no | `false` | |

**Response:**

```json
{
  "registered": [{"project_id": 42, "name": "my-repo"}],
  "updated":    [],
  "skipped":    [{"project_id": 7,  "name": "other-repo"}],
  "failed":     []
}
```

### `POST /gitlab/webhook`

Receives GitLab webhook events. Called by GitLab, not directly.

**Headers required by GitLab:**
- `X-Gitlab-Token: <webhook_token>`

**Response when code phrase found:**

```json
{
  "found": true,
  "trigger_results": [
    { "id": 999, "status": "created" }
  ]
}
```

**Response when code phrase not found:**

```json
{ "found": false }
```

---

## Triggers

### `gitlab_pipeline`

Calls the GitLab pipeline trigger API. The pipeline receives three CI variables:

| Variable | Content |
|---|---|
| `AI_FLOW_EVENT` | Event type, e.g. `note` |
| `AI_FLOW_CONTEXT` | JSON: event, user, project, MR, note, commit |
| `AI_FLOW_INPUT` | Raw comment text |

Equivalent curl:
```bash
curl -X POST "$GITLAB_HOST/api/v4/projects/$PROJECT_ID/trigger/pipeline" \
  -F "token=$TRIGGER_TOKEN" \
  -F "ref=$BRANCH" \
  -F "variables[AI_FLOW_EVENT]=note" \
  -F "variables[AI_FLOW_CONTEXT]={...}" \
  -F "variables[AI_FLOW_INPUT]=trigger-bot fix the tests"
```

### `openclaw`

Posts the flow context to an OpenClaw agent endpoint as a task message.

```bash
curl -X POST "$OPENCLAW_HOST/plugins/webhooks/trigger" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENCLAW_OPERATOR_TOKEN" \
  -H "X-OpenClaw-Webhook-Secret: $OPENCLAW_WEBHOOK_SECRET" \
  -d '{"message": "<OPENCLAW_GENERAL_PROMPT>\n\n<flow_context as JSON>"}'
```

The message is: `OPENCLAW_GENERAL_PROMPT` + newline + the full `flow_context` JSON. The default `OPENCLAW_GENERAL_PROMPT` instructs the agent to read the GitLab context, perform the requested action using GitLab MCP, and post results back as a GitLab comment.

### Multi-trigger

Set `TRIGGER_TYPE=gitlab_pipeline,openclaw` to fire both sequentially on every matching comment.

---

## Project Structure

```
app/
├── main.py              # FastAPI routes
├── config.py            # All environment variable definitions
├── connectors.py        # MongoDB client
├── database/
│   └── webhooks.py      # Upsert logic
├── services/
│   └── gitlab/
│       ├── client.py    # GitLab API client (projects, hooks, triggers)
│       └── exceptions.py
└── triggers/
    ├── __init__.py      # get_triggers() factory, reads TRIGGER_TYPE
    ├── base.py          # BaseTrigger abstract class
    ├── gitlab_pipeline.py
    └── openclaw.py
```

---

## License

GNU GPL v3. See [LICENSE](LICENSE).
