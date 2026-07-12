import json
import os
from datetime import datetime

MEMORY_FILE = "aegis_memory.json"

# Phrases that signal the user is correcting or teaching Aegis something
CORRECTION_TRIGGERS = [
    "no that's wrong", "no, that's wrong", "that's incorrect", "that's not right",
    "actually i", "actually, i", "remember that", "remember this", "from now on",
    "i prefer", "i like", "i don't like", "i hate", "always", "never do",
    "correction:", "fix that", "that's not what i meant", "don't say",
    "my name is", "call me", "i am a", "i work as", "i study"
]


def load_memory():
    """Load Aegis's memory from file"""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data.setdefault("conversations", [])
    data.setdefault("facts", {})
    data.setdefault("lessons", [])
    return data


def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def add_conversation(memory, role, content):
    memory["conversations"].append({
        "role": role,
        "content": content,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    if len(memory["conversations"]) > 50:
        memory["conversations"] = memory["conversations"][-50:]
    save_memory(memory)


def save_fact(memory, key, value):
    memory["facts"][key] = value
    save_memory(memory)


def add_lesson(memory, lesson_text):
    entry = {
        "lesson": lesson_text,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    if not any(l["lesson"] == lesson_text for l in memory["lessons"]):
        memory["lessons"].append(entry)
        if len(memory["lessons"]) > 100:
            memory["lessons"] = memory["lessons"][-100:]
        save_memory(memory)


def detect_correction(user_input):
    lowered = user_input.lower()
    return any(trigger in lowered for trigger in CORRECTION_TRIGGERS)


def get_conversation_history(memory):
    recent = memory["conversations"][-10:]
    return [{"role": m["role"], "content": m["content"]} for m in recent]


def get_facts_summary(memory):
    if not memory["facts"]:
        return ""
    facts = "\n".join([f"- {k}: {v}" for k, v in memory["facts"].items()])
    return f"\nWhat you know about the user:\n{facts}"


def get_lessons_summary(memory):
    if not memory["lessons"]:
        return ""
    recent_lessons = memory["lessons"][-20:]
    lessons = "\n".join([f"- {l['lesson']}" for l in recent_lessons])
    return f"\nLessons learned from past conversations (apply these, don't repeat past mistakes):\n{lessons}"