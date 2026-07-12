import threading
import queue
from core.brain import build_system_prompt, ask, ask_code, ask_code_with_context, ask_focused
from core.voice import speak
from core.modifier import list_all_files, read_file, rewrite_file, create_feature_file, is_dangerous, backup_file
from self_awareness import AEGIS_IDENTITY, get_file_for_feature
from memory import (
    load_memory, add_conversation, get_conversation_history,
    get_facts_summary, get_lessons_summary, add_lesson, detect_correction
)
from search import web_search, should_search
from core.proactive import start_proactive, set_callback, mark_activity
from core.agent import handle_task
from self_awareness import is_agent_task
from core.reflection import handle_response as handle_reflection_response, start_reflection

memory = load_memory()
last_reply = ""
pending_changes = {}

# Proactive message queue
_proactive_queue = queue.Queue()

def _on_proactive_message(message):
    _proactive_queue.put(message)

set_callback(_on_proactive_message)
start_proactive()
start_reflection()


def extract_lesson(user_input, last_aegis_reply):
    prompt = (
        "The user just corrected or taught the assistant something.\n\n"
        "Assistant's last reply: \"" + last_aegis_reply + "\"\n"
        "User's correction: \"" + user_input + "\"\n\n"
        "Write ONE short instruction under 20 words the assistant should remember. "
        "Output ONLY the instruction. If not a correction, output exactly: NONE"
    )
    result = ask_focused(prompt, max_tokens=60)
    return None if result.upper() == "NONE" else result


def translate_to_hindi(text):
    prompt = (
        "Translate into natural casual spoken Hindi like an educated person "
        "from Delhi or Mumbai speaks — mix English words naturally where people do "
        "(ok, matlab, basically etc). Output ONLY the Hindi translation.\n\n"
        "Text: \"" + text + "\""
    )
    return ask_focused(prompt, max_tokens=300)

def self_test_file(filename):
    """
    After saving, Aegis tests the file itself.
    Checks for syntax errors before declaring success.
    If broken — auto restores backup.
    """
    import ast
    from core.modifier import read_file as rf

    content = rf(filename)
    if not content:
        return {"valid": False, "error": "Could not read saved file"}

    # Only test Python files
    if not filename.endswith(".py"):
        return {"valid": True, "error": None}

    try:
        ast.parse(content)
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Line {e.lineno}: {e.msg}"
        }

def handle_self_modification(user_input, reply):
    """
    Aegis already knows which file handles what via FILE_MAP.
    Reads ONLY that one file, plans the change, waits for save.
    """
    global pending_changes

    # Save command — apply pending changes
    if user_input.strip().lower() in ["save", "save it", "yes save", "apply", "confirm"]:
        if not pending_changes:
            return reply + "\n\n⚠️ No pending changes to save."

        filename = pending_changes.get("filename")
        rewritten = pending_changes.get("rewritten")
        summary = pending_changes.get("summary")

        if not filename or not rewritten:
            pending_changes = {}
            return "⚠️ Pending change is incomplete. Try again."

        dangerous, pattern = is_dangerous(rewritten)
        if dangerous:
            pending_changes = {}
            return f"🛡️ Can't save — contains '{pattern}' which could damage me."

        backup_file(filename)
        success, msg = rewrite_file(filename, rewritten)
        pending_changes = {}

        # Self-test — check if saved file has valid Python syntax
        test_result = self_test_file(filename)
        if not test_result["valid"]:
            # Syntax error — auto restore backup!
            from core.modifier import restore_latest_backup
            restore_latest_backup(filename)
            return (
                f"⚠️ I saved `{filename}` but found a syntax error:\n"
                f"{test_result['error']}\n\n"
                f"🔄 Auto-restored backup — file is safe.\n"
                f"Let me try again with a fix."
            )

        return (
            f"Changed in `{filename}`:\n{summary}\n\n"
            f"{msg}\n"
            f"✅ Self-test passed — syntax is valid!\n"
            f"Restart Aegis to apply changes."
        )

    # Detect code block type
    if "```python" in reply:
        code_marker = "```python"
    elif "```html" in reply:
        code_marker = "```html"
    else:
        code_marker = "```css"

    parts = reply.split(code_marker)
    result_reply = parts[0].strip()

    for part in parts[1:]:
        if "```" not in part:
            continue

        new_code = part.split("```")[0].strip()

        # Step 1 — Aegis already knows which file handles this feature
        filename = get_file_for_feature(user_input)

        # Step 2 — Read ONLY that one file
        file_content = read_file(filename)
        if not file_content:
            result_reply += f"\n\n⚠️ Could not read {filename}."
            continue

        # Step 3 — Focused plan prompt
        plan_prompt = (
            "You are Aegis. Add a feature to ONE of your own files.\n\n"
            "User request: " + user_input + "\n\n"
            "File to update: " + filename + "\n\n"
            "Current content of " + filename + ":\n" + file_content + "\n\n"
            "New feature code:\n" + new_code + "\n\n"
            "YOUR TASK:\n"
            "1. Rewrite the ENTIRE " + filename + " with the feature properly integrated\n"
            "2. Keep ALL existing functionality — do not remove anything\n"
            "3. Write 2-4 bullet points of exactly what you changed\n\n"
            "Respond in EXACTLY this format, nothing else:\n"
            "CHANGES:\n"
            "- bullet 1\n"
            "- bullet 2\n"
            "REWRITTEN_FILE_START\n"
            "(complete rewritten file here)\n"
            "REWRITTEN_FILE_END"
        )

        decision_text = ask_focused(plan_prompt, max_tokens=4096)

        # Step 4 — Parse changes and rewritten file
        changes = []
        rewritten = ""
        parsing_changes = False

        for line in decision_text.split("\n"):
            if line.strip() == "CHANGES:":
                parsing_changes = True
            elif parsing_changes and line.strip().startswith("-"):
                changes.append(line.strip())
            elif "REWRITTEN_FILE_START" in line:
                parsing_changes = False

        if "REWRITTEN_FILE_START" in decision_text and "REWRITTEN_FILE_END" in decision_text:
            rewritten = decision_text.split("REWRITTEN_FILE_START")[1].split("REWRITTEN_FILE_END")[0].strip()

        if not rewritten:
            result_reply += "\n\n⚠️ Could not generate rewrite. Try again."
            continue

        # Step 5 — Store as pending
        changes_summary = "\n".join(changes) if changes else "Feature integrated."
        pending_changes = {
            "filename": filename,
            "rewritten": rewritten,
            "summary": changes_summary
        }

        result_reply += (
            f"\n\n📋 Plan for `{filename}`:\n\n"
            f"📝 What changes:\n{changes_summary}\n\n"
            f"Type **save** to apply, or ask me to adjust first."
        )

    return result_reply


