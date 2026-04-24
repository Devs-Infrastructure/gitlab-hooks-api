from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.services.gitlab import GitLabClient
from app.services.gitlab.exceptions import GitLabAPIError, GitLabAuthenticationError
from app.database.webhooks import save_or_update_webhook
from app.connectors import webhooks_collection
from app.config import CODE_PHRASE
from app.triggers import get_triggers

app = FastAPI(
    title="GitLab Hooks API",
    description="API for handling GitLab webhooks",
    version="1.0.0",
)

# Allow all hosts for development
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Basic Auth security
security = HTTPBasic()

# GitLab client instance
gitlab_client = GitLabClient()


class WebhookRegistrationRequest(BaseModel):
    """Request model for webhook registration.

    All trigger event fields are optional. If not specified, defaults will be used.
    When called second time, existing webhooks will be compared with provided parameters
    and updated if they differ.
    """

    group_id: int = Field(..., description="GitLab group ID to register webhooks for")
    webhook_url: str = Field(..., description="URL where webhook events will be sent")
    webhook_token: str = Field(
        ..., description="Secret token to identify and authenticate the webhook (used to find existing autowebhook)"
    )
    target_trigger_url: str = Field(
        ..., description="URL to POST to when the code phrase is detected in webhook payloads"
    )
    name: str = Field(
        ..., description="Required name/description for the webhook (used to identify existing webhooks, e.g., 'autowebhook')"
    )
    enable_ssl_verification: Optional[bool] = Field(
        True, description="Whether to enable SSL certificate verification"
    )
    # Trigger events
    push_events: Optional[bool] = Field(
        False, description="Trigger on push events (commits pushed to repository)"
    )
    merge_requests_events: Optional[bool] = Field(
        False,
        description="Trigger on merge request events (created, updated, merged)",
    )
    comments_events: Optional[bool] = Field(
        False,
        description="Trigger on comments (notes/comments added or edited on issues or merge requests). Alias for note_events.",
    )
    note_events: Optional[bool] = Field(
        False,
        description="Trigger on comments (notes added or edited on issues or merge requests). Same as comments_events.",
    )
    confidential_issues_events: Optional[bool] = Field(
        False,
        description="Trigger when a confidential issue is created, updated, closed, or reopened",
    )
    issues_events: Optional[bool] = Field(
        False,
        description="Trigger when an issue is created, updated, closed, or reopened",
    )
    # Additional common events
    tag_push_events: Optional[bool] = Field(
        False, description="Trigger on tag push events"
    )
    pipeline_events: Optional[bool] = Field(
        False, description="Trigger on pipeline events"
    )
    job_events: Optional[bool] = Field(False, description="Trigger on job events")
    wiki_page_events: Optional[bool] = Field(
        False, description="Trigger on wiki page events"
    )
    deployment_events: Optional[bool] = Field(
        False, description="Trigger on deployment events"
    )
    releases_events: Optional[bool] = Field(
        False, description="Trigger on release events"
    )


@app.get("/")
async def root():
    return {"message": "GitLab Hooks API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/gitlab/projects")
async def get_gitlab_projects(
    group_id: int,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    credentials: HTTPBasicCredentials = Depends(security),
):
    """Fetch GitLab projects from a specific group using a personal access token.

    Args:
        group_id: Required GitLab group ID to filter projects
        page: Page number (default: 1, or None to use GitLab default)
        per_page: Number of items per page (default: 20, max: 100, or None to use GitLab default)
        credentials: Basic Auth credentials where password is the GitLab PAT

    Returns:
        Dictionary containing:
        - data: List of GitLab projects belonging to the specified group
        - pagination: Dictionary with pagination metadata (total, total_pages, page, per_page, next_page, prev_page)

    Raises:
        HTTPException: If authentication fails or API request fails
    """
    # The token is passed as the password in Basic Auth
    token = credentials.password

    try:
        result = await gitlab_client.get_projects(
            token, group_id=group_id, page=page, per_page=per_page
        )
        return result
    except GitLabAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GitLabAPIError as e:
        status_code = e.status_code or 500
        raise HTTPException(status_code=status_code, detail=str(e))


