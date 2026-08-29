#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
free_models v1.7 — 子代理傀儡工具（glm-4-flash / agnes / lite / nemotron）
================================================================
定位：轻量文本任务的免费 API 工具（分类/打标/摘要/改写/问答/难度路由/仲裁/翻译/利弊/解释/提取），
供 WorkBuddy 子代理、skill、定时任务直接调用（纯 CLI，零常驻）。
API Key 自动从 ~/.workbuddy/models.json 读取，零配置。

傀儡池（稳定性优先于免费；全部真免费，无扣费模型）：
  - glm-4-flash   智谱 GLM-4-Flash     128K 窗口  免费            支持工具（脚本内未启用）
  - agnes-2.5-flash  Agnes AI 2.5     推理模型    永久免费         国内站实测 0.7s
  - agnes-2.0-flash  Agnes AI 2.0     大窗口      永久免费         免费备选
  - lite          讯飞星火 Spark Lite   8K 窗口   永久免费 2 QPS  不支持工具
  - nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free  OpenRouter  免费20RPM/50RPD  实测3.2s
  - openrouter/free  OpenRouter 路由档  自动选可用免费模型  兜底  国内可达  共享50次/天
  - deepseek-ai/DeepSeek-R1-0528-Qwen3-8B  硅基流动  推理模型  国内直连真免费  128K窗口  限速较严
  - THUDM/GLM-Z1-9B-0414  硅基流动  GLM 推理模型  国内直连真免费  128K窗口  1000RPM/50KTPM
  - Qwen/Qwen3-8B  硅基流动  Qwen3 推理  国内直连真免费  32K窗口  1000RPM/50KTPM

傀儡管理规范（v1.3）：
  1. 准入必测：新傀儡收编前必须 health 体检通过
  2. 定期体检：免费模型变动快（可能收费/断线），推荐每周体检
  3. 记录留档：体检结果自动写入同目录「傀儡健康档案.md」
  4. 并行使用：5 个傀儡可同时触发 5 个子代理任务（并发调本脚本）

难度感知路由（v1.4 新增）：
  任务先过 route 评估难度（简单/中等/困难），再按难度分配傀儡——
  简单 → lite/agnes-2.0（省成本）；中等 → glm-4-flash；困难 → agnes-2.5+glm 双交叉。
  依据：Dynamic Model Routing 综述（arXiv 2603.04445）难度感知范式，
  成本降 60% 质量仅差 1 分。

仲裁位 Judge（v1.4 新增）：
  双模型交叉不一致时，用第三个傀儡 judge 仲裁（A/B/一致），
  主模型只在 judge 也拿不准时才兜底——省主模型资源。
  依据：LLM-as-a-Judge 不确定性路由范式。

选型：**加工任务（分类/打标/摘要）优先 glm-4-flash / agnes-2.5-flash**（实测更准更稳）；
lite 仅限短文本高频轻量任务（2 QPS 限速，实测有轻微脑补倾向，不可用于关键判断）。

注意：这些模型在 WorkBuddy 主对话里大多不可用（agent 请求体 600KB+ 超限/触发限流），
本脚本绕开该问题——只发轻量请求，是它们正确的打开方式。

