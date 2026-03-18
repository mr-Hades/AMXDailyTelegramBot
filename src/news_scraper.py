"""CBA chairman-decisions scraper for Program Prospectus registrations."""

import re
from html import unescape
from typing import List, Optional

import requests

from .news_models import ProspectusDecision


class CBAProspectusScraper:
    """Scrapes CBA chairman-decisions page for Program Prospectus registrations."""

    BASE_URL = "https://www.cba.am"
    DECISIONS_URL = f"{BASE_URL}/en/chairman-decisions/"
    KEYWORD = "Program Prospectus"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    TIMEOUT = 30

    # Pattern: <a href=".../{id}/">TITLE</a>\n<span>DATE</span>\n<p>PREVIEW</p>
    _ITEM_RE = re.compile(
        r'<a\s+href="(?P<url>[^"]*chairman-decisions/(?P<id>\d+)/?)">'
        r"(?P<title>.*?)</a>"
        r"\s*<span>(?P<date>\d{4}-\d{2}-\d{2})\s*[\d:]*</span>"
        r"(?:\s*<p>(?P<preview>.*?)</p>)?",
        re.S,
    )

    # Company name patterns from titles
    _COMPANY_PATTERNS = [
        # "... PROGRAM PROSPECTUS OF BONDS OF "COMPANY" TYPE"
        re.compile(
            r"(?:PROSPECTUS|prospectus)\s+(?:OF\s+)?(?:BONDS\s+OF|for\s+(?:\w+\s+)*?(?:Bonds?\s+of))\s+"
            r'["\u201c\u201d](.+?)["\u201c\u201d]',
            re.I | re.S,
        ),
        # "... PROSPECTUS OF "COMPANY" ... BONDS"
        re.compile(
            r'(?:PROSPECTUS)\s+OF\s+["\u201c\u201d](.+?)["\u201c\u201d]',
            re.I | re.S,
        ),
        # Fallback: any quoted company name in title
        re.compile(
            r'["\u201c]([^"\u201d]{3,})["\u201d]',
            re.I,
        ),
    ]

    _SUPPLEMENT_RE = re.compile(r"supplement", re.I)

    def fetch_decisions(self, max_pages: int = 5) -> List[ProspectusDecision]:
        """Fetch all Program Prospectus decisions from CBA, across all pages."""
        all_decisions: List[ProspectusDecision] = []
        seen_ids: set = set()

        for page in range(1, max_pages + 1):
            items = self._fetch_page(page)
            if not items:
                break

            for item in items:
                if item.decision_id not in seen_ids:
                    seen_ids.add(item.decision_id)
                    all_decisions.append(item)

        return all_decisions

    def fetch_latest_decisions(self, known_ids: set) -> List[ProspectusDecision]:
        """Fetch only new decisions not in known_ids. Stops at first known page."""
        new_decisions: List[ProspectusDecision] = []

        for page in range(1, 10):
            items = self._fetch_page(page)
            if not items:
                break

            page_has_new = False
            for item in items:
                if item.decision_id not in known_ids:
                    new_decisions.append(item)
                    page_has_new = True

            # If entire page was already known, no point checking further
            if not page_has_new:
                break

        return new_decisions

    def _fetch_page(self, page: int) -> List[ProspectusDecision]:
        """Fetch and parse a single page of decisions."""
        try:
            resp = requests.get(
                self.DECISIONS_URL,
                params={"keyword": self.KEYWORD, "page": page},
                headers=self.HEADERS,
                timeout=self.TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"CBA fetch error (page {page}): {e}")
            return []

        return self._parse_page(resp.text)

    def _parse_page(self, html: str) -> List[ProspectusDecision]:
        """Parse decision items from HTML."""
        decisions: List[ProspectusDecision] = []

        for m in self._ITEM_RE.finditer(html):
            raw_url = m.group("url")
            url = raw_url if raw_url.startswith("http") else self.BASE_URL + raw_url

            title = self._clean_html(m.group("title"))
            preview = self._clean_html(m.group("preview") or "")
            company = self._extract_company(title)
            is_supplement = bool(self._SUPPLEMENT_RE.search(title))

            decisions.append(
                ProspectusDecision(
                    decision_id=m.group("id"),
                    date=m.group("date"),
                    title=title,
                    company_name=company,
                    url=url,
                    preview=preview[:300],
                    is_supplement=is_supplement,
                )
            )

        return decisions

    def _extract_company(self, title: str) -> str:
        """Extract company name from decision title."""
        for pattern in self._COMPANY_PATTERNS:
            m = pattern.search(title)
            if m:
                name = m.group(1).strip()
                # Clean up common suffixes already in the text
                name = re.sub(
                    r"\s*(CLOSED|OPEN)\s+JOINT[- ]STOCK\s+COMPANY.*$",
                    "",
                    name,
                    flags=re.I,
                ).strip()
                name = re.sub(r"\s*,?\s*(an?\s+)?(CJSC|OJSC|LLC|CJSC|JSC).*$", "", name, flags=re.I).strip()
                if name:
                    return name
        return "Unknown"

    @staticmethod
    def _clean_html(text: str) -> str:
        """Remove HTML tags and decode entities."""
        text = unescape(text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
