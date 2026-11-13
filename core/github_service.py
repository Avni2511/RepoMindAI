import re
import base64
import requests
from django.conf import settings


GITHUB_API_BASE = "https://api.github.com"
REQUEST_TIMEOUT = 15

# Supported source-code and project file extensions.
ALLOWED_EXTENSIONS = {
    # Python
    ".py",

    # JavaScript / TypeScript
    ".js", ".ts", ".jsx", ".tsx",

    # Frontend
    ".html", ".css", ".scss", ".sass",
    ".vue", ".svelte",

    # Other programming languages
    ".java", ".cpp", ".c", ".h", ".hpp",
    ".cs", ".go", ".rs", ".php", ".rb",
    ".swift", ".kt", ".kts", ".dart",
    ".scala", ".r", ".sql",

    # Configuration and documentation
    ".json", ".yml", ".yaml", ".toml",
    ".xml", ".ini", ".cfg", ".properties",
    ".md", ".sh",
}

MAX_FILE_SIZE = 200_000  # 200 KB per file


# Programming languages are prioritized over configuration files.
PRIORITY_EXTENSIONS = {
    ".py": 0,
    ".js": 1,
    ".ts": 1,
    ".jsx": 1,
    ".tsx": 1,
    ".java": 1,
    ".cpp": 1,
    ".c": 1,
    ".h": 1,
    ".hpp": 1,
    ".cs": 1,
    ".go": 1,
    ".rs": 1,
    ".php": 1,
    ".rb": 1,
    ".swift": 1,
    ".kt": 1,
    ".kts": 1,
    ".dart": 1,
    ".scala": 1,
    ".r": 1,
    ".sql": 1,
    ".vue": 2,
    ".svelte": 2,
    ".html": 3,
    ".scss": 4,
    ".sass": 4,
    ".css": 4,
}


# Common directories that usually contain application source code.
# These are generic names, not tied to any particular project.
SOURCE_DIRECTORIES = {
    "src",
    "app",
    "apps",
    "lib",
    "server",
    "client",
    "api",
    "backend",
    "frontend",
    "routes",
    "controllers",
    "services",
    "models",
    "views",
    "components",
    "pages",
    "modules",
    "packages",
}


# Files that are mainly project configuration or startup files.
CONFIG_FILES = {
    "settings.py",
    "asgi.py",
    "wsgi.py",
    "manage.py",
    "tsconfig.json",
    "jsconfig.json",
    "webpack.config.js",
    "vite.config.js",
    "vite.config.ts",
    "next.config.js",
    "next.config.ts",
    "babel.config.js",
    "postcss.config.js",
    "eslint.config.js",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "docker-compose.yml",
    "docker-compose.yaml",
    "makefile",
}


# Documentation files are useful, but usually less important
# than actual application code during the first ingestion.
DOCUMENTATION_FILES = {
    "readme.md",
    "contributing.md",
    "changelog.md",
    "license.md",
}


# Avoid dependencies, virtual environments, caches and build output.
EXCLUDED_DIRECTORIES = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    ".cache",
    ".tox",
    ".turbo",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "site-packages",
    "dist",
    "build",
    "coverage",
    "vendor",
    "target",
    "out",
    "migrations",
}


EXCLUDED_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pipfile.lock",
    "composer.lock",
    "cargo.lock",
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

    if repo.endswith(".git"):
        repo = repo[:-4]

    if not repo or repo in {".", ".."}:
        raise ValueError("Invalid repository name.")

    return owner, repo


def github_get(url: str) -> dict | list:
    """Make an authenticated, timed request to the GitHub API."""

    if not url.startswith(f"{GITHUB_API_BASE}/"):
        raise ValueError(
            "Requests are only allowed to the GitHub API."
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = getattr(settings, "GITHUB_TOKEN", None)

    if token:
        headers["Authorization"] = f"Bearer {token}"

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


def get_file_extension(filename: str) -> str:
    """Return a lowercase file extension."""

    if "." not in filename:
        return ""

    return "." + filename.rsplit(".", 1)[-1].lower()



def file_priority(item: dict) -> tuple:
    """
    Assign a priority to each file.

    Lower priority numbers are fetched first.
    """

    path = item["path"]
    parts = path.split("/")
    filename = parts[-1].lower()

    extension = get_file_extension(filename)

    # Programming source files.
    is_source_code = extension in PRIORITY_EXTENSIONS

    # Test files.
    is_test_file = (
        filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename.endswith(".test.js")
        or filename.endswith(".test.ts")
        or filename.endswith(".spec.js")
        or filename.endswith(".spec.ts")
        or any(
            part.lower() in {"tests", "test", "__tests__"}
            for part in parts[:-1]
        )
    )

    # Configuration files.
    is_config = filename in CONFIG_FILES

    # Documentation files.
    is_documentation = (
        filename in DOCUMENTATION_FILES
        or extension == ".md"
    )

    # Common source directories across frameworks.
    has_source_directory = any(
        part.lower() in SOURCE_DIRECTORIES
        for part in parts[:-1]
    )

    # Important application files across frameworks.
    important_files = {
        "models.py",
        "views.py",
        "serializers.py",
        "permissions.py",
        "services.py",
        "tasks.py",
        "consumers.py",
        "routes.py",
        "controllers.py",
        "schemas.py",
        "repositories.py",
        "middleware.py",
        "handlers.py",
        "resolvers.py",
        "models.js",
        "models.ts",
        "controller.js",
        "controller.ts",
        "service.js",
        "service.ts",
        "route.js",
        "route.ts",
        "routes.js",
        "routes.ts",
    }

    # Assign category priority.
    if is_test_file:
        category_priority = 2

    elif is_config:
        category_priority = 4

    elif is_documentation:
        category_priority = 5

    elif filename in important_files:
        category_priority = 0

    elif is_source_code and has_source_directory:
        category_priority = 1

    elif is_source_code:
        category_priority = 3

    else:
        category_priority = 4

    # Prioritize programming languages within each category.
    extension_priority = PRIORITY_EXTENSIONS.get(
        extension, 99
    )

    return (
        category_priority,
        extension_priority,
        path.lower(),
    )


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

    # Select relevant files and sort them by generic priority.
    tree_items.sort(key=file_priority)

    files = []

    for item in tree_items:

        if item.get("type") != "blob":
            continue

        path = item["path"]
        filename = path.rsplit("/", 1)[-1]
        extension = get_file_extension(filename)

        if extension not in ALLOWED_EXTENSIONS:
            continue

        if filename.lower() in EXCLUDED_FILES:
            continue

        # Skip dependency, cache and generated directories.
        if any(
            part.lower() in EXCLUDED_DIRECTORIES
            for part in path.split("/")
        ):
            continue

        # Skip files that exceed the configured size.
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