用法：
  python free_models.py models                         # 列出可用模型（傀儡池）
  python free_models.py health                         # 体检全部傀儡（并发）+ 写入记录
  python free_models.py health lite                    # 体检单个傀儡
  python free_models.py classify "文本" [--model X] [--cats "类别1,类别2"]  # 分类（可自定义类别）
  python free_models.py tags "文本" [--model X]        # 提取关键词标签
  python free_models.py summarize "文本" [--model X]    # 摘要（位置参数优先；也支持 < 文件.txt 管道）
  python free_models.py rewrite "原句" "风格" [--model X] # 改写
  python free_models.py route "任务文本" [--model X]   # 难度路由：评估难度+推荐傀儡（v1.4）
  python free_models.py judge "候选A" "候选B" [--model X] # 仲裁：A/B/一致（v1.4）
  python free_models.py chat "问题" [--model X]        # 自由问答
  python free_models.py translate "文本" [--model X]    # 翻译：中英互译（v1.6）
  python free_models.py proscons "主题" [--model X]     # 利弊分析：利/弊 分列（v1.6）
  python free_models.py explain "概念" [--model X]      # 通俗解释：大白话讲清概念（v1.6）
  python free_models.py extract "文本" [--model X]      # 要素提取：时间/主体/事件/金额/数字（v1.6）
  python free_models.py rate <任务组> <分数1-5> [--note "备注"]  # 调度档案质量评分（v1.7）

  --model 可选：glm-4-flash（默认）/ agnes-2.5-flash / agnes-2.0-flash / lite / nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free / openrouter/free / deepseek-ai/DeepSeek-R1-0528-Qwen3-8B / THUDM/GLM-Z1-9B-0414 / Qwen/Qwen3-8B
  --cats  仅 classify 生效：自定义类别列表，如 --cats "相关,不相关"
  --group 任务组名（v1.7）：批量分派同名归组，调度档案按组聚合评估

调度档案（v1.7）：每次干活命令自动追加同目录「调度档案.jsonl」
  （时间/命令/傀儡/输入长度/输出长度/耗时/退出码/任务组），任务收尾用 rate 补质量分。
  纪律：批量分派必带 --group，任务收尾必 rate。攒 ≥50 条后聚合出实证调度表。
  详见《Puppeteer范式研究简报_Ver2.0.0.md》§六。

输出完整性（v1.7）：classify 多行输入（≥2行）时自动检测输出行数，
  输出行数 < 输入行数 = 疑似截断 → 报错退出码 3（响亮失败，禁止静默截断）。
  批量分类单批 ≤20 行（经验阈值；超阈值预检告警）。

