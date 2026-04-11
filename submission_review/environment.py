from models import Action, Observation, State
from tasks import TASKS

MIN_TASK_SCORE = 0.01
MAX_TASK_SCORE = 0.99


INSTRUCTIONS = (
    "You are a senior software engineer reviewing a pull request. "
    "Carefully read the PR title, description, and code diff. "
    "Identify all bugs, security issues, or logic errors introduced by this PR. "
    "Classify the overall severity as 'low', 'medium', or 'high'. "
    "Suggest a concrete fix for the most critical issue. "
    "Only set false_positive=true if the code is genuinely correct with no issues."
)


class PRReviewEnvironment:
    def __init__(self, task_index: int = 0):
        self.task_index = task_index % len(TASKS)
        self.state = State(current_task=self.task_index)

    def reset(self) -> Observation:
        self.state = State(current_task=self.task_index, task_rewards=[])
        task = TASKS[self.task_index]
        return self._make_observation(task)

    def step(self, action: Action):
        task = TASKS[self.task_index]
        reward = self._grade(action, task)

        self.state.total_reward = reward
        self.state.task_rewards = [reward]
        self.state.done = True
        next_obs = Observation(
            pr_title="Task complete",
            pr_description="",
            code_diff="",
            task_difficulty="done",
            instructions="Episode finished.",
        )

        return next_obs, reward, self.state.done, {
            "completed_task": task["task_id"],
            "reward": reward,
            "total_reward": self.state.total_reward,
            "graded": True,
            "grader": task.get("grader")
            or {"enabled": True, "type": "programmatic_rubric"},
        }

    def get_state(self) -> State:
        return self.state

    def _make_observation(self, task: dict) -> Observation:
        return Observation(
            pr_title=task["pr_title"],
            pr_description=task["pr_description"],
            code_diff=task["code_diff"],
            task_difficulty=task["difficulty"],
            instructions=INSTRUCTIONS,
        )

    def _grade(self, action: Action, task: dict) -> float:
        if action.false_positive and not task.get("allowed_false_positive", False):
            return MIN_TASK_SCORE

        issues = task["issues"]
        matched_issue_ids = self._match_issues(action.bugs_found, issues)

        score = 0.0
        detection_score = len(matched_issue_ids) / max(len(issues), 1)
        score += round(detection_score * 0.45, 4)

        extra_claims = self._count_unmatched_bug_reports(action.bugs_found, issues)
        if extra_claims:
            score -= min(extra_claims * 0.05, 0.15)

        severity = action.severity.lower().strip()
        if severity == task["correct_severity"]:
            score += 0.20
        elif self._is_adjacent_severity(severity, task["correct_severity"]):
            score += 0.10

        score += round(self._score_fix(action.suggested_fix, issues) * 0.25, 4)

        if matched_issue_ids and len(matched_issue_ids) == len(issues):
            score += 0.10

        return round(max(MIN_TASK_SCORE, min(score, MAX_TASK_SCORE)), 4)

    def _match_issues(self, bug_reports: list[str], issues: list[dict]) -> set[str]:
        matched_issue_ids: set[str] = set()
        for report in bug_reports:
            report_text = report.lower()
            for issue in issues:
                if issue["id"] in matched_issue_ids:
                    continue
                if any(keyword.lower() in report_text for keyword in issue["keywords"]):
                    matched_issue_ids.add(issue["id"])
        return matched_issue_ids

    def _count_unmatched_bug_reports(self, bug_reports: list[str], issues: list[dict]) -> int:
        unmatched = 0
        for report in bug_reports:
            report_text = report.lower()
            if not any(
                keyword.lower() in report_text
                for issue in issues
                for keyword in issue["keywords"]
            ):
                unmatched += 1
        return unmatched

    def _score_fix(self, suggested_fix: str, issues: list[dict]) -> float:
        fix_text = suggested_fix.lower()
        target_issues = [issue for issue in issues if issue.get("critical", False)] or issues

        issue_scores = []
        for issue in target_issues:
            hits = sum(
                1 for keyword in issue["fix_keywords"] if keyword.lower() in fix_text
            )
            denominator = max(len(issue["fix_keywords"]) / 2, 1)
            issue_scores.append(min(hits / denominator, 1.0))

        if not issue_scores:
            return 0.0

        return sum(issue_scores) / len(issue_scores)

    def _is_adjacent_severity(self, predicted: str, expected: str) -> bool:
        order = ["low", "medium", "high"]
        if predicted not in order or expected not in order:
            return False
        return abs(order.index(predicted) - order.index(expected)) == 1
