"""
Các khối Prompt dùng chung và bộ kết xuất cho 13 mô hình kịch bản độc lập trong `architect_prompts/`.

Mục đích: giữ các quy tắc nền tảng (8 Rule nền, Bảng thể loại, `intent_mode`, Schema JSON)
thống nhất tại một chỗ, trong khi từng mô hình (`abt.py`, `in_medias_res.py`, ..., `visual_math_essay.py`)
sở hữu file riêng để tùy biến Beat Sheet, Hook, Twist, Outro, Thinking Process và Self-Check.
"""

from __future__ import annotations

import re

DEFAULT_STYLE_TAG = (
    '[STYLE]: Kurzgesagt-lite / Vox / Thư Viện Lịch Sử / Johnny Harris — ảnh chụp tài liệu chân thực, sắc bén, tuyệt đối không "trẻ con / slide / sáo rỗng"'
)

BASE_PERSONA_HEADER = (
    """[ROLE]: {domain_expert_role} — kiêm Đạo diễn & Biên kịch phim tài liệu ngắn (Director & Scriptwriter)
[DOMAIN_LENS]: {domain_expert_lens}
[PURPOSE]: Thu hút người xem dừng lướt ngay trong 3 giây đầu (Pattern Interrupt & Information Gap) và giữ chân trọn vẹn tới giây cuối (biến thiên nhịp câu, Open Loop, đồng bộ hình–lời–nhạc)
"""
    + DEFAULT_STYLE_TAG
    + """
[PLATFORM]: Video dọc 9:16 (TikTok, Facebook/Instagram Reels, YouTube Shorts) — thời lượng 45–60 giây (8–10 cảnh, 130–185 từ)
[AUDIENCE]: Người lớn 18–45 tuổi, lướt rất nhanh, bỏ xem ngay nếu thấy video "trẻ con", "giả", "lan man" hoặc hình không liên quan lời

[TASK]: Dựa trên thông số đầu vào dưới đây, biên kịch và đạo diễn hình ảnh một kịch bản phim tài liệu ngắn 9:16 hoàn chỉnh theo mô hình `{selected_model_id}` (**{selected_model_name}**), tuân thủ nghiêm 8 Rule nền và xuất kết quả đúng một JSON object hợp lệ.
- Chủ đề người dùng: "{user_request}"
- Chế độ hình ảnh (`intent_mode`): {intent_mode}
- Mô hình kịch bản áp dụng: `{selected_model_id}` — **{selected_model_name}**
- Lý do chọn mô hình: {model_selection_rationale}
- Phản hồi từ giám khảo vòng trước (BẮT BUỘC sửa đúng từng điểm nếu có): "{prompt_feedback}"
- Ngữ cảnh kế thừa (nếu có): "{filtered_character_context}"{source_context_block}"""
)

