from pyngrok import ngrok, conf
import subprocess, time, smtplib, requests
from email.mime.text import MIMEText

# ---------------- SETTINGS ----------------
FLASK_PORT = 5000
NGROK_AUTH = "326QY7UxwC3Df0Y1lFeUP3P3Sqr_2KnBPNGA9dyN95Y4Zr8aj"
conf.get_default().ngrok_path = r"C:\ngrok\ngrok.exe"   # path to ngrok.exe

# Email (for NGROK URL only)
URL_EMAIL_SENDER   = "zainahmed1208@gmail.com"
URL_EMAIL_PASS     = "eswu vdwt bpcr lrmb"   # Gmail App Password
URL_EMAIL_RECEIVER = "adminmonitor@gmail.com"   # 👈 public URL recipient

# Telegram (for NGROK URL only)
BOT_TOKEN = "8211192262:AAFURlGftQQBcIUE6ldU1UTWx0uITHksqrE"
CHAT_ID   = "1715978704"
# -------------------------------------------

def send_url_email(public_url):
    try:
        msg = MIMEText(f"🔴 Your Edge-AI Surveillance app is LIVE at:\n\n{public_url}")
        msg["From"] = URL_EMAIL_SENDER
        msg["To"] = URL_EMAIL_RECEIVER
        msg["Subject"] = "Surveillance App - Ngrok Public URL"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(URL_EMAIL_SENDER, URL_EMAIL_PASS)
        server.sendmail(URL_EMAIL_SENDER, URL_EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("📧 Ngrok URL emailed successfully.")
    except Exception as e:
        print("❌ Ngrok URL email failed:", e)

def send_url_telegram(public_url):
    try:
        message = f"🔴 Your Edge-AI Surveillance app is LIVE:\n{public_url}"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        print("📲 Ngrok URL sent to Telegram.")
    except Exception as e:
        print("❌ Telegram send failed:", e)

print("🔹 Starting Flask server...")
flask_process = subprocess.Popen(["python", "app.py"])

time.sleep(5)  # allow Flask to start

print("🔹 Connecting Ngrok tunnel...")
ngrok.set_auth_token(NGROK_AUTH)
public_url = ngrok.connect(FLASK_PORT).public_url

print(f"✅ Your app is live at: {public_url}")
print("⚡ Share this link with anyone!")

# Send public URL to email + telegram
send_url_email(public_url)
send_url_telegram(public_url)

# Save to file for reference
with open("ngrok_url.log", "w") as f:
    f.write(f"App live at: {public_url}\n")

try:
    flask_process.wait()
except KeyboardInterrupt:
    print("\n⏹ Stopping servers...")
    flask_process.terminate()
    ngrok.kill()
