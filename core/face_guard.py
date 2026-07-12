import cv2
import os
import numpy as np

AEGIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACE_DIR = os.path.join(AEGIS_DIR, "owner_face")
FACE_IMAGE = os.path.join(FACE_DIR, "owner.jpg")

os.environ['OPENCV_LOG_LEVEL'] = 'SILENT'

# Load face detector once at startup
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)


def capture_owner_face():
    """First time setup — capture and save owner face"""
    os.makedirs(FACE_DIR, exist_ok=True)
    print("Aegis: Opening camera — press SPACE once to capture, Q to skip...")

    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    captured = False

    while True:
        ret, frame = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (45, 255, 130), 2)
            cv2.putText(frame, "Face detected!", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (45, 255, 130), 2)

        cv2.imshow("Aegis Face Setup — Press SPACE to capture, Q to skip", frame)
        key = cv2.waitKey(100) & 0xFF  # 100ms delay prevents multiple captures

        if key == ord(' '):
            if len(faces) > 0:
                cv2.imwrite(FACE_IMAGE, frame)
                print("✅ Face captured successfully!")
                captured = True
                break  # ← break immediately after ONE capture
            else:
                print("⚠️ No face detected — move closer")

        elif key == ord('q'):
            print("⚠️ Face setup skipped — password only mode")
            break

    cam.release()
    cv2.destroyAllWindows()
    return captured


def get_face_signature(image):
    """Extract face region as a normalized signature for comparison"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Try multiple scale settings for better detection
    for scale in [1.1, 1.2, 1.3]:
        try:
            faces = face_cascade.detectMultiScale(
                gray, scale, 3,
                minSize=(50, 50)
            )
            if len(faces) > 0:
                # Get largest face
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                face_roi = gray[y:y+h, x:x+w]
                # Normalize and resize
                face_roi = cv2.resize(face_roi, (100, 100))
                face_roi = cv2.equalizeHist(face_roi)
                return face_roi
        except Exception as e:
            continue

    return None


def is_owner(threshold=0.55):
    """
    Fast face check using OpenCV only.
    No TensorFlow, no DeepFace — under 2 seconds.
    """
    if not os.path.exists(FACE_IMAGE):
        return True  # No face registered — allow access

    owner_img = cv2.imread(FACE_IMAGE)
    if owner_img is None:
        return True

    owner_sig = get_face_signature(owner_img)
    if owner_sig is None:
        print("Warning: no face in saved image — allowing access")
        return True

    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    is_me = False
    attempts = 0
    max_attempts = 20

    while attempts < max_attempts:
        ret, frame = cam.read()
        if not ret:
            attempts += 1
            continue

        current_sig = get_face_signature(frame)
        if current_sig is None:
            attempts += 1
            continue

        try:
            result = cv2.matchTemplate(
                owner_sig.astype(np.float32),
                current_sig.astype(np.float32),
                cv2.TM_CCOEFF_NORMED
            )
            score = result[0][0]

            if score >= threshold:
                is_me = True
                break

        except Exception as e:
            pass

        attempts += 1

    cam.release()
    return is_me


def get_frame_base64(cam):
    """Capture a frame and return as base64 for GUI display"""
    import base64

    ret, frame = cam.read()
    if not ret:
        return None

    # Draw face detection boxes
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    try:
        faces = face_cascade.detectMultiScale(
            gray, 1.2, 3,
            minSize=(50, 50)
        )
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (45, 255, 130), 2)
    except:
        pass

    # Encode to base64
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    b64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{b64}"


def setup_if_needed():
    """Auto setup on first run"""
    if not os.path.exists(FACE_IMAGE):
        print("First time setup — registering your face...")
        capture_owner_face()