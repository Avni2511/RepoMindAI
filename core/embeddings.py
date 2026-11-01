
from sentence_transformers import SentenceTransformer

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def get_embedding_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def generate_embedding(text: str) -> list[float]:
    if not text or not text.strip():
        raise ValueError("Text cannot be empty.")

    model = get_embedding_model()
    vector = model.encode(text, normalize_embeddings=True)

    return vector.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    if any(not text or not text.strip() for text in texts):
        raise ValueError("Texts cannot contain empty values.")

    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)

    return vectors.tolist()
