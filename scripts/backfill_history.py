#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 GitHub Issue 重建作业历史：data/homework.json + archive/<学期>/week-NN.md

用途：机器人只从启用那天起才有归档，更早的周需要这个脚本从 Issue 表单回填。

用法（在仓库根目录）：
    python scripts/backfill_history.py

注意：会覆盖 data/homework.json 和 archive/<学期>/week-NN.md 中已存在的同名周。
      日常发布不需要跑，新周由 update_homework.py 自动追加。
"""

import json
import os
import re
import sys
import urllib.request
from datetime import date

REPO = "bertagt/254511-Notifications"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 课程名归一化：表单里的各种写法 → (id, 规范名)
COURSE_MAP = {
    "概率统计B": ("probability-statistics-b", "概率统计B"),
    "概率统计b": ("probability-statistics-b", "概率统计B"),
    "普通物理学": ("general-physics", "普通物理学"),
    "基础生物力学": ("basic-biomechanics", "基础生物力学"),
    "生物力学": ("basic-biomechanics", "基础生物力学"),
    "电路分析与医学电子系统": ("circuit-analysis", "电路分析与医学电子系统"),
    "电路分析医学电子系统": ("circuit-analysis", "电路分析与医学电子系统"),
    "电路分析": ("circuit-analysis", "电路分析与医学电子系统"),
    "基础医学实验": ("basic-medical-experiment", "基础医学实验"),
    "基物实验": ("basic-physics-experiment", "基础物理实验"),
    "基础物理实验": ("basic-physics-experiment", "基础物理实验"),
}

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8,
          "九": 9, "十": 10, "十一": 11, "十二": 12, "十三": 13, "十四": 14,
          "十五": 15, "十六": 16, "十七": 17, "十八": 18}

EMPTY_TOKENS = {"", "no response", "noresponse", "none", "n/a", "na", "-", "--", "无"}


def api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "254511-backfill"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def clean(v):
    t = (v or "").strip()
    if not t:
        return ""
    return "" if t.strip("_").strip("*").strip().lower() in EMPTY_TOKENS else t


def parse_section(body, label):
    m = re.search(r"###\s*" + re.escape(label) + r"\s*\n+(.*?)(?=\n###|\Z)", body, re.S)
    if not m:
        return ""
    lines = [l for l in m.group(1).splitlines() if not l.strip().startswith("###")]
    return clean("\n".join(lines))


def parse_items(items):
    out = []
    for raw in items.splitlines():
        line = raw.strip()
        if not line or line.startswith("```"):
            continue
        parts = [p.strip() for p in line.split("|")]
        while len(parts) < 3:
            parts.append("")
        if not parts[0]:
            continue
        out.append({"course": parts[0], "task": parts[1], "due": clean(parts[2])})
    return out


def course_of(raw):
    key = (raw or "").strip()
    if key in COURSE_MAP:
        return COURSE_MAP[key]
    compact = key.replace(" ", "")
    for k, v in COURSE_MAP.items():
        if k in compact or compact in k:
            return v
    return ("unknown", key)


def parse_due(text, year=2026):
    t = (text or "").strip()
    if not t:
        return {"kind": "none", "raw": ""}
    if t in ("以通知为准", "以老师通知为准", "待定", "TBD"):
        return {"kind": "unknown", "raw": t}

    m = re.match(r"^(\d{1,2})[.月](\d{1,2})日?\s*(.*)$", t)
    if m:
        month, day, rest = int(m.group(1)), int(m.group(2)), m.group(3).strip()
        tm = re.search(r"(\d{1,2})[:：](\d{2})", rest)
        return {"kind": "absolute", "raw": t,
                "date": f"{year}-{month:02d}-{day:02d}",
                "time": f"{int(tm.group(1)):02d}:{tm.group(2)}" if tm else None,
                "note": rest if rest and not tm else None}

    weeks = []
    for tok in re.findall(r"第\s*([一二三四五六七八九十\d]+)\s*周", t):
        n = int(tok) if tok.isdigit() else CN_NUM.get(tok)
        if n and n not in weeks:
            weeks.append(n)
    if weeks:
        return {"kind": "relative_week", "raw": t, "week": weeks[0], "weeks": weeks}
    return {"kind": "text", "raw": t}


def season_of(week):
    m = re.search(r"(\d{2})\s*(秋|春|夏|冬)", week)
    if not m:
        return "unknown"
    return f"{2000 + int(m.group(1))}-{'fall' if m.group(2) in '秋冬' else 'spring'}"


def week_no(week):
    m = re.search(r"第\s*(\d+)\s*周", week)
    return int(m.group(1)) if m else None


def build_block(label, items, notes):
    lines = [f"# 📅 {label}", ""]
    if notes:
        note_html = "<br>".join(l.strip() for l in notes.splitlines() if l.strip())
        lines += [f'<div class="notice">📌 {note_html}</div>', ""]
    lines += ["| 科目 | 作业内容 | 截止时间 |", "|------|----------|----------|"]
    for it in items:
        due = it["due"]["raw"]
        cell = f'<span class="deadline">{due}</span>' if due else '<span class="tbd">以老师通知为准</span>'
        lines.append(f'| {it["course"]} | {it["task"]} | {cell} |')
    lines += ["", "---", ""]
    return "\n".join(lines)


def fetch_all_issues():
    out, page = [], 1
    while True:
        batch = api(f"https://api.github.com/repos/{REPO}/issues"
                    f"?state=all&per_page=50&page={page}")
        if not batch:
            break
        out += [i for i in batch if "pull_request" not in i]
        if len(batch) < 50:
            break
        page += 1
    return out


def main():
    weeks, courses = {}, {}

    for iss in sorted(fetch_all_issues(), key=lambda x: x["number"]):
        body = iss.get("body") or ""
        if "### 周次" not in body:
            continue
        week = parse_section(body, "周次")
        items_raw = parse_section(body, "作业列表")
        notes = parse_section(body, "特别提醒（可选）")
        if not week or not items_raw:
            continue
        n = week_no(week)
        if n is None:
            continue

        has_label = any(l["name"] == "homework" for l in iss.get("labels", []))
        if n in weeks and not has_label:
            continue  # 同一周有正式表单时，不用重复的那条

        parsed = []
        for it in parse_items(items_raw):
            cid, cname = course_of(it["course"])
            courses.setdefault(cid, {"id": cid, "name": cname, "aliases": []})
            if it["course"] not in courses[cid]["aliases"]:
                courses[cid]["aliases"].append(it["course"])
            parsed.append({"course": it["course"], "course_id": cid,
                           "course_name": cname, "task": it["task"],
                           "due": parse_due(it["due"])})

        weeks[n] = {
            "week": n, "label": week, "season": season_of(week),
            "issue": iss["number"], "issue_title": iss.get("title", ""),
            "published": (iss.get("created_at") or "")[:10],
            "notes": notes, "items": parsed,
        }
        print(f"  ✓ #{iss['number']} {week} → {len(parsed)} 门课")

    ordered = [weeks[k] for k in sorted(weeks)]
    payload = {
        "schema_version": 1,
        "generated_at": date.today().isoformat(),
        "generator": "scripts/backfill_history.py",
        "source": f"github.com/{REPO} issues",
        "season": ordered[0]["season"] if ordered else "unknown",
        "weeks_count": len(ordered),
        "items_count": sum(len(w["items"]) for w in ordered),
        "courses": sorted(courses.values(), key=lambda c: c["name"]),
        "weeks": ordered,
    }

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "homework.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    for w in ordered:
        adir = os.path.join(ROOT, "archive", w["season"])
        os.makedirs(adir, exist_ok=True)
        items = "\n".join(
            f'{i["course"]} | {i["task"]} | {i["due"]["raw"]}' for i in w["items"])
        head = (
            f"<!-- 归档于 {date.today().isoformat()}，来源 GitHub Issue #{w['issue']}"
            f"（{w['issue_title']}，{w['published']} 提交） -->\n"
            f"> 学期：{w['season']} ｜ 第 {w['week']} 周 ｜ 共 {len(w['items'])} 门课"
            f" ｜ 原始表单：Issue #{w['issue']}\n\n"
        )
        with open(os.path.join(adir, f"week-{w['week']:02d}.md"), "w", encoding="utf-8") as f:
            f.write(head + build_block(w["label"], w["items"], w["notes"]))

    print(f"\n✅ data/homework.json：{payload['weeks_count']} 周 / "
          f"{payload['items_count']} 条 / {len(courses)} 门课")
    print(f"✅ archive 已重建第 {ordered[0]['week']}–{ordered[-1]['week']} 周")


if __name__ == "__main__":
    main()
