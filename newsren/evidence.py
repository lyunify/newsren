"""Find quoted evidence and comparison candidates; never adjudicate truth by word overlap."""

import re
from urllib.parse import urlsplit

from newsren.related import content_terms
from newsren.text import STOPWORDS, english_words, normalize_url, numeric_values, split_sentences

QUESTION_WORDS = frozenset({"what", "which", "when", "where", "why", "how", "who", "explain", "compare",
                           "please", "tell", "happened", "changed", "story", "evidence", "summarize", "summarise", "describe", "say", "says", "use"})
GENERIC_SUBJECTS = QUESTION_WORDS | STOPWORDS | {"revenue", "earnings", "funding", "finance", "technology", "industry", "education", "report"}
CONTEXT_WORDS = frozenset({"filing", "filings", "report", "reports", "study", "paper", "company", "announcement", "news"})
TERM_FAMILIES = {"energy": {"energy", "power", "electricity", "gas", "methane", "fuel"},
                 "earnings": {"earnings", "profit", "profits", "income"},
                 "revenue": {"revenue", "revenues", "sales"}}


def research_terms(question: str) -> set[str]:
    return set(english_words(question)) - STOPWORDS - QUESTION_WORDS


def source_kind(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host.endswith(".gov") or host in {"arxiv.org", "doi.org"}:
        return "original document / official release"
    return "reporting / provenance not independently established"


def collect_evidence(question: str, stories: list[dict], limit: int = 8, focus: str = "") -> list[dict]:
    terms = research_terms(question)
    if not terms:
        terms = research_terms(focus)
    if not terms:
        return []
    subject_groups = []
    for phrase in re.findall(r"\b[A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\b", question):
        group = set(english_words(phrase)) - GENERIC_SUBJECTS
        if group:
            subject_groups.append(group)
    subject_terms = set().union(*subject_groups) if subject_groups else set()
    focus_terms = terms - subject_terms - CONTEXT_WORDS
    expanded_focus = set().union(*(TERM_FAMILIES.get(term, {term}) for term in focus_terms)) if focus_terms else set()
    ranked = []
    for position, story in enumerate(stories):
        url = story.get("url") or ""
        if urlsplit(url).scheme not in {"http", "https"}:
            continue
        title_terms = set(english_words(story.get("title") or ""))
        article_terms = title_terms | set(english_words(story.get("excerpt") or ""))
        if subject_groups and not any(group <= article_terms for group in subject_groups):
            continue
        for field in ("excerpt", "title"):
            text = story.get(field) or ""
            for sentence in split_sentences(text):
                sentence_words = set(english_words(sentence))
                hits = terms & sentence_words
                if not hits:
                    continue
                focus_hits = expanded_focus & sentence_words
                if expanded_focus and not focus_hits:
                    continue
                score = len(hits) + 2 * len(focus_hits) + 0.25 * len(title_terms & terms)
                start = text.find(sentence)
                ranked.append((score, position, story, sentence,
                               {"field": field, "start": start, "end": start + len(sentence)}))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    found, used = [], set()
    for _, _, story, sentence, span in ranked:
        # One strongest passage per article; do not let one outlet fill the evidence budget.
        key = (normalize_url(story["url"]), story.get("id"))
        if key in used:
            continue
        used.add(key)
        found.append({"id": f"S{len(found) + 1}", "story_id": story.get("id") or "",
                      "title": story.get("title") or "", "url": story["url"],
                      "source_name": story.get("source_name") or "Unknown source",
                      "published_at": story.get("published_at") or "",
                      "retrieved_at": story.get("retrieved_at") or "",
                      "quote": sentence, "span": span, "source_kind": source_kind(story["url"]),
                      "category": story.get("category") or "", "scope": "RSS title/excerpt snapshot"})
        if len(found) >= limit:
            break
    return found


def compare_evidence(evidence: list[dict]) -> list[dict]:
    comparisons = []
    for index, left in enumerate(evidence):
        for right in evidence[index + 1:]:
            a, b = content_terms(left["quote"]), content_terms(right["quote"])
            base_a = {term for term in a if not term.lstrip("+-")[0].isdigit() and term != "not"}
            base_b = {term for term in b if not term.lstrip("+-")[0].isdigit() and term != "not"}
            if len(base_a & base_b) < 3 or len(base_a & base_b) / max(len(base_a | base_b), 1) < 0.7:
                continue
            citations = [left["id"], right["id"]]
            nums_a = numeric_values(left["quote"])
            nums_b = numeric_values(right["quote"])
            if nums_a and nums_b and nums_a != nums_b:
                comparisons.append({"kind": "numeric_difference", "citations": citations,
                                    "note": "Different numbers in similar passages. Check entity, period, units and revisions before drawing a conclusion."})
            elif ("not" in a) != ("not" in b):
                comparisons.append({"kind": "negation_difference", "citations": citations,
                                    "note": "Similar passages differ in negation. Read both original sources; this is a comparison candidate, not a fact check."})
            elif a == b and left["source_name"] != right["source_name"]:
                comparisons.append({"kind": "repeated_claim", "citations": citations,
                                    "note": "This claim occurs in different outlets. Syndication and source independence have not been checked."})
    return comparisons[:8]
