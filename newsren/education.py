"""Locate education-study passages, without turning keyword matches into verdicts."""

import re


def inspect_study(paper, question):
    evidence, by_anchor = [], {}
    paragraphs = paper["paragraphs"]
    methods = [p for p in paragraphs if re.search(r"method|design|participant", p["section"], re.I)]
    results = [p for p in paragraphs if re.search(r"result|finding", p["section"], re.I)]
    discussion = [p for p in paragraphs if re.search(r"discussion|limitation|conclusion", p["section"], re.I)]

    def cite(paragraph):
        anchor = paragraph["anchor"]
        if anchor not in by_anchor:
            ref = f"P{len(evidence) + 1}"
            by_anchor[anchor] = ref
            text = paragraph["text"]
            evidence.append({"id": ref, "story_id": "", "title": paper["title"],
                             "url": paper["url"], "source_name": paper["journal"] or "Original study",
                             "published_at": paper["published_at"], "retrieved_at": paper["retrieved_at"],
                             "quote": text, "source_text": text,
                             "span": {"field": f"article.{anchor}", "start": 0, "end": len(text)},
                             "section": paragraph["section"], "source_kind": "primary research article",
                             "category": "education", "scope": "Original article paragraph (JATS full text)"})
        return by_anchor[anchor]

    def find(rows, pattern, preferred=""):
        matches = [p for p in rows if re.search(pattern, p["text"], re.I)]
        if preferred:
            matches.sort(key=lambda p: not bool(re.search(preferred, p["text"], re.I)))
        return matches[0] if matches else None

    fields = {}
    patterns = {
        "population": r"\b(?:students?|pupils?|undergraduates?|school|college|university)\b",
        "sample": r"\b(?:\d[\d,]*|one thousand|nearly a thousand)\s+(?:students?|participants?|pupils?|learners?)\b|\b[Nn]\s*=\s*\d+",
        "design": r"\b(?:RCT|randomi[sz]ed|randomly assigned|observational|quasi-experimental|crossover)\b",
        "groups": r"\b(?:control group|control condition|control arm|control students|assigned (?:each|to)|three groups|two groups)\b",
        "limitations": r"\b(?:limit(?:ed|ation|ations)|specific context|single (?:school|high school)|not measured)\b",
    }
    for name, pattern in patterns.items():
        preferred = patterns["sample"] if name == "population" else r"\b(?:RCT|randomi[sz]ed controlled trial)\b" if name == "design" else ""
        row = find(discussion if name == "limitations" else methods, pattern, preferred)
        fields[name] = {"status": "passage_found" if row else "not_found", "citations": [cite(row)] if row else []}

    outcomes = {}
    outcome_patterns = {
        "practice": r"\bpractice\b|\bassisted (?:task|exercise)",
        "independent_test": r"\bunassisted\b|\bunaided\b|without (?:AI|assistance|(?:the )?(?:AI )?tutor)",
        "retention": r"\bretention\b|delayed (?:test|exam)",
        "transfer": r"\btransfer\b|\b(?:novel|unfamiliar) (?:tasks|problems)\b",
    }
    for name, pattern in outcome_patterns.items():
        candidates = [p for p in results if re.search(pattern, p["text"], re.I)
                      and re.search(r"\b(?:scored|scores|increased|decreased|higher|lower|indistinguishable|improv\w*|degrad\w*|diminish\w*|found|find|no significant)\b", p["text"], re.I)
                      and not re.search(r"future|not (?:measured|assessed|tested)|did not (?:measure|assess|test)", p["text"], re.I)]
        row = candidates[0] if candidates else None
        outcomes[name] = {"status": "measurement_passage_found" if row else "not_established",
                          "citations": [cite(row)] if row else []}
    citations = list(dict.fromkeys(ref for field in list(fields.values()) + list(outcomes.values()) for ref in field["citations"]))
    universal = re.search(r"\balways\b|\bevery (?:student|learner)\b|\ball (?:students|learners)\b|所有学生|总是", question, re.I)
    broad_learning = re.search(r"\blearn(?:ing)?\b|学习", question, re.I)
    status = "overgeneralization_risk" if universal else (
        "needs_qualification" if broad_learning else "needs_human_review")
    note = ("Universal claims exceed the population and tasks documented in this study." if universal else
            "Check the stated outcome separately: assisted practice, independent tests, retention and transfer are different measures.")
    return {"paper": {key: value for key, value in paper.items() if key != "paragraphs"},
            "fields": fields, "outcomes": outcomes, "evidence": evidence,
            "claim_check": {"status": status, "citations": citations, "note": note},
            "method_note": "Rule-based passage suggestions, not verified facts or a causal verdict. Missing passages do not prove the study omitted a measure; inspect the full paper."}
