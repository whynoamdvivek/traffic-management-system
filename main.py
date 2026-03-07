# main.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2, numpy as np, os, time, threading

from vehicle_detector import detect_vehicles
from signal_controller import decide_signal

# optional beep (harmless)
try:
    import winsound
    def beep(): winsound.Beep(800, 150)
except Exception:
    def beep(): None

class TrafficGUI:
    def __init__(self, root):
        self.root = root
        root.title("TLMS-VIVEK —")
        root.geometry("1200x720")
        self.style = ttk.Style(root)
        try:
            self.style.theme_use("clam")
        except:
            pass

        # state
        self.paths = {}        # direction -> path or "CAM"
        self.frames = {}       # direction -> PIL image
        self.counts = {}
        self.boxes = {}
        self.cameras = {}      # direction -> cv2.VideoCapture
        self.auto_process = tk.BooleanVar(value=False)

        self._build_ui()
        self._update_ui_loop()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(side="top", fill="x")

        # grid columns so buttons don't overlap
        for c in range(0, 10):
            top.grid_columnconfigure(c, weight=1)

        dirs = ["North","South","East","West"]
        for i, d in enumerate(dirs):
            btn = ttk.Button(top, text=f"Load {d}", command=lambda dd=d: self.load_image(dd))
            btn.grid(row=0, column=i, padx=4, sticky="nsew")
            cam = ttk.Button(top, text=f"Cam {d}", command=lambda dd=d: self.open_camera(dd))
            cam.grid(row=1, column=i, padx=4, pady=(4,0), sticky="nsew")

        # Process Now — big and visible
        proc_btn = ttk.Button(top, text="🚦  Process Now  🚦", command=self.process_all)
        proc_btn.grid(row=0, column=5, rowspan=2, padx=12, pady=2, sticky="nsew")
        proc_btn.configure(width=18)

        # NOTE:

        auto_cb = ttk.Checkbutton(top, text="Auto Process", variable=self.auto_process)
        auto_cb.grid(row=0, column=6, padx=6, sticky="w")

        settings_btn = ttk.Button(top, text="Settings", command=self.open_settings)
        settings_btn.grid(row=0, column=9, padx=6, sticky="e")

        export_btn = ttk.Button(top, text="Export CSV", command=self.export_csv)
        export_btn.grid(row=1, column=9, padx=6, sticky="e")

        # middle
        mid = ttk.Frame(self.root)
        mid.pack(side="top", fill="both", expand=True, padx=8, pady=6)
        left = ttk.Frame(mid)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(mid, width=320)
        right.pack(side="right", fill="y")

        # canvases
        self.canvases = {}
        dirs_frame = ttk.Frame(left)
        dirs_frame.pack(fill="both", expand=True)
        for i, d in enumerate(dirs):
            c = tk.Canvas(dirs_frame, width=520, height=240, bg="#222")
            c.grid(row=i//2, column=i%2, padx=6, pady=6)
            self.canvases[d] = c

        # treeview
        cols = ("Direction", "Count")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=8)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(padx=6, pady=6, fill="y")

        # init rows
        for d in dirs:
            self.tree.insert("", "end", iid=d, values=(d, 0))

        # output and log
        self.output_var = tk.StringVar(value="GREEN → —")
        out_lbl = ttk.Label(right, textvariable=self.output_var, font=("Arial", 14, "bold"), foreground="darkgreen")
        out_lbl.pack(pady=(10,4))

        ttk.Label(right, text="Log:").pack(anchor="w", padx=6)
        self.log = tk.Text(right, height=12, width=40)
        self.log.pack(padx=6, pady=4)

    # ---------------- image/camera load ----------------
    def load_image(self, direction):
        path = filedialog.askopenfilename(filetypes=[("Images","*.jpg *.png *.webp *.jpeg")])
        if not path:
            return
        self.paths[direction] = path
        img = Image.open(path).convert("RGB")
        self.frames[direction] = img
        self._draw_on_canvas(direction, img)
        self._log(f"Loaded image for {direction}: {os.path.basename(path)}")

    def open_camera(self, direction):
        # opens default webcam (index 0) and grabs one frame for this direction
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(0)
        if not cap or not cap.isOpened():
            messagebox.showerror("Camera", "Cannot open camera (index 0).")
            return
        self.cameras[direction] = cap
        self.paths[direction] = "CAM"
        self._log(f"Camera opened for {direction}")
        def grab_frame():
            ret, frame = cap.read()
            if not ret:
                self._log("Camera frame grab failed.")
                return
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(frame)
            self.frames[direction] = pil
            self._draw_on_canvas(direction, pil)
            if self.auto_process.get():
                self.process_all()
        threading.Thread(target=grab_frame, daemon=True).start()

    # ---------------- processing ----------------
    def process_all(self):
        if not self.frames:
            messagebox.showwarning("No images", "Load at least one image or open camera.")
            return

        self.counts.clear(); self.boxes.clear()

        for d, pil in self.frames.items():
            # convert PIL to cv2 BGR
            frame = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
            try:
                # use detector default threshold inside detect_vehicles (no slider)
                cnt, bxs = detect_vehicles(frame)
            except Exception as e:
                self._log(f"Detection error for {d}: {e}")
                cnt, bxs = 0, []

            self.counts[d] = cnt
            self.boxes[d] = bxs

            # annotate
            annotated = frame.copy()
            for (x1,y1,x2,y2,score) in bxs:
                cv2.rectangle(annotated, (x1,y1),(x2,y2), (0,255,0), 2)
                cv2.putText(annotated, f"{score:.2f}", (x1, y1-6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,0), 1)

            annotated = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            pil2 = Image.fromarray(annotated).resize((520,240))
            self.frames[d] = pil2
            self._draw_on_canvas(d, pil2)

            self.tree.item(d, values=(d, cnt))

        # decide signal using counts only (emergency removed)
        green_dir, green_t = decide_signal(self.counts, {})  # pass empty emergency dict
        self.output_var.set(f"GREEN → {green_dir} for {green_t} s")
        self._log(f"Decision: {green_dir} for {green_t}s")

    # ---------------- helpers ----------------
    def _draw_on_canvas(self, direction, pil_img):
        c = self.canvases[direction]
        cw = int(c.winfo_width()) or 520
        ch = int(c.winfo_height()) or 240
        img = pil_img.copy().resize((cw, ch))
        tkimg = ImageTk.PhotoImage(img)
        c.delete("all")
        c.create_image(0,0,anchor="nw",image=tkimg)
        c.image = tkimg

    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("360x200")
        ttk.Label(win, text="Settings currently minimal (no confidence slider).").pack(pady=12)
        ttk.Label(win, text="Auto Process will re-run detection every 4s if camera frames open.").pack(pady=6)

    def export_csv(self):
        if not self.counts:
            messagebox.showwarning("No data", "No detection results to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")])
        if not path:
            return
        import csv
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Direction","Count","Timestamp"])
            for d in ["North","East","South","West"]:
                writer.writerow([d, self.counts.get(d,0), time.strftime("%Y-%m-%d %H:%M:%S")])
        self._log(f"Exported CSV: {os.path.basename(path)}")
        messagebox.showinfo("Exported", f"CSV saved to {path}")

    def _log(self, text):
        ts = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {text}\n")
        self.log.see("end")

    def _update_ui_loop(self):
        # if auto_process and cameras opened, refresh camera frames and process
        if self.auto_process.get():
            for dir_, cap in list(self.cameras.items()):
                if cap and cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil = Image.fromarray(frame)
                        self.frames[dir_] = pil
                        self._draw_on_canvas(dir_, pil)
            self.process_all()
        self.root.after(4000, self._update_ui_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = TrafficGUI(root)
    root.mainloop()
