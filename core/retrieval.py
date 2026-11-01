import torch
from sentence_transformers import util

from core.models import CodeChunk
from core.embeddings import generate_embedding


def retrieve_relevant_chunks(
    question: str,
    repository_id: int,
    top_k: int = 3,
) -> list[dict]:
    """Retrieve the most relevant saved code chunks."""

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    chunks = list(
        CodeChunk.objects.filter(
            repository_id=repository_id
        ).only(
            "file_path",
            "start_line",
            "end_line",
            "content",
            "embedding",
        )
    )

    if not chunks:
        return []

    # Generate an embedding only for the user's question.
    question_vector = generate_embedding(question)

    # Reuse the embeddings already saved in the database.
    chunk_vectors = torch.tensor(
        [chunk.embedding for chunk in chunks],
        dtype=torch.float32,
    )

    question_tensor = torch.tensor(
        question_vector,
        dtype=torch.float32,
    ).unsqueeze(0)

    similarities = util.cos_sim(
        question_tensor,
        chunk_vectors,
    )[0]

    k = min(top_k, len(chunks))
    ranked_indices = torch.topk(similarities, k=k).indices.tolist()

    results = []

    for index in ranked_indices:
        chunk = chunks[index]

        results.append({
            "file_path": chunk.file_path,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "content": chunk.content,
            "similarity": float(similarities[index]),
        })

    return results