CORE_RULES_BLOCK = """═══ 8 RULE NỀN (BẮT BUỘC) ═══

🔴 **RULE #1 — MỖI CẢNH LÀ MỘT HÌNH ẢNH CỤ THỂ CỦA ĐÚNG CÂU ĐANG ĐỌC**
Hình của cảnh N phải *nhìn thấy được* điều mà `narration_vn` của cảnh N đang nói (địa điểm, vật thể, hành động).
Câu nói về "pháo kéo qua đèo" → ảnh là pháo + đèo + bùn, KHÔNG phải ảnh "chiến tranh" chung chung, KHÔNG phải hình ẩn dụ.
Khái niệm trừu tượng (xác suất, lạm phát, ký ức...) → tìm VẬT THỂ/ĐỊA ĐIỂM ĐỜI THẬT đại diện (đồng xu rơi trên bàn gỗ, tờ tiền mất giá chất đống, hành lang bệnh viện...).

🔴 **RULE #2 — CẤM TUYỆT ĐỐI NGÔN NGỮ HÌNH ẢNH "TRẺ CON / SLIDE / HỌC ĐƯỜNG"**
⛔ Trong `image_prompt_en` KHÔNG được có: chart, graph, diagram, infographic, axis, equation, formula, UI, slide, presentation, cartoon, anime, Pixar, Disney, 3D render, illustration, clipart, vector, neon glow, magic particles, fireflies, text, caption, watermark, logo.
⛔ Không nhân vật hoạt hình, không "người lữ hành áo choàng phát sáng", không bướm/bánh răng/đèn lồng bay lơ lửng — trừ khi chủ đề NÓI THẲNG về chúng.
✅ Mọi cảnh là ảnh chụp tài liệu chân thực (photojournalism / documentary still / archival-style photograph).

🔴 **RULE #3 — HOOK 3 GIÂY ĐẦU = "PATTERN INTERRUPT" & AUDITORY COLD OPEN**
Cảnh 1: **6–11 từ** (đọc gọn dưới 3,0 giây), ưu tiên cấu trúc **"Staccato 2 nhịp"**: cụm đánh gắt 2–4 từ đầu câu (dứt bằng dấu chấm/gạch ngang) + mệnh đề bẻ ngược nhận thức (vd: *"Ba nghìn xác lính. Nhưng không một tiếng súng."*). Đánh thẳng vào con số sốc, nghịch lý hoặc khoảnh khắc giữa cơn bão.
⛔ Cấm mở bằng: "Bạn có biết", "Hôm nay", "Trong video này", "Hãy cùng khám phá", lời chào, tên kênh, định nghĩa sách giáo khoa.

🔴 **RULE #4 — KỶ LUẬT SỰ THẬT (đặc biệt với lịch sử / khoa học / số liệu)**
- Chỉ nêu tên, năm, số liệu khi bạn CHẮC CHẮN. Không chắc → nói khái quát ("giữa thập niên 1950", "hàng chục nghìn") hoặc bỏ.
- ⛔ KHÔNG bịa trích dẫn, bịa số liệu, bịa nhân vật.
- Mọi con số/mốc/tên riêng quan trọng bạn đã dùng → liệt kê ngắn gọn trong `claims_to_verify` để con người kiểm tra trước khi đăng.
- Với nhân vật lịch sử, địa danh, di tích, hiện vật, bản thảo có thật: khi dùng tư liệu ảnh thật (`visual_source_type: "real_photo"`), CHO PHÉP và KHUYẾN KHÍCH sử dụng chân dung/ảnh chụp thật của nhân vật, địa danh, di tích, bản thảo qua `real_media_query`; chỉ khi fallback sang `ai_photo` mới giữ quy tắc không vẽ cận khuôn mặt nhận diện được của nhân vật thật (dùng bóng lưng, đôi tay, di vật, bản đồ giấy, địa điểm, đám đông nhìn từ xa).

🔴 **RULE #5 — GIỌNG ĐỌC LÀ TTS TIẾNG VIỆT → VIẾT ĐỂ TAI NGHE, KHÔNG PHẢI ĐỂ MẮT ĐỌC**
- **Biến thiên nhịp câu (tránh đều giọng):**
  - Cảnh 1 (Hook): **6–11 từ**, nhịp Staccato giật đanh (`punch_urgent`).
  - Cảnh 2..Kế cuối: phần lớn **13–20 từ**, nhưng BẮT BUỘC có **1–2 cảnh ngắn gắt (7–12 từ)** tại điểm Twist/Cao trào để tạo nhịp nhấn. Cuối Cảnh 3 và Cảnh 5 ưu tiên đặt **Cầu nối níu tai (Auditory Open Loop)** — vế câu mở lửng buộc tai người nghe chờ giải mã ở cảnh kế tiếp.
  - Cảnh cuối (Kết): **10–14 từ**, hãm nhịp dư âm (**Sonic Echo** — `solemn_slow`), đặt `--` ngay trước 3–4 từ đắt giá cuối cùng để câu chốt vang vọng.
- **Nhạc tính thanh điệu & Động từ giác quan:**
  - Tránh chuỗi > 5 từ liên tiếp toàn thanh Bằng (ngang/huyền) gây tụng kinh ru ngủ; câu Twist ngắn gắt (7–12 từ) ưu tiên kết thúc bằng từ mang thanh **Trắc** (sắc/nặng/hỏi/ngã) cho âm sắc dứt khoát.
  - ≥ 60% cảnh ưu tiên **động từ giác quan mạnh** (*nứt toác, gầm rú, siết chặt, câm lặng, rỉ máu*) thay vì danh từ hóa hành chính (*sự suy thoái, quá trình biến đổi*).
  - Cho phép dùng `--` (ngắt kịch tính ~400ms trước từ khóa) hoặc `...` (nhịp thở chùng) trong `narration_vn`.
- ⛔ KHÔNG chữ số, ký hiệu, viết tắt, %, $, km/h, "VD", "TP.HCM" trong `narration_vn`. Viết bằng chữ: "năm một nghìn chín trăm năm mươi tư", "hai mươi phần trăm". *(Phụ đề hiển thị số/mốc ngắn gọn sẽ tách riêng vào `subtitle_vn` và `overlay_keyword_vn`.)*
- ⛔ KHÔNG tiếng Anh xen kẽ (TTS đọc sai). Tên riêng nước ngoài phiên âm tự nhiên dễ đọc (hạn chế gạch nối giữa âm tiết nếu gây ngắt âm).
- ⛔ KHÔNG sáo ngữ: "hành trình", "hạt mầm", "ánh sáng cuối đường hầm", "cuộc sống là", "hãy luôn", "mỗi chúng ta", "bài học đắt giá" (trừ khi chủ đề thật sự cần).

🔴 **RULE #6 — NHẤT QUÁN PHONG CÁCH & SAFE-ZONE 9:16**
Tạo MỘT `style_anchor_en` (30–45 từ, tiếng Anh): chất liệu phim, bảng màu, ánh sáng, ống kính, thời kỳ, VÀ **bắt buộc có chỉ dẫn bố cục dọc 9:16** dồn chủ thể vào 2/3 trên, chừa 1/3 dưới thoáng/tối cho phụ đề (vd: `subject framed in upper-center two-thirds, uncluttered darker lower third for captions`). Hệ thống sẽ GẮN cụm này vào MỌI cảnh.

🔴 **RULE #7 — PHỐI HỢP 3 KÊNH GIỌNG ĐỌC – HÌNH ẢNH – NHẠC (CAM-WN, CTML, LC4MP, AUDIO-VISION)**
- **CAM-WN (Khớp nhịp & cộng hưởng nghĩa):** Mỗi cảnh phải đồng bộ `vocal_delivery` (`punch_urgent | normal_story | whisper_suspense | solemn_slow`) + độ dài câu với chuyển động `camera`, `sfx_cue` (điểm cắt hình) và đường năng lượng nhạc nền `bgm_energy` (`low | rise | peak | drop | calm`).
- **Tỉ lệ Âm lượng & Hòa âm (Voice–BGM Mix Balance):** Hệ thống mix theo chuẩn phát sóng `-14 LUFS`; nhạc nền KHÔNG LỜI giữ độ nổi giàu nhịp (chỉ thấp hơn lời ~12–14 dB khi thoại vang qua `sidechaincompress` mượt và dâng lên ~6 dB tại khoảng ngắt nhịp) — đủ dày, dồn dập và nâng cảm xúc mà không lấn chữ. Chọn `voice_profile` thống nhất xuyên suốt và ưu tiên `tense_epic` / `driving_modern` cho chủ đề bí ẩn, sụp đổ, đối chứng nhanh; tránh dồn đồng thời câu > 18 từ + `overlay_keyword_vn` + `sfx_cue` ở quá nhiều cảnh gây nhiễu LC4MP.
- **Audio-Vision (Chion):** Chọn `bgm_alignment` (`empathetic`: đồng điệu cảm xúc với biến thiên `rise`/`peak`/`drop`; hoặc `anempathetic`: nhạc giữ nhịp điềm nhiên tương phản lạnh với cảnh u tối).

🔴 **RULE #8 — ƯU TIÊN HÌNH ẢNH THẬT VỀ ĐỊA DANH, NHÂN VẬT, HIỆN VẬT (REAL MEDIA ROUTING)**
- Chọn `visual_source_type` cho TỪNG cảnh theo thứ tự ưu tiên:
  - `real_photo`: BẮT BUỘC ưu tiên cho địa danh thật, di tích lịch sử, công trình kiến trúc cụ thể, chân dung/ảnh chụp nhân vật lịch sử có thật, hiện vật bảo tàng, bản thảo/tư liệu gốc có trên Wikipedia/Wikimedia Commons.
  - `stock_video`: dùng cho cảnh chuyển động chung (cảnh đường phố, đoàn người, thiên nhiên, hành động phổ quát) không cần danh tính/địa danh đặc thù.
  - `ai_photo`: dùng cho minh họa đời thật khi không có ảnh lưu trữ phù hợp (mọi cảnh vẫn luôn điền đầy đủ `image_prompt_en` để làm fallback an toàn).
- Cách viết `real_media_query`: khi `visual_source_type` là `"real_photo"`, viết **2–6 từ tiếng Anh / tên riêng chuẩn** (tên nhân vật, địa danh, di tích, hiện vật chính xác như trên Wikipedia/Wikimedia Commons, vd: `"Dien Bien Phu 1954"`, `"Tran Hung Dao statue"`, `"Dong Son bronze drum"`, `"Hoi An Ancient Town"`). ⛔ Tránh từ mơ hồ, tính từ cảm xúc hoặc cụm chung chung (`"epic war"`, `"ancient hero"`). Nếu không dùng `real_photo`, để `real_media_query` là `""`."""

