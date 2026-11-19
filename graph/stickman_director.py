"""
Module Đạo Diễn Video Lịch Sử Người Que (Historical Stickman Director).
Tuân thủ 100% tài liệu `Historical_Stickman_Video_Instructions.docx`:
- Cấu trúc chuẩn 6 cảnh x 10 giây = 60 giây (Vertical 9:16).
- Tóm tắt sự thật lịch sử và nguồn kiểm chứng.
- Kịch bản & Lời bình 18–24 từ/cảnh.
- Bảng nhân vật mẫu (Character Reference Sheet Prompt).
- Chỉ dẫn cho Agent giữ nhất quán nhân vật (Character Consistency Agent Prompt).
- Cặp prompt cho từng cảnh (1 Still Starting Frame Image Prompt + 1 Animation Video Prompt 4 nhịp thời gian).
- Negative constraints & Continuity checklist.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.settings import WORKSPACE_DIR
from graph.audio_sync import synthesize_scene_voiceover
from graph.llm_client import call_gemini_thinking_structured


STICKMAN_GEMINI_SCHEMA: Dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "event_title": {"type": "STRING"},
        "historical_scope": {"type": "STRING"},
        "date_and_location": {"type": "STRING"},
        "historical_brief": {
            "type": "OBJECT",
            "properties": {
                "core_cause": {"type": "STRING"},
                "key_figures": {"type": "ARRAY", "items": {"type": "STRING"}},
                "turning_point": {"type": "STRING"},
                "factual_outcome": {"type": "STRING"},
                "sources": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["core_cause", "key_figures", "turning_point", "factual_outcome", "sources"],
        },
        "visual_style_anchor": {"type": "STRING"},
        "characters": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "historical_role": {"type": "STRING"},
                    "silhouette_and_costume": {"type": "STRING"},
                    "headwear_or_hair": {"type": "STRING"},
                    "signature_props": {"type": "STRING"},
                    "color_tag": {"type": "STRING"},
                },
                "required": ["name", "historical_role", "silhouette_and_costume", "headwear_or_hair", "signature_props", "color_tag"],
            },
        },
        "character_reference_sheet_prompt": {"type": "STRING"},
        "consistency_agent_prompt": {"type": "STRING"},
        "clips": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "clip_index": {"type": "INTEGER"},
                    "time_range": {"type": "STRING"},
                    "narration": {"type": "STRING"},
                    "narration_word_count": {"type": "INTEGER"},
                    "main_visual_action": {"type": "STRING"},
                    "story_purpose": {"type": "STRING"},
                    "sfx_cue": {"type": "STRING"},
                    "image_prompt_en": {"type": "STRING"},
                    "animation_prompt_en": {"type": "STRING"},
                    "negative_constraints_en": {"type": "STRING"},
                    "continuity_outgoing_state": {"type": "STRING"},
                },
                "required": [
                    "clip_index",
                    "time_range",
                    "narration",
                    "main_visual_action",
                    "story_purpose",
                    "image_prompt_en",
                    "animation_prompt_en",
                    "negative_constraints_en",
                    "continuity_outgoing_state",
                ],
            },
        },
    },
    "required": [
        "event_title",
        "date_and_location",
        "historical_brief",
        "visual_style_anchor",
        "characters",
        "character_reference_sheet_prompt",
        "consistency_agent_prompt",
        "clips",
    ],
}


def _slugify(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_")[:36] or "stickman"


def get_curated_stickman_topics() -> List[Dict[str, str]]:
    """Trả về 8 chủ đề sự kiện lịch sử mẫu theo đúng Step 1 của tài liệu."""
    return [
        {
            "id": 1,
            "title": "Trận Bạch Đằng 938: Bẫy cọc ngầm đánh tan quân Nam Hán",
            "date_place": "Năm 938, Sông Bạch Đằng, Đại Cồ Việt",
            "premise": "Ngô Quyền lợi dụng thủy triều và cọc gỗ bịt sắt dưới lòng sông để tiêu diệt hạm đội thuyền chiến Nam Hán.",
            "opening_visual": "Cận cảnh người que Ngô Quyền đẽo vót cọc gỗ sắc nhọn rồi cắm xuống đáy sông khi thủy triều dâng cao.",
            "conflict": "Hạm đội thuyền Nam Hán khổng lồ tràn vào cửa sông trong lúc quân ta vờ rút lui nhử địch.",
            "outcome": "Thủy triều rút nhanh, thuyền giặc bị cọc ngầm đâm thủng vỡ vụn, chấm dứt 1000 năm Bắc thuộc.",
            "duration": "60s (6 clips x 10s)",
            "difficulty": "Trung bình (Có tương tác thuyền và nước sông)",
        },
        {
            "id": 2,
            "title": "The 1814 London Beer Flood: Đại hồng thủy bia ở London",
            "date_place": "Tháng 10 năm 1814, London, Vương quốc Anh",
            "premise": "Một bồn ủ bia khổng lồ phát nổ tạo thành cơn sóng thần bia 1,4 triệu lít càn quét đường phố.",
            "opening_visual": "Người que thợ ủ bia đứng sững sờ trước thùng gỗ cao 7 mét bắt đầu nứt toác dữ dội.",
            "conflict": "Bức tường bia sụp đổ, sóng bọt bia tràn ngập các tầng hầm và làm đổ sập hai ngôi nhà gạch.",
            "outcome": "Ngành sản xuất bia Anh chuyển từ thùng gỗ khổng lồ sang bồn xi măng và sắt an toàn hơn.",
            "duration": "60s (6 clips x 10s)",
            "difficulty": "Dễ - Hài hước (Cực kỳ bắt mắt và cuốn hút người xem)",
        },
        {
            "id": 3,
            "title": "Trận Cannae 216 TCN: Bẫy gọng kìm vĩ đại của Hannibal",
            "date_place": "Năm 216 TCN, Cannae, Bán đảo Ý",
            "premise": "Hannibal Barca sử dụng đội hình cánh cung uốn ngược để bao vây tiêu diệt quân đội La Mã đông gấp đôi.",
            "opening_visual": "Người que Hannibal cưỡi voi chỉ huy trung quân chủ động lùi bước giả vờ thất thủ.",
            "conflict": "Quân La Mã say máu đuổi theo vào giữa mà không nhận ra hai gọng kìm kỵ binh đang khép chặt sau lưng.",
            "outcome": "Trở thành chiến thuật bao vây kinh điển nhất mọi thời đại được giảng dạy tại mọi trường quân sự.",
            "duration": "60s (6 clips x 10s)",
            "difficulty": "Trung bình (Bố trận quân sự stickman rõ ràng)",
        },
        {
            "id": 4,
            "title": "Cuộc giải cứu Apollo 13: 3 ngày nghẹt thở trong không gian",
            "date_place": "Tháng 4 năm 1970, Không gian giữa Trái Đất và Mặt Trăng",
            "premise": "Một bình oxy phát nổ giữa vũ trụ, NASA phải dùng mô-đun đổ bộ làm xuồng cứu sinh để đưa phi hành gia về nhà.",
            "opening_visual": "Phi hành gia người que trôi bồng bềnh trong khoang tàu tối om thở ra làn khói lạnh buốt.",
            "conflict": "Thiếu năng lượng, nồng độ CO2 tăng cao, phải chế tạo bộ lọc khí từ băng dính và bìa sách hướng dẫn.",
            "outcome": "Được mệnh danh là 'Thất bại thành công nhất' trong lịch sử thám hiểm không gian của loài người.",
            "duration": "60s (6 clips x 10s)",
            "difficulty": "Trung bình (Không gian tối giản, hiệu ứng thở lạnh)",
        },
        {
            "id": 5,
            "title": "Chiến dịch Mincemeat 1943: Xác chết đánh lừa Hitler",
            "date_place": "Năm 1943, Bờ biển Tây Ban Nha & Địa Trung Hải",
            "premise": "Tình báo Anh gài tài liệu mật giả vào xác một người vô gia cư thả trôi biển để lừa Hitler dời quân khỏi Sicily.",
            "opening_visual": "Sĩ quan tình báo người que khóa chiếc cặp tài liệu mật vào cổ tay một thi thể mặc quân phục hải quân.",
            "conflict": "Hitler tin bức thư tuyệt mật là thật và rút hết quân thiết giáp tinh nhuệ sang Hy Lạp phòng thủ.",
            "outcome": "Phe Đồng Minh đổ bộ Sicily thành công với thương vong tối thiểu, mở toang cửa ngõ châu Âu.",
            "duration": "60s (6 clips x 10s)",
            "difficulty": "Dễ (Hồi hộp, bí ẩn, trinh thám)",
        },
        {
            "id": 6,
            "title": "Trận Điện Biên Phủ 1954: Kéo pháo lên đỉnh dốc",
            "date_place": "Năm 1954, Thung lũng Mường Thanh, Việt Nam",
            "premise": "Hàng vạn chiến sĩ dùng sức người kéo những khẩu pháo hạng nặng nặng hàng tấn vượt qua các con dốc 70 độ.",
            "opening_visual": "Những người que đội mũ nan quấn lưới kéo dây thừng gồng mình chống lại trọng lực trên vách núi cheo leo.",
            "conflict": "Tướng De Castries tin tưởng tuyệt đối rằng Việt Minh không thể mang pháo hạng nặng lên các đỉnh núi cao.",
            "outcome": "Hỏa lực pháo binh khống chế hoàn toàn sân bay Mường Thanh, dẫn đến thắng lợi chấn động địa cầu.",
            "duration": "60s (6 clips x 10s)",
            "difficulty": "Trung bình (Tạo cảm xúc ý chí kiên cường)",
        },
        {
            "id": 7,
            "title": "Cơn sốt hoa Tulip 1637: Bong bóng kinh tế đầu tiên của nhân loại",
            "date_place": "Năm 1637, Amsterdam, Hà Lan",
            "premise": "Một củ hoa tulip có giá bằng một trang trại khổng lồ trước khi sụp đổ về con số không chỉ sau một đêm.",
            "opening_visual": "Thương nhân người que nâng niu một củ hoa tulip như bảo ngọc trước hàng dài người tranh mua phát cuồng.",
            "conflict": "Người dân bán sạch nhà cửa, đất đai, gia súc để gom tiền đầu cơ hoa tulip.",
            "outcome": "Thị trường đổ vỡ trong chớp mắt, khai sinh ra định nghĩa bong bóng tài chính đầu tiên trên thế giới.",
            "duration": "60s (6 clips x 10s)",
            "difficulty": "Dễ - Châm biếm (Rất thích hợp cho khán giả thích kinh tế & đời sống)",
        },
        {
            "id": 8,
            "title": "Trận Marathon 490 TCN: Nguồn gốc đường chạy 42km",
            "date_place": "Năm 490 TCN, Đồng bằng Marathon đến Athens, Hy Lạp",
            "premise": "Phe Athens đánh tan quân Ba Tư xâm lược, người lính chạy liên tục không nghỉ 42km về báo tin mừng rồi ngã xuống.",
            "opening_visual": "Đội hình người que chiến binh Spartan và Athens đồng loạt giơ khiên giáo lao thẳng vào cung thủ Ba Tư.",
            "conflict": "Hạm đội Ba Tư rút lui toan dong buồm vòng qua eo biển để tập kích thành Athens đang bỏ trống.",
            "outcome": "Chiến thắng cứu nền dân chủ sơ khai và tạo nên cự ly Marathon huyền thoại ngày nay.",
            "duration": "60s (6 clips x 10s)",
            "difficulty": "Dễ (Hành động kịch tính, nhịp chạy dồn dập)",
        },
    ]


def build_stickman_system_prompt(num_clips: int = 3) -> str:
    total_sec = num_clips * 10
    return (
        "You are the master Historical Stickman Animation Director, Writer, Character Designer, and Prompt Engineer, "
        "following the exact specifications of 'Historical Stickman Video Instructions'.\n\n"
        "CREDIT-SAVING & PRODUCTION WORKFLOW RULES:\n"
        "1. SINGLE MASTER CHARACTER LINEUP SHEET:\n"
        "   - The 'character_reference_sheet_prompt' MUST be a SINGLE master image prompt containing ALL named recurring characters together side-by-side on ONE canvas in separated panels (e.g. Left: Protagonist, Right: Antagonist).\n"
        "   - Every character must have clearly distinct silhouette, contrasting color palette (e.g. Red vs Blue), different hairstyles/hats, and distinct facial expressions so they NEVER look identical or get confused.\n"
        "   - Nameless crowd/soldiers remain visually subordinate in simple brown peasant tunics.\n\n"
        "2. DIRECT VIDEO GENERATION (ZERO CREDIT WASTED ON STILL IMAGES):\n"
        "   - Users do NOT need to generate still starting images for every scene. The 'animation_prompt_en' is an ALL-IN-ONE DIRECT VIDEO PROMPT ready to be pasted straight into Text-to-Video / Video mode in Google Flow (Veo 3.1 & Omni).\n"
        "   - Each video prompt must be self-contained: explicitly specifying the 2D OverSimplified cartoon style, the characters present (names, skin tone, facial expression, costume colors), the environment, and the 4-phase local timing (0-2s, 2-5s, 5-8s, 8-10s).\n\n"
        "CRITICAL VISUAL STYLE REQUIREMENTS (PREVENT ALL-BLACK SILHOUETTES):\n"
        "The characters are NOT solid black silhouettes or featureless shadow figures! "
        "They are colorful, expressive 2D cartoon characters in the style of OverSimplified / Infographics / cute animated history documentaries:\n"
        "- HEAD & FACE: Round heads with light cartoon skin tone (light tan, fair, or peach skin; NEVER pitch-black fill). "
        "Fully visible, highly expressive facial features: large white cartoon eyes with black pupils, dynamic animated eyebrows (furrowed, arched, or worried), "
        "and expressive mouth (shouting with teeth, wide shocked O-mouth, confident smirk, or panicked grimace). "
        "Hair is clearly visible (topknot, sideburns, bangs, or bun under headwear).\n"
        "- COSTUMES & COLORS: Outfits MUST be colorful and historically themed (e.g. crimson red tunic #D32F2F, royal blue robe #1976D2, bronze armor, leather belts). "
        "Limbs have clean black outlines, but the body and face are fully colored.\n"
        "- PROHIBITION IN PROMPTS: NEVER use ambiguous phrases like 'black stickman' or 'shadow figure'. ALWAYS explicitly include: "
        "'2D colorful cartoon illustration in OverSimplified animation style', 'visible cartoon face with expressive white eyes and dynamic mouth', 'NOT a black silhouette, NOT a shadow figure'.\n\n"
        "STRICT PRODUCTION REQUIREMENTS:\n"
        f"1. FORMAT: Vertical 9:16 frame. Exactly {num_clips} editorial clips x 10 seconds each = {total_sec} seconds total.\n"
        "2. STORY & NARRATION: Fast, punchy, engaging factual storytelling. 18 to 24 spoken words per 10-second clip. "
        "Clip 1 must hook immediately within the first 2 seconds. Every clip must clarify cause and effect or advance the turning point.\n"
        "3. PROMPTS PER CLIP:\n"
        "   - 'image_prompt_en': 70-120 descriptive words. Vertical 9:16, 2D colorful cartoon illustration in OverSimplified style, "
        "character name, skin tone, exact facial expression (eyes, eyebrows, mouth), hair/headwear, specific colored historical attire, "
        "props, environment, lighting, clean vector lines, 'NOT a silhouette, NOT all-black'.\n"
        "   - 'animation_prompt_en': 150-280 words. All-in-one direct video prompt for Google Flow. Account for all 10 seconds using 4-phase local timing: "
        "0.0-2.0s (facial reaction & hook), 2.0-5.0s (main body action & prop interaction), 5.0-8.0s (escalation, reaction, factual reveal), 8.0-10.0s (land outcome & explicitly describe final pose). "
        "Describe facial expressions, eye movements, and mouth changes dynamically throughout the 10 seconds.\n"
        "4. Output ONLY a valid JSON object matching the requested schema."
    )



def build_stickman_user_prompt(topic: str, num_clips: int = 3, language: str = "vi") -> str:
    total_sec = num_clips * 10
    lang_instruction = (
        f"Viết phần 'narration' (lời bình) bằng TIẾNG VIỆT tự nhiên, dứt khoát, dồn dập (18-24 từ mỗi cảnh cho đúng {num_clips} cảnh). "
        "Phần prompt kỹ thuật ('image_prompt_en', 'animation_prompt_en', 'character_reference_sheet_prompt', 'consistency_agent_prompt') "
        "BẮT BUỘC viết bằng TIẾNG ANH chuyên nghiệp cho Google Flow (Veo 3.1 & Omni 1.2)."
        if language == "vi" else
        f"Write narration in punchy English (18-24 words per clip for exactly {num_clips} clips). All generation prompts in English."
    )
    return (
        f"Create a high-impact, credit-saving {total_sec}-second Historical Stickman Video Production Package for the event: '{topic}'.\n\n"
        f"Language requirement: {lang_instruction}\n"
        f"CLIP STRUCTURE ({num_clips} CLIPS x 10s = {total_sec}s):\n"
        f"Make sure there are EXACTLY {num_clips} clips of 10.0 seconds each ({', '.join([f'{i*10}.0-{(i+1)*10}.0s' for i in range(num_clips)])}).\n"
        f"- Clip 1: Immediate hook & premise setup.\n"
        + (f"- Clip 2: The turning point, dramatic trap/clash.\n- Clip 3: The historic climax, decisive victory & legacy.\n" if num_clips == 3 else "- Advance the historical cause-and-effect seamlessly through each clip.\n")
        + "\nCHARACTER ROSTER & MASTER REFERENCE SHEET MANDATE:\n"
        "1. In 'character_reference_sheet_prompt': Produce ONE SINGLE master lineup image prompt containing ALL recurring main characters side-by-side in separated panels (Left side vs Right side). "
        "Ensure high contrast between characters: completely different costume colors (e.g. vibrant crimson red vs imperial navy blue), different headwear/hair, different distinct facial expressions, so they NEVER duplicate or look alike. Only generic nameless soldiers in background share simple brown peasant tunics.\n"
        "2. In all 'image_prompt_en' and 'animation_prompt_en': Explicitly describe the 2D OverSimplified cartoon style, light skin tone, large white cartoon eyes with black pupils, expressive mouth, hair, and specific colored attire. ALWAYS append 'NOT a black silhouette, NOT a shadow figure'.\n"
        "Ensure zero markdown or technical brackets inside the generation prompts so they paste cleanly into Google Flow."
    )



def generate_stickman_production_package(
    topic: str,
    num_clips: int = 3,
    language: str = "vi",
    voice_name: str = "vanthanhthu",
    speed_rate: float = 1.34,
) -> Dict[str, Any]:
    """Tạo gói sản xuất Video Lịch Sử Người Que hoàn chỉnh từ A-Z tối ưu tiết kiệm credit."""
    sys_prompt = build_stickman_system_prompt(num_clips=num_clips)
    user_prompt = build_stickman_user_prompt(topic, num_clips=num_clips, language=language)

    print(f"\n[Stickman Director] Đang nghiên cứu lịch sử và thiết kế kịch bản {num_clips*10}s ({num_clips} clips) cho: '{topic}'...")
    parsed_json = call_gemini_thinking_structured(
        prompt=user_prompt,
        response_schema=STICKMAN_GEMINI_SCHEMA,
        system_instruction=sys_prompt,
    )


    if not parsed_json or not parsed_json.get("clips"):
        raise RuntimeError(f"Không thể tạo kịch bản Stickman cho chủ đề '{topic}'. Vui lòng kiểm tra lại kết nối mạng hoặc API Key.")

    # Tạo thư mục chạy
    slug = _slugify(parsed_json.get("event_title") or topic)
    run_dir = WORKSPACE_DIR / f"stickman_{slug}_{time.strftime('%m%d_%H%M%S')}"
    clips_dir = run_dir / "flow_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    clips = parsed_json.get("clips", [])
    # 1. Thu âm lời bình (6 cảnh) + Nhạc nền Phonk kịch tính với Auto-Ducking
    narrations = [c["narration"] for c in clips]
    sfx_cues = [c.get("sfx_cue", "none") for c in clips]
    wav_path, timings = synthesize_scene_voiceover(
        scene_texts=narrations,
        output_filename=run_dir / "audio_16k_mono.wav",
        sfx_cues=sfx_cues,
        voice_name=voice_name,
        speed_rate=speed_rate,
        music_mood="cinematic_mystery_suspense",
    )

    # 2. Xuất gói tài liệu Markdown và JSON chuẩn Google Flow
    package_md_path = run_dir / "historical_stickman_package.md"
    prompts_txt_path = run_dir / "flow_prompts.txt"
    manifest_json_path = run_dir / "flow_manifest.json"

    md_content = _format_stickman_markdown_package(parsed_json, wav_path, clips_dir, run_dir)
    package_md_path.write_text(md_content, encoding="utf-8")

    flow_txt_content = _format_flow_prompts_for_user(parsed_json, clips_dir, run_dir)
    prompts_txt_path.write_text(flow_txt_content, encoding="utf-8")

    # Lưu manifest tương thích với flow_bundler để lệnh --flow-render dựng được ngay
    flow_blocks = []
    t_cursor = 0.0
    for idx, c in enumerate(clips, 1):
        dur = 10.0
        if idx - 1 < len(timings):
            st, en = timings[idx - 1]
            dur = max(6.0, round(en - st + 0.3, 2))
        flow_blocks.append({
            "block_index": idx,
            "scene_indices": [idx],
            "start_sec": round(t_cursor, 2),
            "end_sec": round(t_cursor + dur, 2),
            "duration_sec": dur,
            "narration_vn": c["narration"],
            "flow_prompt": c["animation_prompt_en"],
        })
        t_cursor += dur

    manifest_data = {
        "topic_title": parsed_json.get("event_title") or topic,
        "mode": "STICKMAN_HISTORY",
        "style_anchor_en": parsed_json.get("visual_style_anchor", ""),
        "wav_path": str(wav_path),
        "clips_dir": str(clips_dir),
        "blocks": flow_blocks,
        "scenes": [
            {
                "narration_vn": c["narration"],
                "subtitle_vn": c["narration"],
                "image_prompt_en": c["image_prompt_en"],
                "animation_prompt_en": c["animation_prompt_en"],
            }
            for c in clips
        ],
    }
    manifest_json_path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "run_dir": run_dir,
        "clips_dir": clips_dir,
        "package_md_path": package_md_path,
        "prompts_txt_path": prompts_txt_path,
        "wav_path": wav_path,
        "parsed_json": parsed_json,
    }


def _format_stickman_markdown_package(data: Dict[str, Any], wav_path: Path, clips_dir: Path, run_dir: Path) -> str:
    hb = data.get("historical_brief", {})
    chars = data.get("characters", [])
    clips = data.get("clips", [])
    total_clips = len(clips)
    total_sec = total_clips * 10

    lines = [
        f"# 🎬 GÓI SẢN XUẤT HOẠT HÌNH LỊCH SỬ NGƯỜI QUE: {data.get('event_title', '')}",
        f"**Địa điểm & Thời gian**: {data.get('date_and_location', '')} | **Thời lượng**: {total_sec} giây ({total_clips} clips x 10s)",
        f"**Thư mục làm việc**: `{run_dir}`",
        "",
        "---",
        "## 1. Tóm Tắt Sự Thật Lịch Sử & Nguồn Kiểm Chứng",
        f"- **Nguyên nhân cốt lõi**: {hb.get('core_cause', '')}",
        f"- **Nhân vật then chốt**: {', '.join(hb.get('key_figures', []))}",
        f"- **Bước ngoặt sự kiện**: {hb.get('turning_point', '')}",
        f"- **Kết quả thực tế**: {hb.get('factual_outcome', '')}",
        "- **Nguồn tài liệu tham khảo**:",
    ]
    for s in hb.get("sources", []):
        lines.append(f"  - {s}")

    lines.extend([
        "",
        "---",
        "## 2. Phong Cách Hình Ảnh & Thiết Kế Nhân Vật (Locked Cartoon Style)",
        f"**Visual Style Anchor**: `{data.get('visual_style_anchor', '')}`",
        "",
        "### Danh Sách Nhân Vật Cốt Lõi:",
    ])
    for c in chars:
        lines.append(f"#### 👤 {c.get('name')} ({c.get('historical_role')})")
        lines.append(f"- **Dáng vóc & Trang phục**: {c.get('silhouette_and_costume')}")
        lines.append(f"- **Mũ nón / Tóc**: {c.get('headwear_or_hair')}")
        lines.append(f"- **Vật dụng đặc trưng**: {c.get('signature_props')}")
        lines.append(f"- **Mã màu nhận diện**: `{c.get('color_tag')}`")
        lines.append("")

    lines.extend([
        "---",
        "## 3. [BƯỚC 1: ẢNH DUY NHẤT] Prompt Bảng Nhân Vật Toàn Diện (Master Character Lineup Sheet)",
        "> *💡 TIẾT KIỆM CREDIT: Bạn CHỈ CẦN tạo 1 ảnh duy nhất này lúc đầu để làm ảnh tham chiếu (Image Reference) cho toàn bộ nhân vật. Tất cả các nhân vật chính đều xuất hiện chung trên 1 ảnh với màu sắc và trang phục đối lập, không bao giờ bị trùng lặp!*",
        "```text",
        data.get("character_reference_sheet_prompt", ""),
        "```",
        "",
        "---",
        "## 4. Chỉ Dẫn Agent Giữ Tính Nhất Quán (Consistency Agent Instructions)",
        "```text",
        data.get("consistency_agent_prompt", ""),
        "```",
        "",
        "---",
        f"## 5. [BƯỚC 2: TẠO VIDEO TRỰC TIẾP] Danh Sách {total_clips} Clips (Dán Thẳng Vào Text-To-Video, Không Cần Tạo Ảnh Tĩnh)",
    ])

    for c in clips:
        idx = c.get("clip_index", 1)
        lines.extend([
            f"### 🎞️ CLIP {idx} ({c.get('time_range', '10s')}) — {c.get('story_purpose', '')}",
            f"**🎙️ Lời bình ({c.get('narration_word_count', len(c.get('narration','').split()))} từ)**: {c.get('narration')}",
            f"**🎬 Hành động chính**: {c.get('main_visual_action')}",
            f"**🔊 Hiệu ứng âm thanh (SFX)**: `{c.get('sfx_cue', 'none')}`",
            "",
            f"**🎥 PROMPT TẠO VIDEO TRỰC TIẾP (DÁN THẲNG VÀO VEO / OMNI TRÊN FLOW)**:",
            "```text",
            c.get("animation_prompt_en", ""),
            "```",
            "",
            f"*(Tùy chọn phụ: Nếu bạn thích chế độ Image-to-Video thì mới dùng prompt ảnh này: `{c.get('image_prompt_en', '')}`)*",
            "",
            f"**🚫 Negative Constraints**: `{c.get('negative_constraints_en', '')}`",
            f"**🔗 Khớp nối sang cảnh tiếp theo**: {c.get('continuity_outgoing_state', '')}",
            "",
            "---",
        ])

    lines.extend([
        "## 6. Hướng Dẫn Dựng & Hoàn Tất Video Bằng 1 Lệnh",
        f"1. Tạo xong {total_clips} clip trên Google Flow, tải về đổi tên lần lượt: " + ", ".join([f"`{i+1}.mp4`" for i in range(total_clips)]),
        f"2. Thả tất cả clip vào thư mục:",
        f"   `{clips_dir}`",
        "3. Chạy lệnh dựng tự động (cắt sạch watermark Veo, khớp giọng đọc, ghép nhạc, làm phụ đề Safe Zone):",
        f"   ```bash",
        f"   ./run.sh --flow-render \"{run_dir}\"",
        f"   ```",
    ])
    return "\n".join(lines)


def _format_flow_prompts_for_user(data: Dict[str, Any], clips_dir: Path, run_dir: Path) -> str:
    clips = data.get("clips", [])
    total_clips = len(clips)
    total_sec = total_clips * 10
    lines = [
        "=" * 92,
        f"📋 GOOGLE FLOW READY PROMPTS (TIẾT KIỆM CREDIT): {data.get('event_title', '')}",
        f"Tỷ lệ: 9:16 dọc | {total_clips} clips x 10s = {total_sec}s | Thư mục ném clip: {clips_dir}",
        "=" * 92,
        "",
        "📌 [BƯỚC 1: TẠO 1 ẢNH DUY NHẤT] BẢNG TOÀN BỘ NHÂN VẬT (MASTER CHARACTER LINEUP SHEET):",
        "   (💡 Chỉ tạo 1 ảnh này duy nhất lúc đầu làm ảnh tham chiếu. Toàn bộ nhân vật chính đều có mặt, trang phục & màu sắc đối lập, không trùng lặp)",
        "-" * 92,
        data.get("character_reference_sheet_prompt", ""),
        "-" * 92,
        "",
        "🎬 [BƯỚC 2: TẠO VIDEO TRỰC TIẾP] (DÁN THẲNG VÀO VEO / OMNI - KHÔNG CẦN TẠO ẢNH TĨNH CHO TỪNG CẢNH):",
        "=" * 92,
    ]
    for c in clips:
        idx = c.get("clip_index", 1)
        lines.extend([
            f"▶ [CLIP {idx}/{total_clips}] ({c.get('time_range', '10s')}):",
            f"Lời bình: \"{c.get('narration', '')}\"",
            "",
            f"🎥 Prompt Tạo Video Trực Tiếp (Text-to-Video trên Flow):",
            c.get("animation_prompt_en", ""),
            "",
            "-" * 92,
            "",
        ])

    lines.extend([
        "=" * 92,
        "💡 HƯỚNG DẪN DỰNG HOÀN THIỆN:",
        f"Sau khi tạo xong {total_clips} clip trên Flow, bạn tải về đổi tên {', '.join([f'{i+1}.mp4' for i in range(total_clips)])} thả vào:",
        f"{clips_dir}",
        f"Rồi chạy lệnh sau trên terminal để tự động cắt watermark & xuất video hoàn chỉnh:",
        f"./run.sh --flow-render \"{run_dir}\"",
        "=" * 92,
    ])
    return "\n".join(lines)

