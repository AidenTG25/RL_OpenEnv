"""Discrete modules per graded task (some hackathon scanners count Python grader files)."""

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
