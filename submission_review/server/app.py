import argparse
import sys
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from environment import PRReviewEnvironment
from models import Action, Observation, State


ENV_NAME = "pr-review-env"
ENV_DESCRIPTION = (
    "An OpenEnv simulation environment for pull request review. "
    "Agents inspect PR diffs, identify bugs and security issues, "
    "classify severity, and suggest fixes."
)

app = FastAPI(title="PR Review Environment", version="1.0.0")
SESSIONS: dict[str, PRReviewEnvironment] = {}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/metadata")
def metadata():
    return {
        "name": ENV_NAME,
        "description": ENV_DESCRIPTION,
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
        },
    }


@app.post("/reset")
def reset():
    session_id = str(uuid.uuid4())
    env = PRReviewEnvironment()
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
