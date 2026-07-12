import requests
import os
import re
from datetime import datetime, timedelta, timezone

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ["GITHUB_REPOSITORY_OWNER"]


def get_contributions():
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    headers = {"Authorization": f"bearer {TOKEN}"}
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"login": USERNAME}},
        headers=headers,
    )
    resp.raise_for_status()
    data = resp.json()
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for week in weeks:
        for day in week["contributionDays"]:
            days.append(day)
    days.sort(key=lambda d: d["date"])
    total = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return days, total


def calculate_streaks(days):
    today = datetime.now(timezone.utc).date()
    day_map = {d["date"]: d["contributionCount"] for d in days}

    # Current streak: go backwards from today (skip today if no commits yet)
    current_streak = 0
    check_date = today
    started = False
    while True:
        date_str = check_date.isoformat()
        count = day_map.get(date_str, 0)
        if count > 0:
            current_streak += 1
            started = True
            check_date -= timedelta(days=1)
        else:
            if not started and check_date == today:
                # today has no commits yet — check from yesterday
                check_date -= timedelta(days=1)
            else:
                break

    # Longest streak ever
    max_streak = 0
    streak = 0
    for day in days:
        if day["contributionCount"] > 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return current_streak, max_streak


def generate_svg(current_streak, max_streak, total, updated_at):
    fire = "🔥" if current_streak > 0 else "💤"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="180">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>
  <rect width="480" height="180" rx="14" fill="url(#bg)" stroke="#30363d" stroke-width="1.5"/>

  <text x="240" y="34" text-anchor="middle" font-family="'Segoe UI',monospace" font-size="15" fill="#e6edf3" font-weight="bold">{fire} GitHub Commit Streak</text>

  <!-- Current Streak -->
  <text x="100" y="92" text-anchor="middle" font-family="monospace" font-size="42" fill="#f78166" font-weight="bold">{current_streak}</text>
  <text x="100" y="114" text-anchor="middle" font-family="'Segoe UI',monospace" font-size="12" fill="#8b949e">Current Streak</text>
  <text x="100" y="130" text-anchor="middle" font-family="'Segoe UI',monospace" font-size="11" fill="#6e7681">days</text>

  <line x1="210" y1="52" x2="210" y2="148" stroke="#30363d" stroke-width="1"/>

  <!-- Longest Streak -->
  <text x="310" y="92" text-anchor="middle" font-family="monospace" font-size="42" fill="#3fb950" font-weight="bold">{max_streak}</text>
  <text x="310" y="114" text-anchor="middle" font-family="'Segoe UI',monospace" font-size="12" fill="#8b949e">Longest Streak</text>
  <text x="310" y="130" text-anchor="middle" font-family="'Segoe UI',monospace" font-size="11" fill="#6e7681">days</text>

  <line x1="400" y1="52" x2="400" y2="148" stroke="#30363d" stroke-width="1"/>

  <!-- Total -->
  <text x="440" y="92" text-anchor="middle" font-family="monospace" font-size="24" fill="#58a6ff" font-weight="bold">{total}</text>
  <text x="440" y="114" text-anchor="middle" font-family="'Segoe UI',monospace" font-size="12" fill="#8b949e">Total</text>
  <text x="440" y="130" text-anchor="middle" font-family="'Segoe UI',monospace" font-size="11" fill="#6e7681">commits</text>

  <text x="240" y="166" text-anchor="middle" font-family="monospace" font-size="10" fill="#484f58">Updated: {updated_at} UTC</text>
</svg>"""


def update_readme(current_streak, max_streak):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    block = f"""<!-- STREAK_START -->
## 🔥 Commit Streak

> 매일 커밋하면 스트릭이 쌓여요!

![Commit Streak](./streak/streak.svg)

| | |
|---|---|
| 현재 스트릭 | **{current_streak}일** |
| 최장 스트릭 | **{max_streak}일** |

<!-- STREAK_END -->"""

    if "<!-- STREAK_START -->" in content:
        content = re.sub(
            r"<!-- STREAK_START -->.*?<!-- STREAK_END -->",
            block,
            content,
            flags=re.DOTALL,
        )
    else:
        content += "\n" + block + "\n"

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)


def main():
    days, total = get_contributions()
    current_streak, max_streak = calculate_streaks(days)
    updated_at = __import__("datetime").datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    os.makedirs("streak", exist_ok=True)
    svg = generate_svg(current_streak, max_streak, total, updated_at)
    with open("streak/streak.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    update_readme(current_streak, max_streak)
    print(f"Current streak: {current_streak} days | Longest: {max_streak} days | Total: {total}")


if __name__ == "__main__":
    main()
