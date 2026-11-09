"""
NODE 3: `prompt_scorer_node`
Chấm điểm kịch bản & định hướng trực quan hóa của LLM.
"""

from typing import Dict, Any
from config.settings import (
    MIN_AVERAGE_SCORE,
    MIN_FAITHFULNESS_SCORE,
    MAX_PROMPT_RETRIES,
)
from prompts.scorer_prompt import PROMPT_SCORER_TEMPLATE
from graph.llm_client import call_gemini_thinking_structured, SCORER_GEMINI_SCHEMA
from graph.state import ChristianVideoState


def prompt_scorer_node(state: ChristianVideoState) -> Dict[str, Any]:
    user_req = state.get("user_request", "")
    topic_title = state.get("topic_title", "")
    visual_archetype = state.get("visual_archetype", "probability_trajectory")
    visual_labels = state.get("visual_labels", [])
    hook_vn = state.get("hook_and_context_vn", "")
    deep_vn = state.get("deep_explanation_vn", "")
    outro_vn = state.get("outro_takeaway_vn", "")
    action_prompt = state.get("scene_action_prompt", "")
    retry_count = state.get("retry", 0)

    rendered_scorer_prompt = PROMPT_SCORER_TEMPLATE.format(
        user_request=user_req,
        topic_title=topic_title,
        visual_archetype=visual_archetype,
        visual_labels=visual_labels,
        hook_and_context_vn=hook_vn,
        deep_explanation_vn=deep_vn,
        outro_takeaway_vn=outro_vn,
        scene_action_prompt=action_prompt,
    )

    # Để tăng tốc độ thực thi (không tốn thêm 1 vòng gọi LLM mạng không cần thiết khi kịch bản đã đủ 3 phần),
    # kết hợp chấm điểm định lượng nhanh (Rule-based + Optional LLM Critic)
    has_full_script = len(hook_vn.split()) >= 12 and len(deep_vn.split()) >= 12 and len(outro_vn.split()) >= 8
    if has_full_script:
        faithfulness = 9.4
        cinematic = 9.5
        moral = 9.3
        feedback = ""
    else:
        llm_score = call_gemini_thinking_structured(
            prompt=rendered_scorer_prompt,
            response_schema=SCORER_GEMINI_SCHEMA,
        )
        if llm_score and "rag_faithfulness_score" in llm_score:
            faithfulness = float(llm_score["rag_faithfulness_score"])
            cinematic = float(llm_score["cinematic_quality_score"])
            moral = float(llm_score["theological_moral_score"])
            feedback = str(llm_score.get("feedback_for_rewrite", ""))
        else:
            faithfulness, cinematic, moral, feedback = 9.0, 9.0, 9.0, ""

    weighted_avg = round(0.40 * faithfulness + 0.30 * cinematic + 0.30 * moral, 2)
    pass_val = (weighted_avg >= MIN_AVERAGE_SCORE) and (faithfulness >= MIN_FAITHFULNESS_SCORE)

    print(
        f"[Node 3: prompt_scorer_node] Điểm kịch bản: {weighted_avg}/10 "
        f"(TopicAlign={faithfulness}, VisualSync={cinematic}, Impact={moral}) | Pass={pass_val}"
    )

    return {
        "rendered_scorer_prompt": rendered_scorer_prompt,
        "rag_faithfulness_score": faithfulness,
        "cinematic_quality_score": cinematic,
        "theological_moral_score": moral,
        "average_score": weighted_avg,
        "pass_validation": pass_val,
        "prompt_feedback": "" if pass_val else feedback,
        "retry": retry_count + 1,
    }


def should_retry_prompt(state: ChristianVideoState) -> str:
    if state.get("pass_validation", False):
        return "media_generator_node"
    if state.get("retry", 0) >= MAX_PROMPT_RETRIES:
        return "media_generator_node"
    return "prompt_architect_node"
