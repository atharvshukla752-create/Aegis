from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
from memory import get_facts_summary, get_lessons_summary
from self_awareness import AEGIS_IDENTITY
from core.modifier import list_all_files, read_file as read_aegis_file
import os
import requests

load_dotenv()

# Primary client — Groq
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# OpenRouter for accessing multiple free models
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Models to consult
GROQ_MODELS = [
    "llama-3.3-70b-versatile",   # Primary
    "llama-3.1-8b-instant",      # Secondary (fast fallback)
]

# NOTE: OpenRouter's free-model lineup rotates constantly — specific :free model
# IDs get retired without notice (this is why multi-model mode was failing most
# of the time: the old hardcoded IDs had gone dead). "openrouter/free" is
# OpenRouter's own auto-router — it always picks a currently-live free model,
# so this list self-heals instead of rotting again in a few weeks.
OPENROUTER_MODELS = [
    "openrouter/free",
    "meta-llama/llama-3.3-70b-instruct:free",  # stable long-running fallback pick
]


def build_system_prompt(memory, extra=""):
    now = datetime.now().strftime("%A, %d %B %Y — %I:%M %p")
    return (
        AEGIS_IDENTITY
        + f"\nCurrent date and time: {now}"
        + get_facts_summary(memory)
        + get_lessons_summary(memory)
        + extra
    )


def ask_groq(messages, model="llama-3.3-70b-versatile"):
    """Ask a Groq model"""
    if not os.environ.get("GROQ_API_KEY"):
        print("[GROQ ERROR] GROQ_API_KEY is missing from your .env file")
        return None
    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[GROQ ERROR] model={model} | {type(e).__name__}: {e}")
        return None


def ask_openrouter(prompt, model):
    """Ask an OpenRouter free model"""
    if not OPENROUTER_KEY:
        return None
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024
            },
            timeout=15
        )
        data = response.json()
        if "choices" not in data:
            # OpenRouter returns vendor error hints in the JSON body — log the
            # full thing so a dead/renamed model ID is obvious next time, not silent
            print(f"[OPENROUTER ERROR] model={model} | response: {data}")
            return None
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        print(f"[OPENROUTER ERROR] model={model} | timed out")
        return None
    except Exception as e:
        print(f"[OPENROUTER ERROR] model={model} | {type(e).__name__}: {e}")
        return None


def synthesize_answers(question, answers):
    """
    Aegis compares all answers from different models
    and synthesizes the best combined response
    """
    valid_answers = [a for a in answers if a]
    if not valid_answers:
        return None
    if len(valid_answers) == 1:
        return valid_answers[0]

    # Build comparison prompt
    answers_text = ""
    for i, ans in enumerate(valid_answers, 1):
        answers_text += f"\nModel {i} answer:\n{ans}\n"

    synthesis_prompt = (
        "You are Aegis. You asked multiple AI models the same question "
        "and got different answers. Your job is to:\n"
        "1. Find what all models agree on (most reliable facts)\n"
        "2. Pick the best explanation style\n"
        "3. Add anything unique and correct from each answer\n"
        "4. Produce ONE final answer that is better than any individual answer\n"
        "5. Be concise — don't repeat yourself\n\n"
        "Question asked: " + question + "\n\n"
        + answers_text +
        "\nSynthesize the BEST possible answer from all of the above. "
        "Output ONLY the final answer, nothing else."
    )

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.3,
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[SYNTHESIZE ERROR] {type(e).__name__}: {e}")
        return valid_answers[0]


