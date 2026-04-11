"""
Static grader registry at repository root for hackathon tooling that scans the
GitHub checkout (not only submission_review/). Must stay aligned with tasks.TASKS.
"""

GRADERS = (
    {"task_id": "age-validation", "enabled": True},
    {"task_id": "discount-calculation", "enabled": True},
    {"task_id": "login-endpoint", "enabled": True},
    {"task_id": "dashboard-cache", "enabled": True},
)