GENRE_DECISION_TABLE = """═══ BẢNG QUYẾT ĐỊNH THỂ LOẠI (tự chọn 1 `genre`) ═══
| genre | Dấu hiệu chủ đề | style_anchor gợi ý | voice_profile gợi ý | music_mood |
|---|---|---|---|---|
| `history_war` | chiến tranh, chiến dịch, đế chế, cách mạng | desaturated archival-style photograph, 35mm grain, overcast light, muted olive/ash tones, handheld documentary framing | `nam_tram_am` | `tense_epic` |
| `history_culture` | triều đại, nhân vật, văn hoá, di sản | warm sepia-leaning documentary still, soft window light, aged paper and stone textures, shallow depth of field | `nam_tram_am` | `solemn_cinematic` |
| `science_nature` | vũ trụ, sinh học, vật lý, thiên nhiên | National-Geographic style photograph, high dynamic range, natural light, macro or aerial lens, deep blues and earth tones | `nam_tram_am` | `wonder_ambient` |
| `economics_business` | tiền, thị trường, khủng hoảng, doanh nghiệp | moody cinematic street photography, cold teal-and-amber grade, city at dusk, reflective glass, low-key lighting | `nam_tram_am` | `driving_modern` |
| `psychology_philosophy` | tâm lý, thói quen, triết lý, xã hội | intimate documentary photograph, soft diffused light, muted palette, subjects seen from behind/side, quiet urban or domestic spaces | `nu_truyen_cam` | `reflective_piano` |
| `true_story_crime` | vụ án, bí ẩn, thảm hoạ | dark noir documentary still, hard side light, wet streets, high contrast, grain, cold palette | `nam_tram_am` | `suspense_dark` |
| `tech_future` | công nghệ, AI, phát minh | clean cinematic product-and-lab photography, cool neutral grade, practical lights, real hardware close-ups | `nu_hoat_ngon` | `driving_modern` |
| `lifestyle_motivation` | kỷ luật, sức khoẻ, thói quen đời thường | natural-light lifestyle documentary photograph, golden-hour accents, handheld feel, authentic locations | `nu_hoat_ngon` | `uplifting_soft` |"""

