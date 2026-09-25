#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
作业自动发布机器人的核心脚本
=================================
作用：读取学委填写的 Issue 表单内容，自动把新一周的作业
      插入到 homework.md 顶部（旧作业自动往下沉留档），
      并在 index.md 的"最新动态"里加一条记录。

工作原理（给学委的编程小课堂 🧬）：
1. GitHub Actions 在云端收到你提交的表单后，把表单内容
   存进环境变量 ISSUE_BODY 传给本脚本
2. 脚本用"正则表达式"从表单文本里切出各个栏目
3. 把栏目内容拼装成 Markdown 表格
4. 写回 homework.md 和 index.md
5. 后续步骤由 workflow 自动 git 提交发布
"""

import os
import re
from datetime import date


def parse_section(body: str, label: str) -> str:
    """从 Issue 正文里切出某个栏目的内容。

    Issue 表单的正文长这样：
        ### 周次
        26秋 第 4 周
        ### 作业列表
        ...
    所以按 "### 栏目名" 切一刀就能拿到内容。
    """
    pattern = r"###\s*" + re.escape(label) + r"\s*\n+(.*?)(?=\n###|\Z)"
    match = re.search(pattern, body, re.S)
    return match.group(1).strip() if match else ""


def build_week_block(week: str, items: str, notes: str, screenshot: str) -> str:
    """把表单内容拼装成一周的 Markdown 板块。"""
    lines = [f"# 📅 {week}", ""]

    if notes:
        lines.append(f'<div class="notice">📌 {notes}</div>')
        lines.append("")

    lines.append("| 科目 | 作业内容 | 截止时间 |")
    lines.append("|------|----------|----------|")

    for raw in items.splitlines():
        line = raw.strip()
        if not line or line.startswith("```"):
            continue
        # 每行按竖线拆成三栏，缺的栏补空
        parts = [p.strip() for p in line.split("|")]
        while len(parts) < 3:
            parts.append("")
        subject, task, due = parts[0], parts[1], parts[2]
        if not subject:
            continue
        due_cell = f'<span class="due">{due}</span>' if due else "——"
        lines.append(f"| {subject} | {task} | {due_cell} |")

    lines.append("")

    if screenshot:
        lines.append("### 🖼 Numbers 截图备份")
        lines.append("")
        lines.append(screenshot)
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


WEEKLY_START = "<!-- ROBOT:WEEKLY:START"
WEEKLY_END = "<!-- ROBOT:WEEKLY:END"


def update_homework(block: str, homework_path: str):
    """把新一周板块写入 homework.md。

    规则：
    - 文件里有 ROBOT:WEEKLY:START / END 标记 → 只替换标记之间的
      "每周作业区"，旧周直接被换掉（不留档）；标记之外的长期作业区
      原样保留，机器人绝不触碰。
    - 没有标记（旧版文件）→ 自动在 front matter 之后创建标记区。
    """
    with open(homework_path, "r", encoding="utf-8") as f:
        content = f.read()

    wrapped = (
        f"{WEEKLY_START} 机器人管理区：每周作业只保留最新一周，旧周会被自动替换掉 -->\n\n"
        + block
        + "\n<!-- ROBOT:WEEKLY:END -->\n"
    )

    if WEEKLY_START in content and WEEKLY_END in content:
        # 替换标记之间的内容（含标记本身，重建一致的标记）
        pattern = re.compile(
            r"<!--\s*ROBOT:WEEKLY:START[^>]*?-->"
            r".*?"
            r"<!--\s*ROBOT:WEEKLY:END\s*-->\n?",
            re.S,
        )
        if not pattern.search(content):
            print("警告：标记格式异常，跳过更新以免误删长期作业")
            return
        content = pattern.sub(wrapped, content, count=1)
        print("已替换每周作业区（旧周不留档）")
    else:
        # 旧版文件没有标记：在 front matter 之后插入标记区
        fm = re.match(r"\A(---\n.*?\n---\n)", content, re.S)
        if fm:
            head = fm.group(1)
            rest = content[fm.end():].lstrip("\n")
            content = head + "\n" + wrapped + "\n" + rest
        else:
            content = wrapped + "\n" + content
        print("未找到每周区标记，已自动创建（下次起只替换标记内内容）")

    with open(homework_path, "w", encoding="utf-8") as f:
        f.write(content)


def update_index(week: str, index_path: str):
    """在 index.md 的"最新动态"最上面加一行。文件不存在时自动跳过。"""
    if not os.path.exists(index_path):
        print("index.md 不存在，跳过首页更新")
        return

    today = date.today().strftime("%m.%d").lstrip("0")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_line = f"- **{today}** {week}已更新 → [查看](homework.html)"
    anchor = "## 🏠 最新动态"
    if anchor in content:
        content = content.replace(
            anchor, anchor + "\n\n" + new_line, 1
        )
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"index.md 已更新：{new_line}")
    else:
        print("index.md 中没找到'最新动态'锚点，跳过首页更新")


if __name__ == "__main__":
    body = os.environ.get("ISSUE_BODY", "")
    if not body:
        raise SystemExit("没有拿到表单内容，退出")

    week = parse_section(body, "周次")
    items = parse_section(body, "作业列表")
    notes = parse_section(body, "特别提醒（可选）")
    screenshot = parse_section(body, "Numbers 截图（可选）")

    if not week or not items:
        raise SystemExit(f"表单信息不全：周次={week!r}，作业列表为空={not items}")

    print(f"本周：{week}")
    print(f"课程数：{len([l for l in items.splitlines() if l.strip() and not l.strip().startswith('```')])}")

    block = build_week_block(week, items, notes, screenshot)
    update_homework(block, "homework.md")
    update_index(week, "index.md")
    print("✅ homework.md 与 index.md 更新完成")
