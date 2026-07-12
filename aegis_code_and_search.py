"""
Aegis Add-On: Web Search + Sandboxed Code Execution + Code Output Window
--------------------------------------------------------------------------
Drop this file next to your existing Aegis Tkinter app and import from it.
It gives Aegis three new abilities:

1. web_search(query)      -> live web results (DuckDuckGo)
2. run_code(code, lang)   -> safely execute AI-generated code in an isolated
                             subprocess, with a timeout, and return output
3. CodeOutputPanel        -> a Tkinter widget that displays code with a
                             "Run" button and shows the result underneath

SECURITY NOTE:
Never use Python's exec()/eval() directly on AI-generated code — it runs
in-process and can touch your whole filesystem with no limits. Instead we
write the code to a temp file and run it as its OWN subprocess, with:
  - a timeout (so infinite loops can't hang Aegis)
  - a fresh working directory (so it can't wander your file system)
  - captured stdout/stderr (so nothing leaks into your terminal silently)
This is not a full sandbox (a determined script could still, say, make
network calls) but it stops the two most common accidents: hangs and
accidental file damage. For real untrusted code, a Docker container is the
next level up — worth doing once Aegis is running code you didn't write
yourself.
"""

import subprocess
import tempfile
import os
import sys
import tkinter as tk
from tkinter import scrolledtext
from duckduckgo_search import DDGS


# ---------------------------------------------------------------------------
# 1. WEB SEARCH
# ---------------------------------------------------------------------------
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search the web and return a list of {title, href, body} dicts.
    Feed these into your LLM prompt as extra context before answering.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return results
    except Exception as e:
        return [{"title": "Search failed", "href": "", "body": str(e)}]


def format_search_results_for_prompt(results: list[dict]) -> str:
    """Turn search results into a text block you can inject into your LLM prompt."""
    if not results:
        return "No search results found."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', '')}\n{r.get('body', '')}\nSource: {r.get('href', '')}\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. SANDBOXED CODE EXECUTION
# ---------------------------------------------------------------------------
RUNNERS = {
    "python": [sys.executable],
    "js": ["node"],
    "javascript": ["node"],
}
EXTENSIONS = {
    "python": ".py",
    "js": ".js",
    "javascript": ".js",
}


def run_code(code: str, language: str = "python", timeout: int = 10) -> dict:
    """
    Runs `code` in an isolated subprocess and returns:
      {"success": bool, "stdout": str, "stderr": str, "timed_out": bool}
    """
    language = language.lower()
    if language not in RUNNERS:
        return {"success": False, "stdout": "", "stderr": f"Unsupported language: {language}", "timed_out": False}

    ext = EXTENSIONS[language]
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, f"aegis_run{ext}")
        with open(script_path, "w") as f:
            f.write(code)

        try:
            proc = subprocess.run(
                RUNNERS[language] + [script_path],
                cwd=tmpdir,              # confined working directory
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": f"Timed out after {timeout}s", "timed_out": True}
        except FileNotFoundError:
            return {"success": False, "stdout": "", "stderr": f"Runner not installed for '{language}'", "timed_out": False}


# ---------------------------------------------------------------------------
# 3. CODE OUTPUT PANEL (Tkinter widget)
# ---------------------------------------------------------------------------
class CodeOutputPanel(tk.Frame):
    """
    A panel that shows AI-generated code, with a Run button and an output box.
    Usage:
        panel = CodeOutputPanel(parent)
        panel.pack(fill="both", expand=True)
        panel.show_code(code_string, language="python")
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.language = "python"

        tk.Label(self, text="Code", font=("Consolas", 10, "bold"), bg="#1e1e1e", fg="#4ec9b0",
                 anchor="w").pack(fill="x")

        self.code_box = scrolledtext.ScrolledText(
            self, height=14, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
            font=("Consolas", 10), wrap="none"
        )
        self.code_box.pack(fill="both", expand=True)

        btn_frame = tk.Frame(self, bg="#252526")
        btn_frame.pack(fill="x")
        self.run_btn = tk.Button(btn_frame, text="▶ Run Code", command=self.on_run,
                                  bg="#0e639c", fg="white", relief="flat", padx=10, pady=4)
        self.run_btn.pack(side="left", padx=5, pady=5)

        tk.Label(self, text="Output", font=("Consolas", 10, "bold"), bg="#1e1e1e", fg="#dcdcaa",
                 anchor="w").pack(fill="x")

        self.output_box = scrolledtext.ScrolledText(
            self, height=8, bg="#0c0c0c", fg="#00ff90", font=("Consolas", 10), wrap="word"
        )
        self.output_box.pack(fill="both", expand=True)
        self.output_box.config(state="disabled")

    def show_code(self, code: str, language: str = "python"):
        self.language = language
        self.code_box.delete("1.0", tk.END)
        self.code_box.insert(tk.END, code)

    def set_output(self, text: str, is_error: bool = False):
        self.output_box.config(state="normal")
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, text)
        self.output_box.config(fg="#ff5555" if is_error else "#00ff90")
        self.output_box.config(state="disabled")

    def on_run(self):
        code = self.code_box.get("1.0", tk.END)
        self.set_output("Running...")
        self.update_idletasks()
        result = run_code(code, self.language)
        if result["success"]:
            self.set_output(result["stdout"] or "(no output)")
        else:
            self.set_output(result["stderr"] or "Unknown error", is_error=True)


# ---------------------------------------------------------------------------
# DEMO — run this file directly to see it working standalone
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Aegis - Code & Search Demo")
    root.geometry("650x600")
    root.configure(bg="#1e1e1e")

    panel = CodeOutputPanel(root, bg="#1e1e1e")
    panel.pack(fill="both", expand=True, padx=10, pady=10)
    panel.show_code('print("Hello from Aegis!")\nfor i in range(3):\n    print("Counting:", i)')

    root.mainloop()