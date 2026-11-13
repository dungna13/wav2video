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
    python main.py --mine nha_gia_kim --chunk 14 # khai thác 3-5 góc kể sắc nét từ 1 chunk sách
    python main.py --model myth_vs_reality "Bí ẩn văn minh Maya"
    python main.py --logs                      # xem checkpoint & error log gần nhất

Chế độ (`--mode`): NO_HUMAN_BROLL (mặc định/tự suy ra) | HUMAN_NO_LIPSYNC | HUMAN_WITH_LIPSYNC (chưa có nhép môi).
Luồng: filter_context (RAG nếu có --book) -> intent_router -> prompt_architect (kịch bản + cảnh)
       -> prompt_scorer (kiểm tra cứng + LLM critic) -> media_generator -> visual_judge.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict

from graph.book_rag import (
    get_chunk_by_idx,
    get_next_pending_chunk,
    ingest_book,
    list_book_chunks,
    mark_chunk_done,
)
from graph.flow_bundler import prepare_flow_workspace, render_from_flow_clips
from graph.hitl_cli import run_hitl_cli
from graph.web_app import start_server
from graph.llm_client import ANGLE_MINER_GEMINI_SCHEMA, call_gemini_thinking_structured
from graph.run_logger import print_diagnostics, start_run_log
from graph.workflow import create_christian_short_video_app
from prompts.angle_miner_prompt import render_angle_miner_prompt


