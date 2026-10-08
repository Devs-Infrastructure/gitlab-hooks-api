"""Application configuration."""
from decouple import config

GITLAB_HOST = config("GITLAB_HOST")

MONGO_URL = config(
    "MONGO_URL",
    default="mongodb://root:example@localhost:27017/"
)

CODE_PHRASE = config("CODE_PHRASE", default="trigger-bot")

# --- Trigger configuration ---
TRIGGER_TYPE = config("TRIGGER_TYPE", default="gitlab_pipeline")

# --- OpenCode trigger ---
OPENCODE_HOST     = config("OPENCODE_HOST", default="")
OPENCODE_USERNAME = config("OPENCODE_USERNAME", default="opencode")
OPENCODE_PASSWORD = config("OPENCODE_PASSWORD", default="")
OPENCODE_TRIGGER_PHRASE = config("OPENCODE_TRIGGER_PHRASE", default="boss")
# Per-repo checkout, e.g. /workspace/{path_with_namespace}. Empty = server cwd, repo cloned under it.
OPENCODE_DIRECTORY = config("OPENCODE_DIRECTORY", default="")
OPENCODE_AGENT     = config("OPENCODE_AGENT", default="")
# "provider/model"
OPENCODE_MODEL     = config("OPENCODE_MODEL", default="")
OPENCODE_RUN_TIMEOUT = config("OPENCODE_RUN_TIMEOUT", default=3600, cast=int)
# Seconds to wait for a sent prompt to start running before reporting failure.
OPENCODE_START_TIMEOUT = config("OPENCODE_START_TIMEOUT", default=60, cast=int)
# Link posted in MR replies; placeholders {session_id}, {directory}. Empty = id only.
OPENCODE_SESSION_URL = config("OPENCODE_SESSION_URL", default="")
# GitLab token (api scope) used to reply to the triggering MR comment. Empty = no replies.
OPENCODE_GITLAB_TOKEN = config("OPENCODE_GITLAB_TOKEN", default="")

OPENCODE_INITIAL_PROMPT = config("OPENCODE_INITIAL_PROMPT", default=(
    "Work on {mr_url}. Use glab to read the MR, comments, discussions, diff and CI. "
    "Use the repository at {repo_dir} (clone {path_with_namespace} there with glab if missing). "
    "Create or reuse {worktree}, checkout the MR source branch ({source_branch}) there, "
    "and verify the worktree is on {source_branch} before editing. "
    "Do all work only in that worktree. Make the smallest requested change, test it, "
    "commit and push to the existing MR branch. Never create another MR or unrelated branch.\n\n"
    "Request: {request}"
))
OPENCODE_FOLLOWUP_PROMPT = config("OPENCODE_FOLLOWUP_PROMPT", default=(
    "New instruction for {mr_url}: {request}. "
    "Refresh relevant context with glab and continue in the existing MR worktree ({worktree})."
))

# Review newly opened MRs (needs merge_requests_events on the webhook).
OPENCODE_REVIEW_ON_OPEN = config("OPENCODE_REVIEW_ON_OPEN", default=True, cast=bool)
OPENCODE_REVIEW_PROMPT = config("OPENCODE_REVIEW_PROMPT", default=(
    "Review {mr_url} ({source_branch} -> {target_branch}). Read the MR and diff with glab; "
    "check out {source_branch} in {worktree} (repo {repo_dir}, clone {path_with_namespace} if missing) "
    "and read the surrounding code. Do not edit, commit or push - unless asked.\n\n"
    "Report only real problems, most important first:\n"
    "1. Correctness: logic errors, edge cases, error handling, races.\n"
    "2. Security: injection, auth gaps, leaked secrets, unsafe input.\n"
    "3. Codebase fit: duplicates existing helpers, breaks established patterns.\n"
    "4. Garbage: dead code, debug leftovers, unrelated changes.\n"
    "No style nitpicks.\n\n"
    "Post each finding (problem + fix) as an inline comment on the exact line: glab api POST "
    "projects/{project_id}/merge_requests/{mr_iid}/discussions with a text position "
    "(diff_refs SHAs; new_path/new_line, or old_path/old_line for removed lines). "
    "End with one short summary note."
))
