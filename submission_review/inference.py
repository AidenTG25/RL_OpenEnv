import json
import os

import requests
from openai import OpenAI


API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:8000")
TASK_NAME = os.environ.get("TASK_NAME", "pr-review-curriculum")
BENCHMARK = os.environ.get("BENCHMARK", "pr-review-env")
TOTAL_TASKS = int(os.environ.get("TOTAL_TASKS", "4"))

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

SYSTEM_PROMPT = """\
You are a senior software engineer conducting a pull request code review.

You will be given a PR title, description, and code diff.
Your job is to identify all bugs, security issues, and logic errors.

Priorities:
- Only report issues that are directly supported by the diff.
- Prefer concrete code-level findings over speculative infrastructure concerns.
- Treat authorization, tenant isolation, cross-account data exposure, SQL injection,
  weak credential handling, and brute-force risk as high-severity issues.
- For loops over lists or arrays, explicitly check for off-by-one errors,
  out-of-range indexing, and incorrect use of len(...)+1.
- For caching changes, check whether user-controlled identifiers can expose another
  account's data or break tenant scoping.
- For auth/login changes, check for SQL injection, weak hashing/token generation,
  plaintext password handling, and missing rate limiting.

Respond only with a valid JSON object in this exact format:
{
  "bugs_found": ["<description of bug 1>", "<description of bug 2>"],
  "severity": "low" | "medium" | "high",
  "suggested_fix": "<concrete fix for the most critical issue>",
  "false_positive": false
}

Rules:
- bugs_found must be a list of strings
- severity must be exactly one of: low, medium, high
- suggested_fix must be a specific, actionable fix
- false_positive: set to true only if the code is genuinely correct
- Do not include speculative deployment issues unless the diff explicitly shows them.
"""


def call_llm(obs: dict) -> dict:
    user_msg = (
        f"PR Title: {obs['pr_title']}\n\n"
        f"PR Description: {obs['pr_description']}\n\n"
        f"Code Diff:\n```\n{obs['code_diff']}\n```\n\n"
        "Review this PR and respond with the required JSON."
    )
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=800,
        temperature=0.0,
    )
    raw = response.choices[0].message.content.strip()

    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            try:
                return json.loads(part)
            except Exception:
                continue
    return json.loads(raw)


def run_inference():
    rewards = []
    step_num = 0
    success = False
    score = 0.0

    print(f"[START] task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME}")

    for task_index in range(TOTAL_TASKS):
        reset_resp = requests.post(f"{ENV_URL}/reset", json={"task_index": task_index})
        reset_resp.raise_for_status()
        obs = reset_resp.json()
        session_id = obs.pop("session_id")
        headers = {"X-Session-Id": session_id}
        error = None
        try:
            action = call_llm(obs)
        except Exception as exc:
            error = str(exc)
            action = {
                "bugs_found": ["Could not parse LLM response"],
                "severity": "low",
                "suggested_fix": "N/A",
                "false_positive": False,
            }

        step_resp = requests.post(f"{ENV_URL}/step", json=action, headers=headers)
        step_resp.raise_for_status()
        result = step_resp.json()

        reward = result.get("reward", 0.0)
        done = result.get("done", False)
        obs = result.get("observation", {})
        rewards.append(reward)
        step_num += 1
        action_str = json.dumps(action, separators=(",", ":"), ensure_ascii=True)
        print(
            f"[STEP] step={step_num} "
            f"action={action_str} "
            f"reward={reward:.2f} "
            f"done={str(done).lower()} "
            f"error={error if error else 'null'}"
        )

        if not done:
            error = "task episode did not terminate after one review step"

    if rewards:
        score = sum(rewards) / len(rewards)
        success = score > 0.0

    rewards_str = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} "
        f"steps={step_num} "
        f"score={score:.3f} "
        f"rewards={rewards_str}"
    )

    return score


if __name__ == "__main__":
    run_inference()
