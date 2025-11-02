# GitLab Hooks API

A FastAPI-based service for managing GitLab webhooks and automating CI/CD pipeline triggers based on comment-based commands.

## Overview

This service provides a centralized API for registering and managing webhooks across multiple GitLab projects within a group. It can automatically trigger GitLab CI/CD pipelines when specific code phrases are detected in comments on merge requests or issues.

## Features

- **Bulk Webhook Registration**: Register webhooks for all projects in a GitLab group (including nested subgroups) with a single API call
- **Webhook Management**: Automatically detects and updates existing webhooks based on configuration
- **Comment-Based Pipeline Triggers**: Monitors webhook events and triggers CI/CD pipelines when a configurable code phrase is found in comments
- **Multiple Event Types**: Supports various GitLab webhook events (push, merge requests, comments, issues, pipelines, etc.)
- **MongoDB Storage**: Persists webhook configurations and trigger tokens for reliable operation
- **GitLab API Integration**: Full integration with GitLab API for webhook and pipeline trigger management

## Tech Stack

- **FastAPI** - Modern Python web framework
- **MongoDB** - Database for storing webhook configurations (via Motor async driver)
- **httpx** - Async HTTP client for GitLab API calls
- **Python 3.11+** - Required Python version
- **Docker** - Containerized deployment support

## Prerequisites

- Python 3.11 or higher
- MongoDB instance (local or remote)
- GitLab instance with API access
- GitLab Personal Access Token (PAT) with appropriate permissions

## Installation

### Using uv (Recommended)

```bash
# Install dependencies
uv pip install -e .

# Or install with dev dependencies
uv pip install -e ".[dev]"
```

### Using pip

```bash
pip install -e .
```

## Configuration

Configure the application using environment variables:

- `GITLAB_HOST` - GitLab instance URL (default: `https://git.the-devs.com`)
- `MONGO_URL` - MongoDB connection string (default: `mongodb://root:example@localhost:27017/`)
- `CODE_PHRASE` - Code phrase to detect in comments for triggering pipelines (default: `trigger-bot`)

Create a `.env` file or set these environment variables:

```env
GITLAB_HOST=https://gitlab.example.com
MONGO_URL=mongodb://user:password@localhost:27017/
CODE_PHRASE=trigger-bot
```

## Running the Application

### Development Mode

```bash
# Using the dev script
uv run dev

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker Deployment

### Using Docker Compose

```bash
# Start MongoDB and the application
docker-compose up -d
```

### Building Docker Image

```bash
docker build -t gitlab-hooks .
docker run -p 8000:8000 \
  -e GITLAB_HOST=https://gitlab.example.com \
  -e MONGO_URL=mongodb://mongodb:27017/ \
  -e CODE_PHRASE=trigger-bot \
  gitlab-hooks
```

## API Endpoints

### Health Check

- `GET /` - Returns API status
- `GET /health` - Health check endpoint

### GitLab Operations

- `GET /gitlab/projects?group_id={id}` - List all projects in a GitLab group
  - **Authentication**: Basic Auth (username: any, password: GitLab PAT)

- `POST /gitlab/register-webhooks` - Register or update webhooks for all projects in a group
  - **Authentication**: Basic Auth (username: any, password: GitLab PAT)
  - **Request Body**: See `WebhookRegistrationRequest` model for details
  - **Returns**: Summary of registered, updated, and skipped projects

- `POST /gitlab/webhook` - Receive GitLab webhook events
  - **Authentication**: Token-based via `X-Gitlab-Token` header
  - **Functionality**: Detects code phrase in comments and triggers CI/CD pipelines

## Usage Example

### Register Webhooks for a Group

```bash
curl -X POST "http://localhost:8000/gitlab/register-webhooks" \
  -u "username:your-gitlab-pat" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": 123,
    "webhook_url": "https://your-service.com/gitlab/webhook",
    "webhook_token": "your-secret-token",
    "target_trigger_url": "https://gitlab.example.com/api/v4/projects/{project_id}/trigger/pipeline",
    "name": "autowebhook",
    "merge_requests_events": true,
    "note_events": true,
    "push_events": false
  }'
```

### Configure GitLab Webhook

In your GitLab project settings, add a webhook pointing to:
```
https://your-service.com/gitlab/webhook
```

Set the secret token to match the `webhook_token` used during registration.

## Project Structure

```
gitlab-hooks/
├── app/
│   ├── main.py              # FastAPI application and endpoints
│   ├── config.py            # Configuration management
│   ├── connectors.py        # MongoDB connection
│   ├── database/
│   │   └── webhooks.py      # Webhook database operations
│   └── services/
│       └── gitlab/
│           ├── client.py    # GitLab API client
│           └── exceptions.py # Custom exceptions
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile              # Docker image definition
├── pyproject.toml          # Project dependencies and metadata
└── dev.py                  # Development server script
```

## How It Works

1. **Webhook Registration**: When you call `/gitlab/register-webhooks`, the service:
   - Fetches all projects in the specified GitLab group (including nested subgroups)
   - Creates or updates webhooks for each project
   - Creates pipeline trigger tokens for each project
   - Stores the configuration in MongoDB

2. **Webhook Processing**: When GitLab sends a webhook event to `/gitlab/webhook`:
   - The service validates the webhook token
   - Checks if the code phrase appears in comment content
   - If found, triggers the GitLab CI/CD pipeline using the stored trigger token
   - Passes webhook context as pipeline variables (`AI_FLOW_EVENT`, `AI_FLOW_CONTEXT`, `AI_FLOW_INPUT`)

## License

This project is proprietary software.