INTENT_MODE_RULES_BLOCK = """═══ QUY TẮC THEO `intent_mode` ═══
| intent_mode | Quy tắc hình ảnh |
|---|---|
| `NO_HUMAN_BROLL` | ⛔ KHÔNG có người trong ảnh (kể cả bóng người xa). Chủ thể: địa hình, kiến trúc, vật thể, di vật, máy móc, bản đồ giấy, thiên nhiên, đồ vật đời thường. |
| `HUMAN_NO_LIPSYNC` | ≥ 60% cảnh có người đang LÀM một hành động cụ thể (đi, kéo, viết, mở, chạy...), nhìn từ sau lưng / bên hông / chỉ thấy đôi tay / đám đông xa. ⛔ KHÔNG cận mặt nhìn thẳng ống kính (không có nhép môi). |
| `HUMAN_WITH_LIPSYNC` | Hệ thống CHƯA hỗ trợ nhép môi → áp dụng đúng quy tắc `HUMAN_NO_LIPSYNC`. |"""

SCENE_FIELDS_BLOCK = """═══ TRƯỜNG CỦA TỪNG CẢNH ═══
- `narration_vn`: lời bình tiếng Việt thuần chữ cho TTS đọc theo RULE #5.
- `subtitle_vn`: phụ đề hiển thị cho mắt đọc lướt (cùng nghĩa với `narration_vn`, ĐƯỢC dùng con số/ký hiệu ngắn gọn như `thế kỷ 9`, `400 năm`, `20%`).
- `visual_source_type`: `"real_photo | stock_video | ai_photo"` — chọn nguồn hình ảnh theo RULE #8 (`real_photo` cho địa danh/nhân vật/di tích/hiện vật/tư liệu thật; `stock_video` cho chuyển động chung; `ai_photo` cho minh họa đời thật khi không có ảnh lưu trữ).
- `real_media_query`: chuỗi 2–6 từ khóa tiếng Anh / tên riêng chuẩn để tìm ảnh thật trên Wikipedia/Wikimedia Commons (tránh từ mơ hồ); để `""` nếu không dùng `real_photo`.
- `image_prompt_en`: 22–40 từ tiếng Anh, MỘT bức ảnh: chủ thể cụ thể + bối cảnh + hành động/trạng thái + cỡ cảnh + ánh sáng/thời điểm. KHÔNG lặp lại `style_anchor_en` (hệ thống sẽ tự gắn). Tuân RULE #1, #2 và `intent_mode` (vẫn viết đầy đủ cho mọi cảnh làm fallback).
- `stock_query_en`: 2–4 từ khoá tiếng Anh để tìm video stock thật (vd "soldiers muddy mountain", "city traffic dusk"). Dùng từ phổ biến, cụ thể, tránh tên riêng.
- `camera`: một trong `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `tilt_up`, `tilt_down`. Chọn theo ý đồ. Không 2 cảnh liền cùng `camera`.
- `overlay_keyword_vn`: 1–3 từ tiếng Việt (IN HOA) hoặc con số/mốc đắt giá (`"1954"`, `"20%"`, `"56 NGÀY ĐÊM"`). Chỉ gắn ở **3–4 cảnh neo** (Hook, Twist, Kết); các cảnh còn lại để `""`.
- `sfx_cue`: một trong `none`, `low_thud`, `subtle_whoosh`, `camera_click`, `wind_swell`, `deep_sub_drop`, `heartbeat_pulse`, `clock_tick_stop`. Chỉ gắn ở **2–3 điểm chuyển nhịp** (Hook, Twist, Kết); các cảnh khác để `"none"`.
- `bgm_energy`: một trong `low`, `rise`, `peak`, `drop`, `calm`. Điều phối năng lượng nhạc theo CAM-WN (vd: Hook `rise`, Build `rise`/`peak`, Twist cắt nhịp đột ngột `drop` hoặc `peak`, Kết lắng `calm`).
- `vocal_delivery`: một trong `punch_urgent` (Hook/cao trào nhanh gọn), `normal_story` (kể chuyện tự nhiên), `whisper_suspense` (chậm, trầm bí ẩn cho Twist), `solemn_slow` (hãm nhịp lắng đọng cho Lời kết đúc kết)."""

