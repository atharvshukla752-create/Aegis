import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'

import cv2
import sys
import threading
import webview
import base64
import numpy as np
from core.face_guard import is_owner, setup_if_needed, face_cascade


def speak_galat():
    """Speak 'galat password' on wrong attempt"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say("Galat password hai. Access denied.")
        engine.runAndWait()
    except Exception as e:
        print(f"TTS error: {e}")


class SecurityApi:
    def __init__(self):
        self.cam = cv2.VideoCapture(0)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.access_granted = False

    def get_frame(self):
        """Return current webcam frame as base64 for display"""
        if not self.cam.isOpened():
            return None

        ret, frame = self.cam.read()
        if not ret or frame is None:
            return None

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = np.ascontiguousarray(gray)
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (45, 255, 130), 2)
        except cv2.error:
            pass  # skip drawing box this frame, still show video

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        b64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{b64}"

    def check_face(self):
        """Try face recognition"""
        try:
            result = is_owner()
        except Exception as e:
            print(f"Face check error: {e}")
            result = False

        if result:
            self.access_granted = True
            self._release_camera()
            return {"success": True, "message": "✅ Welcome back!"}
        else:
            threading.Thread(target=speak_galat, daemon=True).start()
            return {"success": False, "message": "❌ Face not recognized"}

    def check_password(self, password):
        """Check password"""
        if password == "110796|2.o":
            self.access_granted = True
            self._release_camera()
            return {"success": True, "message": "✅ Access granted!"}
        else:
            threading.Thread(target=speak_galat, daemon=True).start()
            return {"success": False, "message": "❌ Galat password!"}

    def _release_camera(self):
        if self.cam.isOpened():
            self.cam.release()

    def stop_camera(self):
        self._release_camera()


SECURITY_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', Arial, sans-serif; }
    body {
        background: #0a0a0a;
        height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #fff;
        gap: 20px;
    }
    #title {
        font-size: 28px;
        font-weight: 700;
        color: #2dd673;
        letter-spacing: 4px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .dot {
        width: 12px; height: 12px;
        border-radius: 50%;
        background: #2dd673;
        box-shadow: 0 0 10px #2dd673;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 8px #2dd673; }
        50% { transform: scale(1.3); box-shadow: 0 0 16px #2dd673; }
        100% { transform: scale(1); box-shadow: 0 0 8px #2dd673; }
    }
    #subtitle { font-size: 13px; color: #555; letter-spacing: 2px; }
    #cam-container {
        position: relative;
        border: 2px solid #222;
        border-radius: 16px;
        overflow: hidden;
        width: 320px;
        height: 240px;
        background: #111;
    }
    #cam-feed {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    #cam-overlay {
        position: absolute;
        bottom: 10px;
        left: 50%;
        transform: translateX(-50%);
        font-size: 11px;
        color: #2dd67388;
        letter-spacing: 1px;
    }
    #status {
        font-size: 13px;
        color: #666;
        height: 20px;
        transition: color 0.3s;
    }
    #status.success { color: #2dd673; }
    #status.error { color: #ff4444; }
    .btn-row { display: flex; gap: 12px; }
    .btn {
        padding: 12px 28px;
        border-radius: 12px;
        border: none;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s;
        letter-spacing: 1px;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    #faceBtn { background: #2dd673; color: #000; }
    #faceBtn:hover:not(:disabled) { opacity: 0.85; }
    #faceBtn:active:not(:disabled) { transform: scale(0.97); }
    #pwdBtn {
        background: #1a1a1a;
        color: #fff;
        border: 1px solid #333;
    }
    #pwdBtn:hover { background: #2a2a2a; }

    #pwd-panel {
        display: none;
        flex-direction: column;
        gap: 10px;
        align-items: center;
    }
    #pwd-input {
        background: #1a1a1a;
        border: 1px solid #333;
        color: #fff;
        padding: 12px 18px;
        border-radius: 12px;
        font-size: 15px;
        width: 280px;
        outline: none;
        text-align: center;
        letter-spacing: 3px;
    }
    #pwd-input:focus { border-color: #2dd673; }
    #submitBtn {
        background: #2dd673;
        color: #000;
        padding: 11px 32px;
        border-radius: 12px;
        border: none;
        font-weight: 700;
        cursor: pointer;
        font-size: 14px;
        width: 280px;
    }
    #submitBtn:hover { opacity: 0.85; }
    #backBtn {
        background: transparent;
        border: none;
        color: #444;
        font-size: 12px;
        cursor: pointer;
        margin-top: 4px;
    }
    #backBtn:hover { color: #888; }
</style>
</head>
<body>
    <div id="title">
        <div class="dot"></div>
        AEGIS
    </div>
    <div id="subtitle">IDENTITY VERIFICATION</div>

    <div id="cam-container">
        <img id="cam-feed" src="" />
        <div id="cam-overlay">SCANNING</div>
    </div>

    <div id="status">Position your face in the camera</div>

    <div class="btn-row" id="main-btns">
        <button class="btn" id="faceBtn">🔍 Scan Face</button>
        <button class="btn" id="pwdBtn">🔑 Password</button>
    </div>

    <div id="pwd-panel">
        <input id="pwd-input" type="password" placeholder="Enter password" maxlength="20" />
        <button id="submitBtn">Unlock Aegis</button>
        <button id="backBtn">← Back to face scan</button>
    </div>

<script>
    const camFeed = document.getElementById('cam-feed');
    const status = document.getElementById('status');
    const faceBtn = document.getElementById('faceBtn');
    const pwdBtn = document.getElementById('pwdBtn');
    const pwdPanel = document.getElementById('pwd-panel');
    const mainBtns = document.getElementById('main-btns');
    const pwdInput = document.getElementById('pwd-input');
    const submitBtn = document.getElementById('submitBtn');
    const backBtn = document.getElementById('backBtn');

    let feedActive = true;

    async function updateFeed() {
        if (!feedActive) return;
        try {
            const frame = await window.pywebview.api.get_frame();
            if (frame) camFeed.src = frame;
        } catch(e) {}
    }
    setInterval(updateFeed, 100);

    function setStatus(msg, type) {
        status.textContent = msg;
        status.className = type || '';
    }

    faceBtn.addEventListener('click', async () => {
        faceBtn.disabled = true;
        setStatus('Scanning face...');
        const result = await window.pywebview.api.check_face();
        if (result.success) {
            feedActive = false;
            setStatus('✅ Welcome back!', 'success');
            setTimeout(() => window.pywebview.api.launch_aegis(), 800);
        } else {
            setStatus('❌ Face not recognized. Try again or use password.', 'error');
            faceBtn.disabled = false;
        }
    });

    pwdBtn.addEventListener('click', () => {
        mainBtns.style.display = 'none';
        pwdPanel.style.display = 'flex';
        pwdInput.focus();
    });

    backBtn.addEventListener('click', () => {
        pwdPanel.style.display = 'none';
        mainBtns.style.display = 'flex';
        pwdInput.value = '';
        setStatus('Position your face in the camera');
    });

    submitBtn.addEventListener('click', async () => {
        const pwd = pwdInput.value;
        if (!pwd) return;
        submitBtn.disabled = true;
        setStatus('Checking...');
        const result = await window.pywebview.api.check_password(pwd);
        if (result.success) {
            feedActive = false;
            setStatus('✅ Access granted!', 'success');
            setTimeout(() => window.pywebview.api.launch_aegis(), 800);
        } else {
            setStatus('❌ Galat password! Try again.', 'error');
            pwdInput.value = '';
            submitBtn.disabled = false;
        }
    });

    pwdInput.addEventListener('keypress', e => {
        if (e.key === 'Enter') submitBtn.click();
    });
</script>
</body>
</html>
"""

security_window = None


def launch_aegis():
    """Launch main Aegis window after auth — create new window BEFORE destroying old one"""
    from ui_api import Api
    from ui_html import HTML

    api = Api()
    webview.create_window(
        'Aegis',
        html=HTML,
        js_api=api,
        width=480,
        height=720,
        resizable=True,
        background_color='#f5f6f8'
    )

    # Destroy the security window only after the new one has been created
    if security_window is not None:
        try:
            security_window.destroy()
        except Exception as e:
            print(f"Error destroying security window: {e}")


class SecurityApiWithLaunch(SecurityApi):
    def launch_aegis(self):
        """Called from JS after successful auth"""
        threading.Thread(target=launch_aegis, daemon=True).start()


if __name__ == '__main__':
    setup_if_needed()

    security_api = SecurityApiWithLaunch()

    security_window = webview.create_window(
        'Aegis — Identity Verification',
        html=SECURITY_HTML,
        js_api=security_api,
        width=420,
        height=620,
        resizable=False,
        background_color='#0a0a0a'
    )

    webview.start()