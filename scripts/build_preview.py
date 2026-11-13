#!/usr/bin/env python3
"""把 _layouts/default.html + *.md 合成为完整静态站。

用法：
    # 本地预览（输出 preview*.html，链接指向 preview 文件）
    python scripts/build_preview.py

    # 正式站（输出到 _site/，链接用正式文件名）
    python scripts/build_preview.py --site

正式站模式供 EdgeOne / 任意静态托管使用，不依赖 Jekyll。
"""

import os
import re
import sys

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAYOUT = os.path.join(ROOT, "_layouts", "default.html")
SITE_TITLE = "254511班学习主页"

# (md 文件, 正式文件名, nav, show_banner, 标题)
PAGES = [
    ("index.md", "index.html", "home", True, "首页"),
    ("homework.md", "homework.html", "homework", False, "作业"),
    ("notices.md", "notices.html", "notices", False, "学习通知"),
]

# 预览模式下的文件名与首页地址
PREVIEW_MAP = {
    "index.html": "preview.html",
    "homework.html": "preview-homework.html",
    "notices.html": "preview-notices.html",
}


def render_md(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    raw = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", raw, flags=re.S)
    return markdown.markdown(
        raw,
        extensions=["tables", "fenced_code", "md_in_html", "sane_lists", "nl2br"],
        output_format="html5",
    )


def apply_liquid(tpl: str, nav: str, show_banner: bool, title: str,
                 content: str, link: dict) -> str:
    """link 是本模式下三个页面的真实 URL。"""
    s = tpl

    s = re.sub(r"\{%\s*assign[^%]*%\}", "", s)

    pat_banner = re.compile(r"\{%\s*if\s+page\.show_banner\s*%\}(.*?)\{%\s*endif\s*%\}", re.S)
    s = pat_banner.sub(lambda m: m.group(1) if show_banner else "", s)

    def cond(m):
        return m.group(2) if m.group(1) == nav else ""

    s = re.sub(r'\{%\s*if\s+current\s*==\s*"(\w+)"\s*%\}(.*?)\{%\s*endif\s*%\}', cond, s, flags=re.S)

    s = s.replace("{{ page.title }}", title)
    s = s.replace("{{ site.title }}", SITE_TITLE)
    s = s.replace("{{ '/' | relative_url }}", link["home"])
    s = s.replace("{{ '/homework.html' | relative_url }}", link["homework"])
    s = s.replace("{{ 'homework.html' | relative_url }}", link["homework"])
    s = s.replace("{{ 'notices.html' | relative_url }}", link["notices"])
    s = s.replace("{{ page.nav | default: 'home' }}", nav)
    s = re.sub(r"\{\{\s*content\s*\}\}", lambda _: content, s)

    # md 正文里的站内链接
    s = s.replace('href="homework.html"', 'href="' + link["homework"] + '"')
    s = s.replace('href="notices.html"', 'href="' + link["notices"] + '"')

    leftovers = re.findall(r"\{[{%][^}]*[}%]\}", s)
    if leftovers:
        print("  ! 残留 Liquid:", leftovers[:5], file=sys.stderr)
    return s


def main():
    site_mode = "--site" in sys.argv
    out_dir = os.path.join(ROOT, "_site") if site_mode else ROOT

    with open(LAYOUT, encoding="utf-8") as f:
        tpl = f.read()

    if site_mode:
        link = {"home": "index.html", "homework": "homework.html", "notices": "notices.html"}
        os.makedirs(out_dir, exist_ok=True)
    else:
        link = {"home": "preview.html",
                "homework": "preview-homework.html",
                "notices": "preview-notices.html"}

    for md_name, site_name, nav, banner, title in PAGES:
        md_path = os.path.join(ROOT, md_name)
        if not os.path.exists(md_path):
            print(f"  跳过 {md_name}（不存在）")
            continue

        out_name = site_name if site_mode else PREVIEW_MAP[site_name]
        html = apply_liquid(tpl, nav, banner, title, render_md(md_path), link)
        with open(os.path.join(out_dir, out_name), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  {md_name} → {os.path.join(os.path.basename(out_dir), out_name) if site_mode else out_name}")

    if site_mode:
        # 静态资源一起带走
        import shutil
        for d in ("assets", "files"):
            src = os.path.join(ROOT, d)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(out_dir, d), dirs_exist_ok=True)
                print(f"  {d}/ → _site/{d}/")
        for f in ("calendar.ics", "favicon.ico"):
            src = os.path.join(ROOT, f)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(out_dir, f))
                print(f"  {f} → _site/{f}")
        print(f"✅ 正式站已生成：{out_dir}")


if __name__ == "__main__":
    main()
