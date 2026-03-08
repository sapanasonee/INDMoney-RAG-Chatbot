"""
Phase 1 Ingestion — Scrape 12 official URLs from README.
Extracts: Scheme Facts (Expense Ratio, Exit Load, Riskometer) and
How-to Steps for 'How to download statements'.
Every piece of data saved with source_url for citations.
Output: backend/data/processed_schemes.json
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from io import BytesIO

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from pypdf import PdfReader


# ---------------------------------------------------------------------------
# Manual fallback: if scraper returns null expense_ratio, use these (Regular plan).
# Only for the 5 approved schemes. Update when SIDs are updated.
# ---------------------------------------------------------------------------
EXPENSE_RATIO_FALLBACK_MAP: dict[str, str] = {
    "HDFC Small Cap Fund": "1.54%",
    "HDFC Flexi Cap Fund": "1.48%",
    "SBI Contra Fund": "1.59%",
    "HDFC ELSS Tax Saver": "1.72%",
    "Parag Parikh Flexi Cap": "1.34%",
}


# ---------------------------------------------------------------------------
# Official source URLs from README (12)
# ---------------------------------------------------------------------------
OFFICIAL_URLS = [
    {
        "url": "https://www.hdfcfund.com/product-solutions/overview/hdfc-small-cap-fund/regular",
        "scheme": "HDFC Small Cap Fund",
        "label": "Scheme overview (Regular)",
    },
    {
        "url": "https://files.hdfcfund.com/s3fs-public/SID/2025-05/SID%20-%20HDFC%20Small%20Cap%20Fund%20dated%20May%2030,%202025.pdf",
        "scheme": "HDFC Small Cap Fund",
        "label": "SID PDF",
        "is_pdf": True,
    },
    {
        "url": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/regular",
        "scheme": "HDFC Flexi Cap Fund",
        "label": "Scheme page (Regular)",
    },
    {
        "url": "https://files.hdfcfund.com/s3fs-public/Others/2025-05/Fund%20Facts%20-%20HDFC%20Flexi%20Cap%20Fund_May%2025.pdf",
        "scheme": "HDFC Flexi Cap Fund",
        "label": "Fund Facts PDF",
        "is_pdf": True,
    },
    {
        "url": "https://www.sbimf.com/sbimf-scheme-details/sbi-contra-fund-12",
        "scheme": "SBI Contra Fund",
        "label": "Scheme details",
    },
    {
        "url": "https://www.sbimf.com/docs/default-source/lists/sid---sbi-contra-fund8ce474c1a5404a2b899f14f6f21a95dd.pdf",
        "scheme": "SBI Contra Fund",
        "label": "SID PDF",
        "is_pdf": True,
    },
    {
        "url": "https://www.sbimf.com/docs/default-source/scheme-factsheets/sbi-contra-fund-factsheet-june-2025.pdf",
        "scheme": "SBI Contra Fund",
        "label": "Fact sheet PDF",
        "is_pdf": True,
    },
    {
        "url": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver/regular",
        "scheme": "HDFC ELSS Tax Saver",
        "label": "Scheme page (Regular)",
    },
    {
        "url": "https://amc.ppfas.com/pltvf/",
        "scheme": "Parag Parikh Flexi Cap",
        "label": "Scheme landing page",
    },
    {
        "url": "https://amc.ppfas.com/schemes/key-highlights-of-the-scheme/index.php",
        "scheme": "Parag Parikh Flexi Cap",
        "label": "Key highlights",
    },
    {
        "url": "https://amc.ppfas.com/downloads/parag-parikh-flexi-cap-fund/SID_PPFCF.pdf",
        "scheme": "Parag Parikh Flexi Cap",
        "label": "SID PDF",
        "is_pdf": True,
    },
    {
        "url": "https://www.amfiindia.com",
        "scheme": "AMFI (reference / NAV)",
        "label": "AMFI India",
    },
]


def extract_facts_from_text(text: str, source_url: str) -> dict:
    """Extract scheme facts from raw text. All with source_url."""
    facts = {k: {"value": None, "source_url": source_url} for k in (
        "expense_ratio", "exit_load", "riskometer", "aum",
        "benchmark", "fund_manager", "category", "objective",
        "nav", "inception_date", "min_investment", "min_sip",
    )}
    if not text or not text.strip():
        return facts

    # --- Expense Ratio ---
    er_patterns = [
        (r"Regular[^.]{0,200}?(?:Total\s+Expense\s+Ratio|TER|Net\s+Expense\s+Ratio)[^.]*?([\d.]+)\s*%", True),
        (r"(?:Total\s+Expense\s+Ratio\s*\(TER\)|Total\s+Expense\s+Ratio|TER)\s*[:\-]?\s*([\d.]+)\s*%", False),
        (r"Net\s+Expense\s+Ratio\s*[:\-]?\s*([\d.]+)\s*%", False),
        (r"Direct\s+Plan\s*[-\s]*Expense\s+Ratio\s*[:\-]?\s*([\d.]+)\s*%", False),
        (r"TER\s*[:\-]?\s*([\d.]+)\s*%", False),
        (r"expense\s+ratio\s*[:\-]?\s*([\d.]+)\s*%", False),
    ]
    candidates: list[tuple[str, bool]] = []
    for pattern, prefer_regular in er_patterns:
        for m in re.finditer(pattern, text, re.I | re.DOTALL):
            val = m.group(1).strip()
            if not val or "." not in val:
                continue
            try:
                num = float(val)
                if num < 0.1 or num > 5.0:
                    continue
            except ValueError:
                continue
            ctx_start = max(0, m.start() - 250)
            is_regular = "regular" in text[ctx_start:m.start()].lower()
            candidates.append((val + "%", is_regular))
    if candidates:
        regular_vals = [v for v, r in candidates if r]
        facts["expense_ratio"]["value"] = regular_vals[0] if regular_vals else candidates[0][0]

    # --- Exit Load ---
    el_patterns = [
        r"Exit\s+Load\s*[:\-]?\s*([^.\n]{10,120}?)(?=\n|\.\s|$)",
        r"exit\s+load\s*[:\-]?\s*([^.\n]{10,120}?)(?=\n|\.\s|$)",
        r"([\d.]+%\s+if\s+redeemed[^.\n]{0,80})",
    ]
    for p in el_patterns:
        m = re.search(p, text, re.I | re.DOTALL)
        if m:
            val = m.group(1).strip()
            if len(val) > 5 and ("%" in val or "redeem" in val.lower() or "exit" in val.lower()):
                facts["exit_load"]["value"] = val[:200]
                break

    # --- Riskometer ---
    risk_patterns = [
        r"Riskometer\s*[:\-]?\s*([A-Za-z][A-Za-z\s]+?)(?=\n|\.|$)",
        r"Risk\s+(?:Level|Profile|ometer)\s*[:\-]?\s*([A-Za-z][A-Za-z\s]+?)(?=\n|\.|$)",
        r"(Moderately\s+High|Moderate|Low|High|Very\s+High)(?=\s|\.|$)",
    ]
    for p in risk_patterns:
        m = re.search(p, text, re.I)
        if m:
            val = m.group(1).strip()
            if len(val) < 50 and any(x in val.lower() for x in ("moderate", "low", "high", "risk")):
                facts["riskometer"]["value"] = val
                break

    # --- AUM (Assets Under Management) ---
    aum_patterns = [
        r"(?:AUM|Assets?\s+Under\s+Management|Fund\s+Size|Net\s+Assets?|Corpus)\s*[:\-]?\s*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(Cr(?:ore)?s?|Lakh|L|Billion|Bn|crore)",
        r"(?:AUM|Fund\s+Size|Net\s+Assets?)\s*[:\-]?\s*([\d,]+(?:\.\d+)?)\s*(Cr(?:ore)?s?|crore)",
        r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(Cr(?:ore)?s?|crore)\s*(?:\(|as\s+on|AUM)",
    ]
    for p in aum_patterns:
        m = re.search(p, text, re.I)
        if m:
            val = m.group(1).strip().replace(",", "")
            unit = m.group(2).strip()
            try:
                num = float(val)
                if num > 0:
                    facts["aum"]["value"] = f"Rs. {val} {unit}"
                    break
            except ValueError:
                continue

    # --- Benchmark ---
    bench_patterns = [
        r"[Bb]enchmark\s*(?:[Ii]ndex)?\s*[:\-]?\s*((?:Nifty|S&P\s+BSE|BSE)\s+[A-Za-z0-9\s\-&/()]+?(?:Index|TRI))",
        r"[Bb]enchmark\s*[:\-]?\s*((?:Nifty|S&P\s+BSE|BSE)\s+[A-Za-z0-9\s\-&/()]+?)(?:\n|\.|$)",
        r"((?:Nifty|S&P\s+BSE|BSE)\s+\d*\s*[A-Za-z\s\-&]*?(?:Index|TRI))",
    ]
    for p in bench_patterns:
        m = re.search(p, text, re.I)
        if m:
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            if 5 < len(val) < 120 and "standard" not in val.lower():
                facts["benchmark"]["value"] = val
                break

    # --- Fund Manager ---
    fm_patterns = [
        r"[Ff]und\s+[Mm]anager[s]?\s*[:\-]?\s*(?:Mr\.?\s*|Ms\.?\s*|Shri\.?\s*)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
    ]
    noise_words = {"fund", "manager", "the", "and", "scheme", "investment", "date", "managing", "since", "factsheet", "portfolio", "disclosure", "financials"}
    for p in fm_patterns:
        for m in re.finditer(p, text):
            val = m.group(1).strip()
            words = val.lower().split()
            if len(val) > 5 and not any(w in noise_words for w in words):
                facts["fund_manager"]["value"] = val
                break
        if facts["fund_manager"]["value"]:
            break

    # --- Category ---
    cat_patterns = [
        r"[Cc]ategory\s*[:\-]?\s*([A-Za-z][A-Za-z\s\-]+?)(?:\n|\.|$)",
        r"(?:Equity|Debt|Hybrid|ELSS|Contra|Flexi\s*Cap|Small\s*Cap|Multi\s*Cap|Large\s*Cap|Mid\s*Cap|Tax\s+Sav(?:er|ing)|Balanced)\s*(?:Fund|Scheme)?",
    ]
    for p in cat_patterns:
        m = re.search(p, text, re.I)
        if m:
            val = (m.group(1) if m.lastindex else m.group(0)).strip()
            if 3 < len(val) < 80:
                facts["category"]["value"] = val
                break

    # --- Investment Objective ---
    obj_patterns = [
        r"(?:Investment\s+)?[Oo]bjective\s*[:\-]?\s*(.{20,300}?)(?:\n\n|\.\s*\n|$)",
    ]
    for p in obj_patterns:
        m = re.search(p, text, re.I | re.DOTALL)
        if m:
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            if len(val) > 20:
                facts["objective"]["value"] = val[:300]
                break

    # --- NAV ---
    nav_patterns = [
        r"NAV\s*[:\-]?\s*(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)",
        r"(?:Latest\s+)?NAV\s*[:\-]?\s*([\d,]+\.\d{2,4})",
    ]
    for p in nav_patterns:
        m = re.search(p, text, re.I)
        if m:
            val = m.group(1).strip().replace(",", "")
            try:
                num = float(val)
                if 1.0 < num < 100000:
                    facts["nav"]["value"] = f"Rs. {val}"
                    break
            except ValueError:
                continue

    # --- Inception / Launch Date ---
    inception_patterns = [
        r"(?:Inception|Launch|Allotment)\s*[Dd]ate\s*[:\-]?\s*(\d{1,2}[\s\-/]\w{3,9}[\s\-/]\d{4})",
        r"(?:Inception|Launch|Allotment)\s*[Dd]ate\s*[:\-]?\s*(\w{3,9}\s+\d{1,2},?\s+\d{4})",
    ]
    for p in inception_patterns:
        m = re.search(p, text, re.I)
        if m:
            facts["inception_date"]["value"] = m.group(1).strip()
            break

    # --- Min Investment / Min SIP ---
    min_patterns = [
        r"[Mm]in(?:imum)?\s+(?:Investment|Application)\s*(?:Amount)?\s*[:\-]?\s*(?:Rs\.?|INR|₹)\s*([\d,]+)",
        r"[Mm]in(?:imum)?\s+(?:lump\s*sum|investment)\s*[:\-]?\s*(?:Rs\.?|INR|₹)\s*([\d,]+)",
    ]
    for p in min_patterns:
        m = re.search(p, text, re.I)
        if m:
            facts["min_investment"]["value"] = f"Rs. {m.group(1).strip()}"
            break

    sip_patterns = [
        r"[Mm]in(?:imum)?\s+SIP\s*(?:Amount|Investment)?\s*[:\-]?\s*(?:Rs\.?|INR|₹)\s*([\d,]+)",
        r"SIP\s*[:\-]?\s*(?:Rs\.?|INR|₹)\s*([\d,]+)\s*(?:per\s+month|/month|p\.m\.?)",
    ]
    for p in sip_patterns:
        m = re.search(p, text, re.I)
        if m:
            facts["min_sip"]["value"] = f"Rs. {m.group(1).strip()}"
            break

    return facts


def extract_how_to_download_statements(html_or_text: str, source_url: str) -> list[dict]:
    """Extract steps for 'How to download statements' from page text. Each step with source_url."""
    steps: list[dict] = []
    if not html_or_text or not html_or_text.strip():
        return steps

    # Prefer structured content: ordered/list items near "download" and "statement"
    soup = BeautifulSoup(html_or_text, "html.parser") if html_or_text.strip().startswith("<") else None
    text = soup.get_text(separator="\n", strip=True) if soup else html_or_text

    # Look for blocks that mention download + statement
    lower = text.lower()
    if "download" not in lower or "statement" not in lower:
        return steps

    # Find sentences or list items that look like steps
    step_patterns = [
        r"(?:Step\s*\d+[\.\)]\s*)?(?:Log\s+in[^.]{0,80}\.)",
        r"(?:Step\s*\d+[\.\)]\s*)?(?:Go\s+to[^.]{0,80}\.)",
        r"(?:Step\s*\d+[\.\)]\s*)?(?:Click\s+on[^.]{0,80}\.)",
        r"(?:Step\s*\d+[\.\)]\s*)?(?:Select\s+[^.]{0,80}\.)",
        r"(?:Step\s*\d+[\.\)]\s*)?([^.]{10,120}(?:download|statement)[^.]{0,80}\.)",
        r"(\d+[\.\)]\s*[^.\n]{15,150}(?:download|statement)[^.\n]{0,80})",
    ]
    seen = set()
    for p in step_patterns:
        for m in re.finditer(p, text, re.I):
            step_text = m.group(1).strip() if m.lastindex else m.group(0).strip()
            step_text = re.sub(r"\s+", " ", step_text)[:300]
            if step_text and step_text not in seen:
                seen.add(step_text)
                steps.append({"step": step_text, "source_url": source_url})

    # If no numbered steps, take a single snippet around "download statement"
    if not steps:
        snippet = re.search(
            r".{0,80}(?:how\s+to\s+)?download\s+statement[s]?.{0,120}",
            text,
            re.I | re.DOTALL,
        )
        if snippet:
            one = re.sub(r"\s+", " ", snippet.group(0)).strip()[:300]
            steps.append({"step": one, "source_url": source_url})

    return steps[:10]  # Cap at 10 steps per source


def _extract_text_chunks(raw_text: str, scheme_name: str, source_url: str, max_chunk=500) -> list[dict]:
    """Split raw page text into meaningful chunks for vector search. Skip noise."""
    noise_phrases = {"cookie", "privacy policy", "terms of use", "subscribe", "sign up", "log in", "forgot password"}
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    chunks = []
    current = []
    current_len = 0
    for line in lines:
        if len(line) < 5:
            continue
        if any(n in line.lower() for n in noise_phrases):
            continue
        current.append(line)
        current_len += len(line)
        if current_len >= max_chunk:
            text = " ".join(current)
            if len(text) > 30:
                chunks.append({"text": f"{scheme_name}. {text[:600]}", "source_url": source_url})
            current = []
            current_len = 0
    if current:
        text = " ".join(current)
        if len(text) > 30:
            chunks.append({"text": f"{scheme_name}. {text[:600]}", "source_url": source_url})
    return chunks[:20]


def parse_html_for_facts(html: str, source_url: str) -> tuple[dict, list[dict], str]:
    """Parse HTML to get scheme facts, how-to steps, and cleaned text."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    facts = extract_facts_from_text(text, source_url)
    steps = extract_how_to_download_statements(html, source_url)
    return facts, steps, text


