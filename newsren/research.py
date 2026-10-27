"""Bounded, source-grounded research orchestration."""

import time
import uuid
from datetime import datetime, timezone
from urllib.request import build_opener

from newsren.evidence import collect_evidence, compare_evidence, research_terms
from newsren.fetch import fetch_source
from newsren.sources import APPROVED_SOURCES
from newsren.papers import PaperClient, normalize_identifier
from newsren.education import inspect_study

CATEGORY_TERMS = {
    "technology": {"ai", "model", "chip", "chips", "benchmark", "software", "semiconductor"},
    "education": {"education", "school", "schools", "student", "students", "learning", "classroom"},
    "industry": {"industry", "supply", "manufacturing", "supplier", "factory", "jobs"},
    "finance": {"finance", "earnings", "revenue", "bank", "funding", "sec", "filing", "rates"},
}


class ResearchAgent:
    def __init__(self, fetcher=fetch_source, clock=time.monotonic, synthesizer=None, paper_client=None):
        self.fetcher = fetcher
        self.clock = clock
        self.synthesizer = synthesizer
        self.paper_client = paper_client

    def run(self, question: str, stories: list[dict], context: dict | None = None, live: bool = False, use_model: bool = False, paper_id: str = "") -> dict:
        question = (question or "").strip()
        if not question or len(question) > 1000:
            raise ValueError("Enter a question between 1 and 1000 characters.")
        paper_id = (paper_id or "").strip()
        if paper_id:
            normalize_identifier(paper_id)
        started = self.clock()
        deadline = started + 30
        created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        terms = research_terms(question)
        scores = {category: len(terms & words) for category, words in CATEGORY_TERMS.items()}
        if context and context.get("category") in scores:
            scores[context["category"]] += 1
        if paper_id:
            scores["education"] += 10
        categories = sorted(scores, key=lambda category: -scores[category])
        selected = [source for category in categories for source in APPROVED_SOURCES if source["category"] == category][:3]
        if paper_id:
            selected = [source for source in APPROVED_SOURCES if source["category"] == "education"][:3]
        plan = ["Search saved articles and retained story versions for evidence matching the question.",
                "Retrieve at most three approved feeds; stop scheduling sources after 30 seconds, with per-source socket/read limits." if live else "Use saved news only; no feed retrieval was requested.",
                "Compare quoted claims, numbers and negation; preserve differences for human review.",
                "Return cited passages, limitations and an immutable research record."]
        catalog = list(stories)
        limitations = ["Only RSS titles/excerpts are available; full articles, methods and paywalled documents were not read.",
                       "Outlet diversity does not establish source independence or prove a claim correct.",
                       "The answer below quotes evidence. It is not a model-generated synthesis or personalized advice."]
        steps = [{"tool": "plan", "status": "complete", "detail": f"Goal: {question}. Priority category: {categories[0]}."}]
        calls, exhausted = 0, False
        study = None
        if paper_id:
            plan.insert(1, "Retrieve the supplied DOI/PMC article through Europe PMC; locate education-study methods, outcomes and limitations.")
            client = self.paper_client or PaperClient()
            try:
                paper = client.fetch(paper_id, timeout=min(20, max(0, deadline - self.clock())))
                study = inspect_study(paper, question)
                limitations[0] = "Study suggestions use selected original-paper paragraphs; other news evidence is limited to RSS titles/excerpts. Tables and supplementary files were not evaluated."
                limitations += [study["method_note"], "Publication metadata does not independently verify peer review. The PMC copy and journal article are the same study, not independent corroboration."]
                steps.append({"tool": "primary_paper", "status": "complete", "url": paper["api_url"], "detail": f"Read JATS full text for {paper['pmcid']} through Europe PMC."})
                steps.append({"tool": "education_study_check", "status": "complete", "detail": "Located candidate methods, population, sample, groups, outcomes and limitations; separated practice from independent tests, retention and transfer. Human review required."})
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                steps.append({"tool": "primary_paper", "status": "failed", "detail": detail})
                limitations.append(f"Original study could not be checked: {detail}. No full-text findings were inferred.")
            calls += client.request_count
        if live:
            opener = build_opener()
            for source in selected:
                remaining = deadline - self.clock()
                if remaining <= 0:
                    exhausted = True
                    limitations.append("Retrieval budget exhausted; remaining sources were not requested.")
                    break
                calls += 1
                try:
                    fresh, error = self.fetcher(source, created, opener, timeout=min(12, remaining))
                except Exception as exc:
                    fresh, error = [], f"{type(exc).__name__}: {exc}"
                steps.append({"tool": "approved_feed", "source": source["name"], "url": source["url"],
                              "status": "failed" if error else "complete", "detail": error or f"Retrieved {len(fresh)} articles."})
                if error:
                    limitations.append(f"{source['name']}: {error}. Saved evidence remains available.")
                else:
                    catalog = [item for item in catalog if item.get("id") not in {s.get("id") for s in fresh}] + fresh
        focus = context.get("title", "") if context else ""
        news_catalog = [item for item in catalog if item.get("category") == "education"] if study else catalog
        evidence = collect_evidence(question, news_catalog, focus=focus)
        if study:
            evidence = study["evidence"] + evidence
            limitations.append("Education news passages are topical context; they are not assumed to independently evaluate this study.")
        comparisons = compare_evidence(evidence)
        steps += [{"tool": "evidence_search", "status": "complete", "detail": f"Searched {len(news_catalog)} news articles; selected {len(evidence)} cited passages including original-paper evidence when supplied."},
                  {"tool": "claim_comparison", "status": "complete", "detail": f"Flagged {len(comparisons)} comparison candidates; no truth verdict assigned."}]
        if len({e["source_name"] for e in evidence}) < 2:
            limitations.append("Fewer than two outlets support this search. Independent corroboration was not established.")
        if not evidence:
            limitations.append("No matching evidence was found. Try a named organization, event or technical term, or request approved-source retrieval.")
        if any(not e["published_at"] for e in evidence):
            limitations.append("Some sources did not provide a publication timestamp.")
        run = {"id": uuid.uuid4().hex, "created_at": created, "question": question,
                "context_id": (context or {}).get("id", ""), "live": live,
                "status": "evidence_found" if evidence else "insufficient_evidence",
                "plan": plan, "steps": steps, "evidence": evidence, "comparisons": comparisons,
                "answer": [{"text": row["quote"], "citations": [row["id"]], "kind": "quotation"} for row in evidence],
                "limitations": limitations, "review": {"status": "pending", "note": ""},
                "metrics": {"retrieval_calls": calls, "articles_searched": len(news_catalog),
                            "evidence_count": len(evidence), "elapsed_seconds": round(self.clock() - started, 3),
                            "budget_exhausted": exhausted or self.clock() >= deadline,
                            "model_calls": 0, "inference_cost": 0}}
        run["synthesis"] = {"status": "not_requested", "model": ""}
        if study:
            run["study"] = {key: value for key, value in study.items() if key != "evidence"}
        run["explanations"] = {}
        if use_model:
            if self.synthesizer is None:
                run["synthesis"]["status"] = "not_configured"
                run["limitations"].append("Model synthesis was requested but is not configured. The source quotations remain available.")
            elif not evidence:
                run["synthesis"]["status"] = "no_evidence"
            else:
                run["metrics"]["model_calls"] = 1
                run["metrics"]["inference_cost"] = None
                run["synthesis"]["model"] = self.synthesizer.model
                run["synthesis"]["provider"] = getattr(self.synthesizer, "provider", "unknown")
                try:
                    output = self.synthesizer.synthesize(question, evidence)
                    run["answer"] = [dict(row, kind="model_synthesis") for row in output["answer"]]
                    run["explanations"] = {name: output[name] for name in ("student", "educator", "professional")}
                    run["limitations"] = [text for text in limitations if not text.startswith("The answer below quotes")]
                    run["limitations"] += output["limitations"] + ["Model citations and numbers were checked mechanically. Semantic support and source reliability still require human review."]
                    run["metrics"]["model_usage"] = output.get("usage", {})
                    run["synthesis"]["status"] = "complete"
                except Exception:
                    run["synthesis"]["status"] = "failed"
                    run["limitations"].append("Model synthesis failed or did not pass citation/number checks. The original evidence quotations were retained.")
                run["steps"].append({"tool": "model_synthesis", "status": run["synthesis"]["status"],
                                     "detail": "One bounded structured-output call; evidence and human-review state preserved."})
        run["metrics"]["elapsed_seconds"] = round(self.clock() - started, 3)
        return run
