"""제보 문장을 영어 또는 한국어로 옮기는 LLM 에이전트.

서비스의 표준 문서 작성은 이 모듈 없이 끝난다.
MAGAZINE_TRANSLATE_LLM=1 일 때만 호출된다.
"""

import asyncio

from app.agents.utils import generate_with_fallback


def translate_text(text: str, target: str) -> str:
    language = "English" if target == "en" else "Korean"
    prompt = (
        "Translate the travel note into {0}. "
        "Keep place names. Return only the translation.\n\n{1}"
    ).format(language, text)
    translated, _model = asyncio.run(
        generate_with_fallback(
            prompt,
            "You translate travel notes. Output plain text in the requested language only.",
        )
    )
    return str(translated or "").strip()
