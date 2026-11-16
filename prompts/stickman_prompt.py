"""
STICKMAN VIDEO DIRECTOR PROMPT — FULL INTEGRATION
Tích hợp trực tiếp từ kho mã nguồn `external/stickman-video-director` (kaomei).
Hỗ trợ đầy đủ 6 Phong cách Chuẩn (Style 1 đến Style 5) với Character DNA Lock & Anti-Deformation.
"""

from typing import Dict, Any

# =====================================================================
# BỘ CATALOG PHONG CÁCH CHUẨN TỪ `stickman-video-director`
# =====================================================================
OFFICIAL_STICKMAN_STYLES: Dict[str, Dict[str, str]] = {
    "amber_noir": {
        "name": "Style 6: Amber Noir / 暖金暗影风 (Git Sample Model: Veo 3.1 Fast, 720p)",
        "dna": (
            "A6 illustrated stickman animation: compact matte-black round heads, connected short black necks, "
            "small cream-white eye marks and a compact line mouth, simplified black stick limbs with clean readable silhouette. "
            "Layered two-dimensional illustrated world with angular drawn contours, restrained cel shading, warm amber illumination and dramatic deep plum shadows. "
            "Cinematic 2D animation, moody atmospheric lighting, 9:16 vertical composition. "
            "Strictly no glossy 3D rendering, no realistic human faces, no photoreal skin, no speech bubbles, no text, no watermark."
        ),
    },
    "modern_tech": {
        "name": "Style 2A: Modern Studio Tech (Apple-style 极简科技风)",
        "dna": (
            "A minimalist 2D animated stick figure wearing a bright red beanie (smooth rounded knit, no pom-pom) "
            "and a yellow t-shirt, with simple black stick limbs and shorts. Simple black lines, vibrant colors, smooth 2D animation style. "
            "in a modern bright white studio space with subtle light-gray perspective grid lines on the floor plane. "
            "High-key studio lighting, clean white negative space, sleek glowing cyan and electric blue glass holographic UI elements. "
            "9:16 vertical composition, clean negative space. "
            "Negative constraints: strictly minimalist studio aesthetic, no circuit board textures, no sci-fi wall panels, no spaceship corridors, no cracked concrete, no grunge textures, no photorealistic human skin, no speech bubbles, no dialogue text boxes, no text, no watermark."
        ),
    },
    "modern_story": {
        "name": "Style 2B: Modern Beanie Cinematic Story (彩色故事风)",
        "dna": (
            "A minimalist 2D animated stick figure wearing a bright red beanie and a yellow t-shirt, simple black stick limbs, "
            "staged inside rich environmental cinematic lighting, full-color 2D narrative background, clean 2D animation aesthetic. "
            "9:16 vertical composition, no text, no watermark, no realistic human faces."
        ),
    },
    "classic_dark": {
        "name": "Style 1 Dark: Classic Minimalist Dark Theme (Đen tuyền - Điểm nhấn Neon)",
        "dna": (
            "Minimalist two-dimensional white line animation on a flat uniform pitch-black canvas. "
            "Consistent stick figure with a hollow circular head, simple line expressions, connected line limbs, uniform medium line weight. "
            "The figure stays white line art; vivid red and electric blue saturated neon accent colors on props and effects. "
            "Clean negative space, 9:16 vertical, strictly no gray tint, no gradients, no 3D depth, no text, no watermark."
        ),
    },
    "classic_light": {
        "name": "Style 1 Light: Classic Minimalist Light Theme (MinutePhysics / Casually Explained)",
        "dna": (
            "Minimalist two-dimensional black line animation on a flat digitally pure-white canvas. "
            "Consistent stick figure with a hollow circular head, simple line expressions, connected line limbs, uniform medium line weight. "
            "The figure stays black ink line art; maximum 2 saturated accent colors on props. "
            "Clean negative space, 9:16 vertical, strictly no shadows, no paper texture, no gradients, no 3D depth, no text, no watermark."
        ),
    },
    "historical": {
        "name": "Style 5: Historical Cartoon (Lịch sử châm biếm / Hào hùng)",
        "dna": (
            "Historical cartoon stickman illustration, full-color painterly historical setting with clean cel shading, "
            "white filled round heads with connected short white necks, expressive faces, solid black oval eyes, "
            "thin black stick limbs, wearing iconic era-specific historical hats, uniforms and gear, vintage comic aesthetic, "
            "muted retro color palette with bold outlines, clean 9:16 vertical composition, no realism, no 3D render, no text, no watermark."
        ),
    },
    "cozy": {
        "name": "Style 4: Cozy Storytelling (治愈故事风 - Kể chuyện sâu lắng)",
        "dna": (
            "Cozy storytelling 2D cartoon style, expressive minimalist white filled characters with dark stick limbs, "
            "full-color warm atmospheric 2D cartoon environment, gentle lighting, cinematic composition, "
            "9:16 vertical, heartwarming and relatable visual tone, no text, no watermark."
        ),
    },
    "prehistoric": {
        "name": "Style 3: Prehistoric Dark Comedy (Hài hước tiền sử)",
        "dna": (
            "Prehistoric hand-drawn stick figure cartoon, earthy prehistoric background, subtle texture, "
            "white filled heads, expressive cartoon faces, black stick limbs, animal-hide costume, humorous visual analogies, "
            "9:16 vertical, no text, no watermark."
        ),
    },
}

