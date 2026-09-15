"""Agent evaluation: scoring, naive baseline, template variants (I6)."""

from agent_eval.scorer import score_payload, run_agent_eval, summarize_results, write_results
from agent_eval.naive_baseline import naive_answer, NAIVE_PROMPT_VERSION

__all__ = [
    "score_payload",
    "run_agent_eval",
    "summarize_results",
    "write_results",
    "naive_answer",
    "NAIVE_PROMPT_VERSION",
]
