"""
NODE 1: `filter_context_node` (Python thuần - 0 Token)
Chuẩn bị ngữ cảnh nhân vật (nếu có) và khởi tạo trạng thái cho Chủ đề (`user_request`).
"""

import re
from typing import Dict, List, Any
from graph.state import ChristianVideoState
from graph.book_rag import format_chunks_for_prompt, get_chunk_by_idx, retrieve_chunks


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

    filtered_context_str = "\n   ".join(matched_traits) if matched_traits else "Video giải thích trực quan (Không cố định nhân vật)."

    book_id = str(state.get("book_id", "") or "").strip()
    book_chunk_idx = int(state.get("book_chunk_idx", 0) or 0)
    retrieved_text = str(state.get("retrieved_scripture", "") or "").strip()
    resolved_chunk_id = int(state.get("book_chunk_id", 0) or 0)

    if not retrieved_text and book_id:
        if book_chunk_idx > 0:
            ch = get_chunk_by_idx(book_id, book_chunk_idx)
            if ch:
                resolved_chunk_id = int(ch["chunk_id"])
                retrieved_text = format_chunks_for_prompt(ch.get("book_title", book_id), [ch])
                print(
                    f"[Node 1: Book RAG] Lấy Chunk #{ch['chunk_idx']} ({ch['section_title']}, {ch['word_count']} từ) từ '{book_id}'"
                )
        else:
            ctx, matched = retrieve_chunks(user_req, book_id=book_id, top_k=2)
            if ctx and matched:
                retrieved_text = ctx
                resolved_chunk_id = int(matched[0]["chunk_id"])
                idxs = ", ".join(f"#{m['chunk_idx']} ({m['section_title']})" for m in matched)
                print(f"[Node 1: Book RAG] Truy xuất {len(matched)} chunk từ '{book_id}': {idxs}")

    print(
        f"[Node 1: filter_context_node] Topic: '{user_req}' | Nhân vật kế thừa: {len(matched_traits)}"
        + (f" | RAG={len(retrieved_text.split())} từ" if retrieved_text else "")
    )

    return {
        "detected_characters": detected_chars,
        "filtered_character_context": filtered_context_str,
        "known_reference_urls": matched_ref_urls,
        "retrieved_scripture": retrieved_text,
        "book_chunk_id": resolved_chunk_id,
        "retry": 0,
        "prompt_feedback": "",
    }
