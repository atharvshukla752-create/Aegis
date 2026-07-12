import os
import shutil

def try_script(script):
    try:
        exec(script)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def rewrite_script(script, original_file_path, backup_path):
    if try_script(script):
        # Save the rewritten script and move the original file to backups
        with open(original_file_path, "w") as f:
            f.write(script)
        # Move the original file to backups
        filename = os.path.basename(original_file_path)
        shutil.move(original_file_path, os.path.join(backup_path, filename))
        print("Script saved and original file backed up.")
    else:
        print("Error: Script execution failed. Not saving changes.")

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
    body { background: #f5f6f8; height: 100vh; display: flex; flex-direction: column; color: #1a1a1a; }
    #titlebar { background: #ffffff; padding: 16px 24px; border-bottom: 1px solid #e8e9ec; display: flex; align-items: center; gap: 12px; }
    #titlebar .dot { 
      width: 10px; 
      height: 10px; 
      border-radius: 50%; 
      background: #2dd673; 
      box-shadow: 0 0 8px #2dd67388; 
      animation: pulse 2s infinite;
    }
    #titlebar h1 { font-size: 18px; font-weight: 600; color: #1a1a1a; }
    #titlebar .stats { margin-left: auto; font-size: 12px; color: #9a9da3; margin-right: 8px; }
    .toggle-btn { border: 1px solid #e8e9ec; background: #f5f6f8; color: #6b6e75; font-size: 12px; font-weight: 600; padding: 8px 14px; border-radius: 10px; cursor: pointer; transition: all 0.15s; }
    .toggle-btn:hover { background: #ececef; }
    .toggle-btn.active { background: #1a1a1a; color: #fff; border-color: #1a1a1a; }
    .toggle-btn.hindi.active { background: #ff8a3d; border-color: #ff8a3d; }
    .toggle-btn.dark.active { background: #6c63ff; border-color: #6c63ff; }
    #chat { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 14px; }
    .message { max-width: 70%; padding: 14px 18px; border-radius: 18px; line-height: 1.5; font-size: 14.5px; animation: fadeIn 0.25s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes pulse {
      0% {
        transform: scale(1);
        box-shadow: 0 0 8px #2dd67388;
      }
      50% {
        transform: scale(1.2);
        box-shadow: 0 0 12px #2dd673cc;
      }
      100% {
        transform: scale(1);
        box-shadow: 0 0 8px #2dd67388;
      }
    }
    .user { background: #1a1a1a; color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
    .aegis { background: #ffffff; color: #1a1a1a; align-self: flex-start; border: 1px solid #e8e9ec; border-bottom-left-radius: 4px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); white-space: pre-wrap; }
    .lesson-tag { align-self: flex-start; background: #eafff3; border: 1px solid #b8f0cf; color: #1d9c5c; font-size: 12px; padding: 8px 14px; border-radius: 12px; max-width: 70%; }
    .system-tag { align-self: center; background: #f0f4ff; border: 1px solid #c8d4f0; color: #4a6cf7; font-size: 12px; padding: 8px 14px; border-radius: 12px; max-width: 80%; }
    .thinking { color: #9a9da3; font-style: italic; }
    #input-area { background: #ffffff; padding: 16px 20px; border-top: 1px solid #e8e9ec; display: flex; gap: 10px; }
    #input { flex: 1; background: #f5f6f8; border: 1px solid #e8e9ec; color: #1a1a1a; padding: 14px 18px; border-radius: 14px; font-size: 14.5px; outline: none; transition: border-color 0.15s; }
    #input:focus { border-color: #1a1a1a; }
    #send { background: #1a1a1a; color: #fff; border: none; padding: 14px 24px; border-radius: 14px; font-weight: 600; cursor: pointer; font-size: 14px; transition: opacity 0.15s; }
    #send:hover { opacity: 0.85; }
    #send:active { opacity: 0.65; }
    #chat::-webkit-scrollbar { width: 6px; }
    #chat::-webkit-scrollbar-thumb { background: #d8dadf; border-radius: 3px; }

    /* Dark mode */
    body.dark { background: #0f0f0f; color: #f0f0f0; }
    body.dark #titlebar { background: #1a1a1a; border-color: #2a2a2a; }
    body.dark #titlebar h1 { color: #f0f0f0; }
    body.dark .aegis { background: #1e1e1e; color: #f0f0f0; border-color: #2a2a2a; }
    body.dark #input-area { background: #1a1a1a; border-color: #2a2a2a; }
    body.dark #input { background: #2a2a2a; border-color: #3a3a3a; color: #f0f0f0; }
    body.dark .toggle-btn { background: #2a2a2a; border-color: #3a3a3a; color: #aaa; }
    body.dark .toggle-btn:hover { background: #3a3a3a; }
    
    .proactive {
    align-self: center;
    background: linear-gradient(135deg, #667eea22, #764ba222);
    border: 1px solid #667eea44;
    color: #4a3f8f;
    font-size: 13px;
    padding: 10px 16px;
    border-radius: 14px;
    max-width: 80%;
    text-align: center;
    animation: fadeIn 0.4s ease;
}
body.dark .proactive {
    color: #a89cf7;
    background: linear-gradient(135deg, #667eea11, #764ba211);
    border-color: #667eea33;
}
#smartwatch-toggle {
    border: 1px solid #e8e9ec;
    background: #f5f6f8;
    color: #6b6e75;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 14px;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.15s;
}
#smartwatch-toggle:hover {
    background: #ececef;
}
#smartwatch-display {
    padding: 16px;
    border: 1px solid #e8e9ec;
    border-radius: 10px;
    background: #f5f6f8;
    display: none;
}
#smartwatch-window {
    padding: 16px;
    border: 1px solid #e8e9ec;
    border-radius: 10px;
    background: #f5f6f8;
    display: none;
}
</style>
</head>
<body>
    <div id="titlebar">
        <div class="dot"></div>
        <h1>Aegis</h1>
        <div class="stats" id="stats">loading...</div>
        <button class="toggle-btn dark" id="darkBtn"> Dark</button>
        <button class="toggle-btn" id="voiceBtn"> Voice</button>
        <button class="toggle-btn hindi" id="hindiBtn">हिंदी</button>
        <button id="smartwatch-toggle" onclick="toggleSmartwatch()">Toggle SmartWatch</button>
        <button class="toggle-btn" id="toggle-smartwatch">Toggle Smartwatch Window</button>
        <button class="toggle-btn" id="python-lesson">Python Lesson</button>
    </div>
    <div id="chat">
        <div class="message aegis">Hello! I'm Aegis — your personal AI assistant. I know who I am, what I'm made of, and I can improve myself. Ask me anything.</div>
    </div>
    <div id="smartwatch-display"></div>
    <div id="smartwatch-window" style="display: none;">
        <h2>This is the SmartWatch Window</h2>
        <p>Time: <span id="smartwatch-time">00:00:00</span></p>
        <p>Health: <span id="smartwatch-health">100%</span></p>
    </div>
    <div id="input-area">
        <input id="input" type="text" placeholder="Message Aegis..." />
        <button id="send">Send</button>
    </div>

<script>
    const chat = document.getElementById('chat');
    const input = document.getElementById('input');
    const send = document.getElementById('send');
    const stats = document.getElementById('stats');
    const voiceBtn = document.getElementById('voiceBtn');
    const hindiBtn = document.getElementById('hindiBtn');
    const darkBtn = document.getElementById('darkBtn');
    const smartwatchToggle = document.getElementById('smartwatch-toggle');
    const smartwatchDisplay = document.getElementById('smartwatch-display');
    const toggleSmartwatchButton = document.getElementById('toggle-smartwatch');
    const smartwatchWindow = document.getElementById('smartwatch-window');
    const pythonLessonBtn = document.getElementById('python-lesson');

    let voiceOn = false;
    let hindiOn = false;
    let darkOn = false;
    let smartwatchOn = false;

    darkBtn.addEventListener('click', () => {
        darkOn = !darkOn;
        darkBtn.classList.toggle('active', darkOn);
        document.body.classList.toggle('dark', darkOn);
    });

    voiceBtn.addEventListener('click', () => {
        voiceOn = !voiceOn;
        voiceBtn.classList.toggle('active', voiceOn);
    });

    hindiBtn.addEventListener('click', () => {
        hindiOn = !hindiOn;
        hindiBtn.classList.toggle('active', hindiOn);
        if (hindiOn && !voiceOn) {
            voiceOn = true;
            voiceBtn.classList.add('active');
        }
    });

    smartwatchToggle.addEventListener('click', () => {
        smartwatchOn = !smartwatchOn;
        smartwatchDisplay.style.display = smartwatchOn ? 'block' : 'none';
    });

    toggleSmartwatchButton.addEventListener('click', () => {
        smartwatchWindow.style.display = smartwatchWindow.style.display === 'none' ? 'block' : 'none';
    });

    pythonLessonBtn.addEventListener('click', () => {
        const lesson = `
            Welcome to Python Programming!
            In this lesson, we'll cover the basics of Python.

            Variables and Data Types:
            In Python, you can assign a value to a variable using the '=' operator.
            For example:
            x = 5
            y = "Hello, World!"

            Basic Operators:
            Python supports various operators for arithmetic, comparison, and logical operations.
            For example:
            Addition: 5 + 3 = 8
            Subtraction: 5 - 2 = 3
            Multiplication: 5 * 2 = 10
            Division: 5 / 2 = 2.5

            Control Structures:
            Control structures determine the flow of your program's execution.
            For example:
            if x > 10:
                print("x is greater than 10")
            else:
                print("x is less than or equal to 10")

            Functions:
            Functions are reusable blocks of code that perform a specific task.
            def greet(name):
                print(f"Hello, {name}!")

            Lists and Loops:
            Lists are ordered collections of items, and loops allow you to iterate over them.
            fruits = ["Apple", "Banana", "Cherry"]
            for fruit in fruits:
                print(fruit)

            Conclusion:
            That's a brief introduction to Python programming!
            Practice these concepts to become proficient in Python.

            Interactive Quiz:
            Answer the following questions to test your understanding:
            What is the value of x?
            What is the data type of y?
            What is the result of 5 + 3?
        `;
        addMessage(lesson, 'message aegis');
    });

    function toggleSmartwatch() {
        var smartwatchWindow = document.getElementById("smartwatch-window");
        if (smartwatchWindow.style.display === "none") {
            smartwatchWindow.style.display = "block";
        } else {
            smartwatchWindow.style.display = "none";
        }
    }

    function addMessage(text, cls) {
        const div = document.createElement('div');
        div.className = cls;
        div.textContent = text;
        chat.appendChild(div);
        chat.scrollTop = chat.scrollHeight;
        return div;
    }

    async function refreshStats() {
        const s = await window.pywebview.api.get_stats();
        stats.textContent = `${s.messages} messages · ${s.lessons} lessons learned`;
    }

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;
        input.value = '';
        addMessage(text, 'message user');
        const thinking = addMessage('Thinking...', 'message aegis thinking');

        const result = await window.pywebview.api.send_message(text, voiceOn, hindiOn);

        chat.removeChild(thinking);

        if (result.lesson) {
            addMessage('Learned: ' + result.lesson, 'lesson-tag');
        }

        if (result.reply.includes('✅')) {
            const parts = result.reply.split('✅');
            if (parts[0].trim()) addMessage(parts[0].trim(), 'message aegis');
            addMessage('✅' + parts[1], 'system-tag');
        } else {
            addMessage(result.reply, 'message aegis');
        }

        refreshStats();
    }

    send.addEventListener('click', sendMessage);
    input.addEventListener('keypress', e => { if (e.key === 'Enter') sendMessage(); });
    refreshStats();

    // Proactive messages from Aegis
async function checkProactive() {
    const msg = await window.pywebview.api.get_proactive_message();
    if (msg) {
        addMessage(msg, 'proactive');
    }
}
// Check every 30 seconds
setInterval(checkProactive, 30000);
</script>
</body>
</html>
"""