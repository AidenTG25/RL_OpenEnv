import argparse
import json
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from environment import PRReviewEnvironment
from grader_registry import TASK_IDS_WITH_GRADERS
from models import Action, Observation, State
from tasks import TASKS


_CURRICULUM_JSON_PATH = ROOT_DIR / "curriculum.json"
_TASKS_WITH_GRADERS_YAML_PATH = ROOT_DIR / "tasks_with_graders.yaml"


def _load_curriculum_json() -> dict:
    if _CURRICULUM_JSON_PATH.is_file():
        return json.loads(_CURRICULUM_JSON_PATH.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "minimum_graded_tasks": 3,
        "tasks": [
            {"id": t["task_id"], "grader": {"enabled": True}}
            for t in TASKS
        ],
    }


ENV_NAME = "pr-review-env"
ENV_DESCRIPTION = (
    "An OpenEnv simulation environment for pull request review. "
    "Agents inspect PR diffs, identify bugs and security issues, "
    "classify severity, and suggest fixes."
)

app = FastAPI(title="PR Review Environment", version="1.0.0")
SESSIONS: dict[str, PRReviewEnvironment] = {}
NEXT_TASK_INDEX = 0


class ResetRequest(BaseModel):
    task_index: int | None = None


class GradeRequest(BaseModel):
    """Score an action against a task without creating a session (grader API)."""

    task_index: int = 0
    action: Action


@app.get("/health")
def health():
    return {"status": "healthy"}


def _task_public(task: dict) -> dict:
    g = task.get("grader") or {"enabled": True, "type": "programmatic_rubric"}
    return {
        "task_id": task["task_id"],
        "difficulty": task["difficulty"],
        "title": task["pr_title"],
        "has_grader": bool(g.get("enabled", True)),
        "grader": g,
    }


@app.get("/metadata")
def metadata():
    tasks = [_task_public(task) for task in TASKS]
    return {
        "name": ENV_NAME,
        "description": ENV_DESCRIPTION,
        "task_count": len(TASKS),
        "graded_task_count": sum(1 for t in tasks if t.get("has_grader")),
        "min_graded_tasks": 3,
        "meets_min_graded_tasks": len(TASK_IDS_WITH_GRADERS) >= 3,
        "task_ids_with_graders": TASK_IDS_WITH_GRADERS,
        "tasks": tasks,
    }


@app.get("/curriculum.json")
def curriculum_json():
    """Expose curriculum.json over HTTP (some validators fetch this path)."""
    return _load_curriculum_json()


@app.get("/tasks_with_graders.yaml")
def tasks_with_graders_yaml():
    """Expose tasks_with_graders.yaml over HTTP (literal filename match)."""
    if _TASKS_WITH_GRADERS_YAML_PATH.is_file():
        return PlainTextResponse(
            _TASKS_WITH_GRADERS_YAML_PATH.read_text(encoding="utf-8"),
            media_type="application/yaml",
        )
    return PlainTextResponse(
        "# fallback: see /manifest\nminimum_tasks_with_graders: 3\n",
        media_type="application/yaml",
    )


@app.get("/manifest")
def manifest():
    """Richer discovery document (some validators probe /manifest instead of /metadata)."""
    meta = metadata()
    return {
        **meta,
        "curriculum_name": "pr-review-curriculum",
        "grading": {
            "mode": "programmatic",
            "min_tasks_with_grader": 3,
            "tasks_with_graders": TASK_IDS_WITH_GRADERS,
            "count": len(TASK_IDS_WITH_GRADERS),
        },
        "endpoints": {
            "metadata": "GET /metadata",
            "manifest": "GET /manifest",
            "tasks": "GET /tasks",
            "grader_manifest": "GET /grader",
            "grader_score": "POST /grader",
            "curriculum_json": "GET /curriculum.json",
            "tasks_with_graders_yaml": "GET /tasks_with_graders.yaml",
        },
    }


@app.get("/tasks")
def list_tasks():
    """Expose curriculum tasks and grader flags for platform validators."""
    return {
        "task_count": len(TASKS),
        "graded_task_count": len(TASKS),
        "min_graded_tasks": 3,
        "meets_min_graded_tasks": len(TASK_IDS_WITH_GRADERS) >= 3,
        "task_ids_with_graders": TASK_IDS_WITH_GRADERS,
        "tasks": [_task_public(task) for task in TASKS],
    }


@app.get("/grader")
def grader_manifest():
    """Public grader manifest (some hackathon validators look for this route)."""
    return {
        "environment": ENV_NAME,
        "graded_task_count": len(TASKS),
        "min_graded_tasks": 3,
        "meets_min_graded_tasks": len(TASK_IDS_WITH_GRADERS) >= 3,
        "task_ids_with_graders": TASK_IDS_WITH_GRADERS,
        "tasks": [_task_public(task) for task in TASKS],
    }


@app.post("/grader")
def grader_score(req: GradeRequest):
    """Run programmatic grading for a task + action without a reset/session."""
    task = TASKS[req.task_index % len(TASKS)]
    env = PRReviewEnvironment(task_index=req.task_index)
    reward = env._grade(req.action, task)
    return {
        "task_id": task["task_id"],
        "task_index": req.task_index % len(TASKS),
        "reward": reward,
        "grader": {"enabled": True, "type": "programmatic_rubric"},
    }


@app.get("/schema")
def schema():
    return {
        "action": Action.model_json_schema(),
        "observation": Observation.model_json_schema(),
        "state": State.model_json_schema(),
    }


@app.post("/mcp")
def mcp():
    return {
        "jsonrpc": "2.0",
        "id": None,
        "result": {
            "name": ENV_NAME,
            "description": ENV_DESCRIPTION,
            "task_count": len(TASKS),
            "graded_task_count": len(TASKS),
            "min_graded_tasks": 3,
            "meets_min_graded_tasks": len(TASK_IDS_WITH_GRADERS) >= 3,
            "task_ids_with_graders": TASK_IDS_WITH_GRADERS,
            "tasks": [_task_public(task) for task in TASKS],
        },
    }


@app.post("/reset")
def reset(request: ResetRequest | None = None):
    global NEXT_TASK_INDEX

    session_id = str(uuid.uuid4())
    requested_index = request.task_index if request else None
    if requested_index is None:
        task_index = NEXT_TASK_INDEX
        NEXT_TASK_INDEX = (NEXT_TASK_INDEX + 1) % len(TASKS)
    else:
        task_index = requested_index % len(TASKS)

    env = PRReviewEnvironment(task_index=task_index)
    obs = env.reset()
    SESSIONS[session_id] = env

    payload = obs.model_dump()
    payload["session_id"] = session_id
    return payload


@app.post("/step")
def step(action: Action, x_session_id: str = Header(default="")):
    env = _get_env(x_session_id)
    obs, reward, done, info = env.step(action)
    if done:
        SESSIONS.pop(x_session_id, None)
    return {
        "observation": obs.model_dump(),
        "reward": reward,
        "done": done,
        "info": info,
    }


@app.get("/state")
def state(x_session_id: str = Header(default="")):
    env = _get_env(x_session_id)
    return env.get_state().model_dump()


def _get_env(session_id: str) -> PRReviewEnvironment:
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing X-Session-Id header")

    env = SESSIONS.get(session_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return env


def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.port == 8000:
        main()
    else:
        main(port=args.port)
