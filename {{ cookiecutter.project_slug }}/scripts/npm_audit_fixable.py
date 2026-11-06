import json
import subprocess
import sys
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "core" / "frontend"


def main() -> int:
    result = subprocess.run(
        ["npm", "audit", "--omit=dev", "--json"],  # noqa: S607 npm is the required audit tool
        capture_output=True,
        text=True,
        cwd=FRONTEND_DIR,
    )

    if result.returncode == 0:
        return 0

    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(result.stderr)
        return 1

    if "vulnerabilities" not in report:
        print(result.stdout or result.stderr)
        return 1

    fixable = []
    unfixable = []

    for name, vuln in report["vulnerabilities"].items():
        entry = f"  {name} ({vuln['severity']})"
        if vuln.get("fixAvailable"):
            fixable.append(entry)
        else:
            unfixable.append(entry)

    if unfixable:
        print(f"[npm-audit] {len(unfixable)} unfixable (no fix available):")
        for line in unfixable:
            print(line)

    if fixable:
        print(f"[npm-audit] {len(fixable)} fixable vulnerabilities found:")
        for line in fixable:
            print(line)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
