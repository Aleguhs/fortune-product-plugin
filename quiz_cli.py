# quiz_cli.py  —— 命令行问答 Demo（双语，默认英文）
# 0 依赖：只用标准库。读取 data/styles.csv，输出到 outputs/ 目录。

import csv, json, datetime, pathlib, argparse

# ---------- Messages (EN & CN) ----------
MSG = {
    "en": {
        "welcome": "Hi! I’m MITAY’s fortune buddy. We’ll ask a few quick questions.",
        "choose_lang": "Language? [en/cn] (default en): ",
        "name": "What's your name or nickname?",
        "mode": "Choose method: [1] Birthdate  [2] Meihua (three random numbers)",
        "dob": "Enter birthdate (YYYY-MM-DD): ",
        "time": "Enter birth time (HH:MM, optional; Enter to skip): ",
        "nums": "Enter three numbers (comma-separated, e.g., 2,9,8): ",
        "target": "Which year-month do you want to check? (YYYY-MM, e.g., 2025-09): ",
        "goal": "Pick your focus (type keyword): career / wealth / health / emotion / love / study / social",
        "confirm": "Great, generating your reading...",
        "result_title": "Your quick reading",
        "month_elem": "Target month leans **{e}**.",
        "goal_line": "Focus **{g}** — prioritize: {fav}.",
        "picks_title": "Your 3 nail picks",
        "cta": "For more personalization, share your nail length/shape or budget.",
        "closing": "Note: This is rules-based inspiration, not professional advice.",
        "saved": "Saved: {j} and {m}",
        "invalid": "Input not recognized, please try again.",
    },
    "cn": {
        "welcome": "嗨！我是 MITAY 的命理小助手。我们会问你几个小问题。",
        "choose_lang": "选择语言？[en/cn]（默认 en）：",
        "name": "请输入你的名字或昵称：",
        "mode": "选择方式：[1] 出生日期  [2] 梅花易数（三个随机数字）",
        "dob": "请输入出生日期 (YYYY-MM-DD)：",
        "time": "请输入出生时间 (HH:MM，可选；直接回车跳过)：",
        "nums": "请输入三个数字（用逗号分隔，如 2,9,8）：",
        "target": "想查看哪一年哪一月？(YYYY-MM，例如 2025-09)：",
        "goal": "选择希望提升的方向（输入关键词）：career / wealth / health / emotion / love / study / social",
        "confirm": "好的，正在为你生成结果……",
        "result_title": "你的简要解读",
        "month_elem": "本月元素倾向 **{e}**。",
        "goal_line": "目标 **{g}** —— 建议优先聚焦：{fav}。",
        "picks_title": "为你精选的 3 款",
        "cta": "想要更个性化的选择，可以告诉我指甲长度/形状或预算。",
        "closing": "提示：以上为规则引擎灵感建议，不构成专业意见。",
        "saved": "已保存：{j} 和 {m}",
        "invalid": "输入无效，请重试。",
    }
}

# ---------- Very simple rules (can be replaced by real BaZi/Meihua later) ----------
MONTH_TO_ELEMENT = {
    "1":"earth","2":"wood","3":"wood","4":"earth","5":"fire","6":"fire",
    "7":"earth","8":"metal","9":"metal","10":"earth","11":"water","12":"water"
}
GOAL_BIAS = {
    "career": ["fire","metal"],
    "wealth": ["metal","earth"],
    "health": ["water","wood"],
    "emotion": ["water","earth"],
    "love":   ["wood","water"],
    "study":  ["wood","fire"],
    "social": ["earth","metal"],
}
# Meihua (toy): last digit -> trigram -> element
MEIHUA_LASTDIGIT_TO_ELEMENT = {0:"water",1:"metal",2:"metal",3:"fire",4:"wood",5:"wood",6:"water",7:"earth",8:"earth",9:"metal"}

