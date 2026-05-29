#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CONFIG_PATH = os.getenv("PORTFOLIO_CONFIG", "assets/portfolio-quality.json")
README_PATH = os.getenv("README_PATH", "README.md")

START_MARKER = "<!-- PORTFOLIO-QUALITY:START -->"
END_MARKER = "<!-- PORTFOLIO-QUALITY:END -->"


def fetch_repo_pushed_at(repo: str, token: str | None) -> str | None:
    url = f"https://api.github.com/repos/{repo}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pushed_at = data.get("pushed_at")
            if not pushed_at:
                return None
            return pushed_at
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"Warning: failed to fetch repo data for {repo}: {exc}", file=sys.stderr)
        return None


def format_date(iso_date: str | None) -> str:
    if not iso_date:
        return "—"
    try:
        return datetime.fromisoformat(iso_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        return "—"


def status_bool(value: bool) -> str:
    return "✅" if value else "—"


def status_link(url: str | None) -> str:
    return f"[✅]({url})" if url else "—"


def main() -> int:
    if not os.path.exists(CONFIG_PATH):
        print(f"Config file not found: {CONFIG_PATH}", file=sys.stderr)
        return 1

    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    projects = config.get("projects", [])
    token = os.getenv("GITHUB_TOKEN")

    rows = []
    for project in projects:
        name = project.get("name", "Unnamed")
        project_url = project.get("project_url") or project.get("repo")
        project_cell = f"[{name}]({project_url})" if project_url else name

        ci = status_bool(bool(project.get("ci")))
        tests = status_bool(bool(project.get("tests")))
        docs = status_link(project.get("docs"))
        demo = status_link(project.get("demo"))

        last_update_override = project.get("last_update")
        if last_update_override:
            last_update = last_update_override
        else:
            repo = project.get("repo")
            pushed_at = fetch_repo_pushed_at(repo, token) if repo else None
            last_update = format_date(pushed_at)

        signal = project.get("signal", "")

        rows.append(
            f"| {project_cell} | {ci} | {tests} | {docs} | {demo} | {last_update} | {signal} |"
        )

    table = "\n".join(
        [
            "| Project | CI/CD | Tests | Docs | Demo | Last update | Signal |",
            "|:--|:--:|:--:|:--:|:--:|:--:|:--|",
            *rows,
        ]
    )

    if not os.path.exists(README_PATH):
        print(f"README not found: {README_PATH}", file=sys.stderr)
        return 1

    with open(README_PATH, "r", encoding="utf-8") as fh:
        readme = fh.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r"[\s\S]*?" + re.escape(END_MARKER)
    )
    replacement = f"{START_MARKER}\n\n{table}\n\n{END_MARKER}"

    if not pattern.search(readme):
        print("Markers not found in README.", file=sys.stderr)
        return 1

    updated = pattern.sub(replacement, readme)

    with open(README_PATH, "w", encoding="utf-8") as fh:
        fh.write(updated)

    print("Portfolio Quality Index updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
