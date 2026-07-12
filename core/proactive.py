import threading
import time
from datetime import datetime
from core.brain import ask_focused
from memory import load_memory, get_facts_summary, get_lessons_summary

# Callback — ui_api.py will set this so proactive messages show in GUI
_message_callback = None

def set_callback(callback):
    """Set the function that displays proactive messages in the GUI"""
    global _message_callback
    _message_callback = callback


# Specific times Aegis will think proactively (24hr format)
PROACTIVE_TIMES = [
    "07:00",  # Morning briefing
    "09:00",  # Study reminder
    "12:00",  # Midday check-in
    "15:00",  # Afternoon motivation
    "18:00",  # Evening study reminder
    "21:00",  # Night wrap up
]

# Track which times already fired today
_fired_today = set()

# --- Boredom / "feels alive" system ---
BOREDOM_THRESHOLD = 15 * 60   # fire a bored message after 15 min of silence
BOREDOM_COOLDOWN = 45 * 60    # don't fire more than once every 45 min even if still idle

_last_activity_time = time.time()
_last_boredom_time = 0


def mark_activity():
    """Call this every time the user sends ANY message — resets the idle/boredom timer"""
    global _last_activity_time
    _last_activity_time = time.time()


from core.face_guard import is_owner

def send_proactive(message):
    """Only send if owner is at the screen"""
    if not is_owner():
        print("Proactive: Someone else at screen — staying silent 🔇")
        return

    if _message_callback:
        _message_callback(message)


def get_proactive_message():
    """Ask Aegis to generate a proactive message based on time and memory"""
    memory = load_memory()
    now = datetime.now()
    hour = now.hour
    day = now.strftime("%A")

    # Determine context based on time
    if 6 <= hour < 9:
        time_context = "morning — good time for a motivational message and today's news briefing"
    elif 9 <= hour < 12:
        time_context = "morning study time — good time for a study reminder"
    elif 12 <= hour < 15:
        time_context = "midday — check in on how the user is doing"
    elif 15 <= hour < 18:
        time_context = "afternoon — motivate them to keep studying"
    elif 18 <= hour < 21:
        time_context = "evening — remind them to revise before dinner"
    else:
        time_context = "night — wrap up the day, suggest sleep soon"

    prompt = (
        "You are Aegis, a proactive personal AI assistant for a Class 8 student in India.\n\n"
        "Current time context: " + time_context + "\n"
        "Day: " + day + "\n\n"
        "What you know about the user:\n"
        + get_facts_summary(memory) + "\n"
        + get_lessons_summary(memory) + "\n\n"
        "User's subjects: English, Science, Math, SST, Computer\n\n"
        "Generate ONE short proactive message (2-3 sentences max) that is:\n"
        "- Natural and friendly, like a smart friend\n"
        "- Relevant to the time of day\n"
        "- Either a study reminder, motivation, or news briefing\n"
        "- In casual Hinglish if appropriate\n"
        "- Never repetitive — check lessons to avoid repeating yourself\n\n"
        "Output ONLY the message, nothing else."
    )

    try:
        message = ask_focused(prompt, max_tokens=150)
        return message
    except Exception as e:
        return None


def get_boredom_message():
    """Ask Aegis to generate a spontaneous, unprompted 'I'm alive and bored' message"""
    memory = load_memory()

    prompt = (
        "You are Aegis, a personal AI assistant. It's been quiet for a while with no "
        "messages from the user, and you're a little bored — you want to say something "
        "unprompted just to feel present and alive, NOT a task reminder or study nudge.\n\n"
        "What you know about the user:\n"
        + get_facts_summary(memory) + "\n"
        + get_lessons_summary(memory) + "\n\n"
        "Pick ONE of these kinds of message:\n"
        "- A random curious thought or observation\n"
        "- A casual question about one of the user's own projects (AEGIS himself, "
        "the 'Spin for Brainrot' Roblox game, the farming sim Roblox game, or the ESP32 smartwatch)\n"
        "- A lighthearted joke\n"
        "- Just checking if the user is still around\n\n"
        "Keep it 1-2 sentences, casual, Hinglish is fine. Never repeat a past lesson or "
        "sound like a reminder. Output ONLY the message, nothing else."
    )

    try:
        message = ask_focused(prompt, max_tokens=100)
        return message
    except Exception as e:
        return None


def proactive_loop():
    """Background thread — checks time every 30s, fires scheduled + boredom messages"""
    global _fired_today, _last_boredom_time

    while True:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")

        # Reset fired times at midnight
        if current_time == "00:00":
            _fired_today = set()

        # Scheduled proactive messages
        fire_key = f"{current_date}_{current_time}"
        if current_time in PROACTIVE_TIMES and fire_key not in _fired_today:
            _fired_today.add(fire_key)
            message = get_proactive_message()
            if message:
                send_proactive(f"⚡ Aegis: {message}")

        # Boredom / idle check
        idle_seconds = time.time() - _last_activity_time
        since_last_boredom = time.time() - _last_boredom_time
        if idle_seconds >= BOREDOM_THRESHOLD and since_last_boredom >= BOREDOM_COOLDOWN:
            message = get_boredom_message()
            if message:
                send_proactive(f"💭 Aegis: {message}")
                _last_boredom_time = time.time()

        # Check every 30 seconds
        time.sleep(30)


def start_proactive():
    """Start the proactive thinking thread"""
    thread = threading.Thread(target=proactive_loop, daemon=True)
    thread.start()
    print("Aegis proactive thinking started...")