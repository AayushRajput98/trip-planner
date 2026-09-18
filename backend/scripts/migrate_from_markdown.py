"""
One-off migration: parse ../../data/trip-plan.md (the hand-authored markdown+
frontmatter trip content from the abandoned static-site pass) into the JSON
files the FastAPI backend serves from backend/data/.

Grammar mirrors js/markdown.js exactly:
  ---
  <yaml frontmatter>
  ---
  ## <n>: <title>
  wd: ...
  km: ...
  load: ...
  star: true            (optional)
  stat: ...
  map: ...
  photos: a, b, c

  > type: html text      (zero or more)

  ### Timetable
  - **HH:MM** [★] what
    desc (optional, indented)

  ### Logistics
  - **Label:** value

Run once: `python scripts/migrate_from_markdown.py`
"""
import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_MD = REPO_ROOT / "data" / "trip-plan.md"
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

TIME_RE = re.compile(r"^-\s+\*\*(\d{1,2}:\d{2})\*\*\s*(★\s*)?(.*)$")
LOGISTICS_RE = re.compile(r"^-\s+\*\*([^*]+):\*\*\s?(.*)$")
FIELD_RE = re.compile(r"^(\w+):\s?(.*)$")
ALERT_RE = re.compile(r"^>\s*(\w+):\s?(.*)$")
HEADER_RE = re.compile(r"^##\s+(.+?):\s*(.*)$")
SECTION_RE = re.compile(r"^###\s+(.+)$")


def parse_day_block(block: str) -> dict:
    lines = block.split("\n")
    header = lines.pop(0)
    hm = HEADER_RE.match(header)
    if not hm:
        raise ValueError(f"Malformed day header: {header!r}")
    day = {"n": hm.group(1).strip(), "title": hm.group(2).strip(),
           "alerts": [], "tl": [], "logistics": []}

    i = 0
    while i < len(lines) and lines[i].strip() != "" and not lines[i].startswith(">") and not lines[i].startswith("#"):
        fm = FIELD_RE.match(lines[i])
        if fm:
            key, val = fm.group(1), fm.group(2)
            if key == "km":
                day["km"] = int(val)
            elif key == "star":
                day["star"] = val.strip() == "true"
            elif key == "photos":
                day["photos"] = [s.strip() for s in val.split(",") if s.strip()]
            else:
                day[key] = val
        i += 1

    while i < len(lines) and lines[i].strip() == "":
        i += 1
    while i < len(lines) and lines[i].startswith(">"):
        am = ALERT_RE.match(lines[i])
        if am:
            day["alerts"].append({"type": am.group(1), "html": am.group(2)})
        i += 1
        while i < len(lines) and lines[i].strip() == "":
            i += 1

    while i < len(lines):
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        if i >= len(lines):
            break
        hm2 = SECTION_RE.match(lines[i])
        if not hm2:
            i += 1
            continue
        section = hm2.group(1).strip()
        i += 1
        if section == "Timetable":
            while i < len(lines) and not lines[i].startswith("### "):
                tm = TIME_RE.match(lines[i])
                if tm:
                    entry = {"time": tm.group(1), "what": tm.group(3).strip(), "status": "planned"}
                    if tm.group(2):
                        entry["key"] = True
                    i += 1
                    desc_lines = []
                    while i < len(lines) and re.match(r"^\s+\S", lines[i]):
                        desc_lines.append(lines[i].strip())
                        i += 1
                    if desc_lines:
                        entry["desc"] = " ".join(desc_lines)
                    day["tl"].append(entry)
                else:
                    i += 1
        elif section == "Logistics":
            while i < len(lines) and not lines[i].startswith("### "):
                lm = LOGISTICS_RE.match(lines[i])
                if lm:
                    day["logistics"].append([lm.group(1).strip(), lm.group(2).strip()])
                i += 1
        else:
            while i < len(lines) and not lines[i].startswith("### "):
                i += 1

    return day


def parse_trip_markdown(text: str) -> dict:
    fm_match = re.match(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?", text)
    if not fm_match:
        raise ValueError("trip-plan.md is missing its --- frontmatter block")
    meta = yaml.safe_load(fm_match.group(1)) or {}
    body = text[fm_match.end():]

    day_blocks = [b.strip() for b in re.split(r"\r?\n(?=##\s)", body) if b.strip()]
    days = [parse_day_block(b) for b in day_blocks]

    data = dict(meta)
    data["days"] = days
    return data


def main():
    if not SOURCE_MD.exists():
        print(f"Source file not found: {SOURCE_MD}", file=sys.stderr)
        sys.exit(1)

    text = SOURCE_MD.read_text(encoding="utf-8")
    data = parse_trip_markdown(text)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    def dump(name, obj):
        path = DATA_DIR / name
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)}")

    dump("meta.json", data["meta"])
    dump("budget.json", {"vehicle": data["vehicle"], "prices": data["prices"], "legs": data["legs"]})
    dump("days.json", data["days"])
    dump("reference.json", {
        "food": data["food"],
        "stays": data["stays"],
        "fuelStops": data["fuelStops"],
        "variants": data["variants"],
        "notes": data["notes"],
        "sources": data.get("sources", []),
        "photoUrls": data.get("photoUrls", {}),
        "photoWiki": data.get("photoWiki", {}),
    })
    dump("checklist.json", [
        {"id": f"c{i+1}", "text": item, "done": False}
        for i, item in enumerate(data["checklist"])
    ])
    dump("expenses.json", [])

    print(f"\nMigrated {len(data['days'])} days from {SOURCE_MD.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
