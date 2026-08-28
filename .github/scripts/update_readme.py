"""Refreshes the auto-generated sections of README.md from GitHub's public API.

Only /users/{username}/events/public and /users/{username}/repos are used —
both endpoints only ever return public data, so private repos/activity can
never leak into the profile even if the token in CI had broader scope.
"""
import json
import re
import urllib.request

USERNAME = "katosamuelraymond"
MAX_ITEMS = 5


def gh_get(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "profile-readme-bot",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def format_activity():
    events = gh_get(
        f"https://api.github.com/users/{USERNAME}/events/public?per_page=30"
    )
    lines = []
    for event in events:
        if len(lines) >= MAX_ITEMS * 3:
            break
        etype = event["type"]
        repo = event["repo"]["name"]
        link = f"[`{repo}`](https://github.com/{repo})"

        if etype == "PushEvent":
            n = len(event["payload"].get("commits", []))
            if n == 0:
                continue
            lines.append(f"- Pushed {n} commit{'s' if n != 1 else ''} to {link}")
        elif etype == "CreateEvent" and event["payload"].get("ref_type") == "repository":
            lines.append(f"- Created {link}")
        elif etype == "PullRequestEvent" and event["payload"].get("action") == "opened":
            title = event["payload"].get("pull_request", {}).get("title", "").strip()
            suffix = f": “{title}”" if title else ""
            lines.append(f"- Opened a pull request in {link}{suffix}")
        elif etype == "ReleaseEvent":
            lines.append(f"- Published a release in {link}")
        elif etype == "IssuesEvent" and event["payload"].get("action") == "opened":
            title = event["payload"].get("issue", {}).get("title", "").strip()
            suffix = f": “{title}”" if title else ""
            lines.append(f"- Opened an issue in {link}{suffix}")

    seen = set()
    deduped = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            deduped.append(line)
    lines = deduped[:MAX_ITEMS]

    return "\n".join(lines) if lines else "- No recent public activity"


def format_repos():
    repos = gh_get(
        f"https://api.github.com/users/{USERNAME}/repos"
        "?sort=pushed&direction=desc&per_page=15"
    )
    repos = [r for r in repos if not r.get("fork")][:MAX_ITEMS]

    lines = []
    for r in repos:
        line = f"- [`{r['name']}`](https://github.com/{USERNAME}/{r['name']})"
        if r.get("description"):
            line += f" — {r['description']}"
        if r.get("language"):
            line += f" ({r['language']})"
        lines.append(line)

    return "\n".join(lines) if lines else "- No public repositories yet"


def replace_section(content, name, body):
    pattern = re.compile(
        rf"(<!--START_SECTION:{name}-->)(.*?)(<!--END_SECTION:{name}-->)",
        re.DOTALL,
    )
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", content)


def main():
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    content = replace_section(content, "activity", format_activity())
    content = replace_section(content, "repos", format_repos())

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
