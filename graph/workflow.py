"""
Module lắp ghép 5 Nodes vào `StateGraph` (Topic -> Intent Router -> LLM Script & Visual Design -> Scorer Gate -> Audio/Video 30fps Renderer -> Output Judge & TikTok Queue).
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Annotated, get_type_hints, get_origin, get_args

from config.settings import CHECKPOINT_DB_PATH
from graph.state import ChristianVideoState
from graph.nodes.filter_context import filter_context_node
from graph.nodes.intent_router import intent_router_node
from graph.nodes.prompt_architect import prompt_architect_node
from graph.nodes.prompt_scorer import prompt_scorer_node, should_retry_prompt
from graph.nodes.media_generator import media_generator_node
from graph.nodes.visual_judge import visual_judge_and_update_registry_node, should_retry_output_gate

try:
    from langgraph.graph import StateGraph, START, END
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    START = "__start__"
    END = "__end__"

    class SqliteSaver:
        def __init__(self, conn: sqlite3.Connection):
            self.conn = conn
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT PRIMARY KEY,
                    state_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.commit()

        def get(self, thread_id: str) -> Dict[str, Any]:
            cur = self.conn.execute(
                "SELECT state_json FROM checkpoints WHERE thread_id = ?", (thread_id,)
            )
            row = cur.fetchone()
            return json.loads(row[0]) if row else {}

        def put(self, thread_id: str, state: Dict[str, Any]):
            self.conn.execute(
                "INSERT OR REPLACE INTO checkpoints (thread_id, state_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (thread_id, json.dumps(state, ensure_ascii=False)),
            )
            self.conn.commit()

    class CompiledStateGraph:
        def __init__(
            self,
            state_schema: Any,
            nodes: Dict[str, Callable],
            edges: Dict[str, str],
            conditional_edges: Dict[str, Any],
            checkpointer: Optional[SqliteSaver] = None,
        ):
            self.state_schema = state_schema
            self.nodes = nodes
            self.edges = edges
            self.conditional_edges = conditional_edges
            self.checkpointer = checkpointer
            self.reducers = self._extract_reducers(state_schema)

        def _extract_reducers(self, schema: Any) -> Dict[str, Callable]:
            reducers = {}
            hints = get_type_hints(schema, include_extras=True)
            for field_name, field_type in hints.items():
                if get_origin(field_type) is Annotated:
                    args = get_args(field_type)
                    if len(args) >= 2 and callable(args[1]):
                        reducers[field_name] = args[1]
            return reducers

        def invoke(
            self, input_state: Dict[str, Any], config: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            thread_id = "default_thread"
            if config and "configurable" in config:
                thread_id = config["configurable"].get("thread_id", "default_thread")

            current_state = self.checkpointer.get(thread_id) if self.checkpointer else {}

            for k, v in input_state.items():
                if k in self.reducers:
                    current_state[k] = self.reducers[k](current_state.get(k), v)
                else:
                    current_state[k] = v

            curr_node = self.edges.get(START)
            while curr_node and curr_node != END:
                node_fn = self.nodes[curr_node]
                updates = node_fn(current_state) or {}

                for k, v in updates.items():
                    if k in self.reducers:
                        current_state[k] = self.reducers[k](current_state.get(k), v)
                    else:
                        current_state[k] = v

                if curr_node in self.conditional_edges:
                    router_fn, mapping = self.conditional_edges[curr_node]
                    route_key = router_fn(current_state)
                    curr_node = mapping.get(route_key, route_key)
                else:
                    curr_node = self.edges.get(curr_node, END)

            if self.checkpointer:
                self.checkpointer.put(thread_id, current_state)

            return current_state

    class StateGraph:
        def __init__(self, state_schema: Any):
            self.state_schema = state_schema
            self.nodes: Dict[str, Callable] = {}
            self.edges: Dict[str, str] = {}
            self.conditional_edges: Dict[str, Any] = {}

        def add_node(self, name: str, fn: Callable):
            self.nodes[name] = fn

        def add_edge(self, start_key: str, end_key: str):
            self.edges[start_key] = end_key

        def add_conditional_edges(
            self, source: str, path: Callable, path_map: Dict[str, str]
        ):
            self.conditional_edges[source] = (path, path_map)

        def compile(
            self, checkpointer: Optional[SqliteSaver] = None
        ) -> CompiledStateGraph:
            return CompiledStateGraph(
                self.state_schema,
                self.nodes,
                self.edges,
                self.conditional_edges,
                checkpointer,
            )


def create_christian_short_video_app(
    checkpoint_db_path: Optional[Path] = None,
):
    """Khởi tạo StateGraph Topic-to-Video Agentic Pipeline."""
    db_file = Path(checkpoint_db_path or CHECKPOINT_DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    builder = StateGraph(ChristianVideoState)

    builder.add_node("filter_context_node", filter_context_node)
    builder.add_node("intent_router_node", intent_router_node)
    builder.add_node("prompt_architect_node", prompt_architect_node)
    builder.add_node("prompt_scorer_node", prompt_scorer_node)
    builder.add_node("media_generator_node", media_generator_node)
    builder.add_node(
        "visual_judge_and_update_registry_node", visual_judge_and_update_registry_node
    )

    builder.add_edge(START, "filter_context_node")
    builder.add_edge("filter_context_node", "intent_router_node")
    builder.add_edge("intent_router_node", "prompt_architect_node")
    builder.add_edge("prompt_architect_node", "prompt_scorer_node")

    builder.add_conditional_edges(
        "prompt_scorer_node",
        should_retry_prompt,
        {
            "prompt_architect_node": "prompt_architect_node",
            "media_generator_node": "media_generator_node",
        },
    )

    builder.add_edge("media_generator_node", "visual_judge_and_update_registry_node")
    builder.add_conditional_edges(
        "visual_judge_and_update_registry_node",
        should_retry_output_gate,
        {
            "media_generator_node": "media_generator_node",
            "done": END,
        },
    )

    sqlite_conn = sqlite3.connect(str(db_file), check_same_thread=False)
    checkpointer = SqliteSaver(sqlite_conn)

    return builder.compile(checkpointer=checkpointer)
