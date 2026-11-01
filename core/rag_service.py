
from core.retrieval import retrieve_relevant_chunks
from core.llm import ask_llm


def answer_repository_question(
    question: str,
    repository_id: int,
    top_k: int = 3,
) -> dict:
    """Answer a question using retrieved repository code."""

    chunks = retrieve_relevant_chunks(
        question=question,
        repository_id=repository_id,
        top_k=top_k,
    )

    if not chunks:
        return {
            "answer": "No indexed code chunks were found for this repository.",
            "sources": [],
        }

    context_parts = []
    sources = []

    for chunk in chunks:
        file_path = chunk["file_path"]
        start_line = chunk["start_line"]
        end_line = chunk["end_line"]

        context_parts.append(
            f"File: {file_path}\n"
            f"Lines: {start_line}-{end_line}\n"
            f"Code:\n{chunk['content']}"
        )

        sources.append({
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "similarity": round(chunk["similarity"], 4),
        })

    context = "\n\n---\n\n".join(context_parts)

    answer = ask_llm(
        question=question,
        context=context,
    )

    return {
        "answer": answer,
        "sources": sources,
    }
