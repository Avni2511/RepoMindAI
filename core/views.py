from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from google.genai import errors

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
    # 1. Read the question from the request body.
    question = request.data.get("question", "")

    # 2. Validate the input.
    if not isinstance(question, str) or not question.strip():
        return Response(
            {"error": "Please provide a non-empty question."},
            status=status.HTTP_400_BAD_REQUEST
        )

    question = question.strip()

    if len(question) > 2000:
        return Response(
            {"error": "Question must be 2000 characters or fewer."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 3. Send the question to Gemini.
    try:
        answer = ask_llm(question)

        # 4. Return Gemini's answer as JSON.
        return Response({
            "question": question,
            "answer": answer
        })

    except RuntimeError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except errors.APIError as exc:
        print("Gemini API error:", repr(exc))
        return Response(
            {"error": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY
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
