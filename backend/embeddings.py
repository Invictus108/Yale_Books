"""Load the CPU model only when an embedding is actually needed."""
from threading import Lock

_model = None
_lock = Lock()


def get_model():
    global _model
    with _lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer("intfloat/e5-small-v2", device="cpu")
    return _model
