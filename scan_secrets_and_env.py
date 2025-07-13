import os
import re

# Set your project root directory
PROJECT_ROOT = "."

# Patterns to search for hardcoded secrets
SECRET_PATTERNS = [
    r'password\s*=\s*[\'"].+[\'"]',
    r'key\s*=\s*[\'"].+[\'"]',
    r'token\s*=\s*[\'"].+[\'"]',
    r'aws_secret_access_key\s*=\s*[\'"].+[\'"]',
    r'aws_access_key_id\s*=\s*[\'"].+[\'"]',
]

# Load environment variable names from .env.example
env_vars = []
with open(os.path.join(PROJECT_ROOT, ".env.example")) as f:
    for line in f:
        match = re.match(r'^([A-Z0-9_]+)=', line)
        if match:
            env_vars.append(match.group(1))

# Scan files for hardcoded secrets and env var usage
hardcoded_secrets = []
env_var_usage = {var: False for var in env_vars}
hardcoded_candidates = []

for root, dirs, files in os.walk(PROJECT_ROOT):
    for file in files:
        if file.endswith((".py", ".sh", ".yaml", ".yml", ".tf", ".json")):
            path = os.path.join(root, file)
            with open(path, errors="ignore") as f:
                content = f.read()
                # Check for hardcoded secrets
                for pattern in SECRET_PATTERNS:
                    for match in re.findall(pattern, content, re.IGNORECASE):
                        hardcoded_secrets.append((path, match))
                # Check for env var usage
                for var in env_vars:
                    if re.search(var, content):
                        env_var_usage[var] = True
                # Check for hardcoded values (simple heuristic)
                for line in content.splitlines():
                    if re.match(r'.*=\s*[\'"].+[\'"]', line) and not any(var in line for var in env_vars):
                        hardcoded_candidates.append((path, line.strip()))

# Print results
print("\n--- Hardcoded Secrets ---")
for path, secret in hardcoded_secrets:
    print(f"{path}: {secret}")

print("\n--- Unused Environment Variables (in .env.example but not used) ---")
for var, used in env_var_usage.items():
    if not used:
        print(var)

print("\n--- Hardcoded Values That Could Be Environment Variables ---")
for path, line in hardcoded_candidates:
    print(f"{path}: {line}")

print("\nScan complete.")