import re
from typing import Any, Dict, Optional

import numpy as np


MULTI_HOP_PATTERNS = [
    r"\band\b",
    r"\bor\b",
    r"\bcompare\b",
    r"\bbetween\b",
    r"\bsame\b",
    r"\bdifference\b",
    r"\brelationship\b",
    r"\bfirst\b.*\bthen\b",
    r"\bafter\b",
    r"\bbefore\b",
    r"\bwhy\b",
    r"\bhow\b",
    r"\bwhich\b.*\bmore\b",
]


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def cosine_sim(a: Any, b: Any) -> float:
    """Return cosine similarity for two vectors, falling back to 0.5 if invalid."""
    try:
        vec_a = np.asarray(a, dtype=np.float32)
        vec_b = np.asarray(b, dtype=np.float32)
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0 or norm_b == 0:
            return 0.5
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))
    except Exception:
        return 0.5


def estimate_query_complexity(query: str) -> float:
    """Estimate query complexity in [0, 1] with deterministic lexical rules."""
    if not query:
        return 0.0

    normalized_query = query.lower()
    words = re.findall(r"[A-Za-z0-9]+", query)

    length_score = min(len(words) / 40.0, 1.0) * 0.35

    matched_patterns = sum(
        1 for pattern in MULTI_HOP_PATTERNS if re.search(pattern, normalized_query)
    )
    multi_hop_score = min(matched_patterns / 4.0, 1.0) * 0.40

    capitalized_terms = re.findall(r"\b[A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*)*\b", query)
    ignored_entity_terms = {
        "i",
        "the",
        "a",
        "an",
        "what",
        "which",
        "who",
        "where",
        "when",
        "why",
        "how",
    }
    entity_like_terms = [
        term
        for term in capitalized_terms
        if term.lower() not in ignored_entity_terms
    ]
    entity_score = min(len(entity_like_terms) / 4.0, 1.0) * 0.25

    return _clip(length_score + multi_hop_score + entity_score, 0.0, 1.0)


def compute_adaptive_lambda(
    query: str,
    query_embedding: Optional[Any] = None,
    seed_embedding: Optional[Any] = None,
    lambda_0: float = 0.55,
    beta: float = 0.10,
    gamma: float = 0.08,
    lambda_min: float = 0.35,
    lambda_max: float = 0.75,
) -> Dict[str, float]:
    complexity = estimate_query_complexity(query)
    sim_q_seed = 0.5
    if query_embedding is not None and seed_embedding is not None:
        sim_q_seed = cosine_sim(query_embedding, seed_embedding)

    lambda_q = lambda_0 + beta * sim_q_seed - gamma * complexity
    lambda_q = _clip(lambda_q, lambda_min, lambda_max)

    return {
        "lambda": lambda_q,
        "complexity": complexity,
        "sim": sim_q_seed,
    }