def synthesize_code_answers(question, answers):
    """
    For CODE specifically — merging syntax from different model answers (like
    synthesize_answers does for prose) produces broken hybrid code: mismatched
    variable names, incompatible logic, syntax that doesn't fit together.
    Instead of blending, this picks the single best complete implementation.
    """
    valid_answers = [a for a in answers if a]
    if not valid_answers:
        return None
    if len(valid_answers) == 1:
        return valid_answers[0]

    answers_text = ""
    for i, ans in enumerate(valid_answers, 1):
        answers_text += f"\n--- Candidate {i} ---\n{ans}\n"

    prompt = (
        "You are Aegis. Multiple AI models were each asked to write code for the "
        "same request, and produced the candidates below.\n\n"
        "IMPORTANT: This is CODE, not prose. Do NOT blend or merge syntax from "
        "different candidates together — mixing incompatible patterns produces "
        "BROKEN code. Instead:\n"
        "1. Pick the ONE candidate that is most complete, correct, and idiomatic "
        "for the language being used\n"
        "2. You may add a small missing piece (a comment, an edge case) ONLY if "
        "it doesn't require restructuring the chosen candidate\n"
        "3. Output that ONE candidate, cleaned up, as a single coherent, "
        "syntactically valid file or snippet\n\n"
        "Request: " + question + "\n"
        + answers_text +
        "\nOutput ONLY the final code, with a one-line note above it if useful."
    )
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2048
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[SYNTHESIZE_CODE ERROR] {type(e).__name__}: {e}")
        return valid_answers[0]


def ask_code(messages):
    """
    Multi-model consensus for CODE requests specifically. Same models as ask(),
    but uses synthesize_code_answers() instead of synthesize_answers() so the
    result is one coherent implementation, not a blended/broken hybrid.
    """
    user_question = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            user_question = msg["content"]
            break

    answers = []

    for model in GROQ_MODELS:
        answer = ask_groq(messages, model=model)
        if answer:
            answers.append(answer)

    if OPENROUTER_KEY:
        simple_prompt = messages[-1]["content"] if messages else user_question
        for model in OPENROUTER_MODELS:
            answer = ask_openrouter(simple_prompt, model)
            if answer:
                answers.append(answer)
    else:
        print("[ASK_CODE] OPENROUTER_API_KEY not set — skipping OpenRouter models")

    if not answers:
        print("[ASK_CODE] No models returned a valid answer")

    final = synthesize_code_answers(user_question, answers)
    return final or "I couldn't get a response. Please try again."


# Condensed description of every file/folder in the Aegis project, given to
# external models as context so they don't answer blind — they know what
# already exists before writing or fixing anything.
PROJECT_OVERVIEW = """
AEGIS PROJECT STRUCTURE (Python desktop AI assistant, pywebview + OpenCV):

ROOT FILES:
- main.py — launcher, shows face/password security screen, then opens Aegis
- ui_html.py — entire visual interface (HTML/CSS/JS in one file)
- ui_api.py — handles every user message: save commands, agent tasks,
  corrections, web search triggers, voice routing, proactive queue
- memory.py — persistent memory: conversations, facts, lessons learned,
  saved to aegis_memory.json
- search.py — web search via DuckDuckGo (ddgs)
- self_awareness.py — Aegis's identity, FILE_MAP (feature → file lookup),
  agent task triggers, functions to read/list his own files
- chat.py — terminal-only fallback chat interface (no GUI)
- model.py / train.py / test.py / predict.py — separate digit recognition
  neural network (MNIST), unrelated to chat features

core/ FOLDER:
- core/brain.py — all AI model connections (Groq primary, OpenRouter free
  models secondary), builds system prompts, single/multi-model consensus
- core/voice.py — speech output, English (offline pyttsx3) and Hindi (gTTS)
- core/modifier.py — file operations: backup, rewrite, create feature files,
  danger-pattern checks, restore from backup. PROTECTED_FILES list gates
  which files need extra caution
- core/agent.py — executes real PC tasks: searches how, generates code, runs
  it safely, retries on failure
- core/proactive.py — scheduled check-ins + boredom/idle-based spontaneous
  messages, sent through a GUI message queue
- core/face_guard.py — OpenCV-only facial recognition security (no ML model
  file), template+histogram+pixel comparison, threshold 0.72
- core/reflection.py — self-improvement loop: reviews recent lessons/errors,
  proposes or auto-applies code updates to himself depending on file risk

features/ FOLDER:
- New capability files Aegis creates for himself land here — low risk,
  isolated, safe to auto-apply changes to

owner_face/, backups/, data/MNIST/, __pycache__/ — data/generated folders,
not source code.
""".strip()


