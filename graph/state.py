"""
Định nghĩa State của LangGraph (`ChristianVideoState`), hàm Reducer (`character_registry_reducer`),
và các Structured Output Schemas cho hệ thống Topic-to-Video Agentic Pipeline.
"""

from typing import TypedDict, Annotated, Dict, List, Optional, Any

try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def dict(self):
            return self.__dict__

    def Field(default=None, default_factory=None, **kwargs):
        return default_factory() if default_factory is not None else default


class NewCharacterItemSchema(BaseModel):
    key_name: str = Field(default="unknown")
    aliases: List[str] = Field(default_factory=list)
    visual_traits: str = Field(default="")


class SceneSchema(BaseModel):
    narration_vn: str = Field(default="")
    subtitle_vn: str = Field(default="")
    image_prompt_en: str = Field(default="")
    stock_query_en: str = Field(default="")
    camera: str = Field(default="zoom_in")
    overlay_keyword_vn: str = Field(default="")
    sfx_cue: str = Field(default="none")


class PromptArchitectOutput(BaseModel):
    topic_title: str = Field(default="")
    genre: str = Field(default="")
    narrative_model: str = Field(default="abt")
    narrative_model_reason: str = Field(default="")
    thinking_process: str = Field(default="")
    style_anchor_en: str = Field(default="")
    music_mood: str = Field(default="")
    scenes: List[SceneSchema] = Field(default_factory=list)
    story_moral: str = Field(default="")
    claims_to_verify: List[str] = Field(default_factory=list)


class JudgeScoreOutput(BaseModel):
    hook_score: float = Field(default=0.0)
    visual_match_score: float = Field(default=0.0)
    story_score: float = Field(default=0.0)
    average_score: float = Field(default=0.0)
    pass_validation: bool = Field(default=False)
    feedback_for_rewrite: str = Field(default="")


class VisualScoreMetrics(TypedDict):
    clip_prompt_score: float
    continuity_score: float
    identity_pose_score: float
    sharpness_score: float
    visual_total_score: float
    failure_reason: Optional[str]


class OutputScoreMetrics(TypedDict):
    lse_c: float
    lse_d: float
    av_offset_frames: int
    mouth_sharp_ratio: float
    bbox_jitter_px: float
    output_total_score: float
    failure_reason: Optional[str]


class CharacterProfile(TypedDict):
    key_name: str
    name: str
    aliases: List[str]
    visual_traits: str
    reference_image_url: str
    seed: int


def character_registry_reducer(
    existing: Optional[Dict[str, CharacterProfile]],
    updates: Optional[Dict[str, CharacterProfile]],
) -> Dict[str, CharacterProfile]:
    registry = dict(existing) if existing else {}
    if updates:
        for char_key, profile in updates.items():
            key = char_key.lower().strip()
            if key not in registry:
                registry[key] = profile
            else:
                registry[key] = {**registry[key], **profile}
    return registry


def error_logs_reducer(
    existing: Optional[List[str]],
    updates: Optional[List[str]],
) -> List[str]:
    logs = list(existing) if existing else []
    if updates:
        logs.extend(str(x) for x in updates if x)
    return logs


class ChristianVideoState(TypedDict):
    user_request: str
    intent_mode: str  # NO_HUMAN_BROLL | HUMAN_NO_LIPSYNC | HUMAN_WITH_LIPSYNC (người dùng chọn hoặc router tự suy ra)
    effective_intent_mode: str  # chế độ thực sự được render (LIPSYNC chưa hỗ trợ -> HUMAN_NO_LIPSYNC)
    intent_notes: str
    characters: Annotated[Dict[str, CharacterProfile], character_registry_reducer]

    # Node 1 (`filter_context_node` + Book RAG QueryRewriter)
    book_id: str
    book_chunk_idx: int
    book_chunk_id: int
    rag_relevance_score: float
    rag_retry_count: int
    rag_tried_chunk_ids: List[int]
    rag_search_query: str
    detected_characters: List[str]
    filtered_character_context: str
    known_reference_urls: List[str]

    # Node 2 (`prompt_architect_node` - LLM tự lên kịch bản 3 phần + Thiết kế đồ họa Manim)
    topic_title: str
    scripture_reference: str
    retrieved_scripture: str
    visual_archetype: str
    visual_labels: List[str]
    rendered_architect_prompt: str
    thinking_process: str
    scene_action_prompt: str
    hook_and_context_vn: str
    deep_explanation_vn: str
    outro_takeaway_vn: str
    story_moral: str
    new_characters: Dict[str, CharacterProfile]
    genre: str
    preferred_narrative_model: str
    narrative_model: str
    narrative_model_reason: str
    style_anchor_en: str
    music_mood: str
    scenes: List[Dict[str, Any]]
    claims_to_verify: List[str]

    # Node 3 (`prompt_scorer_node`)
    rendered_scorer_prompt: str
    rag_faithfulness_score: float
    script_groundedness_score: float
    cinematic_quality_score: float
    theological_moral_score: float
    average_score: float
    pass_validation: bool
    prompt_feedback: str
    retry_target: str
    retry: int

    # Node 4 (`media_generator_node`)
    video_generation_mode: str
    final_prompt: str
    generated_media_url: str
    active_seed: int
    scene_narration_vn: str
    outro_reflection_vn: str
    closing_prayer_vn: str
    voiceover_wav_path: str
    subtitles_ass_path: str
    prepped_visual_path: str
    final_master_video_path: str
    audio_duration_sec: float
    audio_sync_features: Dict[str, Any]
    prev_scene_frame_path: str
    continuity_harmonized: bool
    visual_scores: VisualScoreMetrics
    asset_report: Dict[str, Any]

    # Node 5 (`visual_judge_and_update_registry_node`)
    face_similarity_score: float
    wav2lip_pads: List[int]
    face_restored_applied: bool
    output_scores: OutputScoreMetrics
    tiktok_publish_status: str
    tiktok_caption: str
    visual_retry_count: int
    last_completed_node: str
    run_status: str
    error_logs: Annotated[List[str], error_logs_reducer]
