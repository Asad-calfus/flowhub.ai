"""Local sentence-embedding generation with hash-based caching.

Model is configurable via the EMBEDDING_MODEL env var (default: a small, local,
free-to-run model - no API cost). Vectors are L2-normalized so cosine similarity
reduces to a dot product.
"""

import hashlib
import json
import os

import numpy as np

DEFAULT_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Embedder:
    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or DEFAULT_MODEL
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        if hasattr(self.model, "get_embedding_dimension"):
            return self.model.get_embedding_dimension()
        return self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        vecs = self.model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
        return np.asarray(vecs, dtype=np.float32)


def encode_with_cache(
    embedder: Embedder, ids: list[str], texts: list[str], cache_dir: str, cache_name: str
) -> np.ndarray:
    """Vectors aligned to `ids`/`texts` order. Skips re-encoding any id whose text hash
    is unchanged since the last run; metadata (ids/hashes) is stored separately from the
    raw vectors so the cache can be diffed without loading the matrix.
    """
    os.makedirs(cache_dir, exist_ok=True)
    vec_path = os.path.join(cache_dir, f"{cache_name}.npy")
    meta_path = os.path.join(cache_dir, f"{cache_name}.json")

    old_meta, old_vecs = [], None
    if os.path.exists(vec_path) and os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            old_meta = json.load(f)
        old_vecs = np.load(vec_path)
    old_by_id = {m["id"]: (m["hash"], i) for i, m in enumerate(old_meta)}

    new_hashes = [_hash(t) for t in texts]
    vectors: list[np.ndarray | None] = [None] * len(ids)
    to_encode = []
    for i, (rid, h) in enumerate(zip(ids, new_hashes)):
        cached = old_by_id.get(rid)
        if cached and cached[0] == h and old_vecs is not None:
            vectors[i] = old_vecs[cached[1]]
        else:
            to_encode.append(i)

    if to_encode:
        fresh = embedder.encode([texts[i] for i in to_encode])
        for j, i in enumerate(to_encode):
            vectors[i] = fresh[j]

    result = np.stack(vectors).astype(np.float32)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump([{"id": rid, "hash": h} for rid, h in zip(ids, new_hashes)], f)
    np.save(vec_path, result)
    return result
