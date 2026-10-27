"""Editorial research notebook and local human review desk."""

from newsren.pages import FINANCE_NOTICE, _esc, _page
from newsren.ui import contents, display_date, masthead


def _mast(label="Research notebook"):
    return masthead("review" if label == "Review desk" else "research")


def _editorial_display(run):
    """Use translated editorial prose without changing evidence or review decisions."""
    if run.get("revision", {}).get("kind") != "ai_assisted_editorial":
        return run
    copy = run.get("display_copy", {})
    view = dict(run)
    for key in ("question", "answer", "limitations", "explanations"):
        if key in copy:
            view[key] = copy[key]
    note = copy.get("review_note", {})
    if note and run.get("review", {}).get("note") == note.get("original"):
        view["review"] = {**run["review"], "note": note["text"]}
    return view


def _run_list(runs):
    if not runs:
        return '<p class="muted">No saved research runs yet. Start with a question you want to investigate.</p>'
    return "".join(
        f'<article class="notebook-row"><div class="note-meta"><p class="eyebrow">{_esc(display_date(run.get("created_at", "")))}</p>'
        f'<span class="note-status" data-review="{_esc(run.get("review", {}).get("status", "pending"))}">{_esc(run.get("review", {}).get("status", "pending"))}</span></div>'
        f'<h3><a href="/research/{_esc(run["id"])}">{_esc(run.get("question", ""))}</a></h3><span class="row-arrow" aria-hidden="true">↗</span></article>'
        for run in map(_editorial_display, runs))


def render_research_index(runs, context=None, error="", review=False, model_enabled=False, model_provider="OpenAI"):
    context = context or {}
    context_html = f'<p class="muted">Starting from: {_esc(context.get("title"))}</p>' if context else ""
    form = f'''
<div class="research-workspace"><section class="research-intro">
<p class="eyebrow">A question, a plan, a record</p><h1>Follow the evidence.</h1>
<p>Search across saved news, compare sourced passages, and keep the evidence behind an answer.</p>
{context_html}
<ol class="research-steps"><li><span>01</span>Start with a specific question.</li><li><span>02</span>Read passages from the original sources.</li><li><span>03</span>Keep the limits. Make your own judgment.</li></ol></section>
<form method="post" action="/research" class="research-form research-compose">
<p class="eyebrow">A new research note</p><p role="alert">{_esc(error)}</p>
<label for="research-question">What do you want to investigate?</label>
<textarea id="research-question" name="question" rows="3" maxlength="1000" required placeholder="What evidence is there for a specific company, policy, or model claim?"></textarea>
<input type="hidden" name="story_id" value="{_esc(context.get('id', ''))}">
<label for="research-paper">Original education study (optional DOI or PMC ID)</label>
<input id="research-paper" name="paper_id" maxlength="200" placeholder="10.1073/pnas.2422633122 or PMC12232635">
<p class="muted">Providing an ID requests open-access full text from Europe PMC, even with the news refresh option off. We suggest passages for study design, participants, comparisons, outcomes and limits; unavailable evidence stays explicit.</p>
<div class="form-options"><label class="live-choice"><input type="checkbox" name="live" value="1"> Check approved sources for newer reporting</label>
<p class="muted">Otherwise use saved articles and retained versions. New retrieval checks up to three approved feeds; slow connections may take longer.</p>
<label class="live-choice"><input type="checkbox" name="use_model" value="1" {'' if model_enabled else 'disabled'}> Add model synthesis &amp; audience explanations</label>
<p class="muted">{f'When selected, sends your question and the selected public evidence passages to {_esc(model_provider)}. One call with response limits and a socket timeout; API usage may be charged.' if model_enabled else 'Model synthesis is not configured on this server. Evidence research remains available without an API key.'}</p></div>
<button class="primary" type="submit">Research this question <span aria-hidden="true">↗</span></button>
</form></div>'''
    if review:
        form = '<section class="page-intro review-intro"><p class="eyebrow">Human editorial judgment</p><h1>Review desk<span class="brand-mark">.</span></h1><p>Read the evidence and limitations before approving a research note. Approval records your review; it does not publish or deliver anything.</p></section>'
    body = _mast("Review desk" if review else "Research") + f'''<main class="wrap notebook" id="main-content" tabindex="-1">
{form}<section class="block saved-notebook"><div class="section-head"><h2>{'Research awaiting your judgment' if review else 'Your research notebook'}</h2>
<a href="{'/research' if review else '/review'}">{'Start research' if review else 'Open review desk'} ↗</a></div>{_run_list(runs)}</section><p class="notice site-notice">{FINANCE_NOTICE}</p></main>'''
    return _page("Research · The Newsren", body, "research-index-page")


