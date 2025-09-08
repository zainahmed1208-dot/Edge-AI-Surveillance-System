import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk

running = False
cap = None

# -------------------- Animated Rounded Toggle --------------------
class AnimatedToggle(tk.Frame):
    def __init__(self, parent, text, var, *args, **kwargs):
        super().__init__(parent, bg="#1C1C1C", *args, **kwargs)
        self.var = var
        self.width, self.height = 50, 28
        self.knob_pos = 2 if not self.var.get() else 26
        self.target_pos = self.knob_pos

        # Label
        self.label = tk.Label(self, text=text, bg="#1C1C1C", fg="white", font=("Arial", 11))
        self.label.pack(side="left", padx=5)

        # Canvas
        self.canvas = tk.Canvas(self, width=self.width, height=self.height,
                                bg="#1C1C1C", highlightthickness=0)
        self.canvas.pack(side="right", padx=10)
        self.canvas.bind("<Button-1>", self.toggle)

        self.draw()

    def draw(self):
        self.canvas.delete("all")
        # Track (rounded pill)
        if self.var.get():
            fill = "#E41C23"   # Hikvision Red when ON
        else:
            fill = "#555555"   # Grey when OFF

        # Rounded rectangle (pill shape)
        self.canvas.create_oval(2, 2, 26, 26, fill=fill, outline=fill)
        self.canvas.create_oval(24, 2, 48, 26, fill=fill, outline=fill)
        self.canvas.create_rectangle(14, 2, 36, 26, fill=fill, outline=fill)

        # Knob (circle)
        self.canvas.create_oval(self.knob_pos, 2, self.knob_pos + 22, 24,
                                fill="white", outline="white")

    def animate(self):
        if self.knob_pos < self.target_pos:
            self.knob_pos += 2
            if self.knob_pos > self.target_pos:
                self.knob_pos = self.target_pos
            self.draw()
            self.after(10, self.animate)
        elif self.knob_pos > self.target_pos:
            self.knob_pos -= 2
            if self.knob_pos < self.target_pos:
                self.knob_pos = self.target_pos
            self.draw()
            self.after(10, self.animate)

    def toggle(self, event=None):
        self.var.set(not self.var.get())
        self.target_pos = 26 if self.var.get() else 2
        self.animate()

# -------------------- Webcam --------------------
def live_view_toggle():
    global cap, running
    if not running:
        cap = cv2.VideoCapture(0)
        running = True
        update_frame()
        live_btn.config(text="⏹ Stop Live View", bg="#E41C23")
        log_message("▶ Live View started...", "warn")
    else:
        running = False
        if cap:
            cap.release()
        for feed in camera_labels:
            feed.config(image="", text="Camera Disconnected", fg="red")
        live_btn.config(text="▶ Live View", bg="#333333")
        log_message("⏹ Live View stopped.", "warn")

def update_frame():
    global cap, running
    if running and cap:
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imgtk = ImageTk.PhotoImage(image=Image.fromarray(frame))
            camera_labels[0].imgtk = imgtk
            camera_labels[0].config(image=imgtk, text="")
        else:
            camera_labels[0].config(text="Camera Disconnected", fg="red")
    for i in range(1, 4):
        camera_labels[i].config(text="Camera Disconnected", fg="red")
    if running:
        root.after(30, update_frame)

# -------------------- Settings --------------------
def open_settings():
    settings_win = tk.Toplevel(root)
    settings_win.title("Admin Dashboard")
    settings_win.geometry("500x400")
    settings_win.configure(bg="#0D0D0D")
    tk.Label(settings_win, text="⚙ Admin Dashboard", fg="white", bg="#0D0D0D",
             font=("Arial", 16, "bold")).pack(pady=20)

# -------------------- Log Helper --------------------
def log_message(msg, level="info"):
    color = {"success": "lime", "error": "red", "warn": "yellow"}.get(level, "white")
    log_box.insert(tk.END, msg + "\n", color)
    log_box.see(tk.END)

# -------------------- Root --------------------
root = tk.Tk()
root.title("Hik-Connect Style - Edge AI Surveillance")
root.geometry("1400x950")
root.configure(bg="#0D0D0D")

# 🎨 Slider Style
style = ttk.Style()
style.theme_use("clam")
style.configure("Hik.Horizontal.TScale",
                troughcolor="#1C1C1C",
                background="#E41C23",
                sliderthickness=18,
                troughrelief="flat")

