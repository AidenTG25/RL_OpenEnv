# PR Review Environment

An OpenEnv reinforcement learning environment where an AI agent acts as a senior software engineer reviewing pull requests.

## Motivation

Code review is one of the most critical — and cognitively demanding — tasks in software engineering. This environment trains agents to identify bugs, security vulnerabilities, and logic errors in real-world style code diffs, with graded difficulty and partial reward signals.

## Environment Description

The agent receives a pull request (title, description, code diff) and must:
- Identify all bugs/issues introduced by the PR
- Classify overall severity (low / medium / high)
- Suggest a concrete fix for the most critical issue
- Avoid false positives (flagging correct code as buggy)

## Action Space

| Field | Type | Description |
|---|---|---|
| `bugs_found` | `List[str]` | List of bugs identified |
| `severity` | `str` | `low`, `medium`, or `high` |
| `suggested_fix` | `str` | Concrete fix for the critical issue |
| `false_positive` | `bool` | True if agent believes code is correct |

## Observation Space

| Field | Type | Description |
|---|---|---|
| `pr_title` | `str` | Title of the pull request |
| `pr_description` | `str` | Description of PR intent |
| `code_diff` | `str` | Code changes introduced |
| `task_difficulty` | `str` | `easy`, `medium`, or `hard` |
| `instructions` | `str` | Agent instructions |

## Tasks

| Task | Difficulty | Issue Type | Description |
|---|---|---|---|
| Age Validation PR | Easy | Logic bug | Off-by-one in age check (`>` vs `>=`) |
| Discount Calculator PR | Medium | Logic + data handling | Index out of bounds + transaction logging |
| Login Endpoint PR | Hard | Security | SQL injection + weak MD5 hashing + no rate limiting |
| Dashboard Cache PR | Hard | Security + multi-file diff | Broken tenant scoping + cache key issues |

## Reward Function

Each task is scored 0.0–1.0 based on:
- **Issue detection** (0.45) — issue-level matching against expected bugs
- **Severity classification** (0.20) — exact match, partial credit for adjacent severity
- **Fix quality** (0.25) — fix guidance for the critical issue
- **Completeness bonus** (0.10) — awarded when all expected issues are found
- **Precision penalty** — unsupported bug claims reduce score
- **False positive penalty** — returns 0.0 if the agent claims the PR is clean when it is not

## Setup

```bash
# Install dependencies
pip install "open-env-core[cli]" uvicorn fastapi openai

# Build Docker image
docker build -t pr-review-env .

# Run environment
docker run -p 8000:8000 pr-review-env
```

`POST /reset` now returns a `session_id`. Send that value back on `POST /step` and `GET /state`
as the `X-Session-Id` header so each evaluation episode is isolated.

For local development, run:

```bash
python server/app.py
```

OpenEnv runtime endpoints exposed by the server:

- `GET /health`
- `GET /metadata`
- `GET /schema`
- `POST /mcp`
- `POST /reset`
- `POST /step`
- `GET /state`

## Running Inference

```bash
export HF_TOKEN="insert key here"
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export API_BASE_URL=https://router.huggingface.co/v1
export ENV_URL=http://localhost:8000

python inference.py
```

## Baseline Scores

| Task | Expected Reward |
|---|---|
| Easy (age validation) | 0.7 – 0.9 |
| Medium (discount calculator) | 0.5 – 0.8 |
| Hard (login security) | 0.4 – 0.7 |
| Hard (dashboard cache) | 0.3 – 0.6 |