# ---------- Core helpers ----------
def load_styles(path="data/styles.csv"):
    rows=[]
    with open(path,"r",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def month_element(ym: str) -> str:
    try:
        m = int(ym.split("-")[-1])
        return MONTH_TO_ELEMENT.get(str(m), "earth")
    except Exception:
        return "earth"

def favored_elements(goal: str, month_elem: str, extra: str | None = None):
    base = GOAL_BIAS.get(goal, ["fire","metal"])
    seq = base + [month_elem]
    if extra:
        seq = [extra] + seq
    seen=set(); out=[]
    for e in seq:
        if e not in seen:
            out.append(e); seen.add(e)
    return out

def meihua_element_from_nums(nums: list[int]) -> str:
    if not nums:
        return None
    last = int(str(nums[-1])[-1])
    return MEIHUA_LASTDIGIT_TO_ELEMENT.get(last, "earth")

def pick_styles(favored, styles, k=3):
    bag=[s for s in styles if s.get("element") in favored]
    if len(bag)<k:
        for s in styles:
            if s not in bag: bag.append(s)
    return bag[:k]

def render_md(lang, name, ym, month_elem_str, goal, favored, picks):
    m = MSG[lang]
    lines=[]
    lines.append(f"**Chatbot:** {m['result_title']}")
    lines.append(f"- " + m["month_elem"].format(e=month_elem_str))
    lines.append(f"- " + m["goal_line"].format(g=goal, fav=", ".join(favored)))
    lines.append(f"**Chatbot:** {m['picks_title']}")
    for i,s in enumerate(picks,1):
        price = f" £{s['price']}" if s.get("price") else ""
        lines.append(f"{i}. **{s['name']}**{price} — {s['copy']} _(element: {s['element']})_")
    lines.append(f"**Chatbot:** {m['cta']}")
    lines.append(f"**Chatbot:** {m['closing']}")
    return "\n".join(lines)

# ---------- CLI flow ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en", choices=["en","cn"], help="default en")
    args = ap.parse_args()
    lang = args.lang

    m = MSG[lang]
    print(m["welcome"])

    # language switch at runtime (optional)
    raw = input(m["choose_lang"]).strip().lower()
    if raw in ("en","cn"):
        lang = raw
        m = MSG[lang]

    name = input(m["name"]).strip() or "friend"

    mode = None
    while mode not in ("1","2"):
        mode = input(m["mode"] + " ").strip()
        if mode not in ("1","2"):
            print(m["invalid"])

    dob, btime, nums = None, None, []
    if mode == "1":
        dob = input(m["dob"]).strip()
        btime = input(m["time"]).strip() or None
    else:
        nums_str = input(m["nums"]).strip().replace("，",",")
        try:
            nums = [int(x.strip()) for x in nums_str.split(",") if x.strip()!=""]
        except Exception:
            nums = []

    ym = input(m["target"]).strip() or "2025-09"

    goal = None
    valid_goals = {"career","wealth","health","emotion","love","study","social"}
    while goal not in valid_goals:
        goal = input(m["goal"] + " ").strip().lower()
        if goal not in valid_goals:
            print(m["invalid"])

    print(m["confirm"])

    styles = load_styles("data/styles.csv")
    month_elem_str = month_element(ym)
    extra_elem = meihua_element_from_nums(nums) if nums else None  # if meihua chosen, include as extra bias
    favored = favored_elements(goal, month_elem_str, extra=extra_elem)
    picks = pick_styles(favored, styles, k=3)

    # assemble result
    out = {
        "name": name,
        "method": "birthdate" if mode=="1" else "meihua",
        "dob": dob, "birth_time": btime, "nums": nums,
        "target_month": ym,
        "goal": goal,
        "month_element": month_elem_str,
        "elements_considered": favored,
        "picks": picks,
        "generated_at": datetime.datetime.utcnow().isoformat()+"Z"
    }

    # save
    outdir = pathlib.Path("outputs"); outdir.mkdir(parents=True, exist_ok=True)
    stem = f"session_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    jpath = outdir / f"{stem}.json"
    mpath = outdir / f"{stem}.md"
    jpath.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    mpath.write_text(render_md(lang, name, ym, month_elem_str, goal, favored, picks), encoding="utf-8")

    print(m["saved"].format(j=str(jpath), m=str(mpath)))

if __name__ == "__main__":
    main()
