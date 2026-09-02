"""Merge and deduplicate vector + graph retrieval hits."""

from __future__ import annotations

from services.retrieval.models import RetrievalHit


def merge_hits(
    vector_hits: list[RetrievalHit],
    graph_hits: list[RetrievalHit],
    *,
    vector_weight: float = 0.55,
    graph_weight: float = 0.45,
) -> list[RetrievalHit]:
    """Combine hits, boosting items found by both retrievers."""
    combined: dict[str, RetrievalHit] = {}

    for hit in vector_hits:
        key = _dedupe_key(hit)
        weighted = _copy_hit(hit, hit.score * vector_weight)
        combined[key] = weighted

    for hit in graph_hits:
        key = _dedupe_key(hit)
        weighted = _copy_hit(hit, hit.score * graph_weight)
        if key in combined:
            existing = combined[key]
            existing.score = min(1.0, existing.score + weighted.score + 0.15)
            existing.source = "hybrid"
            if len(weighted.content) > len(existing.content):
                existing.content = weighted.content
            if not existing.graph_relationship and weighted.graph_relationship:
                existing.graph_relationship = weighted.graph_relationship
        else:
            combined[key] = weighted

    merged = sorted(combined.values(), key=lambda h: h.score, reverse=True)
    return merged


def _dedupe_key(hit: RetrievalHit) -> str:
    symbol = hit.symbol or hit.function_name or hit.class_name or hit.hit_id
    return f"{hit.file_path}::{symbol}::{hit.start_line}"


def _copy_hit(hit: RetrievalHit, score: float) -> RetrievalHit:
    return RetrievalHit(
        hit_id=hit.hit_id,
        source=hit.source,
        file_path=hit.file_path,
        content=hit.content,
        score=score,
        function_name=hit.function_name,
        class_name=hit.class_name,
        symbol=hit.symbol,
        start_line=hit.start_line,
        end_line=hit.end_line,
        chunk_type=hit.chunk_type,
        graph_relationship=hit.graph_relationship,
    )