def _parse_args(argv) -> Dict[str, Any]:
    opts: Dict[str, Any] = {
        "mode": "",
        "model": "auto",
        "ingest": "",
        "list_book": None,
        "mine": "",
        "book": "",
        "chunk": 0,
        "daily": False,
        "logs": False,
        "flow_prep": False,
        "flow_render": "",
        "hitl": "",
        "ui": False,
        "port": 8000,
        "clips_dir": "",
        "sub_mode": "narration_full",
        "block_sec": 14.0,
        "max_blocks": 4,
        "topic": "",
    }
    words = []
    it = iter(argv)
    for a in it:
        if a == "--mode":
            opts["mode"] = next(it, "").strip().upper()
        elif a == "--model":
            opts["model"] = next(it, "auto").strip().lower()
        elif a == "--ingest":
            opts["ingest"] = next(it, "").strip()
        elif a == "--list-book":
            opts["list_book"] = next(it, "").strip()
        elif a == "--mine":
            opts["mine"] = next(it, "").strip()
        elif a == "--book":
            opts["book"] = next(it, "").strip()
        elif a == "--chunk":
            raw = next(it, "0").strip()
            opts["chunk"] = int(raw) if raw.isdigit() else 0
        elif a == "--daily":
            opts["daily"] = True
        elif a == "--logs":
            opts["logs"] = True
        elif a == "--flow-prep":
            opts["flow_prep"] = True
        elif a == "--flow-render":
            opts["flow_render"] = next(it, "").strip()
        elif a in ("--hitl", "--review"):
            opts["hitl"] = next(it, "").strip()
        elif a in ("--ui", "--web"):
            opts["ui"] = True
        elif a == "--port":
            p = next(it, "8000").strip()
            opts["port"] = int(p) if p.isdigit() else 8000
        elif a == "--clips-dir":
            opts["clips_dir"] = next(it, "").strip()
        elif a == "--sub-mode":
            opts["sub_mode"] = next(it, "narration_full").strip().lower()
        elif a == "--no-sub":
            opts["sub_mode"] = "none"
        elif a == "--block-sec":
            raw = next(it, "14").strip()
            try:
                opts["block_sec"] = max(4.0, float(raw))
            except ValueError:
                opts["block_sec"] = 14.0
        elif a == "--blocks":
            raw = next(it, "4").strip()
            opts["max_blocks"] = max(1, int(raw)) if raw.isdigit() else 4
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

    if opts["logs"]:
        print_diagnostics()
        return

    if opts["ui"]:
        start_server(port=opts["port"])
        return

    if opts["hitl"]:
        run_hitl_cli(opts["hitl"], sub_mode=opts["sub_mode"])
        return

    if opts["flow_render"]:
        res = render_from_flow_clips(
            run_dir=Path(opts["flow_render"]),
            clips_dir=Path(opts["clips_dir"]) if opts["clips_dir"] else None,
            sub_mode=opts["sub_mode"],
        )
        m = res["manifest"]
        r = res["rendered"]
        v = res["visual_scores"]
        o = res["output_scores"]
        print("\n" + "=" * 96)
        print(f"FLOW RENDER HOÀN TẤT: {m['topic_title']}")
        print("=" * 96)
        print(f" • Video        : {r['final_master_video_path']} ({m['audio_duration_sec']}s)")
        print(f" • Hình ảnh     : tổng={v['visual_total_score']} | nét={v['sharpness_score']} | liên tục màu={v['continuity_score']}")
        print(f" • Đầu ra       : tổng={o['output_total_score']} | lệch A/V={o['av_offset_frames']} frame | {res['tiktok_publish_status']}")
        print(f" • Caption      : {res['tiktok_caption']}")
        print("=" * 96)
        return

    if opts["mine"]:
        ch = get_chunk_by_idx(opts["mine"], opts["chunk"] or 1)
        if not ch:
            print(f"Không tìm thấy chunk #{opts['chunk'] or 1} của sách '{opts['mine']}'.")
            return
        prompt = render_angle_miner_prompt(
            source_chunk=ch["content"],
            book_title=ch.get("book_title", opts["mine"]),
            num_angles=4,
        )
        res = call_gemini_thinking_structured(
            prompt=prompt,
            response_schema=ANGLE_MINER_GEMINI_SCHEMA,
            system_instruction="Bạn là Trưởng ban Biên tập Phim Tài liệu Ngắn 9:16. Trả về JSON.",
        )
        angles = (res or {}).get("angles") or []
        print("=" * 96)
        print(f"ANGLE MINER: '{ch.get('book_title')}' | Chunk #{ch['chunk_idx']} ({ch['section_title']})")
        print("=" * 96)
        for idx, ang in enumerate(angles, 1):
            print(f" [{idx}] {ang.get('angle_title')}  ({ang.get('recommended_narrative_model')} | {ang.get('recommended_intent_mode')})")
            print(f"     • Hook  : {ang.get('hook_idea_vn')}")
            print(f"     • Quote : {ang.get('key_evidence_quote')}")
            print(f"     • Lệnh  : ../.venv/bin/python main.py --book {opts['mine']} --chunk {ch['chunk_idx']} --model {ang.get('recommended_narrative_model')} \"{ang.get('user_request_for_architect')}\"")
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

    log_path, stop_log = start_run_log(book_id or topic[:24])
    try:
        app = create_christian_short_video_app(stop_after_tier1=opts["flow_prep"])
        config = {"configurable": {"thread_id": f"topic_to_video_{int(time.time())}"}}

        print("=" * 96)
        print(
            f"CHỦ ĐỀ: {topic}"
            + (f" | BOOK: {book_id}" if book_id else "")
            + (f" (chunk #{chunk_idx})" if chunk_idx else "")
            + (f" | MODE: {opts['mode']}" if opts["mode"] else "")
            + (f" | FLOW-PREP ({opts['block_sec']:.0f}s/block)" if opts["flow_prep"] else "")
        )
        print("=" * 96)

        state = app.invoke(
            {
                "user_request": topic,
                "intent_mode": opts["mode"],
                "preferred_narrative_model": opts["model"],
                "book_id": book_id,
                "book_chunk_idx": chunk_idx,
            },
            config=config,
        )

        if opts["flow_prep"]:
            flow_info = prepare_flow_workspace(
                state,
                target_block_sec=opts["block_sec"],
                max_blocks=opts["max_blocks"],
            )
            print("\n" + "=" * 96)
            print(f"FLOW PREP SẴN SÀNG ({len(flow_info['blocks'])} BLOCK | Audio={flow_info['audio_duration_sec']:.2f}s)")
            print("=" * 96)
            print(f" • File Prompt Google Flow : {flow_info['prompts_path']}")
            print(f" • Thư mục thả clip Flow   : {flow_info['clips_dir']}")
            print(f" • Lệnh dựng sau khi tải  : python main.py --flow-render \"{flow_info['run_dir']}\"")
            print("=" * 96)
            return

        if opts["daily"] and active_chunk:
            mark_chunk_done(int(active_chunk["chunk_id"]), state.get("final_master_video_path", ""))
            print(f"[Book RAG] Đã đánh dấu Chunk #{chunk_idx} là DONE trong hàng đợi hằng ngày.")
    except Exception:
        print(f"\n[Log] Xem toàn bộ log lỗi tại: {log_path}")
        print("[Log] Hoặc chạy: python main.py --logs")
        raise
    finally:
        stop_log()

    scenes = state.get("scenes", [])
    v = state["visual_scores"]
    o = state["output_scores"]
    asset = state.get("asset_report", {})

    print("\n" + "=" * 96)
    print("BẢNG 1: KỊCH BẢN & CẢNH")
    print("=" * 96)
    print(f" • Tiêu đề   : {state['topic_title']}   | Thể loại: {state.get('genre')}   | Mô hình: {state.get('narrative_model')}   | Mode: {state.get('intent_mode')} -> {state.get('effective_intent_mode')}")
    print(f" • Phong cách: {state.get('style_anchor_en')}")
    for i, sc in enumerate(scenes, 1):
        sfx_tag = f", sfx={sc.get('sfx_cue')}" if sc.get("sfx_cue") and sc.get("sfx_cue") != "none" else ""
        print(f"   [{i}] ({sc.get('camera')}, {sc.get('media_source')}{sfx_tag}) {sc['narration_vn']}")
    print(f" • Cần kiểm chứng trước khi đăng: {state.get('claims_to_verify')}")

    print("\n" + "=" * 96)
    print("BẢNG 2: CHẤM ĐIỂM")
    print("=" * 96)
    print(f" • Kịch bản: {state['average_score']}/10 (Hook={state['theological_moral_score']}, Khớp hình-lời={state['cinematic_quality_score']}, Mạch kể={state['rag_faithfulness_score']}) | Pass={state['pass_validation']} | Lần thử: {state['retry']}")
    clip_txt = f" | CLIP={v['clip_prompt_score']}" if v.get("clip_prompt_score") is not None else ""
    print(f" • Hình ảnh: tổng={v['visual_total_score']}{clip_txt} | nét={v['sharpness_score']} | liên tục màu={v['continuity_score']} | cảnh thật={v.get('real_scene_ratio')} | lỗi={v['failure_reason']}")
    print(f" • Đầu ra  : tổng={o['output_total_score']} | lệch A/V={o['av_offset_frames']} frame | trạng thái={state['tiktok_publish_status']} | vấn đề={o['failure_reason']}")

    print("\n" + "=" * 96)
    print("BẢNG 3: FILE")
    print("=" * 96)
    print(f" • Video        : {state['final_master_video_path']}  ({state['audio_duration_sec']}s)")
    print(f" • Giọng + nhạc : {state['voiceover_wav_path']}")
    if asset.get("contact_sheet"):
        print(f" • Contact sheet: {asset.get('contact_sheet')}")
    print(f" • Timeline     : {asset.get('timeline')}")
    print(f" • Caption      : {state.get('tiktok_caption')}")
    print("=" * 96)


if __name__ == "__main__":
    main()
