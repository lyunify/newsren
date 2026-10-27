# Public demonstration data

`news.json` contains 179 selected public RSS/Atom article excerpts and publisher image URLs from the local demo snapshot. `research.json` contains two selected AI-education research examples: the original Claude run and its separately labelled editorial revision. Both retain their pending human-review status.

These files are deliberately curated export inputs. They do not contain the local SQLite database, browser follow state, provider credentials, the personal assignment document, or unrelated research history. Source passages, credits, dates and limitations remain attached. Image availability depends on the original publishers.

Exporting these files makes no retrieval or model calls. To update the public demonstration, review the JSON changes and push to `main`; GitHub Actions tests the application, exports `_site/` under `/newsren/` and publishes that directory to Pages. Personal documents and presentation PDFs are excluded.
