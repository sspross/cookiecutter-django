"""Pre-commit hook wrapper for pip-audit.

Only fails if there are vulnerabilities with a known fix version.
Vulnerabilities without fixes are reported as warnings but don't block commits.
"""

import json
import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        ["uv", "run", "pip-audit", "-f", "json"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return 0

    try:
        findings = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(result.stderr)
        return 1

    fixable = []
    unfixable = []

    for dep in findings.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            entry = f"  {dep['name']}=={dep['version']} ({vuln['id']})"
            if vuln.get("fix_versions"):
                fix = ", ".join(vuln["fix_versions"])
                fixable.append(f"{entry} -> {fix}")
            else:
                unfixable.append(entry)

    if unfixable:
        print(f"[pip-audit] {len(unfixable)} unfixable (no fix available):")
        for line in unfixable:
            print(line)

    if fixable:
        print(f"[pip-audit] {len(fixable)} fixable vulnerabilities found:")
        for line in fixable:
            print(line)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
