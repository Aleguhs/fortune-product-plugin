# app.py — Streamlit 一步一步问答（中/英）
# 先出“所选月份”的总结性解读 → 再按目标推荐产品+理由
# 新增：综合运势打分（/100）与“三条提升建议”
import streamlit as st
import csv, json, datetime, pathlib

# ========= 文案（中/英） =========
MSG = {
    "en": {
        "title": "MITAY · Fortune × Nails",
        "intro": "Answer a few questions. We’ll summarize your selected month’s energy, score it, then recommend products to boost your focus.",
        "lang": "Language",
        "next": "Next",
        "back": "Back",
        "start": "Start",
        "finish": "Generate",
        "name": "Your name / nickname",
        "method": "Choose method",
        "method_opts": ["Birthdate", "Meihua (three random numbers)"],
        "dob": "Birthdate (YYYY-MM-DD)",
        "time": "Birth time (HH:MM, optional)",
        "nums": "Enter three numbers (comma-separated, e.g., 2,9,8)",
        "target": "Which year-month to read? (YYYY-MM, e.g., 2025-09)",
        "goal": "What do you want to boost?",
        "goal_opts": ["career","wealth","health","emotion","love","study","social"],
        "summary_title": "Monthly Summary",
        "summary_hint": "This summary reflects the energy of your selected month.",
        "score": "Overall score",
        "suggestions": "Three improvement suggestions",
        "picks_title": "Recommended Products (3)",
        "download_md": "Download Markdown",
        "download_json": "Download JSON",
        "footer": "Note: rules-based inspiration, not professional advice.",
        "reason": "Reason",
        "month_energy": "Month {ym} leans **{elem}** element.",
        "goal_energy": "Your focus **{goal}** favors: {fav}.",
        "meihua_energy": "Your Meihua hint adds **{extra}** flavor.",
        "score_hint": "Score factors: month–goal fit, Meihua alignment, and product synergy.",
    },
    "cn": {
        "title": "MITAY · 命理 × 穿戴甲",
        "intro": "回答几个问题。我们会给出当月能量总结与评分，再根据你的目标推荐产品并说明原因。",
        "lang": "语言",
        "next": "下一步",
        "back": "上一步",
        "start": "开始",
        "finish": "生成结果",
        "name": "你的名字 / 昵称",
        "method": "选择方式",
        "method_opts": ["出生日期","梅花易数（三个数字）"],
        "dob": "出生日期 (YYYY-MM-DD)",
        "time": "出生时间 (HH:MM，可选)",
        "nums": "请输入三个数字（用逗号分隔，如 2,9,8）",
        "target": "想查看哪一年哪一月？(YYYY-MM，例如 2025-09)",
        "goal": "希望提升哪个方向？",
        "goal_opts": ["career","wealth","health","emotion","love","study","social"],
        "summary_title": "当月综合解读",
        "summary_hint": "此处仅反映你所选月份的能量概况。",
        "score": "综合评分",
        "suggestions": "三条提升建议",
        "picks_title": "推荐产品（3）",
        "download_md": "下载 Markdown",
        "download_json": "下载 JSON",
        "footer": "提示：规则引擎灵感建议，不构成专业意见。",
        "reason": "推荐理由",
        "month_energy": "所选月份 {ym} 的主导元素为 **{elem}**。",
        "goal_energy": "你的目标 **{goal}** 倾向元素：{fav}。",
        "meihua_energy": "梅花提示带来 **{extra}** 的辅助倾向。",
        "score_hint": "评分维度：月份与目标匹配度、梅花一致度、产品协同度。",
    }
}

# ========= 极简规则（可替换为八字/梅花专业算法） =========
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
MEIHUA_LASTDIGIT_TO_ELEMENT = {0:"water",1:"metal",2:"metal",3:"fire",4:"wood",5:"wood",6:"water",7:"earth",8:"earth",9:"metal"}

def month_element(ym: str) -> str:
    try:
        token = ym.strip()
        m = int(token.split("-")[-1]) if "-" in token else int(token)
        return MONTH_TO_ELEMENT.get(str(m), "earth")
    except Exception:
        return "earth"

def favored_elements(goal: str, month_elem: str, extra: str=None):
    base = GOAL_BIAS.get(goal, ["fire","metal"])
    seq = []
    seen=set()
    for e in (base + [month_elem] if not extra else [extra] + base + [month_elem]):
        if e and e not in seen:
            seen.add(e); seq.append(e)
    return seq or ["earth"]

def meihua_elem_from_nums(nums):
    try:
        if not nums: return None
        last = int(str(nums[-1])[-1])
        return MEIHUA_LASTDIGIT_TO_ELEMENT.get(last, "earth")
    except Exception:
        return None

def load_styles(path="data/styles.csv"):
    rows=[]
    with open(path,"r",encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({k: ("" if r[k] is None else str(r[k])) for k in r})
    return rows

def pick_styles(favored, styles, k=3):
    bag=[s for s in styles if (s.get("element") or "") in favored]
    if len(bag)<k:
        for s in styles:
            if s not in bag: bag.append(s)
    return bag[:k]

# ====== 新增：评分与建议 ======
def compute_score(goal, month_elem_str, extra_elem, picks, favored):
    """
    简单可解释的打分：
    - 基准 60
    - 月元素命中目标偏好 +10
    - 梅花元素命中目标偏好 +10
    - 推荐产品中，元素落在 favored 的占比（最多 +20）
    - 封顶/保底：[30,100]
    """
    score = 60
    if month_elem_str in favored: score += 10
    if extra_elem and (extra_elem in favored): score += 10
    if picks:
        hit = sum(1 for p in picks if (p.get("element") or "") in favored)
        score += int(20 * (hit / max(1,len(picks))))
    score = max(30, min(100, score))
    return score

def make_suggestions(lang, goal, month_elem_str, favored):
    """
    生成三条可执行建议：1条“月份元素型”，1条“目标领域型”，1条“习惯执行型”
    文案足够短，方便放在卡片里。
    """
    # 元素 → 行动语义（非常简化，可自行调整）
    elem_tips_en = {
        "wood":  "Set one growth target; ship small daily progress.",
        "fire":  "Increase visibility: share a weekly highlight.",
        "earth": "Stabilize routines; batch tasks every morning.",
        "metal": "Declutter and set sharp priorities; say no twice.",
        "water": "Protect recovery windows; hydrate and walk 20 min.",
    }
    elem_tips_cn = {
        "wood":  "设一个成长目标；每天小步前进并记录。",
        "fire":  "提高曝光度：每周公开一次成果。",
        "earth": "稳住作息；每天上午批量处理琐事。",
        "metal": "做减法与聚焦；本周学会拒绝两次。",
        "water": "保护修复窗口；多喝水并坚持 20 分钟步行。",
    }
    goal_tips_en = {
        "career":"Book a feedback chat; keep a weekly demo log.",
        "wealth":"Audit expenses; raise price or add upsell.",
        "health":"Schedule 3 workouts; track sleep 7 nights.",
