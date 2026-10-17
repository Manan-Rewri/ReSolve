import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.schemas.leetcode import LeetCodeExample, LeetCodeQuestionData
from app.services import leetcode_client
from app.services.sheets import get_slugs
from app.utils.text import html_to_text, to_problem_slug

URL_IN_TEXT_PATTERN = re.compile(r"https?://[^\s]+")
DEFAULT_DIFFICULTY = "Medium"
DEFAULT_TOPIC = "Algorithms"
EMPTY_STATEMENT = "<p>No description available.</p>"

# ReSolve is for DSA practice, so database-engineering and data-analysis
# problems are filtered out of autocomplete. Every genuine DSA problem carries
# at least one topic tag; the untagged ones are LeetCode's SQL / pandas tracks.
EXCLUDED_TOPICS = frozenset({"database", "pandas"})
EXCLUDED_TITLE_KEYWORDS = (
    "sql",
    "database",
    "mysql",
    "postgres",
    "nosql",
    "redis",
    "query builder",
)


EXAMPLE_PATTERN = re.compile(
    r"<\s*strong\s*>\s*Input\s*:\s*<\s*/\s*strong\s*>(.*?)"
    r"<\s*strong\s*>\s*Output\s*:\s*<\s*/\s*strong\s*>(.*?)"
    r"(?=<\s*strong|</\s*pre|$)",
    re.IGNORECASE | re.DOTALL,
)

MAX_EXAMPLES = 5


def _one_line(text: str) -> str:
    return " ".join(html_to_text(text).split())


def extract_examples(content_html: str) -> List[Dict[str, str]]:
    """Reads the Input/Output examples out of a LeetCode statement.

    Examples live inside <pre> blocks as
      <strong>Input:</strong> ... <strong>Output:</strong> ...
    Returns at most MAX_EXAMPLES pairs, and [] when the statement does not
    follow that shape (graphical output, prose-only examples, and so on).
    """
    if not content_html:
        return []

    examples = []
    for match in EXAMPLE_PATTERN.finditer(content_html):
        example_input = _one_line(match.group(1))
        if not example_input:
            continue
        examples.append({"input": example_input, "output": _one_line(match.group(2))})
        if len(examples) >= MAX_EXAMPLES:
            break
    return examples


def extract_expected_output(content_html: str) -> Optional[str]:
    """Example 1's expected output, used to judge a submitted answer."""
    examples = extract_examples(content_html)
    return examples[0]["output"] if examples and examples[0]["output"] else None


def _is_dsa_problem(title: str, tags: List[str]) -> bool:
    if not tags:
        return False
    if any(tag.strip().lower() in EXCLUDED_TOPICS for tag in tags):
        return False
    lowered = title.lower()
    return not any(keyword in lowered for keyword in EXCLUDED_TITLE_KEYWORDS)


def _to_question_data(
    question: Dict[str, Any], slug: str, fallback_title: str
) -> LeetCodeQuestionData:
    topics = [tag["name"] for tag in question.get("topicTags") or [] if "name" in tag]
    content_html = question.get("content") or EMPTY_STATEMENT
    resolved_slug = question.get("titleSlug") or slug

    return LeetCodeQuestionData(
        frontend_id=str(question.get("questionFrontendId") or ""),
        title=question.get("title") or fallback_title,
        title_slug=resolved_slug,
        url=f"https://leetcode.com/problems/{resolved_slug}/",
        difficulty=question.get("difficulty") or DEFAULT_DIFFICULTY,
        topic=topics[0] if topics else DEFAULT_TOPIC,
        all_topics=topics,
        content_html=content_html,
        content_text=html_to_text(content_html),
        hints=question.get("hints") or [],
        sample_test_case=question.get("sampleTestCase"),
        sample_expected_output=extract_expected_output(content_html),
        examples=[LeetCodeExample(**example) for example in extract_examples(content_html)],
    )


def _to_suggestion(row: Dict[str, Any]) -> Dict[str, Any]:
    tags = row.get("topicTags") or []
    return {
        "frontend_id": str(row.get("questionFrontendId") or ""),
        "title": row.get("title") or "",
        "title_slug": row.get("titleSlug") or "",
        "difficulty": row.get("difficulty") or DEFAULT_DIFFICULTY,
        "topic": tags[0].get("name") if tags else None,
    }


class LeetCodeService:
    async def fetch_problem(self, title_or_url: str) -> LeetCodeQuestionData:
        cleaned_input = title_or_url.strip()
        if not cleaned_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please enter a valid LeetCode problem title or URL.",
            )

        slug = to_problem_slug(cleaned_input)
        question: Optional[Dict[str, Any]] = (
            await leetcode_client.fetch_question_by_slug(slug) if slug else None
        )

        if not question:
            search_term = URL_IN_TEXT_PATTERN.sub("", cleaned_input).strip() or cleaned_input
            fallback_slug = await leetcode_client.search_question_slug(search_term)
            if fallback_slug:
                slug = fallback_slug
                question = await leetcode_client.fetch_question_by_slug(fallback_slug)

        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Could not find LeetCode problem matching '{cleaned_input}'. "
                    "Please verify the title spelling or paste the full LeetCode URL."
                ),
            )

        return _to_question_data(question, slug, cleaned_input)

    async def search_suggestions(
        self, search_term: str, limit: int = 8, sheet_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns [] instead of raising so the search bar degrades when LeetCode is down.

        `sheet_id` restricts results to that practice sheet. An unknown id or
        None searches everything.
        """
        query = (search_term or "").strip()
        if not query:
            return []

        allowed_slugs = get_slugs(sheet_id)

        # Over-fetch, because filtering can discard some rows.
        rows = await leetcode_client.search_question_suggestions(query, limit * 3)
        kept = [
            row
            for row in rows
            if _is_dsa_problem(
                row.get("title") or "",
                [tag["name"] for tag in row.get("topicTags") or [] if "name" in tag],
            )
        ]
        suggestions = [_to_suggestion(row) for row in kept]

        if allowed_slugs is not None:
            suggestions = [s for s in suggestions if s["title_slug"] in allowed_slugs]

        return suggestions[:limit]


leetcode_service = LeetCodeService()