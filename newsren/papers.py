"""Approved, bounded Europe PMC retrieval and JATS source records."""

import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from newsren.network import read_bounded

API = "https://www.ebi.ac.uk/europepmc/webservices/rest/"


def normalize_identifier(value):
    value = (value or "").strip()
    if len(value) > 200:
        raise ValueError("Enter a DOI or PMC ID, not a full paper URL.")
    value = re.sub(r"^https://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^https://pmc\.ncbi\.nlm\.nih\.gov/articles/(PMC\d+)/?$", r"\1", value, flags=re.I)
    if re.fullmatch(r"PMC\d{1,12}", value, re.I):
        return "pmcid", value.upper()
    if re.fullmatch(r"10\.\d{4,9}/[A-Za-z0-9._;()/:+-]+", value):
        return "doi", value.lower()
    raise ValueError("Enter a valid DOI (10.…/…) or PMC ID (PMC…). Arbitrary URLs are not fetched.")


def _text(node):
    return " ".join("".join(node.itertext()).split()) if node is not None else ""


def parse_paper(xml, expected_pmcid, retrieved_at):
    root = ET.fromstring(xml)
    meta, body = root.find("front/article-meta"), root.find("body")
    if root.tag != "article" or meta is None or body is None:
        raise ValueError("The API did not return article full text.")
    ids = {row.get("pub-id-type"): _text(row) for row in meta.findall("article-id")}
    pmcid = ids.get("pmcid") or ids.get("pmcaid", "")
    if pmcid.upper() != expected_pmcid.upper():
        raise ValueError("Returned article identity did not match the requested PMC ID.")
    journal = _text(root.find("front/journal-meta/journal-title-group/journal-title"))
    article_type = root.get("article-type", "")
    status = "preprint" if article_type == "preprint" else (
        "published_journal_article" if article_type == "research-article" and journal else "unknown")
    dates = meta.findall("pub-date")
    dates.sort(key=lambda row: row.get("pub-type", row.get("publication-format", "")) not in {"epub", "electronic"})
    published = ""
    for date in dates:
        year, month, day = (date.findtext(key, "") for key in ("year", "month", "day"))
        if re.fullmatch(r"\d{4}", year):
            published = year
            if month.isdigit() and 1 <= int(month) <= 12:
                published += f"-{int(month):02d}"
                if day.isdigit() and 1 <= int(day) <= 31:
                    published += f"-{int(day):02d}"
            break
    paragraphs = []

    def walk(node, section):
        if node.tag in {"ref-list", "supplementary-material", "table-wrap", "fig", "fn-group"}:
            return
        if node.tag == "sec":
            title = _text(node.find("title"))
            if re.search(r"references|acknowledg|supplement|associated data|footnotes", title, re.I):
                return
            section = f"{section} / {title}" if title else section
        if node.tag == "p":
            text = _text(node)
            if text:
                paragraphs.append({"text": text, "section": section,
                                   "anchor": node.get("id") or f"article-p{len(paragraphs) + 1}"})
            return
        for child in node:
            walk(child, section)

    for abstract in meta.findall("abstract"):
        walk(abstract, "Abstract")
    walk(body, "Body")
    if not any(row["section"] != "Abstract" for row in paragraphs):
        raise ValueError("No usable article body was provided; abstract-only evidence is insufficient.")
    return {"pmcid": pmcid.upper(), "doi": ids.get("doi", "").lower(),
            "title": _text(meta.find("title-group/article-title")), "journal": journal,
            "publication_status": status, "peer_review_verified": False,
            "published_at": published, "retrieved_at": retrieved_at,
            "url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid.upper()}/",
            "api_url": f"{API}{pmcid.upper()}/fullTextXML", "paragraphs": paragraphs}


class PaperClient:
    def __init__(self, opener=None, clock=time.monotonic):
        self.opener = opener or build_opener()
        self.clock = clock
        self.request_count = 0

    def fetch(self, identifier, timeout=20):
        kind, identifier = normalize_identifier(identifier)
        deadline = self.clock() + timeout
        self.request_count = 0

        def read(path, limit):
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise TimeoutError("Primary-paper retrieval budget exhausted.")
            self.request_count += 1
            request = Request(API + path, headers={"User-Agent": "Newsren/1.0 (education evidence notebook)"})
            with self.opener.open(request, timeout=min(12, remaining)) as response:
                return read_bounded(response, limit, deadline, self.clock)

        pmcid = identifier
        if kind == "doi":
            query = urlencode({"query": f'DOI:"{identifier}"', "format": "json", "pageSize": 1})
            data = json.loads(read("search?" + query, 262144))
            results = data.get("resultList", {}).get("result", [])
            if not results or results[0].get("doi", "").lower() != identifier:
                raise ValueError("No matching DOI record was returned by Europe PMC.")
            pmcid = results[0].get("pmcid", "")
            if not re.fullmatch(r"PMC\d{1,12}", pmcid):
                raise ValueError("This DOI has no available PMC full-text record.")
        xml = read(f"{pmcid}/fullTextXML", 4 * 1024 * 1024)
        retrieved = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        paper = parse_paper(xml, pmcid, retrieved)
        if kind == "doi" and paper["doi"] != identifier:
            raise ValueError("Full-text DOI did not match the requested DOI.")
        paper["retrieval_calls"] = self.request_count
        return paper
