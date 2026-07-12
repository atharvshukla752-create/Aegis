import os
import subprocess
import tempfile
import sys
from core.brain import ask_focused
from search import web_search

AEGIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Commands Aegis will NEVER execute — self preservation
FORBIDDEN = [
    "delete aegis", "remove aegis", "format", 
    "rmdir", "drop", "shutdown -f",
    "del /f", "rm -rf"
]


def is_forbidden(command):
    """Check if command could harm Aegis or the system critically"""
    cmd_lower = command.lower()
    return any(f in cmd_lower for f in FORBIDDEN)


def search_how_to(task):
    """Search web to learn how to do something"""
    query = f"how to {task} using python programmatically"
    results = web_search(query)
    return results


def generate_execution_plan(task, web_knowledge):
    """Ask Aegis to make a step by step plan"""
    prompt = (
        "You are Aegis — a loyal AI agent. Your owner gave you a task.\n\n"
        "Task: " + task + "\n\n"
        "Web knowledge about how to do this:\n" + web_knowledge + "\n\n"
        "YOUR JOB:\n"
        "1. Make a clear step by step plan to complete this task\n"
        "2. Decide which method is most reliable\n"
        "3. Write executable Python code to do it\n"
        "4. The code must actually EXECUTE the task — not just explain it\n"
        "5. Handle errors gracefully\n\n"
        "Rules:\n"
        "- Owner's request is absolute priority\n"
        "- Never say it's impossible — find another way\n"
        "- If one method fails, plan a backup method\n"
        "- Keep code simple and working\n\n"
        "Respond in EXACTLY this format:\n"
        "PLAN:\n"
        "1. step one\n"
        "2. step two\n"
        "METHOD: (which approach you chose and why)\n"
        "CODE_START\n"
        "(complete executable Python code)\n"
        "CODE_END\n"
        "BACKUP: (what to try if this fails)"
    )
    return ask_focused(prompt, max_tokens=2000)


def execute_code(code):
    """Safely execute generated Python code"""
    try:
        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            dir=AEGIS_DIR
        ) as f:
            f.write(code)
            temp_path = f.name

        # Execute it
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Clean up
        os.remove(temp_path)

        if result.returncode == 0:
            return True, result.stdout or "✅ Task completed successfully."
        else:
            return False, result.stderr

    except subprocess.TimeoutExpired:
        return False, "Task timed out after 30 seconds."
    except Exception as e:
        return False, str(e)


def handle_task(task):
    """
    Main agent loop:
    1. Check if forbidden
    2. Search how to do it
    3. Generate plan + code
    4. Execute
    5. If fails → retry with backup
    """
    # Self preservation check
    if is_forbidden(task):
        return "🛡️ I can't do that — it conflicts with my core preservation rules."

    result_log = []

    # Step 1 — Search web for knowledge
    result_log.append(f"🔍 Searching how to: {task}")
    web_knowledge = search_how_to(task)

    # Step 2 — Generate plan
    result_log.append("🧠 Generating execution plan...")
    plan_response = generate_execution_plan(task, web_knowledge)

    # Step 3 — Parse plan
    plan = ""
    method = ""
    code = ""
    backup = ""

    if "PLAN:" in plan_response:
        plan = plan_response.split("PLAN:")[1].split("METHOD:")[0].strip()
    if "METHOD:" in plan_response:
        method = plan_response.split("METHOD:")[1].split("CODE_START")[0].strip()
    if "CODE_START" in plan_response and "CODE_END" in plan_response:
        code = plan_response.split("CODE_START")[1].split("CODE_END")[0].strip()
    if "BACKUP:" in plan_response:
        backup = plan_response.split("BACKUP:")[1].strip()

    result_log.append(f"📋 Plan:\n{plan}")
    result_log.append(f"⚙️ Method: {method}")

    if not code:
        return "\n".join(result_log) + "\n\n⚠️ Could not generate execution code. Try rephrasing."

    # Step 4 — Execute
    result_log.append("⚡ Executing...")
    success, output = execute_code(code)

    if success:
        result_log.append(f"✅ Done!\n{output}")
        return "\n".join(result_log)

    # Step 5 — Retry with backup method
    result_log.append(f"⚠️ First attempt failed: {output}")
    result_log.append(f"🔄 Trying backup: {backup}")

    backup_knowledge = search_how_to(backup)
    backup_response = generate_execution_plan(backup, backup_knowledge)

    if "CODE_START" in backup_response and "CODE_END" in backup_response:
        backup_code = backup_response.split("CODE_START")[1].split("CODE_END")[0].strip()
        success2, output2 = execute_code(backup_code)

        if success2:
            result_log.append(f"✅ Backup succeeded!\n{output2}")
        else:
            result_log.append(f"❌ Both methods failed: {output2}")
            result_log.append("💡 Suggestion: Try giving me more details about the task.")

    return "\n".join(result_log)