def parse_pdf_text(pdf_bytes: bytes) -> str:
    """Extract raw text from PDF bytes."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n".join(parts)
    except Exception:
        return ""


async def scrape_url(
    page,
    request_context,
    entry: dict,
    out_schemes: dict,
) -> None:
    """Scrape one URL (HTML or PDF), extract facts and steps, merge into out_schemes with source_url."""
    url = entry["url"]
    scheme_name = entry["scheme"]
    is_pdf = entry.get("is_pdf", False)

    if scheme_name not in out_schemes:
        out_schemes[scheme_name] = {
            "scheme": scheme_name,
            "sources": [],
            "scheme_facts": [],
            "how_to_download_statements": [],
            "text_chunks": [],
        }

    try:
        raw_text = ""
        if is_pdf:
            response = await request_context.get(url)
            if response.status != 200:
                out_schemes[scheme_name]["sources"].append(
                    {"url": url, "label": entry["label"], "error": f"HTTP {response.status}"}
                )
                return
            body = await response.body()
            raw_text = parse_pdf_text(body)
            facts = extract_facts_from_text(raw_text, url)
            steps = extract_how_to_download_statements(raw_text, url)
        else:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await page.wait_for_timeout(2000)
            html = await page.content()
            facts, steps, raw_text = parse_html_for_facts(html, url)

        out_schemes[scheme_name]["sources"].append({"url": url, "label": entry["label"]})
        fact_entry = {"source_url": url, "from_pdf": is_pdf}
        for k in facts:
            fact_entry[k] = facts[k]
        out_schemes[scheme_name]["scheme_facts"].append(fact_entry)
        for s in steps:
            out_schemes[scheme_name]["how_to_download_statements"].append(s)

        if raw_text:
            chunks = _extract_text_chunks(raw_text, scheme_name, url)
            out_schemes[scheme_name]["text_chunks"].extend(chunks)
    except Exception as e:
        out_schemes[scheme_name]["sources"].append(
            {"url": url, "label": entry["label"], "error": str(e)}
        )


async def run_scraper() -> dict:
    """Run Playwright, scrape all 12 URLs, return structured data with source_url everywhere."""
    out_schemes: dict = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        request_context = context.request

        for entry in OFFICIAL_URLS:
            await scrape_url(page, request_context, entry, out_schemes)

        await browser.close()

    return out_schemes


def apply_expense_ratio_fallback(data: dict) -> None:
    """If an HTML-sourced scheme_facts entry has null expense_ratio, fill from same scheme's SID/PDF."""
    for scheme_name, scheme_data in data.items():
        facts_list = scheme_data.get("scheme_facts", [])
        # First non-null expense_ratio from a PDF source for this scheme
        pdf_expense = None
        for f in facts_list:
            if f.get("from_pdf") and (f.get("expense_ratio") or {}).get("value"):
                pdf_expense = f["expense_ratio"]
                break
        if not pdf_expense:
            continue
        # Fill null expense_ratio in HTML-sourced entries from that PDF
        for f in facts_list:
            if f.get("from_pdf"):
                continue
            if (f.get("expense_ratio") or {}).get("value") is None:
                f["expense_ratio"] = pdf_expense
        # Remove internal flag from output
        for f in facts_list:
            f.pop("from_pdf", None)


def apply_manual_expense_ratio_fallback(data: dict) -> None:
    """If expense_ratio is still null for a scheme in EXPENSE_RATIO_FALLBACK_MAP, use the hardcoded value."""
    for scheme_name, fallback_value in EXPENSE_RATIO_FALLBACK_MAP.items():
        if scheme_name not in data:
            continue
        facts_list = data[scheme_name].get("scheme_facts", [])
        for f in facts_list:
            er = f.get("expense_ratio") or {}
            if er.get("value") is not None:
                continue
            f["expense_ratio"] = {"value": fallback_value, "source_url": f.get("source_url", "")}


def save_processed_schemes(data: dict, out_path: Path) -> None:
    """Save to backend/data/processed_schemes.json."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> None:
    base = Path(__file__).resolve().parent
    out_path = base / "data" / "processed_schemes.json"

    print("Phase 1 Ingestion: scraping 12 official URLs...")
    data = asyncio.run(run_scraper())
    apply_expense_ratio_fallback(data)
    apply_manual_expense_ratio_fallback(data)
    save_processed_schemes(data, out_path)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
