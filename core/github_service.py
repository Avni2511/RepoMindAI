import re
import base64
import requests
from django.conf import settings


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

# Prefer source code over documentation and configuration files.
PRIORITY_EXTENSIONS = {
    ".py": 0,
    ".js": 1,
    ".ts": 1,
    ".jsx": 1,
    ".tsx": 1,
    ".html": 2,
    ".json": 3,
    ".yml": 3,
    ".yaml": 3,
    ".toml": 3,
    ".md": 4,
    ".css": 4,
}

EXCLUDED_DIRECTORIES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
}


def parse_github_url(repo_url: str) -> tuple[str, str]:
    """Extract owner and repository name from a GitHub URL."""

    pattern = (
        r"https?://github\.com/"
        r"([A-Za-z0-9-]+)/"
        r"([A-Za-z0-9_.-]+)/?"
    )

    match = re.fullmatch(pattern, repo_url.strip())

    if not match:
        raise ValueError(
            "Please provide a valid GitHub repository URL."
        )

    owner, repo = match.groups()

    if repo in {".", ".."}:
        raise ValueError("Invalid repository name.")

    # Allow common GitHub repository URLs ending in .git.
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not repo or repo in {".", ".."}:
        raise ValueError("Invalid repository name.")

    return owner, repo





def github_get(url: str) -> dict | list:
    """Make an authenticated, timed request to the GitHub API."""

    # Only allow requests to the official GitHub API host.
    if not url.startswith(f"{GITHUB_API_BASE}/"):
        raise ValueError("Requests are only allowed to the GitHub API.")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Add authentication only when a token is configured.
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    response = requests.get(
        url,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 401:
        raise ValueError(
            "GitHub authentication failed. Check your GITHUB_TOKEN."
        )

    if response.status_code == 403:
        print("\n--- GitHub API diagnostic ---")
        print("Request URL:", url)
        print(
            "Rate limit remaining:",
            response.headers.get("X-RateLimit-Remaining"),
        )
        print(
            "Rate limit resource:",
            response.headers.get("X-RateLimit-Resource"),
        )
        print(
            "Rate limit reset:",
            response.headers.get("X-RateLimit-Reset"),
        )
        print("Retry after:", response.headers.get("Retry-After"))
        print("GitHub response:", response.text[:1000])
        print("--- End diagnostic ---\n")

        raise ValueError(
            "GitHub returned HTTP 403. "
            "Check the diagnostic details in the Django terminal."
        )

    if response.status_code == 429:
        print("GitHub response:", response.text[:1000])
        raise ValueError(
            "GitHub returned HTTP 429. Wait before retrying."
        )

    if response.status_code == 404:
        raise ValueError(
            "Repository or resource not found, or not publicly accessible."
        )

    response.raise_for_status()
    return response.json()

def fetch_repository(repo_url: str) -> dict:
    """Fetch basic metadata for a public GitHub repository."""

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

    if max_files <= 0:
        return []

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

    tree_items = tree_data.get("tree", [])

    # Sort source files before documentation and configuration files.
    tree_items.sort(
        key=lambda item: (
            PRIORITY_EXTENSIONS.get(
                "." + item["path"].rsplit(".", 1)[-1].lower()
                if "." in item["path"].rsplit("/", 1)[-1]
                else "",
                99,
            ),
            item["path"],
        )
    )

    files = []

    for item in tree_items:
        if item.get("type") != "blob":
            continue

        path = item["path"]
        filename = path.rsplit("/", 1)[-1]

        extension = (
            "." + filename.rsplit(".", 1)[-1].lower()
            if "." in filename
            else ""
        )

        if extension not in ALLOWED_EXTENSIONS:
            continue

        # Avoid generated files and dependency directories.
        if any(
            part.lower() in EXCLUDED_DIRECTORIES
            for part in path.split("/")
        ):
            continue

        # Skip files GitHub reports as too large.
        if item.get("size", 0) > MAX_FILE_SIZE:
            continue

        file_data = github_get(item["url"])

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
