"""Rewrites the LIVE block in README.md from public GitHub activity. Stdlib only."""
import json, os, random, re, sys, urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

USER = os.environ.get("GH_USER", "Rukshan2000")
TZ = ZoneInfo("Asia/Colombo")
BARS = " ▁▂▃▄▅▆▇█"
JOKES = [
    "It works on my machine. Ship the machine.",
    "99 bugs in the code. Fix one. 127 bugs in the code.",
    "There's no place like 127.0.0.1",
    "I don't always test my code, but when I do, it's in production.",
    "My IoT fridge has better uptime than my sleep schedule.",
    "Weeks of coding can save you hours of planning.",
    "Git commit -m 'final_final_v3_really_final'",
    "Hardware: the part of the computer you can kick.",
]
MOODS = [  # first match wins
    (r"fix|bug|patch|hotfix|error", "🧯 debugging the matrix"),
    (r"feat|add|new|implement|create", "🚀 shipping new features"),
    (r"refactor|clean|rename|move", "🧹 cleaning the codebase"),
    (r"doc|readme", "📚 writing the manual"),
    (r"test", "🧪 breaking things on purpose"),
    (r"style|ui|css|design", "🎨 pixel pushing"),
]

def mood(messages):
    text = " ".join(messages).lower()
    hits = Counter()
    for pat, label in MOODS:
        hits[label] = len(re.findall(pat, text))
    best, n = hits.most_common(1)[0] if hits else ("", 0)
    return best if n else "🌙 recharging / plotting something"

def spark(counts):
    top = max(counts) or 1
    return "".join(BARS[round(c / top * 8)] if c else BARS[0] for c in counts)

def vibe(hour):
    if 5 <= hour < 9: return "☕ booting up with tea"
    if 9 <= hour < 18: return "💻 probably coding"
    if 18 <= hour < 23: return "🔥 side-project hours"
    return "🦉 night-owl mode / or asleep"

def fetch(url, token=None):
    token = token or os.environ.get("GITHUB_TOKEN")
    req = urllib.request.Request(url, headers={"User-Agent": "readme-updater", "Accept": "application/vnd.github+json",
                                               **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def build(events, now):
    pushes = [e for e in events if e["type"] == "PushEvent"]
    msgs, days = [], [0] * 7
    for e in pushes:
        commits = e["payload"].get("commits") or []
        msgs += [c["message"].split("\n")[0] for c in commits]
        age = (now.date() - datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")).astimezone(TZ).date()).days
        if 0 <= age < 7: days[6 - age] += max(len(commits), 1)
    repos = [e["repo"]["name"].split("/")[1] for e in events if e["repo"]["name"].split("/")[1] != USER]
    now_building = repos[0] if repos else "something secret 🤫"
    top_repo = Counter(repos).most_common(1)[0][0] if repos else "—"
    last = msgs[0][:60] if msgs else "—"
    rows = [
        f"  ◉ LIVE · updated {now:%d %b %Y · %H:%M} (Colombo)",
        "",
        f"  🔨 now building ...... {now_building}",
        f"  🏆 most active repo .. {top_repo}",
        f"  📝 last commit ....... \"{last}\"",
        f"  🌡️ mood .............. {mood(msgs[:30])}",
        f"  🕐 local time ........ {now:%H:%M} — {vibe(now.hour)}",
        "",
        f"  last 7 days  {spark(days)}  {sum(days)} commits",
        f"  🃏 \"{random.Random(now.date().toordinal()).choice(JOKES)}\"",
    ]
    return "```text\n" + "\n".join(rows) + "\n```"

def main():
    now = datetime.now(TZ)
    try:
        events = fetch(f"https://api.github.com/users/{USER}/events/public?per_page=100")
    except Exception as e:  # keep the last good README instead of crashing the workflow
        print(f"fetch failed: {e}"); return
    # events API dropped commit lists; fill messages for the latest pushes from their head commit
    for e in [e for e in events if e["type"] == "PushEvent"][:15]:
        if not e["payload"].get("commits") and e["payload"].get("head"):
            try:
                c = fetch(f"https://api.github.com/repos/{e['repo']['name']}/commits/{e['payload']['head']}")
                e["payload"]["commits"] = [{"message": c["commit"]["message"]}]
            except Exception:
                pass
    block = build(events, now)
    path = os.path.join(os.path.dirname(__file__), "../../README.md")
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"(<!--LIVE:START-->).*?(<!--LIVE:END-->)", lambda m: f"{m[1]}\n{block}\n{m[2]}", s, flags=re.S)
    if os.environ.get("GH_PAT"):  # GITHUB_TOKEN can't see your private repos; a PAT can
        try:
            total, page = 0, 1
            while batch := fetch(f"https://api.github.com/user/repos?affiliation=owner&per_page=100&page={page}", os.environ["GH_PAT"]):
                total += len(batch); page += 1
            s = re.sub(r"(total%20repositories-)\d+(-)", rf"\g<1>{total}\g<2>", s)
        except Exception as e:
            print(f"repo count failed: {e}")
    open(path, "w", encoding="utf-8").write(s)

def test():
    assert mood(["fix login bug", "feat: add iot"]) == "🧯 debugging the matrix"
    assert mood([]).startswith("🌙")
    assert spark([0, 4, 8]) == " ▄█"
    now = datetime(2026, 11, 4, 12, tzinfo=TZ)
    ev = [{"type": "PushEvent", "created_at": "2026-11-04T05:00:00Z", "repo": {"name": "Rukshan2000/AgroPlus"},
           "payload": {"commits": [{"message": "feat: barcode auth"}]}}]
    out = build(ev, now)
    assert "AgroPlus" in out and "1 commits" in out and "barcode" in out
    print("ok")

if __name__ == "__main__":
    test() if "--test" in sys.argv else main()
