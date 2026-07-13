"""
aegisweb/chat.py — message handling for AegisWeb, built fresh.
Reuses Aegis's real intelligence (core/brain.py, memory.py, search.py) —
these are the parts that actually think, and there's no reason to
duplicate them. What this file deliberately does NOT do is import
anything from ui_api.py's handle_self_modification() / pending_changes
system. That whole code path simply doesn't exist here. AegisWeb was
never given the ability to propose or apply changes to its own files —
not blocked after the fact, just never wired up in the first place.
"""
import os
import sys
# Make the parent AEGIS folder importable so we can reuse core/, memory.py,
# search.py without copying them into this folder.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.brain import build_system_prompt, ask, ask_code_with_context
from memory import load_memory, add_conversation, get_conversation_history
from search import web_search, should_search
memory = load_memory()
CODE_KEYWORDS = [
    "code", "script", "function", "python", "lua", "javascript",
    "html", "css", "algorithm", "debug", "syntax", "class ", "def ",
    "variable", "write a program", "fix this bug",
]
def send_message(user_input: str) -> dict:
    user_input = user_input.strip()
    if not user_input:
        return {"reply": ""}
    add_conversation(memory, "user", user_input)
    search_context = ""
    if should_search(user_input):
        search_context = "\n\n" + web_search(user_input)
    history = get_conversation_history(memory)
    messages = [
        {"role": "system", "content": build_system_prompt(memory, search_context)}
    ] + history
    is_code_request = any(kw in user_input.lower() for kw in CODE_KEYWORDS)
    if is_code_request:
        # ask_code_with_context gives real project-aware code answers —
        # same quality as the desktop app — but nothing downstream of
        # this ever looks at the reply and asks "should I rewrite one
        # of my own files based on this?" That question just isn't
        # asked in AegisWeb at all.
        reply = ask_code_with_context(user_input)
    else:
        reply = ask(messages, use_multi_model=True)
    add_conversation(memory, "assistant", reply)
    return {"reply": reply}
def get_stats() -> dict:
    return {
        "messages": len(memory["conversations"]),
    }