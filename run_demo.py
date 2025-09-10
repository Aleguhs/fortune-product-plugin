# run_demo.py —— 0依赖可运行Demo（规则 + 模板，输出 Markdown 和 JSON）
import csv, json, argparse, datetime, pathlib

MESSAGES = {
    "cn": {
        "opening": "嗨 {name} 👋 我是 MITAY 的命理小助手。我们用规则+模板免费生成解读。",
        "fortune_intro": "你的简要解读：",
        "picks_intro": "为你精选的 3 款：",
        "cta": "想要更个性化的选择，可以告诉我指甲长度/形状或预算。",
        "closing": "以上为规则引擎建议，仅作灵感参考，祝你顺利 💫",
    },
    "en": {
        "opening": "Hey {name} 👋 I’m MITAY’s fortune buddy. Free reading via rules + templates.",
        "fortune_intro": "Your quick read:",
        "picks_intro": "Your 3 style picks:",
        "cta": "For more personalization, tell me your nail length/shape or budget.",
        "closing": "Rules-based inspiration only. Shine on 💫",
    },
}

# 极简规则（可后续换成八字/梅花）
MONTH_TO_ELEMENT = {
    "1":"earth","2":"wood","3":"wood","4":"earth","5":"fire","6":"fire",
    "7":"earth","8":"metal","9":"metal","10":"earth","11":"water","12":"water"
}
GOAL_BIAS = {
    "career": ["fire","metal"],
    "wealth": ["metal","earth"],
    "love":   ["wood","water"],
    "health": ["water","wood"],
}

def load_styles(path="data/styles.csv"):
    rows=[]
    with open(path,"r",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def pick_elements(target_month:str, goal:str):
    m = int(target_month.split("-")[-1])
    month_elem = MONTH_TO_ELEMENT.get(str(m), "earth")
    favored = []
    seen = set()
    for e in GOAL_BIAS.get(goal, ["fire","metal"]) + [month_elem]:
        if e not in seen:
            favored.append(e); seen.add(e)
    return month_elem, favored

def pick_styles(favored, styles, k=3):
    bag=[s for s in styles if s["element"] in favored]
    if len(bag) < k:
        for s in styles:
            if s not in bag:
                bag.append(s)
    return bag[:k]

def render_markdown(lang, name, target_month, notes, picks):
    msg = MESSAGES["cn" if lang!="en" else "en"]
    lines=[]
    lines.append(f"**Chatbot:** {msg['opening'].format(name=name)}")
    lines.append(f"**Chatbot:** {msg['fortune_intro']}")
    for n in notes:
        lines.append(f"- {n}")
    lines.append(f"**Chatbot:** {msg['picks_intro']}")
    for i,s in enumerate(picks,1):
        price = f" £{s['price']}" if s.get("price") else ""
        lines.append(f"{i}. **{s['name']}**{price} — {s['copy']} _(element: {s['element']})_")
    lines.append(f"**Chatbot:** {msg['cta']}")
    lines.append(f"**Chatbot:** {msg['closing']}")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="Serena")
    ap.add_argument("--target_month", default="2025-09")       # 目标月份
    ap.add_argument("--goal", default="wealth",
                    choices=["career","wealth","love","health"])
    ap.add_argument("--lang", default="cn", choices=["cn","en"])
    args = ap.parse_args()

    styles = load_styles("data/styles.csv")
    month_elem, favored = pick_elements(args.target_month, args.goal)
    notes = [
        f"{args.target_month} 的月元素倾向 **{month_elem}**。" if args.lang=="cn"
        else f"Month {args.target_month} leans **{month_elem}**.",
        f"目标 **{args.goal}**，优先聚焦元素：{', '.join(favored)}。" if args.lang=="cn"
        else f"Focus **{args.goal}**, prioritize: {', '.join(favored)}."
    ]
    picks = pick_styles(favored, styles, k=3)

    out = {
        "name": args.name,
        "target_month": args.target_month,
        "goal": args.goal,
        "month_element": month_elem,
        "elements_considered": favored,
        "picks": picks,
        "generated_at": datetime.datetime.utcnow().isoformat()+"Z"
    }

    outdir = pathlib.Path("outputs"); outdir.mkdir(parents=True, exist_ok=True)
    (outdir/"recommend.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir/"recommend.md").write_text(render_markdown(args.lang, args.name, args.target_month, notes, picks), encoding="utf-8")
    print("✅ 已生成 outputs/recommend.json 和 outputs/recommend.md")

if __name__ == "__main__":
    main()
