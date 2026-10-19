from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from google.genai import errors

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