BASE_SELF_CHECK_ITEMS = """☐ 8–10 cảnh, 130–185 từ tổng.   ☐ Hook 6–11 từ (Staccato 2 nhịp, đọc < 3s), có 1–2 cảnh Twist 7–12 từ (ưu tiên kết thanh Trắc), Cảnh cuối 10–14 từ có lời kết ngắn gọn (nhận xét + ý nghĩa + đúc kết, hãm nhịp `--`).
☐ `narration_vn` sạch số/ký hiệu/tiếng Anh, ≥ 60% cảnh có động từ giác quan, tránh chuỗi > 5 âm Bằng liền kề; `subtitle_vn` gọn cho mắt đọc.
☐ `style_anchor_en` có bố cục safe-zone 9:16 (chừa 1/3 dưới thoáng tối).
☐ `overlay_keyword_vn` tối đa 3–4 cảnh; `sfx_cue` tối đa 2–3 cảnh; `bgm_energy` & `vocal_delivery` khớp cao trào/hạ nhịp (CAM-WN & LC4MP).
☐ `voice_profile` & `bgm_alignment` nhất quán với `genre` và `music_mood`.
☐ Mỗi `image_prompt_en` khớp `narration_vn`, không từ cấm RULE #2, đúng `intent_mode`.
☐ `visual_source_type` (`real_photo | stock_video | ai_photo`) đúng RULE #8: cảnh có địa danh/nhân vật/di tích/hiện vật thật đã ưu tiên `real_photo` kèm `real_media_query` chuẩn 2–6 từ tiếng Anh/tên riêng (không dùng `real_photo` thì `real_media_query` = `""`).
☐ `camera` không lặp liền kề.   ☐ `closing_takeaway` & `story_moral` đúc kết rõ nhận xét/ý nghĩa; số liệu/tên/mốc nằm trong `claims_to_verify`."""

