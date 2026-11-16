"""
NODE 1: `filter_context_node` — Chuẩn bị ngữ cảnh nhân vật + Book RAG Hybrid Search & QueryRewriter.
"""

import re
from typing import Any, Dict, List, Optional

from graph.book_rag import format_chunks_for_prompt, get_chunk_by_idx, retrieve_chunks, list_all_book_ids
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

# ─── Schema xác định sách từ topic ─────────────────────────────────────────
_BOOK_RESOLVER_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "resolved_book_id": {"type": "STRING"},  # book_id tìm thấy, hoặc "" nếu không rõ
        "confidence": {"type": "STRING"},         # "high" | "medium" | "low"
        "reasoning": {"type": "STRING"},
        "needs_clarification": {"type": "BOOLEAN"},
        "clarification_question": {"type": "STRING"},
    },
    "required": ["resolved_book_id", "confidence", "needs_clarification", "clarification_question"],
}


def _resolve_book_from_topic(topic: str, available_book_ids: List[str]) -> Dict[str, Any]:
    """
    Phân tích topic/user_request để xác định sách nào trong DB nên được dùng.

    Logic:
    - Nếu topic đề cập tên sách/tác giả rõ ràng → tìm book_id tương ứng (high confidence).
    - Nếu topic chung chung (không nhắc tên sách) → trả needs_clarification=True để hỏi người dùng.
    - Nếu topic hỏi "chương X" mà không nêu tên sách → needs_clarification=True.
    - Nếu DB chỉ có 1 sách → tự động dùng sách đó (medium confidence).
    - Nếu không nhắc sách nào và DB có nhiều sách → needs_clarification=True.
    """
    if not available_book_ids:
        return {
            "resolved_book_id": "",
            "confidence": "low",
            "reasoning": "Không có sách nào trong DB.",
            "needs_clarification": False,
            "clarification_question": "",
        }

    books_list = ", ".join(f'"{b}"' for b in available_book_ids)
    prompt = (
        f"Yêu cầu người dùng: \"{topic}\"\n"
        f"Danh sách book_id có trong database: [{books_list}]\n\n"
        "Nhiệm vụ: Xác định xem yêu cầu trên có đang gọi một cuốn sách hay chương sách cụ thể nào trong database không.\n"
        "Quy tắc:\n"
        "1. Nếu người dùng chỉ nói chung chung 'chương abc' hay 'chương X', 'đoạn X' mà KHÔNG nói rõ sách nào: BẮT BUỘC đặt `needs_clarification` = true, `resolved_book_id` = '', `clarification_question` = câu hỏi xác nhận lại xem họ muốn lấy chương đó từ cuốn sách nào trong số các sách hiện có.\n"
        "2. Nếu người dùng nói rõ tên sách hoặc chi tiết/nhân vật đặc trưng gắn liền với 1 cuốn sách trong database: trả `resolved_book_id` = book_id tương ứng, `confidence` = 'high', `needs_clarification` = false.\n"
        "3. Nếu yêu cầu là một chủ đề tự do hoàn toàn (lịch sử, khoa học, đời sống...) và KHÔNG yêu cầu sách nào: trả `resolved_book_id` = '', `confidence` = 'low', `needs_clarification` = false (hệ thống sẽ xử lý bằng keywords, không kéo RAG sách vào).\n"
        "4. Nếu yêu cầu nhắc tới một cuốn sách KHÔNG có trong database: `needs_clarification` = true, giải thích rõ sách đó chưa có trong database và gợi ý các sách đang có.\n"
        "Trả về JSON theo schema đã cho."
    )
    result = call_gemini_thinking_structured(
        prompt=prompt,
        response_schema=_BOOK_RESOLVER_SCHEMA,
        system_instruction=(
            "Bạn là hệ thống xác định nguồn tư liệu sách cho pipeline tạo video. "
            "Chỉ trả về JSON theo schema, không giải thích thêm."
        ),
    )
    return result or {
        "resolved_book_id": "",
        "confidence": "low",
        "reasoning": "Không xác định được.",
        "needs_clarification": True,
        "clarification_question": f"Bạn muốn làm video về sách nào? Có các sách: {books_list}",
    }


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

    # ── Tự động xác nhận sách khi book_id chưa được chỉ rõ ──────────────────
    book_id = str(state.get("book_id", "") or "").strip()
    book_chunk_idx = int(state.get("book_chunk_idx", 0) or 0)
    is_rag_retry = state.get("retry_target") == "retry_rag"

    if not book_id and not book_chunk_idx and not is_rag_retry:
        # Lấy danh sách tất cả sách trong DB
        try:
            available_books = list_all_book_ids()
        except Exception:
            available_books = []

        if available_books:
            resolver = _resolve_book_from_topic(user_req, available_books)
            resolved_id = str(resolver.get("resolved_book_id", "") or "").strip()
            needs_clarify = bool(resolver.get("needs_clarification", False))

            if needs_clarify:
                # Trả về trạng thái yêu cầu xác nhận — pipeline sẽ dừng ở đây để hỏi người dùng
                clarification_q = resolver.get("clarification_question", "")
                print(
                    f"[Node 1: Book Resolver] Topic '{user_req}' không rõ sách → "
                    f"Cần xác nhận: {clarification_q}"
                )
                return {
                    "retrieved_scripture": "",
                    "book_chunk_id": 0,
                    "rag_relevance_score": 0.0,
                    "rag_retry_count": 0,
                    "rag_tried_chunk_ids": [],
                    "rag_search_query": user_req,
                    "retry_target": "",
                    "retry": 0,
                    "prompt_feedback": "",
                    "filtered_character_context": "Video giải thích trực quan (Không cố định nhân vật).",
                    "detected_characters": [],
                    "known_reference_urls": [],
                    # Signal cho workflow dừng lại hỏi người dùng
                    "needs_book_clarification": True,
                    "clarification_question": clarification_q,
                    "book_id": "",
                }
            elif resolved_id:
                # Đã xác định được sách → gán book_id tự động
                print(
                    f"[Node 1: Book Resolver] Topic '{user_req}' → "
                    f"Tự động dùng sách '{resolved_id}' "
                    f"(confidence={resolver.get('confidence', '?')})"
                )
                book_id = resolved_id

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

    # book_id đã được resolved hoặc lấy từ state ở trên
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
        "book_id": book_id,
        "book_chunk_id": resolved_chunk_id,
        "rag_relevance_score": s_rag,
        "rag_retry_count": rag_retry_count,
        "rag_tried_chunk_ids": tried_ids,
        "rag_search_query": search_query,
        "retry_target": "",
        "retry": int(state.get("retry", 0) or 0) if is_rag_retry else 0,
        "prompt_feedback": "" if not is_rag_retry else "",
        "needs_book_clarification": False,
        "clarification_question": "",
    }
