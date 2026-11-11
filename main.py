"""
Entry point: Topic-to-Video (phim tài liệu ngắn 9:16) — LangGraph pipeline.

    python main.py "Chiến dịch Điện Biên Phủ 1954"
    python main.py --mode HUMAN_NO_LIPSYNC "Một ngày của người thợ gốm Bát Tràng"

Chế độ Sách RAG & Đăng Hằng Ngày:
    python main.py --ingest NhaGiaKim_328a96be03.epub
    python main.py --list-book nha_gia_kim
    python main.py --book nha_gia_kim "Bí mật hạnh phúc qua hai giọt dầu"
    python main.py --book nha_gia_kim --chunk 14
    python main.py --book nha_gia_kim --daily

Chế độ (`--mode`): NO_HUMAN_BROLL (mặc định/tự suy ra) | HUMAN_NO_LIPSYNC | HUMAN_WITH_LIPSYNC (chưa có nhép môi).
Luồng: filter_context (RAG nếu có --book) -> intent_router -> prompt_architect (kịch bản + cảnh)
       -> prompt_scorer (kiểm tra cứng + LLM critic) -> media_generator -> visual_judge.
"""

import sys
import time
from typing import Any, Dict

from graph.book_rag import (
    get_chunk_by_idx,
    get_next_pending_chunk,
    ingest_book,
    list_book_chunks,
    mark_chunk_done,
)
from graph.workflow import create_christian_short_video_app


def _parse_args(argv) -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "mode": "",
        "ingest": "",
        "list_book": None,
        "book": "",
        "chunk": 0,
        "daily": False,
        "topic": "",
    }
    words = []
    it = iter(argv)
    for a in it:
        if a == "--mode":
            opts["mode"] = next(it, "").strip().upper()
        elif a == "--ingest":
            opts["ingest"] = next(it, "").strip()
        elif a == "--list-book":
            opts["list_book"] = next(it, "").strip()
        elif a == "--book":
            opts["book"] = next(it, "").strip()
        elif a == "--chunk":
            raw = next(it, "0").strip()
            opts["chunk"] = int(raw) if raw.isdigit() else 0
        elif a == "--daily":
            opts["daily"] = True
        else:
            words.append(a)
    opts["topic"] = " ".join(words).strip()
    return opts


def _print_book_queue(book_id: str) -> None:
    rows = list_book_chunks(book_id or None)
    if not rows:
        print(f"Chưa có dữ liệu sách nào trong Book RAG (book_id={book_id or 'latest'}).")
        return
    done_cnt = sum(1 for r in rows if r["status"] == "done")
    print("=" * 96)
    print(f"HÀNG ĐỢI SÁCH '{rows[0]['book_id']}': {len(rows)} chunks | đã đăng/render={done_cnt} | chờ={len(rows) - done_cnt}")
    print("=" * 96)
    for r in rows[:30]:
        mark = "DONE" if r["status"] == "done" else "WAIT"
        print(f" [{mark}] #{r['chunk_idx']:02d} ({r['word_count']:4d}w) | {r['section_title'][:28]:<28} | {r['topic_suggestion'][:55]}")
    if len(rows) > 30:
        print(f" ... và {len(rows) - 30} chunk nữa.")


