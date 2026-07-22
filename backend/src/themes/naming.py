"""Deterministic theme naming from TF-IDF keywords + dominant product module. No LLM."""

MAX_NAME_WORDS = 4


def build_theme_name(keywords: list[str], dominant_module: str | None) -> str:
    words: list[str] = []
    seen: set[str] = set()
    for kw in keywords:
        for w in kw.split():
            wl = w.lower()
            if wl not in seen:
                seen.add(wl)
                words.append(w)
        if len(words) >= MAX_NAME_WORDS:
            break

    if not words:
        phrase = f"{dominant_module} feedback" if dominant_module else "Uncategorized feedback"
        return phrase[0].upper() + phrase[1:]

    phrase = " ".join(words[:MAX_NAME_WORDS])
    if dominant_module and dominant_module.lower() not in phrase.lower():
        phrase = f"{dominant_module} {phrase}"
    return phrase[0].upper() + phrase[1:]
