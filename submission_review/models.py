from pydantic import BaseModel, Field
from typing import List


class Action(BaseModel):
    bugs_found: List[str] = Field(
        description="List of bugs identified in the PR. Each entry should describe one bug."
    )
    severity: str = Field(
        description="Overall severity of issues found: 'low', 'medium', or 'high'"
    )
    suggested_fix: str = Field(
        description="A concrete suggestion for how to fix the most critical issue found."
    )
    false_positive: bool = Field(
        default=False,
        description="Set to True if you believe the code has no real issues."
    )


class Observation(BaseModel):
    pr_title: str = Field(description="Title of the pull request")
    pr_description: str = Field(description="Description of what the PR is supposed to do")
    code_diff: str = Field(description="The code diff/changes introduced by the PR")
    task_difficulty: str = Field(description="Difficulty level: easy, medium, or hard")
    instructions: str = Field(description="Instructions for the agent")


class State(BaseModel):
    current_task: int = Field(default=0, description="Current task index (0=easy, 1=medium, 2=hard)")
    done: bool = Field(default=False, description="Whether the episode is done")
    total_reward: float = Field(default=0.0, description="Accumulated reward so far")
    task_rewards: List[float] = Field(default_factory=list, description="Reward per completed task")
