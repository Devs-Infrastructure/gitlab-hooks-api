"""OpenCode trigger: one OpenCode session per MR, requests serialized per MR."""
import asyncio
import re
from collections import deque

from app.config import (
    OPENCODE_AGENT,
    OPENCODE_DIRECTORY,
    OPENCODE_FOLLOWUP_PROMPT,
    OPENCODE_GITLAB_TOKEN,
    OPENCODE_INITIAL_PROMPT,
    OPENCODE_MODEL,
    OPENCODE_RUN_TIMEOUT,
    OPENCODE_SESSION_URL,
    OPENCODE_START_TIMEOUT,
    OPENCODE_TRIGGER_PHRASE,
)
from app.database.opencode import claim_event, get_mr_session, save_mr_session
from app.services.gitlab import GitLabClient
from app.services.opencode import OpenCodeClient
from app.triggers.base import BaseTrigger

# Module-level: trigger instances are created per request. Per-process only.
_queues: dict[str, deque] = {}
_workers: dict[str, asyncio.Task] = {}


def _phrase_pattern(phrase: str) -> re.Pattern:
    return re.compile(rf"^\s*{re.escape(phrase)}(?![\w-])[\s:,]*", re.IGNORECASE)


def worktree_path(repo_dir: str, mr_iid: int, source_branch: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", source_branch).strip("-")
    worktree = f".worktrees/mr-{mr_iid}-{slug}"
    return worktree if repo_dir == "." else f"{repo_dir}/{worktree}"


def session_link(session_id: str, directory: str | None) -> str:
    if not OPENCODE_SESSION_URL:
        return f"`{session_id}`"
    url = OPENCODE_SESSION_URL.format(session_id=session_id, directory=directory or "")
    return f"[`{session_id}`]({url})"


class OpenCodeTrigger(BaseTrigger):
    """Sends MR instructions to a per-MR OpenCode session via `prompt_async`."""

    def __init__(
        self,
        client: OpenCodeClient | None = None,
        phrase: str = OPENCODE_TRIGGER_PHRASE,
        directory_template: str = OPENCODE_DIRECTORY,
        agent: str = OPENCODE_AGENT,
        model: str = OPENCODE_MODEL,
        run_timeout: int = OPENCODE_RUN_TIMEOUT,
        start_timeout: int = OPENCODE_START_TIMEOUT,
        gitlab: GitLabClient | None = None,
        gitlab_token: str = OPENCODE_GITLAB_TOKEN,
    ):
        self._client = client or OpenCodeClient()
        self._gitlab = gitlab or GitLabClient()
        self._gitlab_token = gitlab_token
        self._pattern = _phrase_pattern(phrase)
        self._directory_template = directory_template
        self._agent = agent or None
        self._model = model or None
        self._run_timeout = run_timeout
        self._start_timeout = start_timeout

    def matches(self, note: str) -> bool:
        return bool(self._pattern.match(note or ""))

    async def fire(
        self,
        project_id: int,
        ref: str,
        trigger_token: str | None,
        flow_context: dict,
        ai_flow_input: str,
        input_event: str,
    ) -> dict:
        note = flow_context.get("note", {})
        mr = flow_context.get("merge_request", {})
        if note.get("noteable_type") != "MergeRequest" or not mr.get("iid"):
            return {"skipped": "not_a_merge_request_comment"}

        request = self._pattern.sub("", ai_flow_input, count=1).strip()
        if not request:
            return {"skipped": "empty_request"}

        event_key = f"note:{note.get('id')}" if note.get("id") else None
        if event_key and not await claim_event(event_key):
            print(f"[OpenCodeTrigger] Duplicate delivery of {event_key}, ignoring.")
            return {"skipped": "duplicate"}

        project = flow_context.get("project", {})
        job = {
            "project_id": project_id,
            "path_with_namespace": project.get("path_with_namespace") or "",
            "mr_iid": mr["iid"],
            "mr_title": mr.get("title") or "",
            "mr_url": mr.get("url") or "",
            "source_branch": mr.get("source_branch") or ref,
            "request": request,
            "discussion_id": note.get("discussion_id"),
        }
        mr_key = f"{project_id}:{mr['iid']}"
        worker = _workers.get(mr_key)
        waiting = worker is not None and not worker.done()
        position = self._enqueue(mr_key, job)
        print(f"[OpenCodeTrigger] Queued request for MR {mr_key} (position {position}).")
        if waiting:
            await self._reply(job, f"⏳ Queued (#{position}): OpenCode is still working on "
                                   f"a previous request for this MR.")
        return {"status": "queued", "merge_request": mr_key, "position": position}

    async def _reply(self, job: dict, text: str):
        """Answer the triggering MR comment. Never raises."""
        if not self._gitlab_token:
            return
        try:
            await self._gitlab.create_mr_note(
                self._gitlab_token, job["project_id"], job["mr_iid"], text,
                discussion_id=job.get("discussion_id"),
            )
        except Exception as e:
            print(f"[OpenCodeTrigger] MR {job['project_id']}:{job['mr_iid']}: "
                  f"failed to post reply: {e}")

    def _enqueue(self, mr_key: str, job: dict) -> int:
        queue = _queues.setdefault(mr_key, deque())
        queue.append(job)
        worker = _workers.get(mr_key)
        if worker is None or worker.done():
            _workers[mr_key] = asyncio.create_task(self._drain(mr_key))
        return len(queue)

    async def _drain(self, mr_key: str):
        queue = _queues[mr_key]
        while queue:
            job = queue.popleft()
            try:
                await self._process(job)
            except Exception as e:
                print(f"[OpenCodeTrigger] MR {mr_key}: failed to process request: {e}")
                session = job.get("session_id")
                where = f" (session {session_link(session, job.get('directory'))})" if session else ""
                await self._reply(job, f"❌ OpenCode failed{where}: {e}")
        _queues.pop(mr_key, None)
        _workers.pop(mr_key, None)

    def _directory(self, job: dict) -> str | None:
        if not self._directory_template:
            return None
        return self._directory_template.format(
            project_id=job["project_id"], path_with_namespace=job["path_with_namespace"]
        )

    async def _process(self, job: dict):
        project_id, mr_iid = job["project_id"], job["mr_iid"]
        # Without a per-repo directory the session runs in a shared workspace.
        repo_dir = "." if self._directory_template else job["path_with_namespace"]
        worktree = worktree_path(repo_dir, mr_iid, job["source_branch"])
        prompt_vars = {**job, "repo_dir": repo_dir, "worktree": worktree}

        stored = await get_mr_session(project_id, mr_iid)
        session_id = stored and stored.get("session_id")
        directory = stored.get("directory") if stored else self._directory(job)

        if session_id and await self._client.session_exists(session_id, directory):
            text = OPENCODE_FOLLOWUP_PROMPT.format(**prompt_vars)
            print(f"[OpenCodeTrigger] MR {project_id}:{mr_iid}: reusing session {session_id}")
        else:
            directory = self._directory(job)
            session = await self._client.create_session(
                title=f"MR !{mr_iid}: {job['mr_title']}".strip(), directory=directory
            )
            session_id = session["id"]
            await save_mr_session(project_id, mr_iid, {
                "project_id": project_id,
                "mr_iid": mr_iid,
                "session_id": session_id,
                "directory": directory,
                "mr_url": job["mr_url"],
                "source_branch": job["source_branch"],
                "worktree": worktree,
            })
            text = OPENCODE_INITIAL_PROMPT.format(**prompt_vars)
            print(f"[OpenCodeTrigger] MR {project_id}:{mr_iid}: created session {session_id}")

        job["session_id"], job["directory"] = session_id, directory
        link = session_link(session_id, directory)

        if not await self._client.wait_until_idle(session_id, directory, timeout=self._run_timeout):
            print(f"[OpenCodeTrigger] Session {session_id} still busy after "
                  f"{self._run_timeout}s, sending anyway.")

        known_ids = await self._client.message_ids(session_id, directory)
        await self._client.prompt_async(
            session_id, text, directory=directory, agent=self._agent, model=self._model
        )
        print(f"[OpenCodeTrigger] MR {project_id}:{mr_iid}: prompt sent to {session_id}")

        error = await self._client.wait_until_started(
            session_id, known_ids, directory, timeout=self._start_timeout
        )
        if error:
            print(f"[OpenCodeTrigger] MR {project_id}:{mr_iid}: session {session_id} failed: {error}")
            await self._reply(job, f"❌ OpenCode failed to start in session {link}: {error}")
            return
        print(f"[OpenCodeTrigger] MR {project_id}:{mr_iid}: session {session_id} started")
        await self._reply(job, f"🚀 OpenCode started working on this in session {link}.")

        await self._client.wait_until_idle(session_id, directory, timeout=self._run_timeout)
        error = await self._client.last_error(session_id, directory)
        if error:
            print(f"[OpenCodeTrigger] MR {project_id}:{mr_iid}: session {session_id} failed: {error}")
            await self._reply(job, f"❌ OpenCode run failed in session {link}: {error}")
            return
        print(f"[OpenCodeTrigger] MR {project_id}:{mr_iid}: session {session_id} finished")
