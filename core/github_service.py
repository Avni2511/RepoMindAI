
import re
import requests

GITHUB_API_BASE = "https://api.github.com"
REQUEST_TIMEOUT = 15

# Files we are willing to inspect in this first version.
ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".md",
}

MAX_FILE_SIZE = 200_000  # 200 KB per file


def parse_github_url(repo_url: str) -> tuple[str, str]:
    """Extract owner and repository name from a GitHub URL."""

    pattern = (
        r"https?://github\.com/"
        r"([A-Za-z0-9-]+)/"
        r"([A-Za-z0-9_.-]+)/?"
    )

    match = re.fullmatch(pattern, repo_url.strip())

    if not match:
        raise ValueError("Please provide a valid GitHub repository URL.")

    owner, repo = match.groups()

    # Reject URL paths, query strings and fragments by matching
    # the complete URL above.
    if repo in {".", ".."}:
        raise ValueError("Invalid repository name.")

    return owner, repo


def github_get(url: str) -> dict | list:
    """Make a timed request to the GitHub API."""

    response = requests.get(
        url,
        headers={"Accept": "application/vnd.github+json"},
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 404:
        raise ValueError(
            "Repository or resource not found, or not publicly accessible."
        )

    if response.status_code == 403:
        raise ValueError(
            "GitHub rate limit or access restriction. Try again later."
        )

    response.raise_for_status()
    return response.json()


def fetch_repository(repo_url: str) -> dict:
    """Fetch basic information about a public repository."""

    owner, repo = parse_github_url(repo_url)

    data = github_get(
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    )

    return {
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data.get("description"),
        "default_branch": data["default_branch"],
        "html_url": data["html_url"],
    }


def fetch_repository_files(
    repo_url: str,
    max_files: int = 30,
) -> list[dict]:
    """Fetch a limited number of relevant source files."""

    owner, repo = parse_github_url(repo_url)
    metadata = fetch_repository(repo_url)
    branch = metadata["default_branch"]

    tree_url = (
        f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        f"/git/trees/{branch}?recursive=1"
    )

    tree_data = github_get(tree_url)

    if tree_data.get("truncated"):
        raise ValueError(
            "Repository file listing is too large for this version."
        )

    files = []

    for item in tree_data.get("tree", []):
        if item.get("type") != "blob":
            continue

        path = item["path"]
        extension = "." + path.rsplit(".", 1)[-1].lower() \
            if "." in path.rsplit("/", 1)[-1] else ""

        if extension not in ALLOWED_EXTENSIONS:
            continue

        # Avoid likely generated or dependency directories.
        if any(
            part.lower() in {
                ".git", "node_modules", "venv", ".venv",
                "__pycache__", "dist", "build",
            }
            for part in path.split("/")
        ):
            continue

        # Skip files GitHub reports as too large.
        if item.get("size", 0) > MAX_FILE_SIZE:
            continue

        file_data = github_get(item["url"])

        import base64

        if file_data.get("encoding") != "base64":
            continue

        content = base64.b64decode(
            file_data["content"]
        ).decode("utf-8", errors="replace")

        files.append({
            "path": path,
            "size": len(content.encode("utf-8")),
            "content": content,
        })

        if len(files) >= max_files:
            break

    return files