def main():
    opts = _parse_args(sys.argv[1:])

    if opts["ingest"]:
        info = ingest_book(opts["ingest"])
        _print_book_queue(info["book_id"])
        print(f"\nGợi ý chạy ngay:\n  python main.py --book {info['book_id']} --daily")
        return

    if opts["list_book"] is not None:
        _print_book_queue(opts["list_book"])
        return

    book_id = opts["book"]
    chunk_idx = opts["chunk"]
    topic = opts["topic"]
    active_chunk = None

    if opts["daily"]:
        active_chunk = get_next_pending_chunk(book_id or None)
        if not active_chunk:
            print(f"[Book RAG] Toàn bộ chunk của sách '{book_id or 'hiện tại'}' đã hoàn thành!")
            return
        book_id = active_chunk["book_id"]
        chunk_idx = int(active_chunk["chunk_idx"])
        if not topic:
            topic = active_chunk["topic_suggestion"]
    elif book_id and chunk_idx > 0 and not topic:
        active_chunk = get_chunk_by_idx(book_id, chunk_idx)
        if active_chunk:
            topic = active_chunk["topic_suggestion"]

    if not topic:
        topic = "Chiến dịch Điện Biên Phủ 1954: 56 ngày đêm thay đổi cục diện"

    app = create_christian_short_video_app()
    config = {"configurable": {"thread_id": f"topic_to_video_{int(time.time())}"}}

    print("=" * 96)
    print(
        f"CHỦ ĐỀ: {topic}"
        + (f" | BOOK: {book_id}" if book_id else "")
        + (f" (chunk #{chunk_idx})" if chunk_idx else "")
        + (f" | MODE: {opts['mode']}" if opts["mode"] else "")
    )
    print("=" * 96)

    state = app.invoke(
        {
            "user_request": topic,
            "intent_mode": opts["mode"],
            "book_id": book_id,
            "book_chunk_idx": chunk_idx,
        },
        config=config,
    )

    if opts["daily"] and active_chunk:
        mark_chunk_done(int(active_chunk["chunk_id"]), state.get("final_master_video_path", ""))
        print(f"[Book RAG] Đã đánh dấu Chunk #{chunk_idx} là DONE trong hàng đợi hằng ngày.")

    scenes = state.get("scenes", [])
    v = state["visual_scores"]
    o = state["output_scores"]
    asset = state.get("asset_report", {})

    print("\n" + "=" * 96)
    print("BẢNG 1: KỊCH BẢN & CẢNH")
    print("=" * 96)
    print(f" • Tiêu đề   : {state['topic_title']}   | Thể loại: {state.get('genre')}   | Mode: {state.get('intent_mode')} -> {state.get('effective_intent_mode')}")
    print(f" • Phong cách: {state.get('style_anchor_en')}")
    for i, sc in enumerate(scenes, 1):
        print(f"   [{i}] ({sc.get('camera')}, {sc.get('media_source')}) {sc['narration_vn']}")
    print(f" • Cần kiểm chứng trước khi đăng: {state.get('claims_to_verify')}")

    print("\n" + "=" * 96)
    print("BẢNG 2: CHẤM ĐIỂM")
    print("=" * 96)
    print(f" • Kịch bản: {state['average_score']}/10 (Hook={state['theological_moral_score']}, Khớp hình-lời={state['cinematic_quality_score']}, Mạch kể={state['rag_faithfulness_score']}) | Pass={state['pass_validation']} | Lần thử: {state['retry']}")
    print(f" • Hình ảnh: tổng={v['visual_total_score']} | nét={v['sharpness_score']} | liên tục màu={v['continuity_score']} | cảnh thật={v.get('real_scene_ratio')} | lỗi={v['failure_reason']}")
    print(f" • Đầu ra  : tổng={o['output_total_score']} | lệch A/V={o['av_offset_frames']} frame | trạng thái={state['tiktok_publish_status']} | vấn đề={o['failure_reason']}")

    print("\n" + "=" * 96)
    print("BẢNG 3: FILE")
    print("=" * 96)
    print(f" • Video        : {state['final_master_video_path']}  ({state['audio_duration_sec']}s)")
    print(f" • Giọng + nhạc : {state['voiceover_wav_path']}")
    print(f" • Contact sheet: {asset.get('contact_sheet')}   (xem nhanh tất cả cảnh)")
    print(f" • Timeline     : {asset.get('timeline')}")
    print(f" • Caption      : {state.get('tiktok_caption')}")
    print("=" * 96)


if __name__ == "__main__":
    main()