def _study_card(study):
    if not study:
        return ""
    paper = study["paper"]
    labels = {"population": "Study population", "sample": "Participant count", "design": "Study design",
              "groups": "Comparison groups", "limitations": "Study limitations",
              "practice": "Assisted practice", "independent_test": "Independent test",
              "retention": "Long-term retention", "transfer": "Transfer to new tasks"}

    def refs(citations):
        return " ".join(f'<a class="citation" href="#{_esc(ref)}">[{_esc(ref)}]</a>' for ref in citations)

    def rows(items):
        statuses = {"passage_found": "Passage found — review original",
                    "not_found": "Not found in selected passages",
                    "measurement_passage_found": "Result passage found — review outcome and comparison",
                    "not_established": "Not established in selected evidence"}
        return "".join(f'<div class="study-row"><dt>{labels[key]}</dt><dd>{statuses[row["status"]]} {refs(row["citations"])}</dd></div>' for key, row in items.items())

    status = {"preprint": "Preprint", "published_journal_article": "Published journal article", "unknown": "Publication type unknown"}.get(paper["publication_status"], "Publication type unknown")
    check = study["claim_check"]
    check_label = {"needs_qualification": "Learning claim needs qualification", "overgeneralization_risk": "Possible overgeneralization", "needs_human_review": "Claim needs human review"}[check["status"]]
    def field_refs(*keys):
        items = {**study["fields"], **study["outcomes"]}
        return refs(list(dict.fromkeys(ref for key in keys for ref in items[key]["citations"])))

    return f'''<section class="block" id="education-study"><p class="eyebrow">Original research / {_esc(paper['pmcid'])}</p>
<h2>Education study check</h2><h3>{_esc(paper['title'])}</h3>
<p>{_esc(status)} · {_esc(paper['journal'])} · {_esc(paper['published_at'] or 'Date not provided')}</p>
<p class="muted">Peer-review status not independently verified. The repository copy and journal article are one study.</p>
<dl class="study-facts">{rows(study['fields'])}</dl>
<h3>What was measured?</h3><p>Performance with help, performance without help, retention and transfer answer different questions.</p>
<dl class="study-facts outcome-grid">{rows(study['outcomes'])}</dl>
<h3>{_esc(check_label)}</h3><p>{_esc(check['note'])} {refs(check['citations'])}</p>
<h3>Read the study for your audience</h3>
<p class="muted">Reading guides based on the passages above; follow each citation for the authors' actual findings.</p>
<details><summary>For students</summary><p>A score while AI is helping and a score when you work on your own measure different things. Compare the practice and independent-test passages before deciding what was learned. {field_refs('practice', 'independent_test')}</p><p>A missing retention or transfer passage leaves those questions open.</p></details>
<details><summary>For educators</summary><p>Read how the intervention and comparison groups were set up, then compare outcomes with and without assistance. Check the design and limitations before applying the findings to a different class or subject. {field_refs('design', 'groups', 'limitations', 'practice', 'independent_test')}</p></details>
<details><summary>For parents</summary><p>Check which students were included and what tasks they did. Success with AI help does not by itself show that a child can solve unfamiliar problems independently; check the independent-test and transfer evidence separately. {field_refs('population', 'sample', 'independent_test', 'transfer', 'limitations')}</p></details>
<p class="muted study-method">{_esc(study['method_note'])}</p></section>'''