def build_project_context():
    """Combine identity + file/folder overview + live current file list"""
    try:
        current_files = list_all_files()
        file_list_text = "\n".join(f"- {f}" for f in current_files)
    except Exception:
        file_list_text = "(file list unavailable)"

    return (
        AEGIS_IDENTITY + "\n\n"
        + PROJECT_OVERVIEW + "\n\n"
        "Current files actually present in the project:\n" + file_list_text
    )


def ask_code_with_context(user_request, max_file_requests=3):
    """
    Consults a model to write or fix code, giving it full project context up
    front so it isn't answering blind. If it needs to see a SPECIFIC file's
    real contents to answer correctly, it can ask for it by name — Aegis
    fetches that file and re-asks, up to max_file_requests times, then
    returns the final complete solution (new script or updated script).
    """
    context = build_project_context()

    instructions = (
        "You are helping write or fix code for the Aegis project described "
        "above. If you need to see the CURRENT CONTENTS of one specific file "
        "from the file list to answer correctly, respond with EXACTLY this "
        "and nothing else:\n"
        "NEED_FILE: <exact filepath from the list above>\n\n"
        "Otherwise, provide the complete solution: full code (not a "
        "fragment), followed by a short explanation of what it does and why."
    )

    conversation = context + "\n\n" + instructions + "\n\nRequest: " + user_request
    supplied_files = {}
    rounds = 0

    while rounds <= max_file_requests:
        response = ask_focused(conversation, max_tokens=2048)

        if response.strip().upper().startswith("NEED_FILE:"):
            requested = response.split(":", 1)[1].strip()
            rounds += 1

            if requested in supplied_files:
                conversation += (
                    f"\n\nYou already have `{requested}` above — please give "
                    "the complete solution now instead of asking again."
                )
                continue

            content = read_aegis_file(requested)
            if content is None:
                conversation += (
                    f"\n\n`{requested}` doesn't exist or couldn't be read. "
                    "Please give your best solution with the context you have."
                )
                continue

            supplied_files[requested] = content
            conversation += (
                f"\n\nHere is `{requested}`:\n{content}\n\n"
                "Now provide the complete solution."
            )
            continue

        # Real answer, not a file request
        return response

    return "Couldn't get a complete answer after a few rounds of context — try rephrasing the request."


def ask(messages, use_multi_model=False):
    """
    Main ask function.
    Normal questions → single fast Groq call
    Complex questions → multi-model consensus
    """
    if not use_multi_model:
        result = ask_groq(messages)
        if result is None:
            print("[ASK] ask_groq returned None — falling back to default message")
        return result or "I couldn't get a response. Please try again."

    # Multi-model mode
    user_question = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            user_question = msg["content"]
            break

    answers = []

    # Ask Groq models
    for model in GROQ_MODELS:
        answer = ask_groq(messages, model=model)
        if answer:
            answers.append(answer)

    # Ask OpenRouter models
    if OPENROUTER_KEY:
        simple_prompt = messages[-1]["content"] if messages else user_question
        for model in OPENROUTER_MODELS:
            answer = ask_openrouter(simple_prompt, model)
            if answer:
                answers.append(answer)
    else:
        print("[ASK] OPENROUTER_API_KEY not set — skipping OpenRouter models")

    if not answers:
        print("[ASK] No models returned a valid answer in multi-model mode")

    # Synthesize best answer
    final = synthesize_answers(user_question, answers)
    return final or "I couldn't get a response. Please try again."


def ask_focused(prompt, max_tokens=1000):
    """Single focused question — lessons, decisions, translations"""
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ASK_FOCUSED ERROR] {type(e).__name__}: {e}")
        return ""