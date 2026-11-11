"""
NODE 1.5: `intent_router_node` (Python thuần - 0 Token)
Quyết định chế độ hình ảnh theo ý định người dùng (3 router trong `wav2vid.md`):
  - NO_HUMAN_BROLL     : video không người (tư liệu, vật thể, địa điểm) + giọng đọc.
  - HUMAN_NO_LIPSYNC   : có người làm hành động minh hoạ + giọng đọc, không nhép môi.
  - HUMAN_WITH_LIPSYNC : người nói trực diện, nhép môi đúng tiếng.

Ưu tiên: `state["intent_mode"]` do người dùng chọn (CLI `--mode`) > suy luận từ từ khoá trong chủ đề > mặc định NO_HUMAN_BROLL.
LƯU Ý TRUNG THỰC: nhánh render nhép môi CHƯA được cài đặt. Khi chọn HUMAN_WITH_LIPSYNC, hệ thống ghi rõ
`intent_notes` và render như HUMAN_NO_LIPSYNC (`effective_intent_mode`) thay vì giả vờ có lipsync.
"""

from typing import Dict, Any

from graph.state import ChristianVideoState

VALID_MODES = ("NO_HUMAN_BROLL", "HUMAN_NO_LIPSYNC", "HUMAN_WITH_LIPSYNC")

_LIPSYNC_HINTS = ("mc dẫn", "người dẫn", "avatar", "nhép môi", "lipsync", "nói trực diện", "talking head", "host")
_HUMAN_HINTS = ("chân dung", "người lính", "công nhân", "nông dân", "câu chuyện", "chàng trai", "cuộc đời", "cảm xúc", "gia đình", "nhân vật")


def _infer_mode(topic: str) -> str:
    low = topic.lower()
    if any(k in low for k in _LIPSYNC_HINTS):
        return "HUMAN_WITH_LIPSYNC"
    if any(k in low for k in _HUMAN_HINTS):
        return "HUMAN_NO_LIPSYNC"
    return "NO_HUMAN_BROLL"


def intent_router_node(state: ChristianVideoState) -> Dict[str, Any]:
    topic = state.get("user_request", "")
    requested = str(state.get("intent_mode", "") or "").strip().upper()
    if requested in VALID_MODES:
        mode, source = requested, "người dùng chọn"
    else:
        mode, source = _infer_mode(topic), "tự suy ra từ chủ đề"

    notes = f"Chế độ {mode} ({source})."
    effective = mode
    if mode == "HUMAN_WITH_LIPSYNC":
        effective = "HUMAN_NO_LIPSYNC"
        notes += " Nhánh nhép môi chưa được cài đặt -> render như HUMAN_NO_LIPSYNC (không có nhép môi)."

    print(f"[Node 1.5: intent_router_node] {notes} | effective={effective}")
    return {"intent_mode": mode, "effective_intent_mode": effective, "intent_notes": notes}

