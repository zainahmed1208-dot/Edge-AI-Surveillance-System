from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import cv2, numpy as np, os, time, smtplib, requests, collections, subprocess
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- Users ----------------
users = {
    "admin": {"password": generate_password_hash("admin123"), "role": "admin"},
    "viewer": {"password": generate_password_hash("viewer123"), "role": "viewer"}
}

# ---------------- Camera ----------------
camera = None
running = False
last_alert_time = 0

# ---------------- YOLO ----------------
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

settings = {
    "confidence": 0.3,
    "cooldown": 30,
    "objects": {"person": True, "car": True, "dog": True, "cat": True}
}

# ---------------- Email (snapshots) ----------------
SNAP_EMAIL_SENDER   = "zainahmed1208@gmail.com"
SNAP_EMAIL_PASS     = "eswu vdwt bpcr lrmb"
SNAP_EMAIL_RECEIVER = "touheedmasjid05@gmail.com"

# ---------------- Telegram (videos) ----------------
BOT_TOKEN = "8211192262:AAFURlGftQQBcIUE6ldU1UTWx0uITHksqrE"
CHAT_ID = "1715978704"

# ---------------- FFmpeg Path ----------------
FFMPEG_PATH = r"C:\Users\91779\Downloads\ffmpeg-8.0-essentials_build\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe"

# ---------------- Recording ----------------
if not os.path.exists("recordings"):
    os.makedirs("recordings")

fps = 20
frame_size = (640, 480)
buffer = collections.deque(maxlen=fps*5)
recording = False
out = None
last_detection_time = 0
record_duration_after_event = 10

