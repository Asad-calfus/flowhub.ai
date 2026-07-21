import numpy as np

from src.retrieval.embedder import Embedder, encode_with_cache

_embedder = Embedder()  # loaded once per test session (model load is the slow part)


def test_embedding_dimension_is_384():
    vecs = _embedder.encode(["hello world"])
    assert vecs.shape == (1, 384)
    assert _embedder.dimension == 384


def test_embeddings_are_normalized():
    vecs = _embedder.encode(["a completely different sentence about dashboards"])
    norm = np.linalg.norm(vecs[0])
    assert abs(norm - 1.0) < 1e-4


def test_encode_empty_list_returns_empty_array():
    vecs = _embedder.encode([])
    assert vecs.shape == (0, 384)


def test_cache_skips_unchanged_records(tmp_path, monkeypatch):
    calls = {"n": 0}
    real_encode = _embedder.encode

    def counting_encode(texts):
        calls["n"] += 1
        return real_encode(texts)

    monkeypatch.setattr(_embedder, "encode", counting_encode)

    ids = ["a", "b"]
    texts = ["first text", "second text"]
    v1 = encode_with_cache(_embedder, ids, texts, str(tmp_path), "cache")
    assert calls["n"] == 1

    v2 = encode_with_cache(_embedder, ids, texts, str(tmp_path), "cache")
    assert calls["n"] == 1  # no new encode call - everything was cached
    assert np.allclose(v1, v2)


def test_cache_only_reencodes_changed_records(tmp_path, monkeypatch):
    calls = {"texts": []}
    real_encode = _embedder.encode

    def recording_encode(texts):
        calls["texts"].append(list(texts))
        return real_encode(texts)

    monkeypatch.setattr(_embedder, "encode", recording_encode)

    ids = ["a", "b"]
    encode_with_cache(_embedder, ids, ["first text", "second text"], str(tmp_path), "cache")
    encode_with_cache(_embedder, ids, ["first text", "CHANGED"], str(tmp_path), "cache")

    assert calls["texts"][-1] == ["CHANGED"]  # only the changed record was re-encoded