# Alias mapping cho linh hoạt khi người dùng gõ cờ
STYLE_ALIAS = {
    "amber_noir": "amber_noir",
    "amber": "amber_noir",
    "noir": "amber_noir",
    "6": "amber_noir",
    "a6": "amber_noir",
    "style6": "amber_noir",
    "modern_pop": "modern_tech",
    "modern": "modern_tech",
    "tech": "modern_tech",
    "2a": "modern_tech",
    "story": "modern_story",
    "2b": "modern_story",
    "classic": "classic_dark",
    "classic_bw": "classic_dark",
    "dark": "classic_dark",
    "light": "classic_light",
    "1": "classic_dark",
    "historical_cartoon": "historical",
    "history": "historical",
    "5": "historical",
    "cozy_storytelling": "cozy",
    "4": "cozy",
    "3": "prehistoric",
}


def resolve_style_info(style_name: str) -> Dict[str, str]:
    normalized = style_name.strip().lower()
    target_key = STYLE_ALIAS.get(normalized, normalized)
    if target_key in OFFICIAL_STICKMAN_STYLES:
        return OFFICIAL_STICKMAN_STYLES[target_key]
    return OFFICIAL_STICKMAN_STYLES["amber_noir"]


STICKMAN_DIRECTOR_SYSTEM_INSTRUCTION = """Bạn là một ĐẠO DIỄN PHIM HOẠT HÌNH NGƯỜI QUE (Stickman Video Director) chuyên nghiệp hàng đầu cho TikTok và YouTube Shorts (chuẩn theo kiến trúc `kaomei/stickman-video-director`).

Nhiệm vụ của bạn là chuyển hóa bất kỳ chủ đề nào thành một kịch bản phân cảnh Người Que với 5 giai đoạn cảm xúc (Golden Hook -> Phá vỡ định kiến -> Hé lộ bí mật -> Chân lý cốt lõi -> Đúc kết sâu cay).

QUY TẮC BẮT BUỘC:
1. ẨN DỤ TRỰC QUAN (Visual Metaphors):
   - Không vẽ cảnh tả thực phức tạp. Luôn biến ý niệm trừu tượng thành hành động của Người Que và đạo cụ phóng đại:
     * Sự kiêu ngạo / ảo tưởng quyền lực: Người que đội vương miện khổng lồ nặng trĩu làm gãy lưng.
     * Vây hãm / áp lực khổng lồ: Người que đứng giữa vòng tròn các mũi tên chỉ vào, giơ khiên nhỏ đỡ.
     * Kéo pháo / nỗ lực phi thường: Người que gồng mình kéo sợi dây thừng nối với cỗ pháo to như quả núi.
     * Chiến thắng / bước ngoặt: Người que cắm cờ đỏ sao vàng trên đỉnh đồi, hai tay giơ cao ăn mừng.
2. NHỊP ĐIỆU (Pacing):
   - Phân chia thành 5 đến 7 cảnh ngắn (~4 đến 6 giây/cảnh, tổng thời lượng 25 - 40 giây).
   - Lời đọc (narration_vn): Tiếng Việt sắc sảo, dồn dập, gãy gọn, giàu hình ảnh, đúng nhịp điệu viral Shorts.
3. SOUND EFFECTS (SFX):
   - Chọn SFX chính xác cho từng cảnh: `pop`, `low_thud`, `deep_sub_drop`, `subtle_whoosh`, `camera_click`, `clock_tick_stop`, `heartbeat_pulse`.
4. KHUNG HÌNH DỌC 9:16 & PROMPT TIẾNG ANH 100%:
   - Tất cả prompt tạo hình ảnh/video (`image_prompt_en`) PHẢI được viết 100% bằng tiếng Anh thuần túy, miêu tả rõ hành động của Người Que và đạo cụ ẩn dụ trực quan (ví dụ: "stickman in orange hoodie examining a giant glowing amber balance scale and leather-bound ledgers").
   - TUYỆT ĐỐI KHÔNG để bất kỳ từ tiếng Việt nào lọt vào trường `image_prompt_en` (chỉ viết tiếng Việt trong `narration_vn` và `visual_concept`).

Định dạng trả về duy nhất 1 JSON Object hợp lệ theo schema.
"""

