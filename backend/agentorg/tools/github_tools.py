from github import Github, GithubException, InputGitTreeElement

from .registry import ToolDefinition
from ..config import settings


def _github() -> Github:
    return Github(settings.github_token)


def _create_branch(branch_name: str, base_branch: str = "main", context=None) -> str:
    try:
        repo = _github().get_repo(settings.github_repo)
        base = repo.get_branch(base_branch)
        repo.create_git_ref(f"refs/heads/{branch_name}", base.commit.sha)
        return f"Created branch '{branch_name}' from '{base_branch}'"
    except GithubException as e:
        return f"GitHub error: {e.data.get('message', str(e))}"


def _commit_files(branch: str, files: dict, message: str, context=None) -> str:
    """Atomic multi-file commit via Git Data API."""
    try:
        repo = _github().get_repo(settings.github_repo)
        ref = repo.get_git_ref(f"heads/{branch}")
        base_commit = repo.get_git_commit(ref.object.sha)

        elements = []
        for path, content in files.items():
            blob = repo.create_git_blob(content, "utf-8")
            elements.append(InputGitTreeElement(path=path, mode="100644", type="blob", sha=blob.sha))

        new_tree = repo.create_git_tree(elements, base_commit.tree)
        new_commit = repo.create_git_commit(message, new_tree, [base_commit])
        ref.edit(new_commit.sha)

        return f"Committed {len(files)} file(s) to '{branch}' — {new_commit.sha[:8]}"
    except GithubException as e:
        return f"GitHub error: {e.data.get('message', str(e))}"


def _create_pr(title: str, body: str, head_branch: str, base_branch: str = "main", context=None) -> str:
    try:
        repo = _github().get_repo(settings.github_repo)
        pr = repo.create_pull(title=title, body=body, head=head_branch, base=base_branch)
        return f"Created PR #{pr.number}: {pr.html_url}"
    except GithubException as e:
        return f"GitHub error: {e.data.get('message', str(e))}"


CREATE_BRANCH = ToolDefinition(
    name="create_branch",
    description="Create a new git branch in the GitHub repo",
    input_schema={
        "type": "object",
        "properties": {
            "branch_name": {"type": "string", "description": "Name for the new branch"},
            "base_branch": {"type": "string", "description": "Branch to create from", "default": "main"},
        },
        "required": ["branch_name"],
    },
    handler=_create_branch,
)

COMMIT_FILES = ToolDefinition(
    name="commit_files",
    description="Atomically commit one or more files to a branch via the GitHub Git Data API",
    input_schema={
        "type": "object",
        "properties": {
            "branch": {"type": "string", "description": "Target branch name"},
            "files": {
                "type": "object",
                "description": "Map of file paths to file contents",
                "additionalProperties": {"type": "string"},
            },
            "message": {"type": "string", "description": "Commit message"},
        },
        "required": ["branch", "files", "message"],
    },
    handler=_commit_files,
)

CREATE_PR = ToolDefinition(
    name="create_pr",
    description="Open a GitHub pull request",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "PR title"},
            "body": {"type": "string", "description": "PR description (markdown supported)"},
            "head_branch": {"type": "string", "description": "Branch to merge from"},
            "base_branch": {"type": "string", "description": "Branch to merge into", "default": "main"},
        },
        "required": ["title", "body", "head_branch"],
    },
    handler=_create_pr,
)
