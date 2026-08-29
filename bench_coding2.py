# -*- coding: utf-8 -*-
"""编程类省token实测·长输入场景：对比「主模型直写」vs「agnes-2.5写 + 主模型校验」"""
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
            with opener.open(req, timeout=120) as resp:
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
    return data["choices"][0]["message"]["content"].strip(), usage

# 长代码样本（~100 行，含 2 个故意 bug：除零未保护、越界索引）
LONG_CODE = '''import os
import re
from datetime import datetime

class LogAnalyzer:
    def __init__(self, log_dir):
        self.log_dir = log_dir
        self.entries = []

    def load(self):
        for fname in os.listdir(self.log_dir):
            path = os.path.join(self.log_dir, fname)
            if not fname.endswith(".log"):
                continue
            with open(path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.match(r"\\[(\\S+) (\\S+)\\] (.*)", line.strip())
                    if m:
                        ts, level, msg = m.groups()
                        self.entries.append({"ts": ts, "level": level, "msg": msg, "file": fname})

    def error_rate(self):
        total = len(self.entries)
        errs = sum(1 for e in self.entries if e["level"] == "ERROR")
        return errs / total

    def by_level(self):
        out = {}
        for e in self.entries:
            out[e["level"]] = out.get(e["level"], 0) + 1
        return out

    def recent(self, n=10):
        return sorted(self.entries, key=lambda e: e["ts"], reverse=True)[:n]

    def grep(self, keyword):
        return [e for e in self.entries if keyword in e["msg"]]

    def daily_summary(self):
        days = {}
        for e in self.entries:
            day = e["ts"][:10]
            if day not in days:
                days[day] = {"total": 0, "errors": 0}
            days[day]["total"] += 1
            if e["level"] == "ERROR":
                days[day]["errors"] += 1
        for day in days:
            days[day]["rate"] = days[day]["errors"] / days[day]["total"]
        return days

    def slowest_hour(self):
        hours = {}
        for e in self.entries:
            h = e["ts"][11:13]
            hours[h] = hours.get(h, 0) + 1
        if not hours:
            return None
        return max(hours, key=hours.get)

    def cleanup(self, keep_days=7):
        cutoff = datetime.now()
        removed = 0
        for e in self.entries:
            try:
                dt = datetime.strptime(e["ts"], "%Y-%m-%d %H:%M:%S")
                if (cutoff - dt).days > keep_days:
                    removed += 1
            except ValueError:
                pass
        return removed

    def stats(self):
        return {
            "total": len(self.entries),
            "files": len(set(e["file"] for e in self.entries)),
            "levels": self.by_level(),
            "error_rate": round(self.error_rate() * 100, 2),
        }

    def render(self):
        lines = []
        for e in self.entries[:100]:
            lines.append(f"{e['ts']} [{e['level']}] {e['msg']}")
        return "\\n".join(lines)
'''

# 长输入任务：改 bug + 加功能（输入 100 行代码，输出是修改说明+代码片段）
LONG_TASKS = [
    {
        "name": "长代码审查修bug",
        "prompt": f"下面是 LogAnalyzer 类的完整代码（约100行）。它有2个 bug：① error_rate() 当 entries 为空时会除零；② daily_summary() 里 ts 格式解析可能不一致导致 KeyError。请：1) 指出所有 bug 位置 2) 给出修复后的完整类代码。只要修复后的完整代码，不要解释。\n\n代码：\n{LONG_CODE}",
    },
    {
        "name": "长代码加新功能",
        "prompt": f"下面是 LogAnalyzer 类的完整代码（约100行）。请给它新增一个方法 top_errors(n=5)：返回出现次数最多的 n 个 ERROR 消息文本（去重，按次数降序）。要求：复用现有结构，只输出新增方法的完整代码 + 说明插入位置。不要重复输出整个类。\n\n代码：\n{LONG_CODE}",
    },
]

