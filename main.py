"""
Entry point: Hệ thống Topic-to-Video Agentic Pipeline (LangGraph + 3D AI Animation Engine + VITS Neural TTS).
Chỉ cần truyền bất kỳ chủ đề (`user_request`) nào vào, LLM sẽ tự động:
1. Suy luận Chain-of-Thought (`thinking_process`) để tìm hình ảnh ẩn dụ đắt giá nhất.
2. Tự thiết kế Nhân vật chính cố định (`new_characters`) & Thế giới 3D ngay cả khi bạn chưa có sẵn nhân vật/bối cảnh.
3. Thiết kế Bảng Storyboard Lưới 4 Phân cảnh 2x2 Độc lập (`scene_1.jpg`..`scene_4.jpg`) + Thực thể 3D cử động tiền cảnh.
4. Sinh giọng đọc Nam Neural VITS Tiếng Việt (`facebook/mms-tts-vie`) + Studio Broadcast EQ + Nhạc nền Ambient Auto-Ducking.
5. In chi tiết toàn bộ Bảng Điểm Kiểm Định 3 Tầng (Script QA Score, Visual Feature Gate 1, Output SyncNet Gate 2).
"""

import sys
from graph.workflow import create_christian_short_video_app


def main():
    topic = (
        " ".join(sys.argv[1:]).strip()
        if len(sys.argv) > 1
        else "Hiệu ứng cánh bướm và lý thuyết hỗn loạn trong cuộc sống"
    )

    app = create_christian_short_video_app()
    config = {"configurable": {"thread_id": "topic_to_video_session_01"}}

    print("=" * 96)
    print(f"CHỦ ĐỀ ĐẦU VÀO (TOPIC): {topic}")
    print("=" * 96)

    state = app.invoke(
        {
            "user_request": topic,
            "video_generation_mode": "cinematic_3d_animation",
        },
        config=config,
    )

    sync = state["audio_sync_features"]
    v_scores = state["visual_scores"]
    o_scores = state["output_scores"]
    chars = state.get("new_characters", {})
    char_info = ", ".join(f"{c['name']} [{c['visual_traits']}]" for c in chars.values()) or "Tự động"

    print("\n" + "=" * 96)
    print("BẢNG 1: SUY LUẬN THINKING, NHÂN VẬT 3D & KỊCH BẢN 4 PHÂN CẢNH DO LLM THIẾT KẾ")
    print("=" * 96)
    print(f" • Tiêu đề Video          : {state['topic_title']}")
    print(f" • Suy luận Thinking (CoT): {state.get('thinking_process', '')}")
    print(f" • Nhân vật 3D Tự khởi tạo: {char_info}")
    print(f" • Thực thể 3D Chuyển động: {state['visual_archetype']} | 4 Cảnh: {state['visual_labels']}")
    print(f" • Prompt 4 Ô 2x2 Grid    : {state['scene_action_prompt']}")
    print(f" • Phần 1 (Mở đầu Hook)   : {state['scene_narration_vn']}")
    print(f" • Phần 2 (Giải thích)    : {state['outro_reflection_vn']}")
    print(f" • Phần 3 (Đúc kết)       : {state['closing_prayer_vn']}")

    print("\n" + "=" * 96)
    print("BẢNG 2: CHI TIẾT THÔNG SỐ CHẤM ĐIỂM 3 TẦNG (MULTI-STAGE SCORING ENGINE)")
    print("=" * 96)
    print(" [TẦNG 1 - SCRIPT & VISUAL QA CRITIC (Ngưỡng đạt >= 8.0/10)]:")
    print(f"   ├─ Độ bám sát chủ đề (Topic Faithfulness - 40%) : {state['rag_faithfulness_score']} / 10.0")
    print(f"   ├─ Chất lượng Nhân vật & 4 Cảnh 3D (Visual - 30%): {state['cinematic_quality_score']} / 10.0")
    print(f"   ├─ Sức hút Hook & Kết luận (Impact Score - 30%) : {state['theological_moral_score']} / 10.0")
    print(f"   └─ TỔNG ĐIỂM KỊCH BẢN (Average Script Score)    : {state['average_score']} / 10.0  --> PASS={state['pass_validation']} (Lần thử: {state['retry']})")

    print("\n [TẦNG 2 - CHỐT CHẶN VISUAL FEATURE GATE 1 (Ngưỡng đạt >= 0.78)]:")
    print(f"   ├─ S_clip (Độ khớp Prompt - Ngưỡng >= 0.28)     : {v_scores['clip_prompt_score']}")
    print(f"   ├─ S_cont (Liên kết màu cảnh trước - >= 0.75)   : {v_scores['continuity_score']} (Reinhard Harmonized={state['continuity_harmonized']})")
    print(f"   ├─ S_id_pose (Độ ổn định bố cục - >= 0.70)      : {v_scores['identity_pose_score']}")
    print(f"   ├─ S_sharp (Độ sắc nét Laplacian Variance)      : {v_scores['sharpness_score']}")
    print(f"   └─ TỔNG ĐIỂM HÌNH ẢNH (S_visual_total)          : {v_scores['visual_total_score']}  --> Lỗi: {v_scores['failure_reason']}")

    print("\n [TẦNG 3 - CHỐT CHẶN OUTPUT SYNC & QUALITY GATE 2 (Ngưỡng đạt >= 0.80)]:")
    print(f"   ├─ SyncNet LSE-C (Độ tự tin khớp nhịp - >= 5.0) : {o_scores['lse_c']}")
    print(f"   ├─ SyncNet LSE-D (Khoảng cách lệch - <= 7.5)    : {o_scores['lse_d']}")
    print(f"   ├─ A/V Offset Drift (Độ trễ tiếng-hình - <= 2f) : {o_scores['av_offset_frames']} frames")
    print(f"   ├─ S_mouth_sharp (Tỷ lệ bảo toàn độ nét - >=0.7): {o_scores['mouth_sharp_ratio']}")
    print(f"   ├─ S_jitter (Độ rung lắc khung hình - <= 1.8px) : {o_scores['bbox_jitter_px']} px")
    print(f"   └─ TỔNG ĐIỂM ĐẦU RA (S_output_total)            : {o_scores['output_total_score']}  --> Status: {state['tiktok_publish_status']}")

    print("\n" + "=" * 96)
    print("BẢNG 3: ĐƯỜNG DẪN CÁC FILE SẢN PHẨM ĐÃ XUẤT")
    print("=" * 96)
    print(f" • File Video Hoạt hình 3D (30fps MP4)     : {state['final_master_video_path']}")
    print(f" • File Giọng đọc Neural VITS + BGM (.wav) : {state['voiceover_wav_path']} ({sync['duration_sec']}s | {sync['total_video_frames']} frames)")
    print(f" • 4 Khung cảnh 3D Độc lập (2x2 Grid)      : {state['final_master_video_path'].replace('final_master.mp4', 'scene_1.jpg')} .. scene_4.jpg")
    print(f" • Báo cáo JSON Visual Score Gate 1        : {state['final_master_video_path'].replace('final_master.mp4', 'visual_score_report.json')}")
    print(f" • Báo cáo JSON Output Score Gate 2        : {state['final_master_video_path'].replace('final_master.mp4', 'output_score_report.json')}")
    print("=" * 96)


if __name__ == "__main__":
    main()
