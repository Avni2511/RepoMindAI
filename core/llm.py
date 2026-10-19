
from django.conf import settings
from google import genai
from google.genai import types


def ask_llm(question: str) -> str:
    """Send a question to Gemini and return its text answer."""

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=30000),
    )

    prompt = f"""
You are RepoMind AI, a helpful programming assistant.

Explain concepts clearly and concisely.

Important:
- No repository has been indexed yet.
- Never claim to have inspected a repository.
- If asked about a specific repository, explain that indexing
  has not been implemented yet.

User question:
{question}
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=128,
            thinking_config=types.ThinkingConfig(
                thinking_level="low"
            ),
        ),
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text
