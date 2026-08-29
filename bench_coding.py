# -*- coding: utf-8 -*-
"""编程类省token实测：对比「主模型直写」vs「agnes-2.5写 + 主模型校验」"""
import json, os, sys, time, urllib.request, urllib.error

MODELS_CFG = None

def load_cfg(model_id):
    global MODELS_CFG
    if MODELS_CFG is None:
        with open(os.path.expanduser("~/.workbuddy/models.json"), encoding="utf-8") as f:
            MODELS_CFG = {m["id"]: m for m in json.load(f)}
    cfg = MODELS_CFG[model_id]
    url = cfg["url"]
    if not url.endswith("/chat/completions"):
        url = url.rstrip("/") + "/chat/completions"
    return {"api_key": cfg["apiKey"], "url": url}

def call(model_id, system_prompt, user_text, max_tokens=2000):
    """返回 (文本, usage)"""
    cfg = load_cfg(model_id)
    body = json.dumps({
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
        "max_tokens": max_tokens,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(cfg["url"], data=body, headers={
        "Authorization": "Bearer " + cfg["api_key"],
        "Content-Type": "application/json",
    })
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for attempt in range(3):
        try:
            with opener.open(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:200]
            if attempt < 2 and e.code in (429, 500, 502, 503):
                print(f"  ⚠️ {model_id} API {e.code}，重试 {attempt+1}/3…", file=sys.stderr)
                time.sleep(3)
                continue
            raise RuntimeError(f"{model_id} API错误({e.code}): {detail}")
        except Exception as e:
            if attempt < 2:
                print(f"  ⚠️ {model_id} 网络错误 {e}，重试…", file=sys.stderr)
                time.sleep(3)
                continue
            raise RuntimeError(f"{model_id} 网络错误: {e}")
    if "error" in data:
        raise RuntimeError(f"{model_id} 返回错误: {json.dumps(data['error'], ensure_ascii=False)[:200]}")
    usage = data.get("usage", {})
    text = data["choices"][0]["message"]["content"].strip()
    return text, usage

# 3 个简单编程任务
TASKS = [
    {
        "name": "排序函数",
        "prompt": "写一个 Python 函数 quick_sort(arr)，实现快速排序，返回排序后的新列表（不修改原列表）。只要代码，不要解释。",
    },
    {
        "name": "爬虫片段",
        "prompt": "用 Python 写一个函数 fetch_title(url)，用 requests 请求该 URL，从 HTML 中提取 <title> 标签文本返回。假设 requests 已安装。只要代码，不要解释。",
    },
    {
        "name": "数据处理",
        "prompt": "用 Python 写一个函数 process_csv(path)，用 csv 模块读取 CSV 文件（第一行是表头：name,age,city），统计每个 city 的人数，返回 {city: count} 字典。只要代码，不要解释。",
    },
]

WRITE_SYS = "你是一个 Python 程序员。按用户要求写代码。只输出代码本身，不要任何解释、注释说明或 Markdown 代码块标记。"
CHECK_SYS = "你是代码审查员。检查用户给出的 Python 代码是否正确：语法是否正确、逻辑是否完整、能否直接运行。只输出：正确 或 错误+问题描述（一句话）。不要输出修复后的代码。"

def main():
    WRITER = "agnes-2.5-flash"   # 傀儡写代码
    CHECKER = "deepseek-v4-flash-0731"   # 真实主模型（用户当前 WorkBuddy 会话驱动模型）
    results = []
    for task in TASKS:
        name = task["name"]
        print(f"\n===== {name} =====")
        # 路径A：主模型直写（基线）
        t0 = time.time()
        direct_text, direct_usage = call(CHECKER, WRITE_SYS, task["prompt"], max_tokens=1200)
        direct_t = time.time() - t0
        dp = direct_usage.get("prompt_tokens", 0)
        dc = direct_usage.get("completion_tokens", 0)
        # 路径B：傀儡写
        t0 = time.time()
        puppet_text, puppet_usage = call(WRITER, WRITE_SYS, task["prompt"], max_tokens=1200)
        puppet_t = time.time() - t0
        pp = puppet_usage.get("prompt_tokens", 0)
        pc = puppet_usage.get("completion_tokens", 0)
        # 路径B：主模型校验傀儡产出
        t0 = time.time()
        check_text, check_usage = call(CHECKER, CHECK_SYS, puppet_text, max_tokens=200)
        check_t = time.time() - t0
        cp = check_usage.get("prompt_tokens", 0)
        cc = check_usage.get("completion_tokens", 0)
        # 汇总
        direct_total = dp + dc
        puppet_total = (pp + pc) + (cp + cc)
        save_pct = (direct_total - puppet_total) / direct_total * 100 if direct_total else 0
        verdict = "✅正确" if check_text.startswith("正确") else f"⚠️{check_text[:60]}"
        print(f"  直写:      prompt={dp:>6} completion={dc:>6} total={direct_total:>6}  {direct_t:.1f}s")
        print(f"  傀儡写:    prompt={pp:>6} completion={pc:>6}  {puppet_t:.1f}s")
        print(f"  校验:      prompt={cp:>6} completion={cc:>6}  {check_t:.1f}s")
        print(f"  傀儡total: {puppet_total:>6} | 省total {save_pct:+.1f}% | 校验结论: {verdict}")
        results.append({
            "task": name, "direct_total": direct_total, "puppet_total": puppet_total,
            "save_pct": round(save_pct, 1), "verdict": check_text[:60], "puppet_completion": pc,
        })
    print("\n===== 汇总 =====")
    for r in results:
        print(f"{r['task']}: 直写 {r['direct_total']} → 傀儡+校验 {r['puppet_total']} | 省 {r['save_pct']:+.1f}% | {r['verdict']}")

if __name__ == "__main__":
    main()
