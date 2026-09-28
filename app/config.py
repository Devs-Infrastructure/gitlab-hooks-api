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
