from newsren.text import STOPWORDS, english_words, split_sentences

ASK_LIMIT = 6


def find_supporting_sentences(title: str, excerpt: str, question: str) -> list[str]:
    if not (question or "").strip():
        return []
    terms = [word for word in english_words(question) if word not in STOPWORDS]
    if not terms:
        return []
    sentences = []
    for part in (title or "", excerpt or ""):
        for sentence in split_sentences(part):
            if sentence not in sentences:
                sentences.append(sentence)
    scored = []
    for index, sentence in enumerate(sentences):
        words = set(english_words(sentence))
        score = sum(1 for term in terms if term in words)
        if score >= 1:
            scored.append((score, index, sentence))
    scored.sort(key=lambda item: (-item[0], item[1]))
    chosen = sorted(scored[:3], key=lambda item: item[1])
    return [sentence for _, _, sentence in chosen]


def ask_stories(question: str, stories: list[dict]) -> list[dict]:
    found = []
    for story in stories:
        sentences = find_supporting_sentences(story.get("title") or "", story.get("excerpt") or "", question)
        for sentence in sentences:
            found.append(
                {
                    "sentence": sentence,
                    "id": story.get("id") or "",
                    "title": story.get("title") or "",
                    "url": story.get("url") or "",
                    "source_name": story.get("source_name") or "",
                }
            )
            if len(found) >= ASK_LIMIT:
                return found
    return found