@app.post("/gitlab/register-webhooks")
async def register_webhooks(
    request: WebhookRegistrationRequest,
    page: Optional[int] = None,
    per_page: Optional[int] = None,
    credentials: HTTPBasicCredentials = Depends(security),
):
    """Register webhooks (autowebhook) for repositories under a given group.

    If a webhook with the same URL already exists, its settings will be compared
    with the provided parameters and updated if they differ.

    Args:
        request: Request body containing group_id, webhook_url, and trigger event settings
        page: Page number (default: None to fetch all pages, or specify to process a specific page)
        per_page: Number of items per page (default: 100 when fetching all pages, or None to use GitLab default)
        credentials: Basic Auth credentials where password is the GitLab PAT

    Returns:
        JSON summary with registered, updated, and skipped project IDs, plus pagination metadata

    Raises:
        HTTPException: If authentication fails or API request fails
    """
    # The token is passed as the password in Basic Auth
    token = credentials.password

    # Helper function to get boolean value with default
    def get_bool_value(value: Optional[bool], default: bool = False) -> bool:
        return value if value is not None else default

    # Extract webhook settings from request
    # Handle comments_events as an alias for note_events (if either is True, enable it)
    note_events_value = request.note_events
    if note_events_value is None:
        note_events_value = request.comments_events
    elif request.comments_events is True:
        note_events_value = True  # If comments_events is True, ensure note_events is True
    
    enable_ssl_verification = get_bool_value(request.enable_ssl_verification, True)
    push_events = get_bool_value(request.push_events, False)
    merge_requests_events = get_bool_value(request.merge_requests_events, False)
    note_events = get_bool_value(note_events_value, False)
    confidential_issues_events = get_bool_value(request.confidential_issues_events, False)
    issues_events = get_bool_value(request.issues_events, False)
    tag_push_events = get_bool_value(request.tag_push_events, False)
    pipeline_events = get_bool_value(request.pipeline_events, False)
    job_events = get_bool_value(request.job_events, False)
    wiki_page_events = get_bool_value(request.wiki_page_events, False)
    deployment_events = get_bool_value(request.deployment_events, False)
    releases_events = get_bool_value(request.releases_events, False)

    # Event fields mapping for comparison
    event_fields_map = {
        "enable_ssl_verification": enable_ssl_verification,
        "push_events": push_events,
        "merge_requests_events": merge_requests_events,
        "note_events": note_events,
        "confidential_issues_events": confidential_issues_events,
        "issues_events": issues_events,
        "tag_push_events": tag_push_events,
        "pipeline_events": pipeline_events,
        "job_events": job_events,
        "wiki_page_events": wiki_page_events,
        "deployment_events": deployment_events,
        "releases_events": releases_events,
    }

    try:
        # Fetch projects with pagination support
        all_projects = []
        pagination_info = None
        
        if page is not None:
            # Fetch specific page
            result = await gitlab_client.get_projects(
                token, group_id=request.group_id, page=page, per_page=per_page
            )
            all_projects = result["data"]
            pagination_info = result["pagination"]
        else:
            # Fetch all pages automatically
            current_page = 1
            per_page_value = per_page or 100  # Use 100 (max) when fetching all pages
            
            while True:
                result = await gitlab_client.get_projects(
                    token, group_id=request.group_id, page=current_page, per_page=per_page_value
                )
                page_projects = result["data"]
                all_projects.extend(page_projects)
                pagination_info = result["pagination"]
                
                # Check if there are more pages
                if pagination_info.get("next_page") is None:
                    break
                current_page = pagination_info["next_page"]

        registered = []
        updated = []
        skipped = []
        failed = []
        trigger_tokens = {}  # Store project_id -> trigger_token mapping

        # Check each project for existing autowebhook
        for project in all_projects:
            project_id = project["id"]
            project_name = project.get("name", str(project_id))

            try:
                # Get pipeline trigger tokens for the project
                triggers = await gitlab_client.get_project_triggers(token, project_id)

                # Find existing trigger token with description == request.name
                existing_trigger = None
                for trigger in triggers:
                    trigger_description = trigger.get("description", "")
                    if trigger_description == request.name:
                        existing_trigger = trigger
                        break

                # If trigger token not found, create it
                if not existing_trigger:
                    new_trigger = await gitlab_client.create_project_trigger(
                        token=token,
                        project_id=project_id,
                        description=request.name,
                    )
                    trigger_tokens[project_id] = new_trigger.get("token")
                else:
                    trigger_tokens[project_id] = existing_trigger.get("token")

            except GitLabAPIError as e:
                print(f"[Register] project {project_id} ({project_name}): trigger token error: {e}")

            try:
                # Get existing hooks for the project
                hooks = await gitlab_client.get_project_hooks(token, project_id)

                # Find existing webhook by name (this identifies the autowebhook)
                # Name is the primary identifier, with token and URL as fallbacks
                existing_hook = None
                for hook in hooks:
                    hook_token = hook.get("token")
                    hook_url = hook.get("url", "")
                    hook_description = hook.get("description", "")

                    # Primary: match by name (description field in GitLab API)
                    if hook_description == request.name:
                        existing_hook = hook
                        break
                    # Fallback: match by token (reliable identifier)
                    elif hook_token == request.webhook_token:
                        existing_hook = hook
                        break
                    # Fallback: match by URL and name
                    elif hook_url == request.webhook_url and hook_description == request.name:
                        existing_hook = hook
                        break

                if existing_hook:
                    # Compare existing hook settings with requested settings
                    diffs = []
                    for field, requested_value in event_fields_map.items():
                        existing_value = existing_hook.get(field, False)
                        if existing_value != requested_value:
                            diffs.append(f"{field}: {existing_value} -> {requested_value}")

                    if existing_hook.get("url") != request.webhook_url:
                        diffs.append(f"url: {existing_hook.get('url')} -> {request.webhook_url}")
                    if existing_hook.get("token") != request.webhook_token:
                        diffs.append("token changed")
                    if existing_hook.get("description") != request.name:
                        diffs.append(f"description: {existing_hook.get('description')} -> {request.name}")

                    if diffs:
                        print(f"[Register] project {project_id} ({project_name}): updating webhook, changes: {', '.join(diffs)}")
                        await gitlab_client.update_project_hook(
                            token=token,
                            project_id=project_id,
                            hook_id=existing_hook["id"],
                            webhook_url=request.webhook_url,
                            webhook_token=request.webhook_token,
                            description=request.name,
                            enable_ssl_verification=enable_ssl_verification,
                            push_events=push_events,
                            merge_requests_events=merge_requests_events,
                            note_events=note_events,
                            confidential_issues_events=confidential_issues_events,
                            issues_events=issues_events,
                            tag_push_events=tag_push_events,
                            pipeline_events=pipeline_events,
                            job_events=job_events,
                            wiki_page_events=wiki_page_events,
                            deployment_events=deployment_events,
                            releases_events=releases_events,
                        )
                        updated.append(project_id)
                    else:
                        print(f"[Register] project {project_id} ({project_name}): webhook up to date, skipping")
                        skipped.append(project_id)
                else:
                    print(f"[Register] project {project_id} ({project_name}): no existing webhook, creating")
                    await gitlab_client.create_project_hook(
                        token=token,
                        project_id=project_id,
                        webhook_url=request.webhook_url,
                        webhook_token=request.webhook_token,
                        description=request.name,
                        enable_ssl_verification=enable_ssl_verification,
                        push_events=push_events,
                        merge_requests_events=merge_requests_events,
                        note_events=note_events,
                        confidential_issues_events=confidential_issues_events,
                        issues_events=issues_events,
                        tag_push_events=tag_push_events,
                        pipeline_events=pipeline_events,
                        job_events=job_events,
                        wiki_page_events=wiki_page_events,
                        deployment_events=deployment_events,
                        releases_events=releases_events,
                    )
                    registered.append(project_id)

            except GitLabAPIError as e:
                print(f"[Register] project {project_id} ({project_name}): webhook error: {e}")
                failed.append({"project_id": project_id, "error": str(e)})

        # Save webhook data to MongoDB after successful registration
        # Convert trigger_tokens keys from int to str for MongoDB (BSON requires string keys)
        trigger_tokens_for_db = {
            str(project_id): token for project_id, token in trigger_tokens.items()
        }
        
        # Fetch existing webhook data to merge trigger_tokens instead of overwriting
        key = f"{request.group_id}:{request.name}"
        existing_webhook = await webhooks_collection.find_one({"_id": key})
        existing_trigger_tokens = {}
        existing_registered = []
        existing_updated = []
        existing_skipped = []
        
        if existing_webhook and existing_webhook.get("data"):
            existing_data = existing_webhook["data"]
            existing_trigger_tokens = existing_data.get("trigger_tokens", {})
            existing_registered = existing_data.get("registered", [])
            existing_updated = existing_data.get("updated", [])
            existing_skipped = existing_data.get("skipped", [])
        
        # Merge trigger_tokens (new ones take precedence, but don't lose existing ones)
        merged_trigger_tokens = {**existing_trigger_tokens, **trigger_tokens_for_db}
        
        # Merge lists (union, removing duplicates, sorted for consistency)
        merged_registered = sorted(list(set(existing_registered + registered)))
        merged_updated = sorted(list(set(existing_updated + updated)))
        merged_skipped = sorted(list(set(existing_skipped + skipped)))
        
        await save_or_update_webhook(
            request.group_id,
            request.name,
            {
                "url": request.webhook_url,
                "registered": merged_registered,
                "updated": merged_updated,
                "skipped": merged_skipped,
                "webhook_token": request.webhook_token,
                "target_trigger_url": request.target_trigger_url,
                "trigger_tokens": merged_trigger_tokens,
            },
        )

        # Update pagination info for "all pages" case
        if page is None and pagination_info:
            # When fetching all pages, update pagination to reflect total processing
            pagination_info = {
                **pagination_info,
                "page": None,  # Indicates all pages were processed
                "total_processed": len(all_projects),
            }

        return {
            "registered": registered,
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "trigger_tokens": trigger_tokens,
            "pagination": pagination_info,
        }

    except GitLabAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except GitLabAPIError as e:
        status_code = e.status_code or 500
        raise HTTPException(status_code=status_code, detail=str(e))