# Title Bar
title_frame = tk.Frame(root, bg="#0D0D0D")
title_frame.pack(fill="x", pady=5)

settings_btn = tk.Button(title_frame, text="⚙ Settings", command=open_settings,
                         bg="#1C1C1C", fg="white", font=("Arial", 11), relief="flat", padx=10)
settings_btn.pack(side="left", padx=10)

title_label = tk.Label(title_frame, text="Edge-AI Smart Surveillance",
                       font=("Arial", 20, "bold"), fg="#E41C23", bg="#0D0D0D")
title_label.pack(side="left", padx=20)

# Main Frame
main_frame = tk.Frame(root, bg="#1C1C1C")
main_frame.pack(fill="both", expand=True, padx=10, pady=5)

# Video Grid
video_frame = tk.Frame(main_frame, bg="black", width=900, height=600)
video_frame.pack(side="left", padx=5, pady=5)

camera_labels = []
for row in range(2):
    for col in range(2):
        cam_label = tk.Label(video_frame, bg="black", fg="red", text="Camera Disconnected",
                             font=("Arial", 14, "bold"), width=50, height=15, relief="ridge", bd=2)
        cam_label.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
        camera_labels.append(cam_label)

video_frame.grid_rowconfigure(0, weight=1)
video_frame.grid_rowconfigure(1, weight=1)
video_frame.grid_columnconfigure(0, weight=1)
video_frame.grid_columnconfigure(1, weight=1)

# Control Panel
control_frame = tk.Frame(main_frame, bg="#1C1C1C", width=300)
control_frame.pack(side="right", fill="y", padx=10)

# Object Toggles
tk.Label(control_frame, text="Objects to Detect:", fg="white", bg="#1C1C1C", font=("Arial", 12, "bold")).pack(pady=5)
object_vars = {}
for obj in ["person", "car", "dog", "cat"]:
    var = tk.BooleanVar(value=True)
    object_vars[obj] = var
    toggle = AnimatedToggle(control_frame, obj.capitalize(), var)
    toggle.pack(fill="x", pady=8, padx=10)

# Confidence Slider
tk.Label(control_frame, text="Confidence Threshold", fg="white", bg="#1C1C1C", font=("Arial", 12)).pack(pady=5)
conf_scale = tk.DoubleVar(value=0.3)
ttk.Scale(control_frame, from_=0.1, to=1.0, orient="horizontal",
          variable=conf_scale, length=250, style="Hik.Horizontal.TScale").pack(pady=5)

# Cooldown Slider
tk.Label(control_frame, text="Cooldown (sec)", fg="white", bg="#1C1C1C", font=("Arial", 12)).pack(pady=5)
cooldown_scale = tk.IntVar(value=30)
ttk.Scale(control_frame, from_=5, to=120, orient="horizontal",
          variable=cooldown_scale, length=250, style="Hik.Horizontal.TScale").pack(pady=5)

# Live View Button
live_btn = tk.Button(control_frame, text="▶ Live View", font=("Arial", 12), command=live_view_toggle,
                     bg="#333333", fg="white", width=20)
live_btn.pack(pady=15)

# Exit Button
tk.Button(control_frame, text="❌ Exit", font=("Arial", 12), command=root.destroy,
          bg="#E41C23", fg="white", width=20).pack(pady=5)

# Log Window
log_label = tk.Label(root, text="Event / Alert Log", fg="white", bg="#0D0D0D", font=("Arial", 12, "bold"))
log_label.pack(pady=5)

log_frame = tk.Frame(root, bg="#0D0D0D")
log_frame.pack(fill="both", expand=True, padx=10, pady=5)

scrollbar = tk.Scrollbar(log_frame)
scrollbar.pack(side="right", fill="y")

log_box = tk.Text(log_frame, height=10, width=160, bg="black", fg="white", font=("Consolas", 10),
                  yscrollcommand=scrollbar.set)
log_box.pack(side="left", fill="both", expand=True)
scrollbar.config(command=log_box.yview)

log_box.tag_config("lime", foreground="lime")
log_box.tag_config("red", foreground="red")
log_box.tag_config("yellow", foreground="yellow")
log_box.tag_config("white", foreground="white")

root.mainloop()
