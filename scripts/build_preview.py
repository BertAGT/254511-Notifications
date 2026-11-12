#!/usr/bin/env python3
"""把 _layouts/default.html + *.md 合成为本地预览页（不需要装 Jekyll）。

用法：
    /Users/bert/.workbuddy/binaries/python/envs/default/bin/python scripts/build_preview.py

生成 preview.html / preview-homework.html / preview-notices.html
"""

import os
import re
import sys

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = os.path.join(ROOT, "_layouts", "default.html")
SITE_TITLE = "254511班学习主页"

PAGES = [
    # (md 文件, 输出文件, nav, show_banner, 标题)
    ("index.md", "preview.html", "home", True, "首页"),
    ("homework.md", "preview-homework.html", "homework", False, "作业"),
    ("notices.md", "preview-notices.html", "notices", False, "学习通知"),
]


def render_md(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    # 去掉 front matter
    raw = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", raw, flags=re.S)
    return markdown.markdown(
        raw,
        extensions=["tables", "fenced_code", "md_in_html", "sane_lists", "nl2br"],
        output_format="html5",
    )


def apply_liquid(tpl: str, nav: str, show_banner: bool, title: str, content: str) -> str:
    s = tpl

    # {% assign %} 直接删除
    s = re.sub(r"\{%\s*assign[^%]*%\}", "", s)

    # {% if page.show_banner %} 块
    pat_banner = re.compile(r"\{%\s*if\s+page\.show_banner\s*%\}(.*?)\{%\s*endif\s*%\}", re.S)
    s = pat_banner.sub(lambda m: m.group(1) if show_banner else "", s)

    # {% if current == "xxx" %}...{% endif %}
    def cond(m):
        return m.group(2) if m.group(1) == nav else ""

    s = re.sub(r'\{%\s*if\s+current\s*==\s*"(\w+)"\s*%\}(.*?)\{%\s*endif\s*%\}', cond, s, flags=re.S)

    # 变量
    s = s.replace("{{ page.title }}", title)
    s = s.replace("{{ site.title }}", SITE_TITLE)
    s = s.replace("{{ '/' | relative_url }}", "preview.html")
    s = s.replace("{{ '/homework.html' | relative_url }}", "preview-homework.html")
    s = s.replace("{{ 'homework.html' | relative_url }}", "preview-homework.html")
    s = s.replace("{{ 'notices.html' | relative_url }}", "preview-notices.html")
    s = s.replace("{{ page.nav | default: 'home' }}", nav)
    s = re.sub(r"\{\{\s*content\s*\}\}", lambda _: content, s)

    # md 内部链接指向预览文件
    s = s.replace('href="homework.html"', 'href="preview-homework.html"')
    s = s.replace('href="notices.html"', 'href="preview-notices.html"')

    leftovers = re.findall(r"\{[{%][^}]*[}%]\}", s)
    if leftovers:
        print("  ! 残留 Liquid:", leftovers[:5], file=sys.stderr)
    return s


def main():
    with open(LAYOUT, encoding="utf-8") as f:
        tpl = f.read()

    for md_name, out_name, nav, banner, title in PAGES:
        md_path = os.path.join(ROOT, md_name)
        if not os.path.exists(md_path):
            print(f"  跳过 {md_name}（不存在）")
            continue
        html = apply_liquid(tpl, nav, banner, title, render_md(md_path))
        with open(os.path.join(ROOT, out_name), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  {md_name} → {out_name}")


if __name__ == "__main__":
    main()
