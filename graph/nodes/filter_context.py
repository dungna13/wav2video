"""
NODE 1: `filter_context_node` — Chuẩn bị ngữ cảnh nhân vật + Book RAG Hybrid Search & QueryRewriter.
"""

import re
from typing import Any, Dict, List

from graph.book_rag import format_chunks_for_prompt, get_chunk_by_idx, retrieve_chunks
from graph.llm_client import call_gemini_thinking_structured
from graph.state import ChristianVideoState

_QUERY_EXPAND_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "expanded_keywords_vn": {"type": "STRING"},
    },
    "required": ["expanded_keywords_vn"],
}

_RAG_CONFIDENCE_THRESHOLD = 0.78


def _rewrite_rag_query(topic: str, book_id: str, feedback: str = "", prev_query: str = "") -> str:
    """Mở rộng từ khóa khi topic ngắn/trừu tượng hoặc cần truy xuất lại đoạn sách khác (QueryRewriter)."""
    prompt = (
        f"Sách (book_id): {book_id}\n"
        f"Chủ đề video: \"{topic}\"\n"
        f"Truy vấn trước: \"{prev_query or topic}\"\n"
        f"Lý do tìm lại (nếu có): \"{feedback or 'Chủ đề ngắn/ẩn dụ, cần mở rộng từ khóa cụ thể trong sách'}\"\n\n"
        "Hãy liệt kê 6-10 từ khóa tiếng Việt CỤ THỂ (tên nhân vật, sự kiện, đồ vật, địa điểm, tình tiết có thể xuất hiện trong sách) "
        "để tìm đúng đoạn truyện phù hợp nhất với chủ đề trên. Chỉ trả về JSON có key `expanded_keywords_vn`."
    )
    res = call_gemini_thinking_structured(
        prompt=prompt,
        response_schema=_QUERY_EXPAND_SCHEMA,
        system_instruction="Bạn là chuyên gia mở rộng truy vấn tìm kiếm sách tiếng Việt. Trả về JSON ngắn gọn.",
    )
    expanded = str((res or {}).get("expanded_keywords_vn", "")).strip()
    if expanded:
        return f"{topic} {expanded}"
    return topic


def filter_context_node(state: ChristianVideoState) -> Dict[str, Any]:
    user_req = state.get("user_request", "").strip()
    user_req_lower = user_req.lower()
    existing_registry = state.get("characters", {}) or {}

    detected_chars: List[str] = []
    matched_traits: List[str] = []
    matched_ref_urls: List[str] = []

    for char_key, profile in existing_registry.items():
        saved_aliases = profile.get("aliases", [])
        all_patterns = [re.escape(char_key)] + [re.escape(a.lower()) for a in saved_aliases]
        if any(re.search(rf"(?<!\w){pat}(?!\w)", user_req_lower) for pat in all_patterns):
            detected_chars.append(char_key)
            matched_traits.append(f"- {char_key}: {profile['visual_traits']}")
            if profile.get("reference_image_url"):
                matched_ref_urls.append(profile["reference_image_url"])

    filtered_context_str = (
        "\n   ".join(matched_traits) if matched_traits else "Video giải thích trực quan (Không cố định nhân vật)."
    )

    book_id = str(state.get("book_id", "") or "").strip()
    book_chunk_idx = int(state.get("book_chunk_idx", 0) or 0)
    is_rag_retry = state.get("retry_target") == "retry_rag"
    rag_retry_count = int(state.get("rag_retry_count", 0) or 0)
    tried_ids: List[int] = list(state.get("rag_tried_chunk_ids") or [])

    retrieved_text = "" if is_rag_retry else str(state.get("retrieved_scripture", "") or "").strip()
    resolved_chunk_id = int(state.get("book_chunk_id", 0) or 0)
    s_rag = float(state.get("rag_relevance_score", 0.0) or 0.0)
    search_query = str(state.get("rag_search_query") or user_req)

    if not retrieved_text and book_id:
        if book_chunk_idx > 0 and not is_rag_retry:
            ch = get_chunk_by_idx(book_id, book_chunk_idx)
            if ch:
                resolved_chunk_id = int(ch["chunk_id"])
                s_rag = 1.0
                tried_ids.append(resolved_chunk_id)
                retrieved_text = format_chunks_for_prompt(ch.get("book_title", book_id), [ch])
                print(
                    f"[Node 1: Book RAG] Lấy Chunk #{ch['chunk_idx']} ({ch['section_title']}, {ch['word_count']} từ) từ '{book_id}'"
                )
        else:
            if is_rag_retry:
                rag_retry_count += 1
                search_query = _rewrite_rag_query(
                    user_req,
                    book_id,
                    feedback=str(state.get("prompt_feedback", "")),
                    prev_query=search_query,
                )
                print(f"[Node 1: QueryRewriter #{rag_retry_count}] Mở rộng từ khóa -> '{search_query[:120]}'")

            ctx, matched = retrieve_chunks(
                search_query,
                book_id=book_id,
                top_k=2,
                exclude_chunk_ids=tried_ids if is_rag_retry else None,
            )

            # Nếu lần đầu gặp topic quá ngắn/khó tìm và S_rag thấp -> QueryRewriter tự mở rộng 1 lần ngay
            if not is_rag_retry and matched and float(matched[0].get("s_rag", 0.0)) < _RAG_CONFIDENCE_THRESHOLD:
                first_s = float(matched[0].get("s_rag", 0.0))
                expanded_q = _rewrite_rag_query(user_req, book_id)
                if expanded_q != search_query:
                    ctx2, matched2 = retrieve_chunks(expanded_q, book_id=book_id, top_k=2)
                    if matched2 and float(matched2[0].get("s_rag", 0.0)) >= first_s:
                        ctx, matched = ctx2, matched2
                        search_query = expanded_q
                        print(f"[Node 1: QueryRewriter] S_rag={first_s:.2f} < {_RAG_CONFIDENCE_THRESHOLD} -> Tự mở rộng '{expanded_q[:100]}'")

            if ctx and matched:
                retrieved_text = ctx
                resolved_chunk_id = int(matched[0]["chunk_id"])
                s_rag = float(matched[0].get("s_rag", 0.0))
                for m in matched:
                    cid = int(m["chunk_id"])
                    if cid not in tried_ids:
                        tried_ids.append(cid)
                idxs = ", ".join(f"#{m['chunk_idx']} ({m['section_title']}, S_rag={m.get('s_rag', 0):.2f})" for m in matched)
                print(f"[Node 1: Book RAG Hybrid] Truy xuất {len(matched)} chunk từ '{book_id}': {idxs}")

    print(
        f"[Node 1: filter_context_node] Topic: '{user_req}' | Nhân vật kế thừa: {len(matched_traits)}"
        + (f" | RAG={len(retrieved_text.split())} từ (S_rag={s_rag:.2f})" if retrieved_text else "")
    )

    return {
        "detected_characters": detected_chars,
        "filtered_character_context": filtered_context_str,
        "known_reference_urls": matched_ref_urls,
        "retrieved_scripture": retrieved_text,
        "book_chunk_id": resolved_chunk_id,
        "rag_relevance_score": s_rag,
        "rag_retry_count": rag_retry_count,
        "rag_tried_chunk_ids": tried_ids,
        "rag_search_query": search_query,
        "retry_target": "",
        "retry": int(state.get("retry", 0) or 0) if is_rag_retry else 0,
        "prompt_feedback": "" if not is_rag_retry else "",
    }
