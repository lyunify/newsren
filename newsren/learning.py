"""Audience-specific teaching structure grounded in source passages."""

from newsren.text import english_words

CONCEPTS = {
    "ai": "Artificial intelligence: computer systems built to perform tasks such as recognizing patterns, predicting or generating content. A news claim about one task does not establish ability on every task.",
    "benchmark": "A standardized test used to compare performance on specified tasks. A benchmark score alone does not show how a system performs in every real setting.",
    "preprint": "A research manuscript shared publicly before completing the journal's formal peer-review process.",
    "revenue": "Money earned from business activities before subtracting expenses. Revenue is different from profit.",
    "earnings": "Profit remaining after expenses for a reporting period. Check the period and the accounting measure before comparing figures.",
    "funding": "Money provided to support a project or organization. Funding can take different forms, including debt and equity.",
    "backtest": "A simulation of how a method would have performed on historical data. It does not establish future or live performance.",
    "inflation": "An increase in the general level of prices over time, reducing what a fixed amount of money can buy.",
    "policy": "A rule or course of action adopted by an organization or government. An announcement and an implemented policy can have different dates.",
    "supply": "In a supply chain, organizations and activities connect the production and delivery of goods. A claim about one link does not prove effects on every other link.",
    "evidence": "Information that can support or challenge a claim. Its relevance depends on how it was collected and what it actually measures.",
    "source": "The person, document or organization from which information comes. Linking to a source makes a claim traceable; it does not by itself prove the claim true.",
}


def learning_material(story: dict) -> dict:
    source = story.get("source_name") or "the source"
    sentences = list(story.get("summary_sentences") or [])
    quote = sentences[0] if sentences else ""
    words = set(english_words((story.get("title") or "") + " " + (story.get("excerpt") or "")))
    concepts = [{"term": word, "definition": definition} for word, definition in CONCEPTS.items()
                if word != "source" and word in words][:4]
    if not concepts:
        concepts = [{"term": "source", "definition": CONCEPTS["source"]}]
    quiz = []
    if quote:
        quiz.append({"kind": "source_claim", "question": "Which statement is directly supported by the supplied passage?",
                     "options": [quote, "Independent studies have proved this result applies to every setting.",
                                 "The passage guarantees what will happen next."], "answer": 0,
                     "explanation": f"Only the quoted statement is present in {source}'s passage. The other options add unsupported claims."})
    quiz.append({"kind": "evidence_limit", "question": "What would best help you check this report?",
                 "options": ["Count how often the headline is repeated.", "Read the original document and compare its methods, dates and claims.",
                             "Assume an official-looking headline must be correct."], "answer": 1,
                 "explanation": "Trace the original evidence and check context; repetition alone is not independent confirmation."})
    return {"concepts": concepts, "quote": quote,
            "student": {"steps": ["Start with the concepts below, then read the source passage.",
                                   f"Explain in your own words what {source} claims, and name one thing the passage does not establish."]},
            "educator": {"objectives": ["Distinguish a reported claim from independently established evidence.",
                                         "Use a source quote and its date to support an explanation.",
                                         "Transfer the same evidence-checking questions to a different news story."],
                         "activity": "In pairs, label one claim, one piece of evidence and one missing detail. Swap with another pair and discuss what additional source would change the conclusion.",
                         "quiz": quiz},
            "professional": {"questions": ["Which named organization, stakeholder or decision is actually within this source's scope?",
                                              "Are the compared numbers for the same period, units and population?",
                                              "What original document or independent evaluation is needed before acting?"],
                             "limits": "The available material is an RSS title/excerpt. It may omit methods, comparison groups, costs, conflicts and corrections. Reported implications remain hypotheses until supported."}}
