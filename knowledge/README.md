# 知识库

这里放"只有本班才知道"的信息。不是公开资料，而是老师的口头要求、班群约定、踩过的坑。

## 为什么单独建这一层

作业条目谁都能整理，但"基物实验报告必须命名为 `BPhy_第N周_姓名_学号.pdf`、预习报告不能合订"这类规则，公网搜不到、教材上没有、GitHub 里也没有。它们只存在于老师的交代和课程的约定里，一届毕业就散一次。

对智能体来说，这才是真正的壁垒：问"基物实验报告怎么命名"，通用模型只能瞎编，而这里能给出确定答案。

## 目录结构

```
knowledge/
└── courses/                    每门课一张卡片
    ├── probability-statistics-b.md
    ├── general-physics.md
    ├── basic-biomechanics.md
    ├── circuit-analysis.md
    ├── basic-medical-experiment.md
    └── basic-physics-experiment.md
```

每张卡片有五个小节：基本信息、提交与命名、从作业记录归纳的规律、评分构成、踩过的坑。其中"归纳的规律"是我从 `data/homework.json` 里统计生成的，已经填好；其余四节留空等你补。

## 怎么填

一次填一门，五分钟够了。优先填"提交与命名"——这一节的信息量最大，也最不可替代。

填完不用管格式，正常写中文就行，我后续负责结构化。

## 数据怎么流动

```
GitHub Issue 表单
      │
      ▼
data/homework.json  ──►  统计规律  ──►  knowledge/courses/*.md
      │                                        │
      ▼                                        ▼
archive/<学期>/week-NN.md              智能体回答问题的依据
```

作业是每周自动增长的原始事实，课程卡片是提炼后的稳定知识。前者回答"这周有什么作业"，后者回答"这类作业该怎么做"。
