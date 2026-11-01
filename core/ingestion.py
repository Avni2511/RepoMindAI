from django.db import transaction

from core.models import Repository, CodeChunk
from core.github_service import fetch_repository, fetch_repository_files
from core.chunking import chunk_repository_files
from core.embeddings import generate_embeddings


@transaction.atomic
def ingest_repository(repo_url: str, max_files: int = 5) -> dict:
    metadata = fetch_repository(repo_url)

    repository, _ = Repository.objects.update_or_create(
        full_name=metadata["full_name"],
        defaults={
            "name": metadata["name"],
            "repo_url": metadata["html_url"],
            "default_branch": metadata["default_branch"],
        },
    )

    files = fetch_repository_files(repo_url, max_files=max_files)
    chunks = chunk_repository_files(
        files,
        chunk_size=80,
        overlap=10,
    )

    # Generate embeddings for all chunks in one batch.
    valid_chunks = [
        chunk for chunk in chunks
        if chunk["content"].strip()
    ]

    vectors = generate_embeddings([
        chunk["content"] for chunk in valid_chunks
    ])

    # Replace previously stored chunks for this repository.
    repository.chunks.all().delete()

    CodeChunk.objects.bulk_create([
        CodeChunk(
            repository=repository,
            file_path=chunk["file_path"],
            start_line=chunk["start_line"],
            end_line=chunk["end_line"],
            content=chunk["content"],
            embedding=vector,
        )
        for chunk, vector in zip(valid_chunks, vectors)
    ])

    return {
        "repository": repository.full_name,
        "files_fetched": len(files),
        "chunks_created": len(valid_chunks),
        "embeddings_created": len(vectors),
    }
