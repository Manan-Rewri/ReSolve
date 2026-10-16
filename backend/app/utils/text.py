import html
import re

URL_SLUG_PATTERN = re.compile(r"leetcode\.com/problems/([^/?#]+)", re.IGNORECASE)
LEADING_NUMBER_PATTERN = re.compile(r"^\d+[\.\-\:\s]\s*")
NON_SLUG_CHARS_PATTERN = re.compile(r"[^a-zA-Z0-9\s-]")
SEPARATORS_PATTERN = re.compile(r"[\s_]+")


def to_problem_slug(title_or_url: str) -> str:
    url_match = URL_SLUG_PATTERN.search(title_or_url)
    if url_match:
        return url_match.group(1).lower().strip()

    cleaned = LEADING_NUMBER_PATTERN.sub("", title_or_url)
    cleaned = NON_SLUG_CHARS_PATTERN.sub("", cleaned)
    return SEPARATORS_PATTERN.sub("-", cleaned).strip("-").lower()


def html_to_text(html_content: str) -> str:
    if not html_content:
        return ""

    text = re.sub(r"<br\s*/?>", "\n", html_content, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()