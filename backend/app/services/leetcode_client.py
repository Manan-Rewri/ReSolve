import re
from typing import Any, Dict, List, Optional

import httpx

GRAPHQL_URL = "https://leetcode.com/graphql"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Origin": "https://leetcode.com",
}

QUESTION_DATA_QUERY = """
query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    titleSlug
    content
    difficulty
    topicTags { name }
    hints
    sampleTestCase
    codeSnippets {
      langSlug
      code
    }
  }
}
"""

_QUESTIONS_SELECTION = """
  total: totalNum
  questions: data {
    questionFrontendId
    title
    titleSlug
    difficulty
    topicTags { name }
  }
"""

SEARCH_QUERY = """
query problemsetQuestionList($filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: ""
    limit: 5
    skip: 0
    filters: $filters
  ) {%s
  }
}
""" % _QUESTIONS_SELECTION

SUGGEST_QUERY = """
query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
  problemsetQuestionList: questionList(
    categorySlug: $categorySlug
    limit: $limit
    skip: $skip
    filters: $filters
  ) {%s
  }
}
""" % _QUESTIONS_SELECTION

STOP_WORDS = frozenset(
    {
        "problem", "leetcode", "the", "a", "an", "in", "of",
        "to", "for", "and", "or", "on", "with", "by", "is",
    }
)

MATCH_THRESHOLD = 0.4
WORD_PATTERN = re.compile(r"[a-zA-Z0-9]+")

PROBLEMSET_REFERER = "https://leetcode.com/problemset/all/"


def problem_referer(slug: str) -> str:
    return f"https://leetcode.com/problems/{slug}/"


async def _post_graphql(
    query: str,
    variables: Dict[str, Any],
    referer: str,
    timeout: float,
) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers={**HEADERS, "Referer": referer},
            )
        if response.status_code != 200:
            return None
        return response.json()
    except (httpx.HTTPError, ValueError):
        return None


def _question_list(payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not payload:
        return []
    problemset = payload.get("data", {}).get("problemsetQuestionList") or {}
    return problemset.get("questions") or []


async def fetch_question_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    payload = await _post_graphql(
        QUESTION_DATA_QUERY,
        {"titleSlug": slug},
        problem_referer(slug),
        timeout=12.0,
    )
    if not payload:
        return None
    return payload.get("data", {}).get("question")


async def search_question_slug(search_term: str) -> Optional[str]:
    payload = await _post_graphql(
        SEARCH_QUERY,
        {"filters": {"searchKeywords": search_term}},
        PROBLEMSET_REFERER,
        timeout=12.0,
    )
    candidates = _question_list(payload)
    if not candidates:
        return None

    words = [w for w in WORD_PATTERN.findall(search_term.lower()) if w not in STOP_WORDS]
    if not words:
        return candidates[0].get("titleSlug")

    for candidate in candidates:
        target = f"{candidate.get('title', '')} {candidate.get('titleSlug', '')}".lower()
        matched = sum(1 for word in words if word in target)
        if matched / len(words) >= MATCH_THRESHOLD:
            return candidate.get("titleSlug")

    return None


async def search_question_suggestions(search_term: str, limit: int) -> List[Dict[str, Any]]:
    payload = await _post_graphql(
        SUGGEST_QUERY,
        {
            "categorySlug": "",
            "limit": limit,
            "skip": 0,
            "filters": {"searchKeywords": search_term},
        },
        PROBLEMSET_REFERER,
        timeout=10.0,
    )
    return _question_list(payload)