class Api:
    def send_message(self, user_input, voice_on, hindi_on):
        global last_reply
        user_input = user_input.strip()
        if not user_input:
            return {"reply": "", "lesson": None}

        # Reset the boredom/idle timer — user is here, Aegis isn't lonely right now
        mark_activity()

        # Handle any pending self-reflection proposal FIRST — approve/reject
        # must be caught before anything else tries to interpret them.
        handled, reflection_reply = handle_reflection_response(user_input)
        if handled:
            add_conversation(memory, "user", user_input)
            add_conversation(memory, "assistant", reflection_reply)
            last_reply = reflection_reply
            return {"reply": reflection_reply, "lesson": None}

        # Handle save command first
        if user_input.strip().lower() in ["save", "save it", "yes save", "apply", "confirm"]:
            reply = handle_self_modification(user_input, "")
            add_conversation(memory, "user", user_input)
            add_conversation(memory, "assistant", reply)
            last_reply = reply
            return {"reply": reply, "lesson": None}

        # Agent mode — Aegis executes real tasks
        if is_agent_task(user_input):
            add_conversation(memory, "user", user_input)
            reply = handle_task(user_input)
            add_conversation(memory, "assistant", reply)
            last_reply = reply
            if voice_on:
                if hindi_on:
                    speak(translate_to_hindi(reply), hindi=True)
                else:
                    speak(reply, hindi=False)
            return {"reply": reply, "lesson": None}

        # Check for lessons from corrections
        lesson_learned = None
        if detect_correction(user_input) and last_reply:
            lesson = extract_lesson(user_input, last_reply)
            if lesson:
                add_lesson(memory, lesson)
                lesson_learned = lesson

        add_conversation(memory, "user", user_input)

        # Attach file context if modification requested
        extra = ""
        modify_keywords = ["add", "create", "modify", "change", "edit",
                           "update", "feature", "fix", "yourself", "your code"]
        if any(kw in user_input.lower() for kw in modify_keywords):
            relevant_file = get_file_for_feature(user_input)
            content = read_file(relevant_file)
            if content:
                extra += f"\n\nRelevant file ({relevant_file}):\n{content[:2000]}"

        # Web search if needed
        search_context = ""
        if should_search(user_input):
            search_context = "\n\n" + web_search(user_input)

        history = get_conversation_history(memory)
        messages = [
            {"role": "system", "content": build_system_prompt(memory, extra + search_context)}
        ] + history

        # Use multi-model for complex questions
        complex_keywords = [
            "explain", "why", "how does", "what is", "difference between",
            "compare", "best way", "should i", "help me understand",
            "prove", "theory", "science", "history", "math"
        ]
        # Any language — Python (AEGIS), Lua (Roblox), web stack (prototypes)
        code_keywords = [
            "code", "script", "function", "python", "lua", "javascript",
            "html", "css", "roblox", "algorithm", "debug", "syntax",
            "class ", "def ", "variable", "write a program", "fix this bug"
        ]
        is_code_request = any(kw in user_input.lower() for kw in code_keywords)
        use_multi = any(kw in user_input.lower() for kw in complex_keywords) or is_code_request

        if is_code_request and use_multi:
            reply = ask_code_with_context(user_input)
        else:
            reply = ask(messages, use_multi_model=use_multi)
        reply = handle_self_modification(user_input, reply)

        add_conversation(memory, "assistant", reply)
        last_reply = reply

        if voice_on:
            if hindi_on:
                hindi_text = translate_to_hindi(reply)
                speak(hindi_text, hindi=True)
            else:
                speak(reply, hindi=False)

        return {"reply": reply, "lesson": lesson_learned}

    def get_stats(self):
        return {
            "messages": len(memory["conversations"]),
            "lessons": len(memory["lessons"])
        }

    def get_proactive_message(self):
        """Called by frontend every 30 seconds to check for proactive messages"""
        try:
            return _proactive_queue.get_nowait()
        except:
            return None

    def get_file_list(self):
        return list_all_files()

    def read_file(self, filename):
        content = read_file(filename)
        return content if content else "File not found."

    def restore_backup(self, filename):
        from core.modifier import restore_latest_backup
        success, msg = restore_latest_backup(filename)
        return {"success": success, "message": msg}