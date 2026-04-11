"""Repo-root copy for GitHub-only scanners; keep in sync with submission_review/graded_tasks/."""

from . import age_validation
from . import dashboard_cache
from . import discount_calculation
from . import login_endpoint

GRADED_TASK_MODULES = (
    age_validation,
    discount_calculation,
    login_endpoint,
    dashboard_cache,
)
