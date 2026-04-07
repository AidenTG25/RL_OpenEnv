import json
import os

import requests
from openai import OpenAI


API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:8000")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

SYSTEM_PROMPT = """\
You are a senior software engineer conducting a pull request code review.

You will be given a PR title, description, and code diff.
Your job is to identify all bugs, security issues, and logic errors.

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
    total_reward = 0.0
    results = []

    print("[START]")

    reset_resp = requests.post(f"{ENV_URL}/reset")
    reset_resp.raise_for_status()
    obs = reset_resp.json()

    session_id = obs.pop("session_id")
    headers = {"X-Session-Id": session_id}
    step_num = 0

    while True:
        difficulty = obs.get("task_difficulty", "")
        if difficulty == "done":
            break

        try:
            action = call_llm(obs)
        except Exception as exc:
            print(f"[STEP] step={step_num} difficulty={difficulty} reward=0.0 error={exc}")
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

        total_reward += reward
        results.append(
            {
                "difficulty": difficulty,
                "reward": reward,
                "bugs_found": action.get("bugs_found", []),
                "severity": action.get("severity", ""),
                "suggested_fix": action.get("suggested_fix", ""),
            }
        )

        print(
            f"[STEP] step={step_num} "
            f"difficulty={difficulty} "
            f"reward={reward} "
            f"severity={action.get('severity')} "
            f"bugs_found={len(action.get('bugs_found', []))}"
        )

        step_num += 1
        if done:
            break

    avg_reward = round(total_reward / max(len(results), 1), 4)
    print(f"[END] total_reward={round(total_reward, 4)} avg_reward={avg_reward} steps={len(results)}")

    print("\nDetailed Results")
    for result in results:
        print(f"  {result['difficulty']:8s} | reward={result['reward']} | severity={result['severity']}")
        for bug in result["bugs_found"]:
            print(f"             bug: {bug}")
        print(f"             fix: {result['suggested_fix'][:80]}...")
        print()

    return avg_reward


if __name__ == "__main__":
    run_inference()
