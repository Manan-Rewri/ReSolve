import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.schemas.leetcode import LeetCodeQuestionData
from app.services import leetcode_client
from app.utils.text import html_to_text, to_problem_slug

URL_IN_TEXT_PATTERN = re.compile(r"https?://[^\s]+")
DEFAULT_DIFFICULTY = "Medium"
DEFAULT_TOPIC = "Algorithms"
EMPTY_STATEMENT = "<p>No description available.</p>"


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
        self, search_term: str, limit: int = 8
    ) -> List[Dict[str, Any]]:
        """Returns [] instead of raising so the search bar degrades when LeetCode is down."""
        query = (search_term or "").strip()
        if not query:
            return []

        rows = await leetcode_client.search_question_suggestions(query, limit)
        return [_to_suggestion(row) for row in rows]


leetcode_service = LeetCodeService()