
def chunk_text(
    text: str,
    file_path: str,
    chunk_size: int = 80,
    overlap: int = 10,
) -> list[dict]:
    """
    Split text into chunks while preserving original line numbers.

    chunk_size: maximum number of lines per chunk.
    overlap: number of lines shared between consecutive chunks.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size."
        )

    lines = text.splitlines()
    chunks = []
    start = 0

    while start < len(lines):
        end = min(start + chunk_size, len(lines))

        chunk_content = "\n".join(lines[start:end])

        chunks.append({
            "file_path": file_path,
            "start_line": start + 1,
            "end_line": end,
            "content": chunk_content,
        })

        if end == len(lines):
            break

        start = end - overlap

    return chunks


def chunk_repository_files(
    files: list[dict],
    chunk_size: int = 80,
    overlap: int = 10,
) -> list[dict]:
    """Split a collection of repository files into chunks."""

    all_chunks = []

    for file in files:
        file_chunks = chunk_text(
            text=file["content"],
            file_path=file["path"],
            chunk_size=chunk_size,
            overlap=overlap,
        )

        all_chunks.extend(file_chunks)

    return all_chunks
