"""
Entry point: Topic-to-Video (phim tài liệu ngắn 9:16) — LangGraph pipeline.

    python main.py "Chiến dịch Điện Biên Phủ 1954"
    python main.py --mode HUMAN_NO_LIPSYNC "Một ngày của người thợ gốm Bát Tràng"

Chế độ (`--mode`): NO_HUMAN_BROLL (mặc định/tự suy ra) | HUMAN_NO_LIPSYNC | HUMAN_WITH_LIPSYNC (chưa có nhép môi).
Luồng: filter_context -> intent_router -> prompt_architect (kịch bản + cảnh) -> prompt_scorer (kiểm tra cứng + LLM critic)
       -> media_generator (giọng đọc theo cảnh, hình từng cảnh, dựng phim) -> visual_judge (kiểm định đầu ra thật).
"""

import sys
import time

from graph.workflow import create_christian_short_video_app


def _parse_args(argv):
    mode = ""
    words = []
    it = iter(argv)
    for a in it:
        if a == "--mode":
            mode = next(it, "").strip().upper()
        else:
            words.append(a)
    topic = " ".join(words).strip() or "Chiến dịch Điện Biên Phủ 1954: 56 ngày đêm thay đổi cục diện"
    return topic, mode


def main():
    topic, mode = _parse_args(sys.argv[1:])

    app = create_christian_short_video_app()
    config = {"configurable": {"thread_id": f"topic_to_video_{int(time.time())}"}}

    print("=" * 96)
    print(f"CHỦ ĐỀ: {topic}" + (f" | MODE: {mode}" if mode else ""))
    print("=" * 96)

    state = app.invoke({"user_request": topic, "intent_mode": mode}, config=config)

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
