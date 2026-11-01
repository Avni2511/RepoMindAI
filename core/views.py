from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from google.genai import errors
from .chunking import chunk_repository_files
from .rag_service import answer_repository_question
from .github_service import fetch_repository, fetch_repository_files

from .llm import ask_llm


@api_view(["GET"])
def health_check(request):
    return Response({
        "status": "ok",
        "project": "RepoMind AI",
        "message": "Backend is running successfully"
    })



@api_view(["POST"])
def ask_ai(request):
    question = request.data.get("question", "")
    repository_id = request.data.get("repository_id")

    # Validate the question.
    if not isinstance(question, str) or not question.strip():
        return Response(
            {"error": "Please provide a non-empty question."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    question = question.strip()

    if len(question) > 2000:
        return Response(
            {"error": "Question must be 2000 characters or fewer."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate the repository ID.
    if isinstance(repository_id, bool):
        repository_id = None

    try:
        repository_id = int(repository_id)
        if repository_id <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return Response(
            {"error": "Please provide a valid repository_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Retrieve relevant code and ask Gemini using that context.
    try:
        result = answer_repository_question(
            question=question,
            repository_id=repository_id,
            top_k=3,
        )

        return Response({
            "question": question,
            "repository_id": repository_id,
            "answer": result["answer"],
            "sources": result["sources"],
        })

    except RuntimeError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    except errors.APIError as exc:
        print("Gemini API error:", repr(exc))
        return Response(
            {"error": "Gemini could not complete the request. Please try again."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

@api_view(["POST"])
def inspect_repository(request):
    repo_url = request.data.get("repo_url")

    if not isinstance(repo_url, str) or not repo_url.strip():
        return Response(
            {"error": "repo_url is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        repository = fetch_repository(repo_url)

        files = fetch_repository_files(
            repo_url,
            max_files=5,
        )

        return Response({
            "repository": repository,
            "files_fetched": len(files),
            "files": [
                {
                    "path": file["path"],
                    "size": file["size"],
                    "content": file["content"],
                }
                for file in files
            ],
        })

    except ValueError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception:
        # Log details server-side when production logging is configured.
        return Response(
            {"error": "Unable to inspect this repository right now."},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@api_view(["POST"])
def chunk_repository(request):
    repo_url = request.data.get("repo_url")

    if not isinstance(repo_url, str) or not repo_url.strip():
        return Response(
            {"error": "repo_url is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        files = fetch_repository_files(repo_url, max_files=5)

        chunks = chunk_repository_files(
            files,
            chunk_size=80,
            overlap=10,
        )

        return Response({
            "repository_url": repo_url,
            "files_fetched": len(files),
            "chunks_created": len(chunks),
            "chunks": chunks,
        })

    except ValueError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    except Exception:
        return Response(
            {"error": "Unable to chunk this repository right now."},
            status=status.HTTP_502_BAD_GATEWAY,
        )