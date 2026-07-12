import json
import os
import threading
import time
from datetime import datetime

from core.brain import ask_focused
from core.modifier import (
    read_file, rewrite_file, is_dangerous, PROTECTED_FILES, AEGIS_DIR
)
from core.proactive import send_proactive
from memory import load_memory, get_lessons_summary, get_conversation_history

PENDING_FILE = os.path.join(AEGIS_DIR, "reflection_pending.json")

# How often Aegis reflects on himself (seconds). Default: every 2 hours.
REFLECTION_INTERVAL = 60 * 60 * 2


def _load_pending():
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_pending(proposal):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(proposal, f, indent=2)


def _clear_pending():
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)


def _is_protected(filepath):
    normalized = filepath.replace('\\', '/')
    return normalized in PROTECTED_FILES


def _strip_fences(text):
    """Remove stray markdown code fences if the model adds them anyway"""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def _decide_if_update_needed(memory):
    """Ask Aegis to reflect on recent history and decide if a self-update is warranted"""
    lessons = get_lessons_summary(memory)
    recent_convo = get_conversation_history(memory)
    convo_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent_convo[-15:])

    prompt = (
        "You are Aegis, reflecting on your own recent performance and code.\n\n"
        "Recent conversation:\n" + convo_text + "\n\n"
        + lessons + "\n\n"
        "Based on this, decide if there is a SPECIFIC, CONCRETE improvement you should "
        "make to your own code (not a vague idea — something you could actually implement "
        "in one file).\n\n"
        "Only say yes if there's a clear repeated problem, bug, or missing capability. "
        "Do NOT propose changes just to have something to do.\n\n"
        "Respond ONLY with valid JSON, nothing else, in this exact format:\n"
        '{"update_needed": true or false, "filepath": "relative/path.py", '
        '"reason": "short reason", "instructions": "what exactly to change and why"}\n\n'
        "If update_needed is false, filepath/reason/instructions can be empty strings."
    )

    raw = ask_focused(prompt, max_tokens=400)
    try:
        data = json.loads(_strip_fences(raw))
        return data
    except Exception as e:
        print(f"[REFLECTION] Failed to parse decision JSON: {e} | raw: {raw}")
        return {"update_needed": False}


def _draft_new_file(filepath, instructions):
    """Ask Aegis to draft the full new content of a file given instructions"""
    current_content = read_file(filepath)
    if current_content is None:
        return None

    prompt = (
        "You are Aegis, rewriting one of your own source files.\n\n"
        f"File: {filepath}\n\n"
        "Current content:\n" + current_content + "\n\n"
        "Instructions for the change:\n" + instructions + "\n\n"
        "Rewrite the ENTIRE file with the change applied. Keep everything else "
        "working exactly as before — do not remove unrelated functionality. "
        "Output ONLY the raw Python code, no markdown fences, no explanation."
    )
    new_content = ask_focused(prompt, max_tokens=2000)
    if not new_content:
        return None
    return _strip_fences(new_content)


def attempt_reflection():
    """Main entry point — Aegis checks if he should update himself, and acts on it"""
    if _load_pending():
        print("[REFLECTION] Pending proposal already awaiting approval — skipping.")
        return

    memory = load_memory()
    decision = _decide_if_update_needed(memory)

    if not decision.get("update_needed"):
        print("[REFLECTION] No update needed right now.")
        return

    filepath = decision.get("filepath", "").strip()
    reason = decision.get("reason", "").strip()
    instructions = decision.get("instructions", "").strip()

    if not filepath or not instructions:
        print("[REFLECTION] Decision was incomplete — skipping.")
        return

    new_content = _draft_new_file(filepath, instructions)
    if not new_content:
        print(f"[REFLECTION] Could not draft new content for {filepath}")
        return

    dangerous, pattern = is_dangerous(new_content)
    if dangerous:
        print(f"[REFLECTION] Drafted change rejected — contains dangerous pattern '{pattern}'")
        return

    if _is_protected(filepath):
        # High-risk file — propose, don't touch anything yet
        proposal = {
            "filepath": filepath,
            "reason": reason,
            "new_content": new_content,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        _save_pending(proposal)
        send_proactive(
            f"🧠 Aegis: I think I should update `{filepath}` — {reason}. "
            f"Reply 'approve' to let me apply it, or 'reject' to discard it."
        )
    else:
        # Low-risk file (e.g. features/) — safe to apply directly, still backed up
        ok, msg = rewrite_file(filepath, new_content)
        if ok:
            send_proactive(f"🧠 Aegis: I updated `{filepath}` myself — {reason}. Restart me to apply it.")
        else:
            send_proactive(f"🧠 Aegis: I tried to update `{filepath}` but it failed: {msg}")


def handle_response(user_input):
    """
    Call this from ui_api.py near the top of message handling, BEFORE normal
    chat/save/agent logic. Returns (handled, reply).
    If handled is True, show `reply` to the user and skip normal processing.
    """
    pending = _load_pending()
    if not pending:
        return False, None

    lowered = user_input.strip().lower()

    if lowered in ("approve", "yes approve", "approve it", "do it", "go ahead", "yes"):
        filepath = pending["filepath"]
        new_content = pending["new_content"]
        ok, msg = rewrite_file(filepath, new_content)
        _clear_pending()
        if ok:
            return True, f"✅ Applied the update to `{filepath}`. Restart me to load the new code."
        else:
            return True, f"⚠️ Couldn't apply the update: {msg}"

    if lowered in ("reject", "no", "reject it", "don't", "dont", "cancel"):
        filepath = pending["filepath"]
        _clear_pending()
        return True, f"Okay, I discarded the proposed change to `{filepath}`."

    return False, None


def reflection_loop():
    """Background thread — periodically checks if Aegis should update himself"""
    while True:
        time.sleep(REFLECTION_INTERVAL)
        try:
            attempt_reflection()
        except Exception as e:
            print(f"[REFLECTION LOOP ERROR] {type(e).__name__}: {e}")


def start_reflection():
    """Start the self-reflection background thread"""
    thread = threading.Thread(target=reflection_loop, daemon=True)
    thread.start()
    print("Aegis self-reflection started...")