退出码：0=成功 1=配置/网络错误/体检有失败 2=参数错误 3=API错误（含截断检测，v1.7）
"""
import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.request
import urllib.error

# 控制台 UTF-8 输出：GBK 控制台（cmd/Git-Bash 默认）下 emoji（🔴/✅/❌）print 会 UnicodeEncodeError 崩溃
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass  # Python <3.7 或非文本流：忽略

# 各模型的任务级参数（窗口决定单次可处理的文本量，留安全余量）
# max_tokens：推理模型（agnes-2.5-flash）需留推理空间，加大配额
MODELS = {
    "lite":            {"max_chars": 10000,  "max_tokens": 800,  "desc": "讯飞星火 Spark Lite · 8K窗口 · 永久免费 · 2QPS(≈120RPM)"},
    "glm-4-flash":     {"max_chars": 100000, "max_tokens": 800,  "desc": "智谱 GLM-4-Flash · 128K窗口 · 免费（大请求体限流，RPM/TPM未公开）"},
    "agnes-2.5-flash": {"max_chars": 50000,  "max_tokens": 2000, "desc": "Agnes AI 2.5 Flash · 推理模型 · 永久免费 · 20RPM(限额按Key池化) · 国内站实测0.7s"},
    "agnes-2.0-flash": {"max_chars": 50000,  "max_tokens": 800,  "desc": "Agnes AI 2.0 Flash · 永久免费 · 20RPM · Starter 1500次/5h"},
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": {"max_chars": 30000, "max_tokens": 800, "desc": "OpenRouter Nemotron3 Nano · 免费20RPM/50RPD · 实测3.2s · 模型轮换快需周体检"},
    "openrouter/free": {"max_chars": 30000, "max_tokens": 800, "desc": "OpenRouter /free 路由档 · 20RPM+50RPD(充值$10+永久1000RPD) · 兜底 · 模型轮换快需周体检"},
    "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B": {"max_chars": 50000, "max_tokens": 2000, "desc": "硅基流动 DeepSeek-R1-0528-Qwen3-8B · 推理模型 · 国内直连真免费 · 128K窗口 · 限速较严(1000RPM/50KTPM)"},
    "THUDM/GLM-Z1-9B-0414": {"max_chars": 50000, "max_tokens": 2000, "desc": "硅基流动 GLM-Z1-9B-0414 · 推理模型 · 国内直连真免费 · 128K窗口 · 限速较严(1000RPM/50KTPM) · 与 R1 双保险"},
    "Qwen/Qwen3-8B": {"max_chars": 30000, "max_tokens": 2000, "desc": "硅基流动 Qwen3-8B · 推理模型 · 国内直连真免费 · 32K窗口 · 1000RPM/50KTPM · 质量考核全过 2026-08-23"},
}

# 暂停傀儡机制（备用）：未来收编消耗魔粒/限时额度的模型时，加 "paused": True 即自动拦截。
# 当前无暂停模型（qwen×2/魔搭×2 已于 2026-08-23 删除，信息备份在《免费AI模型API接入指南_傀儡池.md》）
PAUSED_MODELS = {k for k, v in MODELS.items() if v.get("paused")}
ACTIVE_MODELS = [k for k in MODELS if k not in PAUSED_MODELS]

TASKS = {
    "classify":  "你是一个文本分类器。只输出类别名称（2-5个字），不要解释。类别参考：财经/科技/电商/生活/教育/健康/娱乐/时政/其他。都不符合时输出'其他'。",
    "tags":      "你是一个关键词提取器。从文本中提取3-5个关键词标签，用顿号分隔，只输出标签本身。",
    "summarize": "你是一个摘要工具。用3-5句话概括输入文本的核心内容，保持客观，不添加原文没有的信息。",
    "rewrite":   "你是一个改写助手。保持原意不变，按照要求的风格改写。只输出改写结果。",
    "chat":      "你是免费模型助手。回答简洁准确，用中文。",
    "route":     "你是任务难度评估器。判断输入任务文本的复杂度，只输出一个词：简单/中等/困难。判断标准：简单=短文本、单点查询、无需推理；中等=需多步处理、有一定推理；困难=长文本、复杂推理、模糊目标或跨领域。不要解释。",
    "judge":     "你是仲裁者（Judge）。对比两个候选答案，判断哪个更准确、更完整、更符合事实。只输出：A 或 B 或 一致。不要解释。候选A和候选B用「候选A:」和「候选B:」标记。",
    "translate": "你是一个专业翻译。把输入文本翻译成另一种语言：中文输入翻成英文，英文输入翻成中文，其他语言译成中文。只输出译文，不要解释。",
    "proscons":  "你是利弊分析助手。针对输入的主题或选项，分别列出利（优点/收益）和弊（缺点/风险），每条一句，格式：\n利：...\n弊：...\n保持客观，不编造。",
    "explain":   "你是通俗解释者。用大白话解释输入的概念或术语，让完全外行的读者也能听懂。可用生活化类比，但必须准确。只输出解释，不要解释你在解释。",
    "extract":   "你是结构化信息提取器。从输入文本中提取关键要素：时间、主体、事件、金额、数字。按以下格式输出，找不到的写'无'：\n时间：\n主体：\n事件：\n金额：\n数字：",
}


# 环境变量模式下的默认端点（models.json 存在时以文件为准）
DEFAULT_URLS = {
    "glm-4-flash":     "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    "lite":            "https://spark-api-open.xf-yun.com/v1/chat/completions",
    "agnes-2.5-flash": "https://apihub.agnes-ai.cn/v1/chat/completions",
    "agnes-2.0-flash": "https://apihub.agnes-ai.cn/v1/chat/completions",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": "https://openrouter.ai/api/v1/chat/completions",
    "openrouter/free": "https://openrouter.ai/api/v1/chat/completions",
    "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B": "https://api.siliconflow.cn/v1/chat/completions",
    "THUDM/GLM-Z1-9B-0414": "https://api.siliconflow.cn/v1/chat/completions",
    "Qwen/Qwen3-8B": "https://api.siliconflow.cn/v1/chat/completions",
}


def fail(msg, code=1):
    """带退出码退出：API错误=3，配置/网络错误=1。消息保留在 SystemExit.args 供 health 记录。"""
    exc = SystemExit(msg)
    exc.code = code
    raise exc


def load_model(model_id):
    """从 ~/.workbuddy/models.json 读取模型配置（apiKey、url）"""
    env_key = f"API_KEY_{model_id.upper().replace('-', '_').replace('/', '_').replace(':', '_')}"
    if os.environ.get(env_key):
        return {"api_key": os.environ[env_key],
                "url": DEFAULT_URLS.get(model_id)}
    models_path = os.path.expanduser("~/.workbuddy/models.json")
    try:
        with open(models_path, encoding="utf-8") as f:
            models = json.load(f)
        cfg = next((m for m in models if m.get("id") == model_id), None)
        if not cfg:
            sys.exit(f"models.json 中未找到 id={model_id} 的配置", )
        url = cfg["url"]
        if not url.endswith("/chat/completions"):
            url = url.rstrip("/") + "/chat/completions"
        return {"api_key": cfg["apiKey"], "url": url}
    except FileNotFoundError:
        sys.exit(f"未找到 models.json，请配置 {model_id} 或设置环境变量 API_KEY_{model_id.upper()}")
    except json.JSONDecodeError:
        sys.exit("models.json 解析失败")


def call(model_id, system_prompt, user_text):
    """调用模型，返回文本结果。超长自动截断到模型窗口内。
    稳定性机制：强制直连（不读系统代理）+ 失败重试 1 次（限流/网络抖动）。"""
    global _LAST_RETRIES
    _LAST_RETRIES = 0
    cfg = load_model(model_id)
    model_cfg = MODELS[model_id]
    max_chars = model_cfg["max_chars"]
    if len(user_text) > max_chars:
        user_text = user_text[:max_chars] + f"\n…(已截断至{max_chars}字)"
    body = json.dumps({
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
        "max_tokens": model_cfg["max_tokens"],
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(cfg["url"], data=body, headers={
        "Authorization": "Bearer " + cfg["api_key"],
        "Content-Type": "application/json",
    })
    # 强制直连：国内 API 直连最稳，不受系统代理（7890）故障影响
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    last_err = None
    for attempt in range(2):  # 失败重试 1 次（间隔 2s）
        try:
            with opener.open(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            if attempt == 0 and e.code in (429, 500, 502, 503):
                last_err = f"API错误({e.code}): {detail}"
                _LAST_RETRIES += 1
                time.sleep(2)
                continue
            fail(f"API错误({e.code}): {detail}", 3)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = f"网络错误: {e}"
            if attempt == 0:
                _LAST_RETRIES += 1
                time.sleep(2)
                continue
            fail(last_err)
    else:
        fail(last_err or "调用失败", 3 if (last_err or "").startswith("API错误") else 1)

    # 兼容两种返回格式：讯飞 {code, choices} / 智谱、Agnes {choices}（错误时用 error 字段）
    if "error" in data:
        fail(f"API错误: {json.dumps(data['error'], ensure_ascii=False)[:300]}", 3)
    if data.get("code") not in (None, 0):
        fail(f"API错误(code={data.get('code')}): {data.get('message')}", 3)
    return data["choices"][0]["message"]["content"].strip()


# 体检记录文件（傀儡健康档案，追加写入）
HERE = os.path.dirname(os.path.abspath(__file__))
HEALTH_RECORD = os.path.join(HERE, "傀儡健康档案.md")
# 调度档案（v1.7）：每次干活命令自动追加一条 JSON，供事后聚合出实证调度表
DISPATCH_LOG = os.path.join(HERE, "调度档案.jsonl")
_LAST_RETRIES = 0  # 最近一次 call() 的重试次数（供调度档案记录）

# 批量分类经验安全阈值（2026-08-23 实测：45 行/23 行均致 glm-4-flash 输出截断，保守取 20）
CLASSIFY_BATCH_LIMIT = 20


def _log_dispatch(record):
    """追加一条调度记录到 调度档案.jsonl。日志失败只告警、不阻断主流程。"""
    try:
        with open(DISPATCH_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"⚠️ 调度档案写入失败: {e}", file=sys.stderr)


def _precheck(task, text, model):
    """输出预算预检（v1.7）：批量分类超经验阈值或估算输出超名义预算 → stderr 告警（不阻断）。"""
    if task != "classify":
        return
    n_lines = len([l for l in text.splitlines() if l.strip()])
    if n_lines > CLASSIFY_BATCH_LIMIT:
        print(f"⚠️ 预检：classify 单批 {n_lines} 行超经验安全阈值 {CLASSIFY_BATCH_LIMIT} 行——"
              f"{model} 输出预算可能不足（glm-4-flash 实测截断）。建议分批或换 agnes-2.5-flash/agnes-2.0-flash。",
              file=sys.stderr)
    est_out_tokens = n_lines * 10  # 每行类别名约 10 token（含余量）
    budget = MODELS[model]["max_tokens"] * 0.7
    if n_lines >= 2 and est_out_tokens > budget:
        print(f"⚠️ 预检：估算输出 ~{est_out_tokens} token 超 {model} 名义预算 ~{int(budget)} token，"
              f"输出可能被截断。建议分批。", file=sys.stderr)


_HEALTH_HEADER = "# 傀儡体检记录（傀儡健康档案）\n\n> 准入规则：新傀儡收编前必须体检通过；现有傀儡定期体检（推荐每周）。\n> **结构**：顶部 = 能力速查表（静态区，手动维护，体检后复核）；下方 = 体检时间序列（动态区，health 自动追加）。\n\n## 二、体检时间序列（自动追加，最新在末尾）\n\n| 时间 | 傀儡 | 状态 | 响应时间 | 备注 |\n|------|------|:---:|:---:|------|\n"


def run_health(model_id):
    """体检单个傀儡：连通性 + 功能测试（classify）+ 计时"""
    start = time.time()
    try:
        result = call(model_id, TASKS["classify"], "央行宣布降准0.5个百分点，释放长期资金约1万亿元")
        return {"model": model_id, "ok": True, "time": round(time.time() - start, 2), "note": f"classify→{result[:12]}"}
    except SystemExit as e:
        return {"model": model_id, "ok": False, "time": round(time.time() - start, 2), "note": str(e)[:60]}


def health(targets):
    """并发体检全部/指定傀儡，打印结果并追加写入体检记录"""
    print(f"傀儡体检 {len(targets)} 个（并发 4）…")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(run_health, m): m for m in targets}
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())
    results.sort(key=lambda r: list(MODELS).index(r["model"]))

    for r in results:
        mark = "✅" if r["ok"] else "❌"
        print(f"  {r['model']:<16} {mark} {r['time']:>6.2f}s  {r['note']}")

    ts = time.strftime("%Y-%m-%d %H:%M")
    lines = [f"| {ts} | {r['model']} | {'✅' if r['ok'] else '❌'} | {r['time']}s | {r['note']} |" for r in results]
    os.makedirs(os.path.dirname(HEALTH_RECORD), exist_ok=True)
    if not os.path.exists(HEALTH_RECORD):
        content = _HEALTH_HEADER + "\n".join(lines) + "\n"
    else:
        content = "\n".join(lines) + "\n"
    with open(HEALTH_RECORD, "a", encoding="utf-8") as f:
        f.write(content)

    print(f"\n体检结果已记录: {HEALTH_RECORD}")
    return 0 if all(r["ok"] for r in results) else 1


def _route_text(task_text, model="glm-4-flash"):
    """难度路由：评估任务难度，返回（难度, 推荐傀儡）。CLI 共用。"""
    difficulty = call(model, TASKS["route"], task_text).strip().rstrip("。")
    ROUTE_MAP = {
        "简单": "lite / agnes-2.0-flash（低成本快跑）",
        "中等": "glm-4-flash / agnes-2.0-flash（默认主力）",
        "困难": "agnes-2.5-flash + glm-4-flash（双交叉验证）",
    }
    rec = ROUTE_MAP.get(difficulty, "agnes-2.0-flash（默认）")
    return difficulty, rec


def _run_task(task, text, model="glm-4-flash", cats=None, style=None, text_b=None):
    """按任务类型执行，返回结果文本。CLI 共用。"""
    if task == "route":
        diff, rec = _route_text(text, model)
        return f"难度: {diff}\n推荐: {rec}"
    if task == "judge":
        pair = f"候选A: {text}\n候选B: {text_b or style or ''}"
        return call(model, TASKS["judge"], pair)
    sp = TASKS[task]
    if task == "classify" and cats:
        sp = f"你是一个文本分类器。只输出类别名称（2-5个字），不要解释。类别参考：{cats}。都不符合时输出'其他'。"
    if task == "rewrite" and style:
        sp += f" 改写风格：{style}。"
    return call(model, sp, text)


def _dispatch_record(task, model, text, out_text, code, t0, group):
    """构造一条调度档案记录（v1.7）"""
    return {
        "type": "dispatch",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "task": task,
        "model": model,
        "text_len": len(text or ""),
        "in_lines": len([l for l in (text or "").splitlines() if l.strip()]),
        "out_len": len(out_text or ""),
        "elapsed_ms": int((time.time() - t0) * 1000),
        "exit_code": code,
        "retry": _LAST_RETRIES,
        "group": group,
    }


def main():
    parser = argparse.ArgumentParser(description="免费模型子代理工具")
    parser.add_argument("task", nargs="?", help="models/health/rate/classify/tags/summarize/rewrite/chat/route/judge/translate/proscons/explain/extract")
    parser.add_argument("text", nargs="?", help="输入文本（rate 命令为任务组名）")
    parser.add_argument("style", nargs="?", help="rewrite 的风格要求 / judge 的候选B / rate 的分数")
    parser.add_argument("--model", default="glm-4-flash", choices=list(MODELS.keys()), help="模型（默认 glm-4-flash）")
    parser.add_argument("--cats", default=None, help="自定义类别列表（逗号分隔），仅 classify 生效，如 --cats '相关,不相关'")
    parser.add_argument("--group", default=None, help="任务组名（v1.7）：批量分派同名归组，调度档案按组聚合")
    parser.add_argument("--note", default=None, help="rate 命令的备注（v1.7）")
    args = parser.parse_args()

    if args.task == "models":
        print("可用模型（🔴=已暂停，不调用、不进全量体检）：")
        for mid, info in MODELS.items():
            mark = "🔴 " if mid in PAUSED_MODELS else "   "
            print(f"  {mark}{mid:<14} {info['desc']}")
        return 0
    if args.task == "health":
        if args.text in MODELS:
            if args.text in PAUSED_MODELS:
                print(f"⚠️ {args.text} 已暂停（消耗魔粒/限时额度），仅显式指定才体检，结果仅供参考")
            targets = [args.text]
        else:
            targets = ACTIVE_MODELS
        return health(targets)
    if args.task == "rate":
        group, score_raw = args.text, args.style
        if not group or not score_raw:
            print("用法: python free_models.py rate <任务组> <分数1-5> [--note \"备注\"]")
            return 2
        try:
            score = int(score_raw)
        except ValueError:
            print(f"分数须为 1-5 整数，实际：{score_raw}")
            return 2
        if not 1 <= score <= 5:
            print(f"分数范围 1-5，实际：{score}")
            return 2
        _log_dispatch({"type": "rating", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                       "group": group, "score": score, "note": args.note or ""})
        print(f"已评分: {group} → {score} 分" + (f"（{args.note}）" if args.note else ""))
        return 0
    # 暂停傀儡拦截：默认调用一律阻止，防止消耗魔粒/额度
    if args.task in TASKS and args.model in PAUSED_MODELS:
        print(f"🔴 {args.model} 已暂停（消耗魔粒/限时额度，非真免费），默认不调用。")
        print(f"如需使用请手动解锁（从 PAUSED_MODELS 移除该模型）。")
        return 2
    if args.task == "route":
        if not args.text:
            print("用法: python free_models.py route \"任务文本\" [--model X]")
            return 2
        t0 = time.time()
        try:
            difficulty, rec = _route_text(args.text, args.model)
        except SystemExit as e:
            _log_dispatch(_dispatch_record("route", args.model, args.text, "",
                                           e.code if isinstance(e.code, int) else 1, t0, args.group))
            raise
        print(f"难度: {difficulty}")
        print(f"推荐: {rec}")
        _log_dispatch(_dispatch_record("route", args.model, args.text,
                                       f"难度: {difficulty}", 0, t0, args.group))
        return 0
    if args.task == "judge":
        if not args.text or not args.style:
            print("用法: python free_models.py judge \"候选A\" \"候选B\" [--model X]")
            return 2
        t0 = time.time()
        try:
            verdict = _run_task("judge", args.text, args.model, text_b=args.style)
        except SystemExit as e:
            _log_dispatch(_dispatch_record("judge", args.model, args.text, "",
                                           e.code if isinstance(e.code, int) else 1, t0, args.group))
            raise
        print(verdict)
        _log_dispatch(_dispatch_record("judge", args.model, args.text, verdict, 0, t0, args.group))
        return 0
    if args.task not in TASKS:
        print(__doc__)
        return 2
    if args.text:
        user_text = args.text
    elif not sys.stdin.isatty():
        user_text = sys.stdin.read()
        if not user_text.strip():
            print(f"用法: python free_models.py {args.task} \"文本\" [--model {args.model}]（管道输入为空）")
            return 2
    else:
        print(f"用法: python free_models.py {args.task} \"文本\" [--model {args.model}]")
        return 2

    system_prompt = TASKS[args.task]
    in_lines = len([l for l in user_text.splitlines() if l.strip()])
    if args.task == "classify":
        cats_ref = args.cats or "财经/科技/电商/生活/教育/健康/娱乐/时政/其他"
        system_prompt = f"你是一个文本分类器。只输出类别名称（2-5个字），不要解释。类别参考：{cats_ref}。都不符合时输出'其他'。"
        if in_lines >= 2:
            system_prompt += (f" 输入共{in_lines}行，逐行分类：每行只输出一个类别名，"
                              f"输出必须恰好{in_lines}行，与输入逐行对应，不要编号、不要合并。")
    if args.task == "rewrite" and args.style:
        system_prompt += f" 改写风格：{args.style}。"

    _precheck(args.task, user_text, args.model)
    t0 = time.time()
    try:
        result = call(args.model, system_prompt, user_text)
    except SystemExit as e:
        _log_dispatch(_dispatch_record(args.task, args.model, user_text, "",
                                       e.code if isinstance(e.code, int) else 1, t0, args.group))
        raise

    # 截断检测（v1.7）：多行输入下输出行数 < 输入行数 = 疑似截断，响亮失败（退出码 3）
    if args.task == "classify" and in_lines >= 2:
        out_lines = len([l for l in result.splitlines() if l.strip()])
        if out_lines < in_lines:
            _log_dispatch(_dispatch_record(args.task, args.model, user_text, result, 3, t0, args.group))
            fail(f"输出疑似截断（输出 {out_lines} 行 < 输入 {in_lines} 行）：{args.model} 输出预算不足。"
                 f"请分批（单批 ≤{CLASSIFY_BATCH_LIMIT} 行）或换 agnes-2.5-flash/agnes-2.0-flash"
                 f"（见手册第十节注意事项 14/15）", 3)

    print(result)
    _log_dispatch(_dispatch_record(args.task, args.model, user_text, result, 0, t0, args.group))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        # SystemExit 带整数 code 时解释器不打印消息——统一在这里输出，保证失败信息响亮可见
        if e.args and isinstance(e.args[0], str):
            print(e.args[0], file=sys.stderr)
        sys.exit(e.code if isinstance(e.code, int) else 1)
