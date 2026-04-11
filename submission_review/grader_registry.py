"""
Grader registry mirrored at repo root (`../grader_registry.py`) for tooling that
only indexes the environment package directory (e.g. HF Space checkout).
"""

from tasks import TASKS

GRADERS = tuple(
    {"task_id": t["task_id"], "enabled": bool(t.get("grader", {}).get("enabled", True))}
    for t in TASKS
)

TASK_IDS_WITH_GRADERS = [t["task_id"] for t in TASKS if t.get("grader", {}).get("enabled", True)]