@app.post("/gitlab/webhook")
async def receive_gitlab_webhook(request: Request):
    """Receive GitLab webhooks, validate token, and trigger target URL if code phrase is found.
    
    Args:
        request: FastAPI Request object containing headers and JSON body
        
    Returns:
        JSON response indicating whether code phrase was found
        
    Raises:
        HTTPException: If X-Gitlab-Token is missing or invalid
    """
    # Extract and validate token
    token = request.headers.get("X-Gitlab-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing X-Gitlab-Token")

    # Find webhook by token
    webhook = await webhooks_collection.find_one({"data.webhook_token": token})
    if not webhook:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Parse JSON payload
    body = await request.json()
    
    # Extract comment text from webhook payload
    # GitLab comment events typically have the note in object_attributes.note
    note = body.get("object_attributes", {}).get("note", "")
    
    # Check if code phrase is in the comment
    found = CODE_PHRASE in note

    if found:
        print("[Webhook] Code phrase found in comment.")
        # Extract project ID from webhook payload
        project_id = body.get("project", {}).get("id")
        if not project_id:
            print("[Webhook] Project ID not found in webhook payload.")
            return {"found": found}
        
        # Get trigger token for this project
        trigger_tokens = webhook["data"].get("trigger_tokens", {})
        trigger_token = trigger_tokens.get(str(project_id))
        if not trigger_token:
            print(f"[Webhook] Trigger token not found for project {project_id}.")
            return {"found": found}
        
        # Extract ref from webhook payload
        # For merge request events, try target_branch or source_branch
        ref = (
            body.get("merge_request", {}).get("source_branch")
            or body.get("ref")
            or body.get("object_attributes", {}).get("ref")
            or body.get("project", {}).get("default_branch")
        )
        if not ref:
            print("[Webhook] Ref not found in webhook payload.")
            return {"found": False}

        # --- Extract only relevant info for the AI ---
        attrs = body.get("object_attributes", {})
        mr = body.get("merge_request", {})
        user = body.get("user", {})
        project = body.get("project", {})
        repo = body.get("repository", {})
        last_commit = mr.get("last_commit", {})

        flow_context = {
            "event": body.get("event_name", body.get("object_kind", "")),
            "user": {
                "name": user.get("name"),
                "username": user.get("username"),
                "email": user.get("email"),
            },
            "project": {
                "id": project.get("id"),
                "name": project.get("name"),
                "path_with_namespace": project.get("path_with_namespace"),
                "web_url": project.get("web_url"),
            },
            "merge_request": {
                "iid": mr.get("iid"),
                "title": mr.get("title"),
                "source_branch": mr.get("source_branch"),
                "target_branch": mr.get("target_branch"),
                "url": mr.get("url") or mr.get("web_url"),
            },
            "note": {
                "text": attrs.get("note"),
                "url": attrs.get("url"),
                "action": attrs.get("action"),
                "created_at": attrs.get("created_at"),
            },
            "commit": {
                "id": last_commit.get("id"),
                "message": last_commit.get("message"),
            },
        }

        ai_flow_input = attrs.get("note") or ""
        input_event = flow_context["event"]

        # --- Fire configured triggers ---
        triggers = get_triggers()
        results = []
        for trigger in triggers:
            result = await trigger.fire(
                project_id=project_id,
                ref=ref,
                trigger_token=trigger_token,
                flow_context=flow_context,
                ai_flow_input=ai_flow_input,
                input_event=input_event,
            )
            results.append(result)
        return {"found": found, "trigger_results": results}
    else:
        print("[Webhook] Code phrase not found.")

    return {"found": found}