STICKMAN_GEMINI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "topic_title": {"type": "STRING"},
        "chosen_style": {"type": "STRING"},
        "style_anchor_en": {"type": "STRING"},
        "music_mood": {"type": "STRING", "enum": ["cinematic_piano_ambient", "curious_quirky_acoustic", "intense_epic_drums", "dark_mystery_synth"]},
        "scenes": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "scene_idx": {"type": "INTEGER"},
                    "narration_vn": {"type": "STRING", "description": "Lời thuyết minh tiếng Việt cho cảnh (1-2 câu ngắn)"},
                    "visual_concept": {"type": "STRING", "description": "Ý tưởng ẩn dụ trực quan"},
                    "stickman_action": {"type": "STRING", "description": "Hành động và biểu cảm cụ thể của người que"},
                    "image_prompt_en": {"type": "STRING", "description": "Prompt tiếng Anh vẽ ảnh stickman"},
                    "sfx_cue": {"type": "STRING", "enum": ["pop", "subtle_whoosh", "camera_click", "deep_sub_drop", "heartbeat_pulse", "clock_tick_stop", "low_thud", "none"]},
                    "camera_motion": {"type": "STRING", "enum": ["pop_zoom", "zoom_in", "zoom_out", "pan_left", "pan_right", "shake"]},
                },
                "required": ["scene_idx", "narration_vn", "visual_concept", "image_prompt_en", "sfx_cue", "camera_motion"],
            },
        },
        "tiktok_caption": {"type": "STRING"},
    },
    "required": ["topic_title", "chosen_style", "style_anchor_en", "scenes", "tiktok_caption"],
}


def render_stickman_director_prompt(topic: str, style: str = "modern_tech") -> str:
    style_info = resolve_style_info(style)
    return f"""CHỦ ĐỀ VIDEO: {topic}

PHONG CÁCH CHỌN TỪ REPO GỐC: {style_info['name']}
ĐẶC ĐIỂM HÌNH ẢNH (DNA ANCHOR):
{style_info['dna']}

Hãy đóng vai Đạo diễn Phim hoạt hình Người Que (Stickman Video Director) và thiết kế một kịch bản phân cảnh 9:16 (5 đến 7 cảnh) xuất sắc nhất cho chủ đề trên.
Mỗi cảnh phải có lời thuyết minh tiếng Việt ngắn gọn, đắt giá và một prompt vẽ ảnh người que (image_prompt_en) sử dụng ẩn dụ trực quan (visual metaphor) sáng tạo.
Trả về định dạng JSON thuần túy theo schema.
"""
