import json
import hashlib
from html import escape

from newsren.depth import cache_stats, impact_sentences, lesson_cloze, tracker_rows
from newsren.learning_pages import render_learning
from newsren.inspect import (
    claim_labels,
    glossary_entries,
    independent_sources,
    other_section_stories,
    uncertainty_sentences,
)
from newsren.related import (
    change_sentences,
    earlier_related,
    material_update,
    new_sentences,
    timeline_stories,
    unrepeated_sentences,
)
from newsren.text import SHORT_TOPICS, STOPWORDS, parse_date
from newsren.ui import contents, display_date, footer, masthead
from newsren.media import display_image_url, safe_image_url

FINANCE_NOTICE = "For information only. This is not investment advice."
NO_SUPPORT = "This story's summary has no sentences that support that question."
ASK_NOTE = "These are sentences from the source, not a synthesis."
NO_EXCERPT = "The source did not provide a summary."
SOURCE_DOWN = "Temporarily unavailable; showing the last fetch."
EMPTY_FEED = "There are no stories to show right now."
LOADING = "Fetching sources"
FOLLOW_EMPTY = "No matching new stories yet."
TRUNCATED_NOTE = "Taken from the source summary; the full text is on the source page."
SUMMARY_NOTE = "Sentences taken from this source."
STUDENT_NOTE = "These sentences come from the source summary; the full article is on the source page."
HOME_DEK = "News organized from source text, without adding facts the source does not contain."
NO_TIME = "The source did not provide a publication time."
RELATED_EMPTY = "No other stories match this title yet."
RELATED_NOTE = "Oldest first. What is new uses words that do not appear in earlier related stories."
THIS_STORY = "This story"
WHAT_IS_NEW = "What is new in this story"
WHAT_CHANGED = "What changed"
BRIEFING = "Briefing"
BRIEFING_NOTE = "These sentences are from matching stories, not a synthesis."
INSPECT_HEADING = "Inspect evidence"
INSPECT_NOTE = "Sources and quoted sentences only. This page does not judge bias."
UNCERTAINTY_HEADING = "Uncertainty language in this source"
NO_UNCERTAINTY = "This summary has no uncertainty words such as may, alleged, or forecast."
SOURCES_HEADING = "Sources in this cluster"
GLOSSARY_HEADING = "Words from this story"
GLOSSARY_NOTE = "Each word is shown with a sentence from this source that contains it."
OTHER_HEADING = "Related developments in other sections"
OTHER_NOTE = "These are other sourced stories, not confirmed effects."
NO_OTHER = "No related stories in other sections yet."
CLAIM_HEADING = "Performance and forecast words"
NO_CLAIM = "No backtest, simulated, live, forecast, or guidance words in this summary."
NO_EARLIER = "There are no earlier related stories to compare."
NOTHING_NEW = "Every content word in this summary also appears in an earlier related story."
FOLLOW_NOTE = "After you save the current question, matching stories with new information appear under Following on the home page."
UNREPEATED_NOTE = "These sentences are from this summary; some of their words do not appear in the comparison stories' titles or summaries."
UNREPEATED_NONE = "Every content word in this summary also appears in a comparison story title or summary."
UNREPEATED_NO_RELATED = "There are no other stories to compare."
EMAIL_NOTE = "Opens your mail app. This site does not send email."
COPY_BRIEFING = "Copy briefing"
EMAIL_BRIEFING = "Email briefing"
LESSON_HEADING = "Lesson"
LESSON_NOTE = "The blank is a word from this source. The discussion prompts quote the title or summary."
IMPACT_HEADING = "Industry impact"
IMPACT_NOTE = "Quoted from sources. Not confirmed effects."
NO_IMPACT = "No supply, cost, jobs, or impact words in these summaries."
TRACKER_HEADING = "Filings and funding"
TRACKER_NOTE = "Finance stories whose title or summary contains earnings, filing, funding, enforcement, guidance, settlement, order, or comment."
NO_TRACKER = "No earnings, filing, funding, or enforcement words in the current finance stories."
STATS_HEADING = "Local cache"
STATS_NOTE = "Counts from this machine's cache. This is not reader analytics."

