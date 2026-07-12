import os
import shutil
from datetime import datetime

AEGIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(AEGIS_DIR, "backups")

PROTECTED_FILES = ['main.py', 'ui_api.py', 'ui_html.py', 'memory.py',
                   'self_awareness.py', 'core/brain.py', 'core/modifier.py',
                   'core/voice.py']

DANGEROUS_PATTERNS = [
    'shutil.rmtree', 'os.rmdir', 'sys.exit()',
    'while True: pass', 'DROP TABLE'
]


def backup_file(filename):
    """Backup a file before modifying it"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    src = os.path.join(AEGIS_DIR, filename)
    if os.path.exists(src):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(BACKUP_DIR, f"{filename.replace('/', '_')}.{timestamp}.bak")
        shutil.copy2(src, dst)
        return dst
    return None


def is_dangerous(code):
    """Check if code contains dangerous patterns"""
    code_lower = code.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in code_lower:
            return True, pattern
    return False, None


def list_all_files():
    """List all relevant Aegis files"""
    files = []
    for root, dirs, filenames in os.walk(AEGIS_DIR):
        # Skip backups and hidden folders
        dirs[:] = [d for d in dirs if d not in ['backups', '__pycache__', '.git']]
        for f in filenames:
            if f.endswith('.py') or f.endswith('.json'):
                rel = os.path.relpath(os.path.join(root, f), AEGIS_DIR)
                files.append(rel.replace('\\', '/'))
    return files


def read_file(filepath):
    """Read any Aegis file"""
    path = os.path.join(AEGIS_DIR, filepath)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def rewrite_file(filepath, new_content):
    """Backup then fully rewrite a file"""
    dangerous, pattern = is_dangerous(new_content)
    if dangerous:
        return False, f"🛡️ I can't do that — contains '{pattern}' which could damage me."

    backup_file(filepath)

    path = os.path.join(AEGIS_DIR, filepath)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True, f"✅ Rewrote '{filepath}' with new feature. Restart Aegis to apply."


def create_feature_file(filename, content):
    """Create a new file in the features/ folder"""
    dangerous, pattern = is_dangerous(content)
    if dangerous:
        return False, f"🛡️ Can't create that — contains '{pattern}' which could damage me."

    filepath = f"features/{filename}"
    path = os.path.join(AEGIS_DIR, filepath)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True, f"✅ Created new feature file 'features/{filename}'."


def restore_latest_backup(filename):
    """Restore most recent backup of a file"""
    if not os.path.exists(BACKUP_DIR):
        return False, "No backups found."

    safe_name = filename.replace('/', '_')
    backups = sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith(safe_name)
    ])

    if not backups:
        return False, f"No backup found for '{filename}'."

    latest = backups[-1]
    src = os.path.join(BACKUP_DIR, latest)
    dst = os.path.join(AEGIS_DIR, filename)
    shutil.copy2(src, dst)

    return True, f"✅ Restored '{filename}' from backup."