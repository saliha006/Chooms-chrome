"""What Pix says when asked ("Hey Pix, what do you see now?"): built from facts the cell already has, so the
answer is instant, works offline and is always true. run.py gathers the facts; this only words them.
"""

DOING = {
    "IDLE": "waiting to start", "DRIVE": "driving over to the plates", "LOCATE": "looking for the next brick",
    "PICK": "picking up a brick", "VERIFY_GRASP": "checking my grip", "INSPECT": "inspecting a brick",
    "DECIDE": "deciding where it goes", "REINSPECT": "taking a second look", "PLACE": "putting a brick in its bowl",
    "VERIFY_PLACE": "checking it landed in the bowl", "LOG": "writing it down", "HOME": "heading home",
    "HOLD": "waiting for something to move out of my way", "PAUSE_HUMAN": "waiting for a hand",
    "DANCE": "dancing", "DONE": "all done", "STOPPED": "stopped", "E-STOP": "stopped: my motors are off",
}
BOWL = {"perfect": "purple", "defective": "orange"}


def _a(name: str) -> str:
    return ("an " if name[0] in "aeiou" else "a ") + name


def _n(x: float) -> str:
    return f"{x:.2f}"


def _last_look(facts: dict) -> str | None:
    s = facts.get("signal")
    if s is None:
        return None
    if s["label"] == "perfect":
        why = f"under my {_n(s['t_low'])} line, so it looks clean"
    elif s["label"] == "defective":
        why = f"over my {_n(s['t_high'])} line" + (f", with a mark at the {s['where'].replace('-', ' ')}" if s.get("where") else "")
    else:
        why = "between my two lines, so I'm not sure yet"
    return f"the last brick scored {_n(s['score'])}, {why}"


def answer(meaning: str, facts: dict) -> str:
    doing = DOING.get(facts.get("state", "IDLE"), "working")
    look = _last_look(facts)
    obstacles = facts.get("obstacles", 0)
    if meaning == "see":
        parts = []
        sight = facts.get("sight")
        if sight and sight["name"] != "unknown":
            parts.append(f"I can see {_a(sight['name'])} in front of my camera.")
        elif sight:
            parts.append("There's something in front of my camera I don't recognise"
                         + (f". My best guess is {_a(sight['guess'])}." if sight.get("guess") else "."))
        parts.append(f"Right now I'm {doing}.")
        parts.append(f"{look[0].upper()}{look[1:]}." if look else "I haven't inspected a brick yet.")
        if obstacles:
            parts.append("There's also something on the plates that isn't a brick, so I'm leaving it alone.")
        return " ".join(parts)
    if meaning == "tally":
        t = facts.get("tally", {})
        n = facts.get("sorted", 0)
        if not n:
            return "None sorted yet. Give me a moment."
        extra = f", and {t.get('rechecked', 0)} needed a second look" if t.get("rechecked") else ""
        return f"I've sorted {n}: {t.get('perfect', 0)} perfect and {t.get('defective', 0)} defective{extra}."
    if meaning == "why":
        decided = facts.get("decided")
        if look is None or decided not in BOWL:
            return "I haven't made a call yet. Ask me again after the first brick."
        return f"Because {look}. That's why it went in the {BOWL[decided]} bowl."
    if meaning == "doing":
        return f"I'm {doing}."
    if meaning == "who":
        return ("I'm Pix. I find the defects in bricks, sort them into the right bowl and explain myself, "
                "which is more than most coworkers do. Also, I look great in a hat.")
    return "Sorry, I only speak brick. Ask me what I see, how many I've sorted, or why I chose that bowl."