def render_research_run(run):
    run = _editorial_display(run)
    review = run.get("review", {"status": "pending"})
    model_complete = run.get("synthesis", {}).get("status") == "complete"
    revision = run.get("revision", {})
    editorial = revision.get("kind") == "ai_assisted_editorial"
    revision_html = ""
    if editorial:
        revision_html = f'''<details class="notice revision-notice"><summary>AI-assisted editorial revision · About this draft</summary>
<p>Revised against saved evidence. This is an editorial draft, separate from the original model output; it does not record human approval.
<a href="/research/{_esc(revision['source_run_id'])}">Read the original research record</a>.</p>
<p>No new retrieval or model API call was made for this revision.</p></details>'''
    if editorial:
        answer_note = "AI-assisted editorial interpretation with citations. Source support and wording still require human review."
    elif model_complete:
        answer_note = "Model-written synthesis with checked citation IDs and numbers. Meaning and source support require human review."
    else:
        answer_note = "Quoted passages with citations. Differences below require judgment."
    answer = "".join(
        f'<blockquote><p>{_esc(row["text"])}</p><p>' + " ".join(
            f'<a class="citation" href="#{_esc(cite)}">[{_esc(cite)}]</a>' for cite in row["citations"]) + '</p></blockquote>'
        for row in run["answer"])
    if not answer:
        answer = '<p>No supporting passages were found. This run cannot answer the question from the available evidence.</p>'
    audience = []
    for name, rows in run.get("explanations", {}).items():
        paragraphs = "".join(f'<p>{_esc(row["text"])} ' + " ".join(f'<a href="#{_esc(ref)}">[{_esc(ref)}]</a>' for ref in row["citations"]) + '</p>' for row in rows)
        audience.append(f'<details><summary>{_esc(name.title())} explanation</summary>{paragraphs}</details>')
    audience_html = f'<section class="block" id="research-audience"><p class="eyebrow">Different readers, shared evidence</p><h2>Explain for your audience</h2>{"".join(audience)}</section>' if audience else ""
    evidence = []
    for row in run["evidence"]:
        evidence.append(f'''<article class="evidence-card" id="{_esc(row['id'])}">
<p class="eyebrow">{_esc(row['id'])} / {_esc(row['source_name'])}</p>
<h3>{_esc(row['title'])}</h3><blockquote>{_esc(row['quote'])}</blockquote>
<p><a href="{_esc(row['url'])}">Read original source ↗</a></p>
<details class="source-details"><summary>Source details &amp; exact passage location</summary><dl class="source-meta"><dt>Published</dt><dd>{_esc(row['published_at'] or 'Not provided')}</dd>
<dt>Retrieved</dt><dd>{_esc(row['retrieved_at'] or 'Not provided')}</dd>
<dt>Document</dt><dd>{_esc(row['source_kind'])}</dd>
<dt>Evidence scope</dt><dd>{_esc(row['scope'])}; exact {_esc(row['span']['field'])} characters {row['span']['start']}–{row['span']['end']}</dd></dl></details></article>''')
    comparisons = []
    labels = {"numeric_difference": "Numbers to check", "negation_difference": "Opposing wording", "repeated_claim": "Repeated claim"}
    for row in run["comparisons"]:
        refs = " ".join(f'<a href="#{_esc(cite)}">[{_esc(cite)}]</a>' for cite in row["citations"])
        comparisons.append(f'<article class="comparison" data-kind="{_esc(row["kind"])}"><h3>{labels.get(row["kind"], "Compare sources")}</h3><p>{_esc(row["note"])} {refs}</p></article>')
    plan = "".join(f'<li>{_esc(step)}</li>' for step in run["plan"])
    tools = "".join(f'<li><strong>{_esc(step.get("source") or step["tool"].replace("_", " "))}</strong> · {_esc(step["status"])}<p>{_esc(step["detail"])}</p></li>' for step in run["steps"])
    limitations = "".join(f'<li>{_esc(text)}</li>' for text in run["limitations"])
    metrics = run["metrics"]
    sections = [("research-answer", "The answer")]
    if run.get("study"):
        sections.append(("education-study", "The study"))
    if audience:
        sections.append(("research-audience", "For your audience"))
    sections += [("research-comparisons", "Compare claims"), ("research-limitations", "The limitations"),
                 ("research-sources", "Original evidence"), ("research-activity", "Research activity"), ("human-review", "Your review")]
    toc = contents(sections, "In this research")
    body = _mast() + f'''<main class="wrap notebook research-reader" id="main-content" tabindex="-1">
<section class="page-intro"><p class="eyebrow">The research notebook / {_esc(display_date(run['created_at']))}</p>
<h1>{_esc(run['question'])}</h1><div class="research-status"><span>{'Evidence found' if run['evidence'] else 'Insufficient evidence'}</span><span data-review="{_esc(review['status'])}">Review: {_esc(review['status'])}</span></div>
<div class="page-actions"><a href="/research">New research ↗</a><a href="/review">Review desk</a><a href="/api/research/{run['id']}">Evidence record (JSON)</a><span class="muted">{len(run['evidence'])} evidence passages</span></div></section>
<div class="reader-layout">{toc}<article class="reader-body">
{revision_html}
<section class="block" id="research-answer"><p class="eyebrow">What the sources say</p><h2>Answer with evidence</h2>
<p class="muted">{answer_note}</p>{answer}</section>
{_study_card(run.get('study'))}
{audience_html}
<section class="block" id="research-comparisons"><details><summary>Compare before concluding</summary>{''.join(comparisons) or '<p>No closely matching claim differences were identified. This does not establish agreement or accuracy.</p>'}</details></section>
<section class="block" id="research-limitations"><h2>What remains unverified</h2><ul>{limitations}</ul></section>
<section class="block" id="research-sources"><p class="eyebrow">Read the original</p><h2>Source notebook</h2>{''.join(evidence) or '<p>No evidence passages.</p>'}</section>
<section class="block" id="research-activity"><details><summary>Research plan &amp; activity</summary><ol>{plan}</ol><details><summary>View the research activity log</summary><ol class="activity-log">{tools}</ol></details>
<p class="muted">{metrics['articles_searched']} articles searched · {metrics['retrieval_calls']} retrievals · {metrics['elapsed_seconds']} seconds · {metrics['model_calls']} model calls</p><p class="muted">Created {_esc(run['created_at'])}</p></details></section>
<section class="block" id="human-review"><p class="eyebrow">Human review</p><h2>Check the evidence</h2>
<p>Review the original documents, numbers, dates and differences before approving. This note is never automatically published.</p>
<p>Current review: {_esc(review['status'])}. {_esc(review.get('note', ''))} {_esc(review.get('reviewed_at', ''))}</p>
<form method="post" action="/review" class="research-form"><input type="hidden" name="run_id" value="{run['id']}">
<label for="review-note">Review notes</label><textarea id="review-note" name="note" rows="2" maxlength="2000"></textarea>
<div class="review-actions"><button class="primary" type="submit" name="status" value="approved">Approve after review</button>
<button type="submit" name="status" value="rejected">Reject / needs correction</button></div></form></section>
<p class="notice site-notice">{FINANCE_NOTICE}</p></article></div></main>'''
    return _page("Research note · The Newsren", body, "research-run-page")
