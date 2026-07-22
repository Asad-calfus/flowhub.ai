"""TF-IDF keyword extraction per theme. Operates on raw feedback_text only (an allowed
input field, not a leakage field) - never on label columns.
"""

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

# The dataset is casual/conversational text (support tickets, chat, app reviews); sklearn's
# default English stopword list misses common filler words that otherwise pollute keywords
# and theme names (e.g. "just really slow" -> keyword "really").
EXTRA_STOP_WORDS = frozenset({
    "like", "really", "just", "instead", "pls", "please", "ve", "ll", "kinda", "gonna",
    "got", "get", "gets", "getting", "way", "ve", "app", "flowhub",
})
STOP_WORDS = frozenset(ENGLISH_STOP_WORDS) | EXTRA_STOP_WORDS


def extract_theme_keywords(
    texts_by_theme: dict[str, list[str]], all_texts: list[str], top_n: int = 8
) -> dict[str, list[str]]:
    """Fit TF-IDF over the full corpus (so idf reflects the whole dataset), then rank each
    theme's vocabulary by mean TF-IDF weight within that theme's texts."""
    vectorizer = TfidfVectorizer(stop_words=list(STOP_WORDS), max_features=2000, ngram_range=(1, 2), min_df=1)
    vectorizer.fit(all_texts)
    vocab = vectorizer.get_feature_names_out()

    result: dict[str, list[str]] = {}
    for theme_id, texts in texts_by_theme.items():
        if not texts:
            result[theme_id] = []
            continue
        matrix = vectorizer.transform(texts)
        mean_scores = np.asarray(matrix.mean(axis=0)).ravel()
        order = np.argsort(-mean_scores)
        result[theme_id] = [vocab[i] for i in order[:top_n] if mean_scores[i] > 0]
    return result
