"""가이드 본문 사이의 TF-IDF 코사인 유사도. 외부 임베딩 모델은 쓰지 않는다."""

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from app.services.qa_engine import article_body


_TOKEN = re.compile(r"[a-z0-9]{2,}|[\uac00-\ud7a3]{2,}")
SIMILARITY_THRESHOLD = 0.95


@dataclass(frozen=True)
class SimilarityPair:
    source_key: str
    target_key: str
    similarity_score: float


def tokenize(text: str) -> List[str]:
    """본문에서 영문·숫자와 한글 어절을 뽑는다."""
    return _TOKEN.findall(article_body(text).lower())


def _tfidf(docs: Sequence[Sequence[str]]) -> List[Dict[str, float]]:
    document_count = len(docs)
    frequencies = [Counter(tokens) for tokens in docs]
    document_frequency: Counter = Counter()
    for frequency in frequencies:
        document_frequency.update(frequency.keys())
    vectors: List[Dict[str, float]] = []
    for frequency in frequencies:
        total = sum(frequency.values()) or 1
        vector: Dict[str, float] = {}
        for term, count in frequency.items():
            inverse = math.log((1.0 + document_count) / (1.0 + document_frequency[term])) + 1.0
            vector[term] = (count / float(total)) * inverse
        vectors.append(vector)
    return vectors


def cosine_similarity(left: Dict[str, float], right: Dict[str, float]) -> float:
    """두 TF-IDF 벡터의 코사인. 빈 벡터는 0이다."""
    if not left or not right:
        return 0.0
    dot = 0.0
    for term, weight in left.items():
        other = right.get(term)
        if other:
            dot += weight * other
    left_norm = math.sqrt(sum(weight * weight for weight in left.values()))
    right_norm = math.sqrt(sum(weight * weight for weight in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def pairwise_similarity(
    documents: Sequence[Tuple[str, str]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> List[SimilarityPair]:
    """키가 다른 문서 쌍 중 코사인이 threshold 이상인 것만 반환한다.

    source_key < target_key 로 한 방향만 남긴다.
    """
    usable = [(str(key), text) for key, text in documents if str(key)]
    vectors = _tfidf([tokenize(text) for _key, text in usable])
    found: List[SimilarityPair] = []
    for left_index, (left_key, _left_text) in enumerate(usable):
        for right_index in range(left_index + 1, len(usable)):
            right_key = usable[right_index][0]
            if left_key == right_key:
                continue
            score = cosine_similarity(vectors[left_index], vectors[right_index])
            if score < threshold:
                continue
            source, target = (left_key, right_key) if left_key < right_key else (right_key, left_key)
            found.append(
                SimilarityPair(
                    source_key=source,
                    target_key=target,
                    similarity_score=round(score, 6),
                )
            )
    found.sort(key=lambda item: (item.source_key, item.target_key))
    return found