WRITE_SYS = "你是一个 Python 程序员。按用户要求写代码。只输出代码本身，不要任何解释或 Markdown 代码块标记。"
CHECK_SYS = "你是代码审查员。检查用户给出的 Python 代码：语法是否正确、逻辑是否完整、能否直接运行。只输出：正确 或 错误+问题描述（一句话）。不要输出修复后的代码。"

def main():
    WRITER = "agnes-2.5-flash"
    CHECKER = "deepseek-v4-flash-0731"   # 真实主模型（用户当前 WorkBuddy 会话驱动模型）
    results = []
    for task in LONG_TASKS:
        name = task["name"]
        print(f"\n===== {name} =====")
        # 输入长度参考
        print(f"  输入文本长度: {len(task['prompt'])} 字符")
        # 路径A：主模型直写（基线，deepseek）——completion 触顶说明 max_tokens 不够，放宽到 5000
        t0 = time.time()
        direct_text, direct_usage = call(CHECKER, WRITE_SYS, task["prompt"], max_tokens=5000)
        direct_t = time.time() - t0
        dp, dc = direct_usage.get("prompt_tokens", 0), direct_usage.get("completion_tokens", 0)
        # 路径B：傀儡写（agnes-2.5）——推理模型长任务 reasoning 吃满预算会空输出，加大 max_tokens
        t0 = time.time()
        puppet_text, puppet_usage = call(WRITER, WRITE_SYS, task["prompt"], max_tokens=4000)
        if not puppet_text.strip():
            print("  ⚠️ agnes-2.5 空输出（reasoning 吃满预算），重试一次…")
            puppet_text, puppet_usage = call(WRITER, WRITE_SYS, task["prompt"], max_tokens=6000)
        puppet_t = time.time() - t0
        pp, pc = puppet_usage.get("prompt_tokens", 0), puppet_usage.get("completion_tokens", 0)
        # 路径B：主模型校验（glm-4-flash）
        print(f"  傀儡输出长度: {len(puppet_text)} 字符, 前80字: {puppet_text[:80]!r}")
        if not puppet_text.strip():
            print("  ⚠️ 傀儡空输出，跳过校验（标记为失败）")
            check_text, check_usage = "错误: 傀儡空输出", {"prompt_tokens": 0, "completion_tokens": 0}
            check_t = 0
        else:
            t0 = time.time()
            check_text, check_usage = call(CHECKER, CHECK_SYS, puppet_text[:15000], max_tokens=300)
            check_t = time.time() - t0
        cp, cc = check_usage.get("prompt_tokens", 0), check_usage.get("completion_tokens", 0)
        direct_total = dp + dc
        puppet_total = (pp + pc) + (cp + cc)
        save_pct = (direct_total - puppet_total) / direct_total * 100 if direct_total else 0
        verdict = "✅正确" if check_text.startswith("正确") else f"⚠️{check_text[:100]}"
        print(f"  直写:      prompt={dp:>6} completion={dc:>6} total={direct_total:>6}  {direct_t:.1f}s")
        print(f"  傀儡写:    prompt={pp:>6} completion={pc:>6}  {puppet_t:.1f}s")
        print(f"  校验:      prompt={cp:>6} completion={cc:>6}  {check_t:.1f}s")
        print(f"  傀儡total: {puppet_total:>6} | 省total {save_pct:+.1f}% | 校验结论: {verdict}")
        results.append({
            "task": name, "direct_total": direct_total, "puppet_total": puppet_total,
            "save_pct": round(save_pct, 1), "verdict": check_text[:80],
            "input_chars": len(task["prompt"]),
        })
    print("\n===== 汇总 =====")
    for r in results:
        print(f"{r['task']} (输入{r['input_chars']}字): 直写 {r['direct_total']} → 傀儡+校验 {r['puppet_total']} | 省 {r['save_pct']:+.1f}% | {r['verdict']}")

if __name__ == "__main__":
    main()
