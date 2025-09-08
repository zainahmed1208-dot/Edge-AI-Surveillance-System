import cv2
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import os
import time
import sys

# -------------------- Load YOLOv3 (FULL, Accurate) --------------------
print("🔹 Loading YOLOv3 (full version)...")
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")

with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]

layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# -------------------- Target Objects --------------------
target_objects = [
    "person", "car", "bird", "cat", "dog", "horse",
    "sheep", "cow", "elephant", "bear", "zebra", "giraffe"
]

# -------------------- Alert Manager (Email + Telegram) --------------------
def send_alert(snapshot_path, detected_object):
    # -------- Email Setup --------
    sender = "zainahmed1208@gmail.com"
    receiver = "touheedmasjid05@gmail.com"
    password = "eswu vdwt bpcr lrmb"  # Gmail App Password

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = f"⚠ ALERT: {detected_object.upper()} Detected by Edge-AI Surveillance MVP"
    body = f"A {detected_object} was detected by your Edge-AI Smart Surveillance System. See attached snapshot."
    msg.attach(MIMEText(body, "plain"))

    if snapshot_path and os.path.exists(snapshot_path):
        with open(snapshot_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(snapshot_path)}")
        msg.attach(part)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()
        print("✅ Email alert sent with snapshot!")
    except Exception as e:
        print("❌ Email failed:", e)

    # -------- Telegram Setup --------
    bot_token = "8211192262:AAFURlGftQQBcIUE6ldU1UTWx0uITHksqrE"
    chat_id = "1715978704"
    message = f"⚠ ALERT: {detected_object.upper()} detected by Edge-AI Surveillance MVP"

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": message})

        if snapshot_path and os.path.exists(snapshot_path):
            url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
            files = {"photo": open(snapshot_path, "rb")}
            data = {"chat_id": chat_id}
            requests.post(url, files=files, data=data)

        print("✅ Telegram alert sent!")
    except Exception as e:
        print("❌ Telegram failed:", e)

# -------------------- YOLO Detection Function --------------------
def detect_objects(frame, output_path=None):
    height, width, _ = frame.shape
    blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0,0,0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    class_ids, confidences, boxes = [], [], []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.2:  # detect everything, then filter
                center_x, center_y, w, h = (
                    int(detection[0] * width),
                    int(detection[1] * height),
                    int(detection[2] * width),
                    int(detection[3] * height),
                )
                x, y = int(center_x - w/2), int(center_y - h/2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    detected_labels = []

    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            label = str(classes[class_ids[i]])
            conf = confidences[i]
            if label in target_objects:
                detected_labels.append(label)
                cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
                cv2.putText(frame, f"{label} {conf:.2f}", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
                print(f"✅ Detected {label} with confidence {conf:.2f}")

    if output_path:
        cv2.imwrite(output_path, frame)

    return frame, detected_labels

# -------------------- Main --------------------
if len(sys.argv) < 2:
    print("Usage:")
    print("  python edge_ai_surveillance_mvp.py --webcam")
    print("  python edge_ai_surveillance_mvp.py --image path/to/image.jpg")
    sys.exit(0)

mode = sys.argv[1]
last_alert_time = 0
cooldown = 30  # seconds between alerts

if mode == "--webcam":
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame, labels = detect_objects(frame, "alert_snapshot.jpg")
        if labels:
            current_time = time.time()
            if current_time - last_alert_time > cooldown:
                for label in labels:
                    send_alert("alert_snapshot.jpg", label)
                last_alert_time = current_time
            else:
                print("⏳ Cooldown active...")

        cv2.imshow("Edge-AI Surveillance MVP", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

elif mode == "--image":
    if len(sys.argv) < 3:
        print("❌ Please provide an image path. Example: python edge_ai_surveillance_mvp.py --image dog.jpg")
        sys.exit(1)

    image_path = sys.argv[2]
    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        sys.exit(1)

    img = cv2.imread(image_path)
    img, labels = detect_objects(img, "alert_snapshot.jpg")

    if labels:
        for label in labels:
            send_alert("alert_snapshot.jpg", label)
    else:
        print("❌ No target objects detected in this image.")

    cv2.imshow("YOLO Image Detection", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

else:
    print("❌ Invalid mode. Use --webcam or --image <path>")
