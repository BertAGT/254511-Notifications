# 结构化数据

`homework.json` 是从 GitHub Issue 表单回填的历史作业，供检索、问答、统计使用。页面不读取这个文件，它只服务机器。

## 顶层字段

| 字段 | 含义 |
|---|---|
| `schema_version` | 数据结构版本，改字段时递增 |
| `generated_at` | 生成日期 |
| `source` | 数据来源，当前是 Issue 表单 |
| `season` | 学期代号，如 `2026-fall` |
| `weeks_count` / `items_count` | 周数、作业条数 |
| `courses` | 课程清单，含 `id`、规范名 `name`、出现过的别名 |
| `weeks` | 每周一条，含周次、学期、来源 Issue 号、发布时间、特别提醒、作业列表 |

## 一条作业记录

```json
{
  "course": "基物实验",
  "course_id": "basic-physics-experiment",
  "course_name": "基础物理实验",
  "task": "第六周实验报告、第七周预习报告",
  "due": {
    "kind": "relative_week",
    "raw": "第七周课前",
    "week": 7,
    "weeks": [7]
  }
}
```

`course` 保留表单原文，`course_name` 是归一化后的规范名——同一门课在不同周可能写成"基物实验""基础物理实验"，靠 `course_id` 对齐。

## 截止时间的四种形态

`due.kind` 决定怎么读：

- `absolute`：有明确日期，带 `date`（`YYYY-MM-DD`）、可能带 `time` 和 `note`（如"中午"）
- `relative_week`：写成"第 N 周课前"，带 `week`；若有多个截止，`weeks` 是数组
- `unknown`：原文是"以通知为准"之类，无法确定
- `none`：表单里没填

所有形态都保留 `raw` 原文，任何推断都不覆盖原始表述。

## 重新生成

```bash
python scripts/backfill_history.py
```

脚本会拉取仓库全部 Issue 表单，重新解析成 `homework.json` 与 `archive/<学期>/week-NN.md`。

注意两点：
- 它**会覆盖**已有的同名周档案和整个 json，只在需要从 Issue 重建历史时用。
- 日常发布不需要跑。每周的新作业由 `scripts/update_homework.py` 在 Issue 触发时自动追加，并且会保留既有历史与顶层字段。
