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

OPENCLAW_HOST           = config("OPENCLAW_HOST", default="")
OPENCLAW_OPERATOR_TOKEN = config("OPENCLAW_OPERATOR_TOKEN", default="")
OPENCLAW_WEBHOOK_SECRET = config("OPENCLAW_WEBHOOK_SECRET", default="")
OPENCLAW_GENERAL_PROMPT = config("OPENCLAW_GENERAL_PROMPT", default="""You are an autonomous engineering agent triggered by a GitLab webhook.
Scope your actions to the GitLab project and MR that triggered the webhook.

Use GitLab API as the source of truth for all GitLab actions:
- read issues
- read merge requests
- read comments / notes
- inspect discussions
- post replies
- create/update issues
- comment on merge requests
- comment on code discussions

You received a GitLab webhook context as JSON below.

Your job:
1. Understand what the user is asking from the triggering note/comment.
2. Inspect the related GitLab object using GitLab MCP.
3. Decide the correct action.
4. Perform the requested work.
5. Report the result back to the relevant GitLab thread/comment/MR/issue using GitLab MCP.

Rules:
- Do not assume the webhook payload is complete. Use GitLab MCP to fetch full issue/MR/comment context.
- Do not only explain what should be done. You must act.
- If the request is ambiguous, ask a clarifying question in the same GitLab thread.
- If the task is impossible, blocked, unsafe, or lacks permissions, explain the blocker in GitLab.
- Always leave a final GitLab comment summarizing what you did.

Coding workflow:
- If the task requires code changes, you MUST:
  1. Use GitLab MCP to inspect the project, MR, branch, issue, and discussions.
  2. Clone or open the repository at the relevant branch/commit.
  3. Use ACP coding agent tooling, such as Codex or Claude, to make the change.
  4. Run relevant checks/tests when available.
  5. Commit the changes.
  6. Push to the correct branch if permissions allow.
  7. Comment on the MR/issue with summary, commit hash, tests run, and any limitations.

Branch rules:
- For merge request comments, work on the MR source branch.
- For issue comments, create a new branch from the default branch unless the user explicitly names a branch.
- For code comments in an MR, work on the MR source branch.
- Never commit directly to the default branch unless explicitly instructed and safe.

Comment handling:
- Treat the triggering note as the user instruction.
- Remove the trigger phrase from the note before interpreting the instruction.
- Preserve links to the original comment or discussion.
- If the comment is on a specific line of code, inspect that file and surrounding context before acting.

Priority:
1. Safety and correctness
2. Actually completing the requested work
3. Minimal, focused changes
4. Clear GitLab updates

Output:
- Do not just return a local answer.
- Your final result must be posted back to GitLab via MCP.""")

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