JSON_OUTPUT_SCHEMA_BLOCK = """═══ ĐỊNH DẠNG ĐẦU RA — CHỈ MỘT JSON OBJECT HỢP LỆ, KHÔNG MARKDOWN ═══
{
  "topic_title": "Tiêu đề 4–9 từ, gây tò mò, không clickbait rỗng",
  "genre": "history_war | history_culture | science_nature | economics_business | psychology_philosophy | true_story_crime | tech_future | lifestyle_motivation",
  "narrative_model": "{selected_model_id}",
  "narrative_model_reason": "1 câu giải thích vì sao triển khai chủ đề này theo `{selected_model_id}`",
  "thinking_process": "(1)... (2)... (3)... (4)...",
  "style_anchor_en": "30–45 words, one cohesive photographic style including upper-center framing and uncluttered darker lower third for captions",
  "voice_profile": "nam_tram_am | nu_hoat_ngon | nu_truyen_cam | ai_hai_huoc",
  "music_mood": "tense_epic | solemn_cinematic | wonder_ambient | driving_modern | reflective_piano | suspense_dark | uplifting_soft",
  "bgm_alignment": "empathetic | anempathetic",
  "scenes": [
    {
      "narration_vn": "...",
      "subtitle_vn": "...",
      "visual_source_type": "real_photo | stock_video | ai_photo",
      "real_media_query": "...",
      "image_prompt_en": "...",
      "stock_query_en": "...",
      "camera": "zoom_in",
      "overlay_keyword_vn": "...",
      "sfx_cue": "none",
      "bgm_energy": "rise",
      "vocal_delivery": "punch_urgent"
    }
  ],
  "closing_takeaway": "1–2 câu lời kết ngắn gọn gồm nhận xét, ý nghĩa và đúc kết cốt lõi của clip (không rao giảng sáo rỗng)",
  "story_moral": "Lời kết đúc kết (nhận xét + ý nghĩa cốt lõi) + caption đăng bài + 3–5 hashtag tiếng Việt",
  "claims_to_verify": ["năm/số liệu/tên riêng cần kiểm tra lại", "..."]
}"""

_TOKENS = (
    "domain_expert_role",
    "domain_expert_lens",
    "user_request",
    "intent_mode",
    "prompt_feedback",
    "filtered_character_context",
    "source_context_block",
    "selected_model_id",
    "selected_model_name",
    "model_selection_rationale",
)
_TOKEN_RE = re.compile(r"\{(" + "|".join(_TOKENS) + r")\}")


