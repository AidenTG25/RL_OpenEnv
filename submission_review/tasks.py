# PR review tasks ordered from easy to hard.
# Each task includes issue-level grading metadata so rewards track correctness,
# completeness, and fix quality more closely than raw output length.

TASKS = [
    {
        "task_id": "age-validation",
        "grader": {"enabled": True, "type": "programmatic_rubric"},
        "difficulty": "easy",
        "pr_title": "Add user age validation",
        "pr_description": (
            "This PR adds a function to validate user age before registration. "
            "Users must be 18 or older."
        ),
        "code_diff": """\
+ def validate_age(age):
+     if age > 18:
+         return True
+     return False
+
+ # Example usage
+ print(validate_age(18))  # Should return True for exactly 18
""",
        "correct_severity": "medium",
        "issues": [
            {
                "id": "age-boundary",
                "title": "Rejects users who are exactly 18",
                "keywords": [
                    "18",
                    "greater than",
                    "greater than or equal",
                    ">=",
                    "off by one",
                    "boundary",
                ],
                "fix_keywords": [
                    ">=",
                    "greater than or equal",
                    "age >= 18",
                ],
                "critical": True,
            }
        ],
        "allowed_false_positive": False,
    },
    {
        "task_id": "discount-calculation",
        "grader": {"enabled": True, "type": "programmatic_rubric"},
        "difficulty": "medium",
        "pr_title": "Add discount calculation for premium users",
        "pr_description": (
            "Applies a 20% discount for premium users and a 10% discount for regular "
            "users. Also logs the transaction for auditing."
        ),
        "code_diff": """\
+ def calculate_price(user_type, price):
+     if user_type == "premium":
+         discount = 0.20
+     else:
+         discount = 0.10
+     final_price = price - (price * discount)
+     print("Transaction: user=" + user_type + " price=" + str(final_price))
+     return final_price
+
+ def apply_bulk_discount(prices, user_type):
+     total = 0
+     for i in range(len(prices) + 1):   # iterates one too many times
+         total += calculate_price(user_type, prices[i])
+     return total
""",
        "correct_severity": "high",
        "issues": [
            {
                "id": "bulk-discount-index",
                "title": "Loop reads one item past the end of the prices list",
                "keywords": [
                    "index",
                    "out of range",
                    "off by one",
                    "len(prices) + 1",
                    "loop",
                    "range",
                ],
                "fix_keywords": [
                    "range(len(prices))",
                    "len(prices)",
                    "remove + 1",
                    "iterate directly",
                ],
                "critical": True,
            },
            {
                "id": "transaction-logging",
                "title": "Logs transaction details to stdout",
                "keywords": [
                    "print",
                    "logging",
                    "logs",
                    "stdout",
                    "sensitive",
                    "price",
                    "transaction",
                ],
                "fix_keywords": [
                    "structured logging",
                    "remove the print",
                    "redact",
                    "mask",
                    "avoid logging",
                ],
                "critical": False,
            },
        ],
        "allowed_false_positive": False,
    },
    {
        "task_id": "login-endpoint",
        "grader": {"enabled": True, "type": "programmatic_rubric"},
        "difficulty": "hard",
        "pr_title": "Add user login endpoint",
        "pr_description": (
            "Implements a login endpoint that checks credentials against the database "
            "and returns a session token on success."
        ),
        "code_diff": """\
+ import sqlite3
+ import hashlib
+
+ def login(username, password):
+     conn = sqlite3.connect("users.db")
+     cursor = conn.cursor()
+
+     # Check credentials
+     query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
+     cursor.execute(query)
+     user = cursor.fetchone()
+
+     if user:
+         token = hashlib.md5(username.encode()).hexdigest()
+         return {"status": "ok", "token": token}
+     return {"status": "fail"}
+
+ # No rate limiting, no input sanitization
""",
        "correct_severity": "high",
        "issues": [
            {
                "id": "sql-injection",
                "title": "Builds the query with an f-string",
                "keywords": [
                    "sql injection",
                    "injection",
                    "f-string",
                    "parameterized",
                    "query",
                ],
                "fix_keywords": [
                    "parameterized",
                    "?",
                    "placeholder",
                    "bound parameter",
                ],
                "critical": True,
            },
            {
                "id": "weak-token-hash",
                "title": "Generates a predictable token with MD5",
                "keywords": [
                    "md5",
                    "weak",
                    "predictable",
                    "hash",
                    "token",
                ],
                "fix_keywords": [
                    "secrets.token_urlsafe",
                    "secure random",
                    "signed token",
                    "bcrypt",
                    "argon2",
                ],
                "critical": False,
            },
            {
                "id": "missing-rate-limit",
                "title": "Allows unlimited login attempts",
                "keywords": [
                    "rate limit",
                    "brute force",
                    "lockout",
                    "throttle",
                ],
                "fix_keywords": [
                    "rate limit",
                    "lockout",
                    "throttle",
                    "backoff",
                ],
                "critical": False,
            },
        ],
        "allowed_false_positive": False,
    },
    {
        "task_id": "dashboard-cache",
        "grader": {"enabled": True, "type": "programmatic_rubric"},
        "difficulty": "hard",
        "pr_title": "Cache dashboard metrics to speed up page loads",
        "pr_description": (
            "Adds a Redis cache for the analytics dashboard so repeated requests do not "
            "recompute expensive metrics. The endpoint should return data scoped to the "
            "current account."
        ),
        "code_diff": """\
diff --git a/api/dashboard.py b/api/dashboard.py
new file mode 100644
index 0000000..b92ab12
--- /dev/null
+++ b/api/dashboard.py
@@
+ import json
+ from flask import request
+ from services.metrics import build_dashboard
+ from services.cache import cache
+
+ def get_dashboard():
+     account_id = request.args.get("account_id")
+     cache_key = "dashboard:" + account_id
+     cached = cache.get(cache_key)
+     if cached:
+         return json.loads(cached)
+
+     dashboard = build_dashboard(account_id)
+     cache.set(cache_key, json.dumps(dashboard), ex=900)
+     return dashboard
+
diff --git a/services/cache.py b/services/cache.py
new file mode 100644
index 0000000..5e2c51a
--- /dev/null
+++ b/services/cache.py
@@
+ import redis
+
+ cache = redis.Redis(host="localhost", port=6379, decode_responses=True)
""",
        "correct_severity": "high",
        "issues": [
            {
                "id": "missing-auth-scope",
                "title": "Trusts a caller supplied account id",
                "keywords": [
                    "authorization",
                    "account_id",
                    "access control",
                    "tenant",
                    "request args",
                    "caller supplied",
                ],
                "fix_keywords": [
                    "authenticated user",
                    "server-side account",
                    "authorize",
                    "session",
                    "token claims",
                ],
                "critical": True,
            },
            {
                "id": "cache-key-collision",
                "title": "Cache key can collide or break when account_id is missing",
                "keywords": [
                    "none",
                    "missing account_id",
                    "cache key",
                    "validation",
                    "dashboard:none",
                ],
                "fix_keywords": [
                    "validate account_id",
                    "reject missing",
                    "normalize key",
                    "required parameter",
                ],
                "critical": False,
            },
            {
                "id": "cross-tenant-cache",
                "title": "Cross-tenant data can be returned from cache",
                "keywords": [
                    "cross-tenant",
                    "cached data",
                    "tenant isolation",
                    "data leak",
                    "dashboard cache",
                ],
                "fix_keywords": [
                    "scope cache to authenticated tenant",
                    "include tenant context",
                    "clear unauthorized cache",
                ],
                "critical": False,
            },
        ],
        "allowed_false_positive": False,
    },
]
