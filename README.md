# The Newsren

A news research and learning reader that connects headlines to source evidence. Built with Python 3.10+, SQLite and HTML/CSS/JavaScript. The application itself uses only the Python standard library.

**[Open the live website](https://lyunify.github.io/newsren/)** · **[AI education research example](https://lyunify.github.io/newsren/research/ec5b777378f642bf816a8a45842481ba/)**

## What it does

- **Discover:** Technology, Education, Industry and Finance sections; publisher images and credits; source links; publication/retrieval timestamps; deduplication and cached source-error recovery.
- **Read and learn:** extractive briefs, questions over a story and connected reporting, Student/Educator/Professional views, glossary concepts, classroom activities and decision prompts.
- **Follow a question:** browser-local follows, version-aware seen markers, material-change filtering and source-based briefings. Copy a briefing or open a mail draft.
- **Research evidence:** plan a bounded approved-source search, inspect current/retained reporting, compare numbers and negation, cite exact passages and save the research record.
- **Investigate AI in education:** optional DOI/PMC full text through Europe PMC, candidate study-design/population/comparison passages and separate assisted-practice, independent-test, retention and transfer outcomes.
- **Synthesize optionally:** opt-in OpenAI or official Anthropic Claude synthesis and cited audience explanations, with citation/number validation and quotation fallback.
- **Review:** immutable research snapshots plus append-only human review decisions. Saved evidence, activity logs, limitations and JSON records remain inspectable.

The interface combines a photo-led three-column edition, a blue underline category menu, responsive reading layouts and reduced-motion-aware transitions. Source images load directly over HTTPS without a referrer; failed images collapse to text. BBC thumbnail routes use a larger version of the same photo with original-image fallback. Small images are capped at their natural width.

## Live demo and local app

This repository contains the application source and the GitHub Pages build workflow. The public website is generated from the curated snapshots in `demo/`; personal documents and local runtime data are excluded.

| Capability | GitHub Pages demo | Local Python app |
| --- | --- | --- |
| News reading, images, categories, audience views | Saved snapshot | Current cache |
| Questions over an article and connected excerpts | Browser-side extractive matches | Server-side extractive matches |
| Follows, seen markers, briefings | This browser, saved snapshot | This browser, current cache |
| Saved research, citations, study check, JSON | Two selected examples | All local saved runs |
| New research and open-access paper retrieval | Requires local app | Available without a model key |
| Approved-feed refresh | Requires local app | Background refresh about every 30 minutes |
| Optional model synthesis | Requires local app | Configured key plus per-run opt-in |
| Persist review decisions | Read-only saved status | Local review desk |

The public demo does not run Python, call a model, refresh itself, or save editorial decisions. The education example remains **pending human review**. A successful model call or passing test suite does not constitute editorial approval.

## Run locally

```bash
python3 server.py
```

Open [The Newsren](http://127.0.0.1:8765) or [Research](http://127.0.0.1:8765/research). The server listens on this machine only. No package installation or API key is required for the evidence workflow.

To try the education workflow, ask `Does AI improve learning?` and enter `10.1073/pnas.2422633122` or `PMC12232635`. Read the original passages before interpreting results. The saved example retains its original model record and a separately labelled editorial revision, both pending human review.

## Optional model synthesis

Evidence research works without a key. Model-written synthesis and cited Student/Educator/Professional explanations support OpenAI or official Anthropic Claude. Set `NEWSREN_ENABLE_MODEL=1`, select `NEWSREN_MODEL_PROVIDER=openai` (the backward-compatible default) or `anthropic`, and configure that provider's key and model before starting/restarting the server. Selection is explicit; a missing key or failure never sends evidence to another provider.

For OpenAI, the required settings are:

- `NEWSREN_ENABLE_MODEL=1`
- `NEWSREN_OPENAI_MODEL`: the exact name of a model in your account supporting Responses and structured JSON output.
- `OPENAI_API_KEY`: set privately in the server environment; never commit it or paste it into a research form.

For the macOS zsh shell, a hidden prompt avoids putting the key in a command:

```zsh
read -r -s 'OPENAI_API_KEY?OpenAI API key: '
export OPENAI_API_KEY
export NEWSREN_ENABLE_MODEL=1
export NEWSREN_MODEL_PROVIDER=openai
export NEWSREN_OPENAI_MODEL='your-supported-model-name'
python3 server.py
```

For official Anthropic Claude, enter the key at the hidden prompt as a separate terminal step, then export the configuration:

```zsh
read -r -s 'ANTHROPIC_API_KEY?Anthropic API key: '
```

```zsh
export ANTHROPIC_API_KEY
export NEWSREN_ENABLE_MODEL=1
export NEWSREN_MODEL_PROVIDER=anthropic
export NEWSREN_ANTHROPIC_MODEL='claude-haiku-4-5-20251001'
python3 server.py
```

The research form then enables **Add model synthesis & audience explanations**. It is unchecked by default. Selecting it sends the question and selected public-source passages to the named configured provider and can incur API charges. No provider key is exposed in the browser or saved in research records. Merely viewing a saved result never calls a model.

The integrations use [OpenAI Responses structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) or [Claude Messages structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs). One call per selected research run; at most eight passages of 1,200 characters, a 1,600-token output cap and a 64 KiB response cap. OpenAI requests set `store=false`; that OpenAI-specific field is not sent to Claude. Citation IDs and signed numbers are validated; missing citations, introduced numbers, invalid/incomplete responses or provider errors retain the original evidence quotations instead. Numbers must preserve their source representation, including signs and percent marks. These checks do not prove semantic entailment: model outputs still require human review.

## Evidence and product limits

News evidence is limited to RSS titles/excerpts. A DOI/PMC ID can retrieve open-access paper paragraphs through Europe PMC; arbitrary URLs, paywalls, tables and supplements are outside the current scope. Publication metadata does not independently establish peer review. Candidate study passages and comparison flags require judgment; missing selected evidence does not prove an outcome was never measured. Source diversity does not prove independence or accuracy.

The free search is lexical and strongest on English questions/articles. A request without matching evidence produces an explicit insufficiency result. Optional citation and number checks do not verify semantic entailment. Original model output, editorial revision and human review stay distinct.

Approved-feed research checks at most three catalog feeds and stops scheduling new requests after 30 seconds; per-source socket/read limits and body caps also apply. DNS and connection timing can exceed nominal budgets, so these are not hard end-to-end guarantees. Paper retrieval uses the fixed Europe PMC API with a bounded request count and XML size. See the retrieval modules for exact limits.

Following uses the loaded snapshot; reload the local app to see later fetches. There are no background per-user monitors, push notifications or automatic emails. Finance and industry coverage is excerpt-based and informational, not investment advice or a causal impact analysis.

## Local data and privacy

Ignored `data/` contains the news cache/history, `intelligence.sqlite3` and optional English display copies. Provider keys stay in the server environment; never commit `.env` files or paste keys into web forms. Browser follows and audience choices use `localStorage` key `newsren.reader`.

Personal assignment Markdown, internal notes under `docs/`, presentation files under `output/`, local editor/planning files, keys and runtime databases are ignored and excluded from the website. `demo/` contains deliberately selected public demonstration inputs. The exporter never includes the local presentation PDF.

## Build the static demo

```bash
python3 -m newsren.static_site --base-path /newsren --output _site
```

This reads the reviewed `demo/news.json` and `demo/research.json`; it does not read the local database, fetch sources or call a model. Exported links include the project path, and backend-only forms become explanatory read-only views. To preview the project path locally, export into `preview/newsren`, serve `preview`, and visit `/newsren/`:

```bash
python3 -m newsren.static_site --output /tmp/newsren-preview/newsren --base-path /newsren
python3 -m http.server 8000 --bind 127.0.0.1 --directory /tmp/newsren-preview
```

On pushes to `main`, GitHub Actions runs the tests, builds `_site/` and deploys that generated directory to GitHub Pages. Pull requests run verification without deployment. No separate website repository is needed. Public data and publisher images may become stale or unavailable between exports.

## Verify

```bash
python3 -m unittest discover -s tests -q
node --check static/reader.js
node --check static/interface.js
node --check static/demo.js
```

The offline suite covers evidence/citation/number validation, provider failure fallback, study distinctions, persistence, source identity, image safety and static subpath export. Tests use controlled providers and temporary data, with no remote model calls. HTTP tests bind loopback ports. GitHub Actions runs the same regression and static build on pushes and pull requests.

## Approved sources

Technology: The Verge, Ars Technica, MIT Technology Review, BBC Technology, IEEE Spectrum. Education: EdSurge, BBC Education. Industry: Supply Chain Dive, BBC Business. Finance: Federal Reserve and SEC press releases.

Publisher stories and images retain their original attribution and rights. The portal links to the original reporting and exposes its evidence limits.