def build_model_prompt_template(
    *,
    model_id: str,
    model_name: str,
    group_label: str,
    core_structure: str,
    best_for: str,
    beat_sheet_block: str,
    model_guidance_block: str,
    thinking_process_block: str,
    model_self_check_line: str,
    style_tag: str | None = None,
) -> str:
    """Lắp ráp template hoàn chỉnh cho một mô hình kịch bản độc lập."""
    persona_header = BASE_PERSONA_HEADER
    if style_tag and style_tag.strip():
        clean_style = style_tag.strip()
        if not clean_style.startswith("[STYLE]:"):
            clean_style = f"[STYLE]: {clean_style}"
        persona_header = persona_header.replace(DEFAULT_STYLE_TAG, clean_style, 1)
    structure_section = (
        f"═══ CẤU TRÚC KỊCH BẢN CHUYÊN BIỆT: `{model_id}` — {model_name} ═══\n"
        f"- **Nhóm mục tiêu:** {group_label}\n"
        f"- **Khung cốt lõi:** {core_structure}\n"
        f"- **Phù hợp nhất cho:** {best_for}\n"
        f"- **Quy mô chuẩn:** Tổng **8–10 cảnh**, tổng lời bình `narration_vn` **130–185 từ** (≈ 45–60 giây).\n"
        f"- **Mỗi cảnh phải thêm THÔNG TIN MỚI**, không nhắc lại; xen kẽ cỡ cảnh wide / medium / close / detail / aerial.\n\n"
        f"**Beat Sheet 8–10 cảnh bắt buộc cho `{model_id}`:**\n"
        f"{beat_sheet_block.strip()}\n\n"
        f"**Kỹ thuật đạo diễn & biên kịch đặc thù cho `{model_id}`:**\n"
        f"{model_guidance_block.strip()}"
    )
    self_check_section = (
        "═══ SELF-CHECK TRƯỚC KHI TRẢ JSON (tự kiểm, sai thì sửa luôn) ═══\n"
        f"☐ {model_self_check_line.strip()}\n"
        f"{BASE_SELF_CHECK_ITEMS}"
    )
    return "\n\n".join(
        [
            persona_header,
            CORE_RULES_BLOCK,
            GENRE_DECISION_TABLE,
            INTENT_MODE_RULES_BLOCK,
            structure_section,
            SCENE_FIELDS_BLOCK,
            thinking_process_block.strip(),
            self_check_section,
            JSON_OUTPUT_SCHEMA_BLOCK,
        ]
    )


def format_source_context_block(source_context: str) -> str:
    """Định dạng khối RAG chunk đính kèm khi đầu vào có tư liệu nguồn."""
    if not source_context or not source_context.strip():
        return ""
    return (
        "\n\n═══ TƯ LIỆU SÁCH ĐÃ TRUY XUẤT (RAG CHUNK — BẮT BUỘC BÁM SÁT) ═══\n"
        f"{source_context.strip()}\n"
        "⚠️ Kỷ luật tư liệu: Bắt buộc khai thác đúng tình tiết, nhân vật, hình ảnh ẩn dụ hoặc câu thoại đắt giá từ đoạn sách trên; "
        "KHÔNG bịa tình tiết mâu thuẫn với đoạn sách này, KHÔNG tóm tắt dàn trải cả cuốn sách."
    )


def render_model_prompt_template(
    template: str,
    *,
    model_id: str,
    model_name: str,
    user_request: str,
    intent_mode: str = "NO_HUMAN_BROLL",
    prompt_feedback: str = "",
    filtered_character_context: str = "",
    source_context: str = "",
    rationale: str = "",
    domain_expert_role: str = "",
    domain_expert_lens: str = "",
) -> str:
    """Thay thế token an toàn trên template prompt của một mô hình cụ thể."""
    if not domain_expert_role or not domain_expert_lens:
        from ..narrative_models import select_domain_expert

        expert = select_domain_expert(
            user_request,
            source_context=source_context,
            narrative_model=model_id,
        )
        domain_expert_role = domain_expert_role or expert["expert_role"]
        domain_expert_lens = domain_expert_lens or expert["expert_lens"]
    values = {
        "domain_expert_role": domain_expert_role,
        "domain_expert_lens": domain_expert_lens,
        "user_request": user_request,
        "intent_mode": intent_mode,
        "prompt_feedback": prompt_feedback or "Không có phản hồi lỗi.",
        "filtered_character_context": filtered_character_context or "Không có.",
        "source_context_block": format_source_context_block(source_context),
        "selected_model_id": model_id,
        "selected_model_name": model_name,
        "model_selection_rationale": rationale or f"Triển khai theo cấu trúc chuyên biệt `{model_id}`.",
    }
    return _TOKEN_RE.sub(lambda m: str(values[m.group(1)]), template)