LABELS = {
    "technology": "Technology",
    "education": "Education",
    "industry": "Industry",
    "finance": "Finance",
}




def json_for_script(payload) -> str:
    return json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")


def _esc(value) -> str:
    return escape("" if value is None else str(value), quote=True)


def _page(title: str, body: str, page_class: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
<meta name="theme-color" content="#f8f9f6">
<link rel="stylesheet" href="/static/design.css">
</head>
<body class="{_esc(page_class)}">
<a class="skip-link" href="#main-content">Skip to content</a>
<div class="reading-progress" aria-hidden="true"></div>
{body}
{footer()}
<script src="/static/reader.js" defer></script>
<script src="/static/interface.js" defer></script>
</body>
</html>"""


def _summary_html(item: dict, limit: int | None) -> str:
    sentences = list(item.get("summary_sentences") or [])
    if limit is not None:
        sentences = sentences[:limit]
    if not sentences:
        return f"<p>{NO_EXCERPT}</p>"
    parts = []
    for sentence in sentences:
        text = _esc(sentence)
        if item.get("summary_truncated"):
            text += "…"
        parts.append(f"<p>{text}</p>")
    note = TRUNCATED_NOTE if item.get("summary_truncated") else SUMMARY_NOTE
    parts.append(f'<p class="summary-note">{note}</p>')
    return "".join(parts)


def reader_catalog(stories: list, history: list | None = None) -> list:
    catalog = []
    comparison = history if history is not None else stories
    for item in stories:
        row = dict(item)
        row["materialUpdate"] = material_update(item, comparison)
        row["changeSentences"] = change_sentences(item, comparison)
        content = json.dumps([item.get("title"), item.get("excerpt"), item.get("summary_sentences")], ensure_ascii=False)
        row["followKey"] = str(item["id"]) + ":" + hashlib.sha256(content.encode()).hexdigest()[:12]
        catalog.append(row)
    return catalog


def _story_image(item, eager=False):
    url = safe_image_url(item.get("image_url"), item.get("url", ""))
    if not url:
        return ""
    display_url = display_image_url(url)
    fallback = f' data-image-fallback="{_esc(url)}"' if display_url != url else ""
    credit = item.get("image_credit") or f'Image via {item.get("source_name", "original source")}'
    return f'''<figure class="story-image"><a href="/story/{_esc(item.get('id'))}" tabindex="-1">
<img src="{_esc(display_url)}"{fallback} alt="{_esc(item.get('image_alt', ''))}" loading="{'eager' if eager else 'lazy'}" decoding="async" referrerpolicy="no-referrer" width="1200" height="800"></a>
<figcaption>{_esc(credit)}</figcaption></figure>'''


def _image_width(item):
    try:
        return max(0, int(item.get("image_width") or 0))
    except (ValueError, TypeError):
        return 0


def _edition_order(items):
    def date_key(item):
        date = parse_date(item.get("published_at") or "")
        return date.timestamp() if date else float("-inf")
    rows = sorted(items, key=date_key, reverse=True)
    photos = [row for row in rows[:12] if safe_image_url(row.get("image_url"), row.get("url", ""))]
    lead = next((row for row in photos if _image_width(row) == 0 or _image_width(row) >= 600), photos[0] if photos else None)
    return [lead, *[row for row in rows if row is not lead]] if lead else rows


def render_home(snapshot: dict, history: list | None = None) -> str:
    stories = _edition_order(snapshot.get("stories") or [])
    refreshing = bool(snapshot.get("refreshing"))
    sources = snapshot.get("sources") or []
    errors = []
    for source in sources:
        if not source.get("last_error"):
            continue
        errors.append(
            f'<p class="source-error" data-category="{_esc(source.get("category"))}">'
            f"{_esc(source.get('name'))} {SOURCE_DOWN}</p>"
        )
    cards = []
    for index, item in enumerate(stories):
        published = item.get("published_at") or NO_TIME
        category = item.get("category") or ""
        image = _story_image(item, eager=index == 0)
        classes = "card" + (" is-lead" if index == 0 else " is-latest-lead" if index == 1 else "") + (" has-image" if image else "")
        image_note = f'<p>Image credit: {_esc(item.get("image_credit") or item.get("source_name"))}</p>' if image else ""
        cards.append(
            f'<article class="{classes}" data-edition-order="{index}" data-image-width="{_image_width(item)}" data-category="{_esc(category)}" style="--order:{min(index, 5)}">'
            f'<div class="card-topline"><span class="category-tag">{_esc(LABELS.get(category, category))}</span>'
            f'<span class="story-source">{_esc(item.get("source_name"))}</span></div>'
            f'{image}'
            f'<h2><a href="/story/{_esc(item.get("id"))}">{_esc(item.get("title"))}</a></h2>'
            f'<div class="story-dek">{_summary_html(item, 2)}</div>'
            f'<div class="card-bottom"><span>{_esc(display_date(item.get("published_at")))}</span>'
            f'<a href="/story/{_esc(item.get("id"))}">Read &amp; explore <span aria-hidden="true">↗</span></a></div>'
            f'<details class="provenance"><summary>Source &amp; timestamps</summary>'
            f'<p>{SUMMARY_NOTE}</p><p>Published {_esc(published)}</p>'
            f'<p>Retrieved {_esc(item.get("retrieved_at"))}</p>'
            f'<p><a href="{_esc(item.get("url"))}">Source link</a></p>{image_note}</details>'
            f"</article>"
        )
    if stories:
        mode = "is-solo" if len(cards) == 1 else "is-compact" if len(cards) <= 4 else ""
        main = f'''<div id="story-list">{''.join(errors)}<div class="edition-front {mode}">
<section class="front-top" data-edition-column="top" {'' if len(cards) > 4 else 'hidden'}><h2 class="column-heading">Top stories</h2>{''.join(cards[4:7])}</section>
<section class="front-lead" data-edition-column="lead" aria-label="Lead story">{cards[0]}</section>
<section class="front-latest" data-edition-column="latest" {'' if len(cards) > 1 else 'hidden'}><h2 class="column-heading">Latest</h2>{''.join(cards[1:4])}</section>
</div><section class="story-grid" data-edition-column="more" aria-label="More stories" {'' if len(cards) > 7 else 'hidden'}><h2 class="more-heading">More stories</h2>{''.join(cards[7:])}</section></div>'''
    elif refreshing:
        main = f'<div class="empty-state"><p class="eyebrow">Building your edition</p><h2 id="loading">{LOADING}</h2></div>'
    else:
        main = f'<div class="empty-state">{"".join(errors)}<h2>A quiet moment.</h2><p>{EMPTY_FEED}</p><button type="button" id="refresh">Retry fetch</button></div>'
    filters = [
        ("all", "All"),
        ("technology", "Technology"),
        ("education", "Education"),
        ("industry", "Industry"),
        ("finance", "Finance"),
        ("following", "Following"),
    ]
    nav = "".join(
        f'<button type="button" data-filter="{key}">{label}</button>' for key, label in filters
    )
    catalog = reader_catalog(stories, history)
    payload = {
        "stories": catalog,
        "sources": sources,
        "refreshing": refreshing,
        "stopwords": sorted(STOPWORDS),
        "shortTopics": sorted(SHORT_TOPICS),
        "followEmpty": FOLLOW_EMPTY,
        "whatChanged": WHAT_CHANGED,
        "briefing": BRIEFING,
        "briefingNote": BRIEFING_NOTE,
        "emailNote": EMAIL_NOTE,
        "copyBriefing": COPY_BRIEFING,
        "emailBriefing": EMAIL_BRIEFING,
    }
    body = f"""
{masthead()}
<main class="wrap edition" id="main-content" tabindex="-1">
<section class="edition-intro">
<div><p class="eyebrow edition-kicker">Technology · Education · Industry · Finance</p>
<h1>A clearer view. <em>A deeper read.</em></h1>
<p class="intro-dek">{HOME_DEK}</p></div>
<aside class="research-feature"><p class="eyebrow">The research notebook</p><h2>Go beyond the headline.</h2>
<p>Ask a question. Read the original evidence. Find what the story leaves open.</p>
<a href="/research">Research a question <span aria-hidden="true">↗</span></a></aside>
</section>
<div id="edition-start" aria-hidden="true"></div><div class="edition-toolbar">
<span class="category-caption">Explore <span aria-hidden="true">/</span></span>
<button class="category-scroll" type="button" data-category-scroll="-1" aria-label="Scroll categories left" aria-controls="category-nav" hidden><span aria-hidden="true">‹</span></button>
<nav class="nav" id="category-nav" aria-label="News categories"><span class="nav-indicator" aria-hidden="true"></span>{nav}</nav>
<button class="category-scroll" type="button" data-category-scroll="1" aria-label="Scroll categories right" aria-controls="category-nav" hidden><span aria-hidden="true">›</span></button>
<span class="edition-count" aria-live="polite">{len(stories)} stories in this edition</span></div>
<div class="news-layout"><div class="news-feed">
{main}
<div id="following" hidden></div>
</div></div>
<div class="edition-utilities">{_tracker_html(stories)}{_stats_html(snapshot)}</div>
<p class="notice site-notice">{FINANCE_NOTICE}</p>
</main>
<script id="newsren-data" type="application/json">{json_for_script(payload)}</script>
"""
    return _page("The Newsren", body, "edition-page")


def _quote_html(story: dict, match) -> str:
    if isinstance(match, dict):
        sentence = match.get("sentence") or ""
        url = match.get("url") or story.get("url")
        source = match.get("source_name") or story.get("source_name")
        story_id = match.get("id") or ""
        title = match.get("title") or "Related story"
        extra = ""
        if story_id and story_id != story.get("id"):
            extra = (
                f"<p>{_esc(source)} · "
                f'<a href="/story/{_esc(story_id)}">{_esc(title)}</a></p>'
            )
        return (
            f"<blockquote><p>{_esc(sentence)}</p>"
            f'<p><a href="{_esc(url)}">Source link</a></p>'
            f"{extra}</blockquote>"
        )
    return (
        f"<blockquote><p>{_esc(match)}</p>"
        f'<p><a href="{_esc(story.get("url"))}">Source link</a></p></blockquote>'
    )


def _related_html(story: dict, related: list | None) -> str:
    rows = list(related or [])
    if not rows:
        return f'<section class="block" id="story-related"><h3>Connected stories</h3><p>{RELATED_EMPTY}</p></section>'
    items = []
    for row in timeline_stories(story, rows):
        item = row["story"]
        published = item.get("published_at") or NO_TIME
        category = item.get("category") or ""
        meta = (
            f"{_esc(published)} · {_esc(LABELS.get(category, category))} · "
            f"{_esc(item.get('source_name'))}"
        )
        if row["is_current"]:
            title = f"<p>{_esc(item.get('title'))} · {THIS_STORY}</p>"
        else:
            title = (
                f'<p><a href="/story/{_esc(item.get("id"))}">'
                f"{_esc(item.get('title'))}</a></p>"
            )
        items.append(f"<li>{title}<p>{meta}</p></li>")
    changed = new_sentences(story, rows)
    if not earlier_related(story, rows):
        new_html = f"<p>{NO_EARLIER}</p>"
    elif changed:
        quotes = "".join(f"<p>{_esc(sentence)}</p>" for sentence in changed)
        new_html = f"<p>{WHAT_IS_NEW}</p>{quotes}"
    else:
        new_html = f"<p>{WHAT_IS_NEW}</p><p>{NOTHING_NEW}</p>"
    return (
        f'<section class="block" id="story-related"><h3>Connected stories</h3>'
        f"<p>{RELATED_NOTE}</p><ol class=\"related-list\">{''.join(items)}</ol>"
        f"{new_html}</section>"
    )


def _glossary_html(story: dict) -> str:
    entries = glossary_entries(story)
    if not entries:
        return ""
    rows = "".join(
        f"<p><strong>{_esc(entry['word'])}</strong> — {_esc(entry['sentence'])}</p>"
        for entry in entries
    )
    return f"<h4>{GLOSSARY_HEADING}</h4><p>{GLOSSARY_NOTE}</p>{rows}"


def _inspect_html(story: dict, related: list | None) -> str:
    rows = list(related or [])
    sources = "".join(
        f'<p>{_esc(item["source_name"])} · <a href="{_esc(item["url"])}">Source link</a></p>'
        for item in independent_sources(story, rows)
    )
    hedges = uncertainty_sentences(story)
    if hedges:
        uncertainty = "".join(f"<p>{_esc(sentence)}</p>" for sentence in hedges)
        uncertainty_html = f"<h4>{UNCERTAINTY_HEADING}</h4>{uncertainty}"
    else:
        uncertainty_html = f"<h4>{UNCERTAINTY_HEADING}</h4><p>{NO_UNCERTAINTY}</p>"
    unrepeated = unrepeated_sentences(story, rows)
    if not rows:
        only_html = f"<p>{UNREPEATED_NO_RELATED}</p>"
    elif unrepeated:
        quotes = "".join(f"<p>{_esc(sentence)}</p>" for sentence in unrepeated)
        only_html = f"<p>{UNREPEATED_NOTE}</p>{quotes}"
    else:
        only_html = f"<p>{UNREPEATED_NONE}</p>"
    others = other_section_stories(story, rows)
    if others:
        other_rows = []
        for item in others:
            sentence = (item.get("summary_sentences") or [""])[0]
            other_rows.append(
                f'<p><a href="/story/{_esc(item.get("id"))}">{_esc(item.get("title"))}</a></p>'
                f"<p>{_esc(sentence)}</p>"
                f'<p>{_esc(item.get("source_name"))} · <a href="{_esc(item.get("url"))}">Source link</a></p>'
            )
        other_html = f"<h4>{OTHER_HEADING}</h4><p>{OTHER_NOTE}</p>{''.join(other_rows)}"
    else:
        other_html = f"<h4>{OTHER_HEADING}</h4><p>{NO_OTHER}</p>"
    claims = claim_labels(story)
    if story.get("category") == "finance":
        if claims:
            claim_rows = "".join(
                f"<p>{_esc(row['label'])}: {_esc(row['sentence'])}</p>" for row in claims
            )
            claim_html = f"<h4>{CLAIM_HEADING}</h4>{claim_rows}"
        else:
            claim_html = f"<h4>{CLAIM_HEADING}</h4><p>{NO_CLAIM}</p>"
    else:
        claim_html = ""
    return (
        f'<section class="block" id="story-inspect"><h3>{INSPECT_HEADING}</h3>'
        f"<p>{INSPECT_NOTE}</p>"
        f"<h4>{SOURCES_HEADING}</h4>{sources}"
        f"{uncertainty_html}"
        f"{only_html}"
        f"{other_html}"
        f"{claim_html}</section>"
    )


def _tracker_html(stories: list) -> str:
    rows = tracker_rows(stories)
    if rows:
        items = "".join(
            f"<p>{_esc(row['label'])} · {_esc(row.get('published_at') or NO_TIME)} · "
            f"{_esc(row.get('source_name'))} · "
            f'<a href="/story/{_esc(row["id"])}">{_esc(row["title"])}</a></p>'
            for row in rows
        )
    else:
        items = f"<p>{NO_TRACKER}</p>"
    return (
        f'<section class="block" id="finance-tracker"><details class="utility-fold"><summary><h3>{TRACKER_HEADING}</h3></summary>'
        f"<p>{TRACKER_NOTE}</p>{items}</details></section>"
    )


def _stats_html(snapshot: dict) -> str:
    stats = cache_stats(snapshot)
    counts = " · ".join(
        f"{stats['by_category'][key]} {LABELS[key]}" for key in ("technology", "education", "industry", "finance")
    )
    return (
        f'<section class="block" id="local-cache"><details class="utility-fold"><summary><h3>{STATS_HEADING}</h3></summary>'
        f"<p>{STATS_NOTE}</p>"
        f"<p>{stats['stories']} stories · {counts}</p>"
        f"<p>{stats['sources_ok']} sources available · {stats['sources_down']} temporarily unavailable</p>"
        f"</details></section>"
    )


def _lesson_html(story: dict) -> str:
    cloze = lesson_cloze(story)
    evidence = (story.get("summary_sentences") or [NO_EXCERPT])[0] if story.get("summary_sentences") else NO_EXCERPT
    if cloze:
        cloze_html = f"<p>{_esc(cloze['prompt'])}</p><p>Answer: {_esc(cloze['answer'])}</p>"
    else:
        cloze_html = f"<p>{NO_EXCERPT}</p>"
    return (
        f'<section class="block" id="story-lesson"><h3>{LESSON_HEADING}</h3>'
        f"<p>{LESSON_NOTE}</p>{cloze_html}"
        f'<p>"{_esc(story.get("title"))}": What does this story claim?</p>'
        f'<p>"{_esc(evidence)}": What evidence does the source give?</p>'
        f"<p>What does this summary not say?</p></section>"
    )


def _impact_html(story: dict, related: list | None) -> str:
    rows = impact_sentences(story, related)
    if rows:
        items = "".join(
            f"<p>{_esc(row['sentence'])}</p>"
            f'<p>{_esc(row.get("source_name"))} · '
            f'<a href="/story/{_esc(row["id"])}">{_esc(row["title"])}</a></p>'
            for row in rows
        )
    else:
        items = f"<p>{NO_IMPACT}</p>"
    return (
        f'<section class="block" id="story-impact"><h3>{IMPACT_HEADING}</h3>'
        f"<p>{IMPACT_NOTE}</p>{items}</section>"
    )


def render_story(story: dict, question: str = "", matches: list | None = None, related: list | None = None) -> str:
    published = story.get("published_at") or NO_TIME
    category = story.get("category") or ""
    finance = f'<p class="notice">{FINANCE_NOTICE}</p>' if category == "finance" else ""
    sentences = list(story.get("summary_sentences") or [])
    evidence = sentences[0] if sentences else NO_EXCERPT
    ask = ""
    if (question or "").strip() and matches is not None:
        if matches:
            quotes = "".join(_quote_html(story, match) for match in matches)
            ask = f"<p>{ASK_NOTE}</p>{quotes}"
        else:
            ask = f"<p>{NO_SUPPORT}</p>"
    professional_notice = f"<p>{FINANCE_NOTICE}</p>" if category == "finance" else ""
    unrepeated = unrepeated_sentences(story, related or [])
    if not (related or []):
        unrepeated_html = f"<p>{UNREPEATED_NO_RELATED}</p>"
    elif unrepeated:
        quotes = "".join(f"<p>{_esc(sentence)}</p>" for sentence in unrepeated)
        unrepeated_html = f"<p>{UNREPEATED_NOTE}</p>{quotes}"
    else:
        unrepeated_html = f"<p>{UNREPEATED_NONE}</p>"
    student_body = "".join(f"<p>{_esc(sentence)}</p>" for sentence in sentences) or f"<p>{NO_EXCERPT}</p>"
    glossary = _glossary_html(story)
    learning = render_learning(story)
    toc = contents([("story-summary", "The brief"), ("story-ask", "Ask a question"),
                    ("story-explain", "Read & learn"), ("story-follow", "Follow up"),
                    ("story-related", "The timeline"), ("story-inspect", "Sources & evidence"),
                    ("story-lesson", "The classroom"), ("story-impact", "Industry context")])
    body = f"""
{masthead()}
<main class="wrap article-reader" id="main-content" tabindex="-1" data-category="{_esc(category)}">
<section class="page-intro" id="story-header">
<p class="eyebrow"><span class="category-tag">{_esc(LABELS.get(category, category))}</span> / {_esc(story.get("source_name"))}</p>
<h1>{_esc(story.get("title"))}</h1>
<div class="meta">
<p>{_esc(display_date(story.get('published_at')))}</p>
<p><a href="{_esc(story.get("url"))}">Source link ↗</a></p>
</div>
<details class="provenance"><summary>Publication &amp; retrieval details</summary><p>Published {_esc(published)}</p><p>Retrieved {_esc(story.get('retrieved_at'))}</p></details>
{finance}
</section>
<div class="reader-layout">{toc}<article class="reader-body">
{_story_image(story, eager=True)}
<section class="block" id="story-summary">
<h3>Summary</h3>
{_summary_html(story, None)}
</section>
<section class="block" id="story-ask">
<h3>Ask this story</h3>
<p>Search this story and its connected sources. <a href="/research?story={_esc(story.get('id'))}">Start a research note ↗</a></p>
<form id="ask-form" class="ask-form" method="get">
<label for="question">Your question</label><input id="question" name="q" value="{_esc(question)}" required>
<button type="submit">Submit</button>
</form>
{ask}
</section>
<section class="block" id="story-explain">
<h3>Explain for</h3>
<div class="audience">
<button type="button" data-choose="student">Student</button>
<button type="button" data-choose="educator">Educator</button>
<button type="button" data-choose="professional">Professional</button>
</div>
<section data-audience="student">{learning['student']}<h4>Source passage</h4>{student_body}<p>{STUDENT_NOTE}</p>{glossary}</section>
<section data-audience="educator" hidden>
{learning['educator']}<h4>Source passage</h4>
{student_body}
<p>"{_esc(story.get("title"))}": What does this story claim?</p>
<p>"{_esc(evidence)}": What evidence does the source give?</p>
<p>What does this summary not say?</p>
{glossary}
</section>
<section data-audience="professional" hidden>
{learning['professional']}<h4>Source passage</h4>
{student_body}
<p>What is the original source: {_esc(story.get("source_name"))} {_esc(story.get("url"))}</p>
<p>Is the time explicit: {_esc(published)}</p>
<p>Which parts are only this source's account and have not been repeated by another source</p>
{unrepeated_html}
{professional_notice}
{glossary}
</section>
</section>
<section class="block" id="story-follow">
<h3>Follow this question</h3>
<div class="follow-row">
<button type="button" id="follow" disabled>Save follow</button>
</div>
<p>{FOLLOW_NOTE}</p>
</section>
{_related_html(story, related)}
{_inspect_html(story, related)}
{_lesson_html(story)}
{_impact_html(story, related)}
</article></div>
</main>
"""
    return _page(story.get("title") or "The Newsren", body, "story-page")


def render_not_found() -> str:
    return _page("Not found", masthead() + '<main class="wrap empty-state" id="main-content" tabindex="-1"><p class="eyebrow">404 / A missing page</p><h1>This story was not found.</h1><p><a href="/">Back to home</a></p></main>')