# ---------------- Helpers ----------------
def add_watermark(frame):
    timestamp_text = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, timestamp_text, (10, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(frame, "ZHGV", (frame.shape[1]-80, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    return frame

def start_recording():
    global out, recording
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"recordings/event_{timestamp}.avi"
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(filename, fourcc, fps, frame_size)
    print(f"🎥 Started recording: {filename}")
    for f in buffer:
        out.write(add_watermark(f))  # clean video only watermark
    recording = True
    return filename

def send_snapshot_email(snapshot_path, obj):
    try:
        msg = MIMEMultipart()
        msg["From"] = SNAP_EMAIL_SENDER
        msg["To"] = SNAP_EMAIL_RECEIVER
        msg["Subject"] = f"⚠ ALERT: {obj.upper()} Detected"
        msg.attach(MIMEText(f"A {obj} was detected. See attached snapshot.", "plain"))

        if snapshot_path and os.path.exists(snapshot_path):
            with open(snapshot_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(snapshot_path)}")
            msg.attach(part)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SNAP_EMAIL_SENDER, SNAP_EMAIL_PASS)
        server.sendmail(SNAP_EMAIL_SENDER, SNAP_EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("📧 Snapshot email sent to", SNAP_EMAIL_RECEIVER)
    except Exception as e:
        print("❌ Snapshot email failed:", e)

def send_video_telegram(video_path, caption=None):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
        with open(video_path, "rb") as vid_file:
            files = {"video": (os.path.basename(video_path), vid_file)}
            data = {"chat_id": CHAT_ID}
            if caption:
                data["caption"] = caption
            resp = requests.post(url, files=files, data=data, timeout=120)
        if resp.status_code == 200:
            print("📲 Video sent to Telegram:", video_path)
        else:
            print("❌ Telegram video send failed:", resp.status_code, resp.text)
    except Exception as e:
        print("❌ Exception while sending video to Telegram:", e)

def stop_recording_and_convert_send():
    global out, recording
    if recording and out is not None:
        out.release()
        recording = False
        print("⏹ Stopped recording")

        try:
            files = sorted(os.listdir("recordings"), reverse=True)
            avi_files = [f for f in files if f.endswith(".avi")]
            if avi_files:
                latest_avi = avi_files[0]
                avi_path = os.path.join("recordings", latest_avi)
                mp4_path = avi_path.replace(".avi", ".mp4")

                print(f"🔄 Converting {latest_avi} to MP4...")
                subprocess.run([FFMPEG_PATH, "-y", "-i", avi_path, "-vcodec", "libx264", "-crf", "23", mp4_path],
                               check=True)

                os.remove(avi_path)
                print(f"✅ Converted and saved as {mp4_path}")

                caption = f"Alert clip: {os.path.basename(mp4_path)}"
                send_video_telegram(mp4_path, caption=caption)
        except Exception as e:
            print("❌ MP4 conversion/send failed:", e)

# ---------------- Detection ----------------
def detect_objects(frame):
    global last_alert_time, last_detection_time, recording
    height, width, _ = frame.shape
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416,416), (0,0,0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    boxes, confidences, class_ids = [], [], []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = int(np.argmax(scores))
            confidence = float(scores[class_id])
            if confidence > settings["confidence"]:
                center_x, center_y, w, h = int(detection[0]*width), int(detection[1]*height), int(detection[2]*width), int(detection[3]*height)
                x, y = int(center_x - w/2), int(center_y - h/2)
                boxes.append([x,y,w,h])
                confidences.append(confidence)
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, settings["confidence"], 0.4)
    detected = []
    if len(indexes) > 0:
        for i in indexes.flatten():
            x,y,w,h = boxes[i]
            label = classes[class_ids[i]]
            if label in settings["objects"] and settings["objects"][label]:
                cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
                cv2.putText(frame, f"{label}", (x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
                detected.append(label)

    if detected:
        now = time.time()
        last_detection_time = now
        if not recording:
            start_recording()
        if now - last_alert_time > settings["cooldown"]:
            last_alert_time = now
            snapshot_path = "alert_snapshot.jpg"
            cv2.imwrite(snapshot_path, frame)
            for obj in detected:
                send_snapshot_email(snapshot_path, obj)
    return frame

# ---------------- Frame generator ----------------
def generate_frames():
    global camera, running, buffer, recording, last_detection_time, out
    while running and camera:
        success, frame = camera.read()
        if not success:
            time.sleep(0.1)
            continue

        frame = cv2.resize(frame, frame_size)
        buffer.append(frame.copy())

        # Detection for alerts
        detect_objects(frame.copy())

        # Record clean video (no boxes, only watermark)
        if recording:
            out.write(add_watermark(frame.copy()))
            if time.time() - last_detection_time > record_duration_after_event:
                stop_recording_and_convert_send()

        # Stream annotated feed (with boxes) to browser
        annotated = detect_objects(frame.copy())
        stream_frame = add_watermark(annotated.copy())
        ret, buffer2 = cv2.imencode('.jpg', stream_frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer2.tobytes() + b'\r\n')

# ---------------- Routes ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        if username in users and check_password_hash(users[username]["password"], password):
            session["user"] = username
            session["role"] = users[username]["role"]
            return redirect(url_for('index'))
        else:
            return render_template("login.html", error="Invalid username or password")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/')
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"], role=session["role"])

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start', methods=['POST'])
def start():
    global camera, running
    if not running:
        camera = cv2.VideoCapture(0)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, frame_size[0])
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_size[1])
        running = True
    return jsonify(status="started")

@app.route('/stop', methods=['POST'])
def stop():
    global camera, running
    running = False
    if camera:
        camera.release()
    if recording:
        stop_recording_and_convert_send()
    return jsonify(status="stopped")

@app.route('/recordings')
def recordings_page():
    files = sorted(os.listdir("recordings"), reverse=True)
    files = [f for f in files if f.endswith(".mp4")]

    display_files = []
    for f in files:
        try:
            name = f.replace("event_", "").replace(".mp4", "")
            dt = datetime.strptime(name, "%Y%m%d-%H%M%S")
            display_name = dt.strftime("%d %b %Y, %H:%M:%S")
        except:
            display_name = f
        display_files.append({"filename": f, "display": display_name})

    return render_template("recordings.html", files=display_files)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory("recordings", filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
