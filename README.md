# PuppetMaster — 把免费 AI 模型收编为"傀儡"子代理

**Orchestrate free LLMs as disposable "puppet" sub-agents under one main model — pure CLI, zero framework, zero cost.**

> 中央编排者动态指挥专用傀儡，而非一个通用大模型干所有事。
> 省 token 只是副产品，真正的价值是**释放主模型的注意力**。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/manual-Ver1.8.1-blue)](docs/PuppetMaster_Ver1.8.1.md)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)](#快速开始)

---

## 这是什么

把多个**免费**大模型 API（智谱 / Agnes AI / 讯飞 / 硅基流动 / OpenRouter 等）收编为**稳定可支配的傀儡**：分类、打标、摘要、改写、问答、难度路由、仲裁、翻译、利弊分析、通俗解释、要素提取——14 个纯 CLI 命令，供你的 AI 工作流（agent / skill / 定时任务 / 脚本）直接调用。

- **纯 CLI，零依赖**：一个 Python 脚本（纯标准库），无常驻服务、无 MCP、无框架——有 Bash 就能调
- **傀儡观**：找的不是"免费模型"，是"干基础活、稳定可支配的傀儡"——免费只是福利，稳定才是命
- **判断权红线**：傀儡只执行、不判断；判断、决策、最终结论永远属于主模型

## 为什么不是又一个多 Agent 框架

| | CrewAI / LangGraph 类框架 | PuppetMaster |
|---|---|---|
| 形态 | 平台/框架，学习成本高 | 单脚本 CLI，`python free_models.py classify "文本"` 即用 |
| 拓扑 | Agent 间可互相通信（自主路径） | **星型**：傀儡零互信、零 peer 通信，全部经主模型 |
| token 经济性 | 自承"前环节产出塞进后环节"成倍膨胀 | 各步独立取原文、结果并列汇总，无链式膨胀 |
| 依赖 | 框架 + 生态 | 纯标准库，任何有 Bash 的壳（agent/定时任务/CI）直接调 |

核心分层原则（**确定性写死、判断放权**）：failover 链、批量阈值、验收标准这些可枚举的规则写死在流程里；选谁干活、结果可不可信、最终结论这些需要理解的判断，放权给主模型。

## 六维增量价值（真实 API 计费实测）

对比「主模型直读原文」vs「傀儡加工后主模型只读结果」（8 类任务）：

| 维度 | 数据/机制 |
|------|----------|
| ① 省 token | 全类型 total 均值省 **64%**（输入密集型 78%，输出密集型 40%） |
| ② 并行干活 | N 个傀儡 = N 个子代理同时跑，批量时间减半 |
| ③ 主模型专注度 | 只读加工后精华，不被原文噪音稀释 |
| ④ 防限流 | 各免费 API 独立窗口互不挤占 |
| ⑤ 窗口容量 | 加工后省窗口，长会话不爆上下文 |
| ⑥ 异构视角 | 多模型交叉验证防单模型偏见（**前提：真异构——同族交叉是伪冗余**） |

## 快速开始

1. 在 `~/.workbuddy/models.json`（或改脚本里的读取路径）登记你的免费模型：

```json
[
  { "id": "glm-4-flash", "apiKey": "YOUR_KEY", "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions" },
  { "id": "lite", "apiKey": "YOUR_KEY", "url": "https://spark-api-open.xf-yun.com/v1/chat/completions" }
]
```

2. 直接用：

```bash
python free_models.py models                          # 查看傀儡池
python free_models.py health                          # 全池体检（准入必测）
python free_models.py classify "央行宣布降准0.5个百分点"
python free_models.py classify "文本" --cats "相关财报,公司动态,噪音"
python free_models.py summarize < article.txt --model glm-4-flash
python free_models.py route "任务文本"                 # 难度感知路由
python free_models.py rate batch-0829 4 --note "备注"  # 调度评分
```

3. 每个 AI 工作流里写一行调度指令即可（以 WorkBuddy 为例）：`用 free_models.py 给这段文字分类："……"`

## 编排纪律（实战踩坑沉淀）

| 纪律 | 一句话 |
|------|--------|
| 仲裁归属 | 双交叉不一致 → **主模型实质仲裁**——裁判若用模型，同族会给自家输出 5-25% 溢价（LLM-as-Judge 自偏好偏差，实测踩过） |
| 命令级验收标准 | 每类任务写明 expected_output——写模糊，AI 交"差不多的东西"糊弄 |
| verify 软失败 | failover 只管硬失败（超时/报错）；"成功返回但答错"靠验收标准对照发现 |
| 批量先试跑 | 大批量先跑 3-5 条样本，通过再放量——单条合格 ≠ 批量合格 |
| 只收真免费 | 按次免费 ≠ 完全免费——警惕魔粒/积分/限时额度暗扣费（实测盲跑消耗教训） |
| 推理模型陷阱 | 部分推理模型把内容写进 reasoning 字段、正文为空——收编前质量考核 |

更多判例（glm 批量截断 = 输出预算超限而非网络问题、推理模型 content 为空、魔搭"空壳"模型、免费档 429 预判……）见文档。

## 文档导航

| 文档 | 内容 |
|------|------|
| [docs/PuppetMaster_Ver1.8.1.md](docs/PuppetMaster_Ver1.8.1.md) | **使用手册（真源）**：编排流程、failover 链、验收标准、调度档案、全部踩坑判例 |
| [docs/Puppeteer范式研究简报_Ver3.0.0.md](docs/Puppeteer范式研究简报_Ver3.0.0.md) | 学术前沿对照：Puppeteer Pattern / 级联路由 / LLM-as-Judge 偏差 / 自我进化 |
| [docs/免费AI模型API接入指南_傀儡技.md](docs/免费AI模型API接入指南_傀儡技.md) | 8 平台接入配置速查 + 省 token 实测全过程 + 编程类实测 |
| [docs/PuppetMaster技能介绍_整合版.md](docs/PuppetMaster技能介绍_整合版.md) | 体系概览（理念向） |
| bench_coding.py / bench_coding2.py | 编程类 token 实测脚本（可复测） |

## 免责与时效

- 免费政策变动极快（实测周期内已有平台改计费制、模型下架），以各平台官网为准；**收编任何模型前先核实完整计费规则**
- 本项目为个人研究与工作流实践，API Key 需自行注册，仓库内不含任何密钥
- 各平台服务条款合规性请自行确认

## License

[MIT](LICENSE) © KuMoo
