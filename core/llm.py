from django.conf import settings
from google import genai
from google.genai import types



def ask_llm(question: str, context: str = "") -> str:
    """Send a question and optional repository context to Gemini."""

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=30000),
    )

    if context.strip():
        repository_instruction = f"""
Answer the user's question using the repository context below.

Rules:
- Base repository-specific answers on the supplied code.
- If the context does not contain enough information, say so.
- Mention source file paths and line numbers when relevant.
- Do not invent code or claim facts unsupported by the context.

Repository context:
{context}
"""
    else:
        repository_instruction = """
No relevant repository code was retrieved.
Do not claim to have inspected repository code.
Explain that there is insufficient indexed code to answer
repository-specific questions accurately.
"""

    prompt = f"""
You are RepoMind AI, a helpful programming assistant.

Explain concepts clearly and concisely.

{repository_instruction}

User question:
{question}
"""

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=512,
            thinking_config=types.ThinkingConfig(
                thinking_level="low"
            ),
        ),
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text
