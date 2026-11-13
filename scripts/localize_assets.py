#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 md 里指向 GitHub 的附件 / 图片下载到仓库本地，改成相对路径。

背景：学委通过 Issue 表单上传的图片和文件，GitHub 会托管在
      github.com/user-attachments/... 下，这些地址国内访问不了。
      但 GitHub Actions 的机器在海外，能正常下载。

流程：
1. 扫所有 md，找出三类外链
   - github.com/user-attachments/assets/xxx      （表单里贴的图）
   - github.com/user-attachments/files/xxx/name  （表单上传的文件）
   - raw.githubusercontent.com/.../files/name    （老的仓库直链）
2. 下载到 assets/img/（图片）或 files/（其他）
3. 把 md 里的 URL 替换成相对路径
4. 记进 .gitignore 之外，随下次 commit 一起提交

可以反复跑：已本地化的链接不会再被处理（它们已经不是外链）。
"""

import hashlib
import os
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; 254511-site-bot)"}

ASSET_RE = re.compile(r"https://github\.com/user-attachments/assets/[A-Za-z0-9-]+")
FILE_RE = re.compile(r"https://github\.com/user-attachments/files/\d+/[^\s)\"'\]<>]+")
RAW_RE = re.compile(r"https://raw\.githubusercontent\.com/[^/\s]+/[^/\s]+/[^/\s]+/files/[^\s)\"'\]<>]+")

MD_FILES = ["index.md", "homework.md", "notices.md"]

# Content-Type → 扩展名
EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/x-zip-compressed": ".zip",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/plain": ".txt",
}


def fetch(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read(), (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()


def target_path(data: bytes, ctype: str, url: str) -> str:
    """决定存哪、叫什么。同内容同文件名，天然去重。"""
    ext = EXT.get(ctype, "")
    if not ext:
        # 从 URL 尾段猜扩展名（user-attachments/files/123/报告.pdf）
        tail = url.rsplit("/", 1)[-1]
        ext = os.path.splitext(tail)[1].lower() if "." in tail else ""
    if not ext:
        ext = ".bin"

    is_image = ctype.startswith("image/")
    folder = os.path.join("assets", "img") if is_image else "files"
    os.makedirs(folder, exist_ok=True)
    name = hashlib.md5(data).hexdigest()[:10] + ext
    return os.path.join(folder, name).replace(os.sep, "/")


def localize(text: str, cache: dict, stats: dict) -> str:
    urls = []
    for pat in (ASSET_RE, FILE_RE, RAW_RE):
        urls.extend(pat.findall(text))

    for url in dict.fromkeys(urls):
        if url in cache:
            text = text.replace(url, cache[url])
            continue
        try:
            data, ctype = fetch(url)
            if not data:
                print(f"  ! 空内容，跳过：{url}")
                continue
            rel = target_path(data, ctype, url)
            if not os.path.exists(rel):
                with open(rel, "wb") as f:
                    f.write(data)
            cache[url] = rel
            stats["ok"] += 1
            print(f"  ✓ {url.split('/')[-1][:36]} → {rel}  ({len(data)}B, {ctype or 'unknown'})")
            text = text.replace(url, rel)
        except Exception as e:
            stats["fail"] += 1
            print(f"  ✗ 下载失败 {url}\n     {e}")
    return text


def main():
    cache, stats = {}, {"ok": 0, "fail": 0}
    changed = []

    for name in MD_FILES:
        if not os.path.exists(name):
            continue
        with open(name, encoding="utf-8") as f:
            src = f.read()
        out = localize(src, cache, stats)
        if out != src:
            with open(name, "w", encoding="utf-8") as f:
                f.write(out)
            changed.append(name)

    print(f"\n完成：下载 {stats['ok']} 个，失败 {stats['fail']} 个，改动 {len(changed)} 个文件")
    if changed:
        print("已修改：" + "、".join(changed))
    # 有失败就让流水线标红，避免静默漏掉
    return 1 if stats["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
