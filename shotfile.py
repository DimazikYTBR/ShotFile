import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path

APP = "ShotFile"
VERSION = "1.0.1"
BUILD = "20261024.3"
GITHUB_RELEASE_API = "https://api.github.com/repos/DimazikYTBR/ShotFile/releases/tags/latest"
GITHUB_REPO_URL = "https://github.com/DimazikYTBR/ShotFile/releases/latest"
UPDATE_CHECK_INTERVAL = 6 * 60 * 60
TON_ADDRESS = "UQAbta5Av9SF3M4SlLTht530Ujth_SWotOpEx3A7cLCf8JxR"
APPDATA = Path(os.environ.get("APPDATA", str(Path.home()))) / APP
CONFIG_PATH = APPDATA / "config.json"

DEFAULTS = {
    "mode": "auto",
    "folder": str(Path.home() / "Downloads" / "ShotFile"),
    "format": "PNG",
    "template": "Screenshot_yyyy-MM-dd_HH-mm-ss",
    "notify": True,
    "autostart": False,
    "start_minimized": False,
    "watch_hotkey": True,
    "gaming_mode": True,
}


BG = "#0a1224"
BG_SIDE = "#0b1428"
PANEL = "#0f1a33"
FIELD = "#142243"
LINE = "#1d2c4d"
FG = "#eef2fb"
MUTED = "#8c99b8"
ACCENT = "#2563eb"
ACCENT_SOFT = "#5b8cff"
NAV_ON = "#2456c9"
BTN = "#1a2748"
BTN_HOVER = "#23345e"
GOOD = "#22c55e"
FONT = "Segoe UI"
ICONS = "Segoe MDL2 Assets"

G_SETTINGS, G_FOLDER, G_PHOTO, G_PAGE = "", "", "", ""
G_PASTE, G_HEART, G_BELL, G_KEYS = "", "", "", ""
G_INFO, G_BOLT, G_CLOSE, G_CHEV = "", "", "", ""
G_DOWN, G_CLOCK, G_POWER, G_CHECK = "", "", "", ""
G_AUTO, G_TRAY = "", ""
G_MIN, G_WCLOSE = "", ""


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in DEFAULTS:
                if k in data:
                    cfg[k] = data[k]
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        APPDATA.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


_TOKEN = re.compile(r"(?<![A-Za-z])(yyyy|MM|dd|HH|mm|ss)(?![A-Za-z])")


def render_name(template, dt):
    values = {
        "yyyy": "%04d" % dt.year, "MM": "%02d" % dt.month, "dd": "%02d" % dt.day,
        "HH": "%02d" % dt.hour, "mm": "%02d" % dt.minute, "ss": "%02d" % dt.second,
    }
    name = _TOKEN.sub(lambda m: values[m.group(1)], template)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or "Screenshot"


def unique_path(folder, name, ext):
    path = Path(folder) / (name + ext)
    n = 1
    while path.exists():
        path = Path(folder) / ("%s_%d%s" % (name, n, ext))
        n += 1
    return path


def save_image(img, cfg, when=None):
    folder = Path(cfg["folder"])
    folder.mkdir(parents=True, exist_ok=True)
    fmt = str(cfg["format"]).upper()
    ext = ".png" if fmt == "PNG" else ".jpg"
    path = unique_path(folder, render_name(cfg["template"], when or datetime.now()), ext)
    if fmt == "PNG":
        img.save(path, "PNG")
    else:
        img.convert("RGB").save(path, "JPEG", quality=95)
    return path


def plural(n, a, b, c):
    m = abs(n) % 100
    d = m % 10
    if 10 < m < 20:
        return c
    if 1 < d < 5:
        return b
    return a if d == 1 else c


def make_icon(size=256, dark=False):
    from PIL import Image, ImageDraw
    s = 4
    big = size * s
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if dark:
        bw = int(big * 0.035)
        d.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.24), fill=(37, 99, 235, 255))
        d.rounded_rectangle((bw, bw, big - 1 - bw, big - 1 - bw), radius=int(big * 0.21), fill=(11, 24, 58, 255))
    else:
        d.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.24), fill=(37, 99, 235, 255))
    m = int(big * 0.24)
    white = (255, 255, 255, 255)
    d.rounded_rectangle((m, m, big - m, big - m), radius=int(big * 0.09), outline=white, width=int(big * 0.06))
    cx, cy, r = int(big * 0.62), int(big * 0.4), int(big * 0.065)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=white)
    d.polygon([
        (int(big * 0.28), int(big * 0.7)), (int(big * 0.43), int(big * 0.5)),
        (int(big * 0.54), int(big * 0.63)), (int(big * 0.62), int(big * 0.55)),
        (int(big * 0.72), int(big * 0.7)),
    ], fill=white)
    return img.resize((size, size), Image.LANCZOS)


def with_check(thumb):
    from PIL import Image, ImageDraw
    t = thumb.convert("RGBA")
    w, h = t.size
    s = 4
    r = int(min(w, h) * 0.3)
    layer = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy, R = w * s // 2, h * s // 2, r * s
    d.ellipse((cx - R - 6 * s, cy - R - 6 * s, cx + R + 6 * s, cy + R + 6 * s), fill=(10, 18, 36, 190))
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(34, 197, 94, 255), width=3 * s)
    d.line([(cx - R * 0.45, cy), (cx - R * 0.1, cy + R * 0.38), (cx + R * 0.5, cy - R * 0.35)], fill=(34, 197, 94, 255), width=3 * s, joint="curve")
    layer = layer.resize((w, h), Image.LANCZOS)
    return Image.alpha_composite(t, layer)


def launch_command():
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.exists() else Path(sys.executable)
    return '"%s" "%s"' % (exe, Path(__file__).resolve())


def set_autostart(enable):
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, APP)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def clipboard_seq():
    import ctypes
    return ctypes.windll.user32.GetClipboardSequenceNumber()


def grab_image():
    from PIL import Image, ImageGrab
    for _ in range(5):
        try:
            data = ImageGrab.grabclipboard()
        except Exception:
            data = None
        if isinstance(data, Image.Image):
            return data
        if data is not None:
            return None
        time.sleep(0.1)
    return None


_mutex = None


def already_running():
    global _mutex
    import ctypes
    _mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ShotFileSingleInstance")
    return ctypes.windll.kernel32.GetLastError() == 183


def appwindow(win, show=True):
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = (style & ~0x80) | 0x40000
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        win.withdraw()
        if show:
            win.after(20, win.deiconify)
    except Exception:
        pass


import tkinter as tk
from tkinter import ttk, filedialog, messagebox

pystray = ImageTk = None


def load_gui():
    global pystray, ImageTk
    from PIL import ImageTk as _it
    import pystray as _ps
    pystray, ImageTk = _ps, _it


MODE_TITLES = {"auto": "Автоматически", "ask": "Спрашивать"}
MODE_HINTS = {
    "auto": "Скриншоты будут сохраняться сразу, без подтверждения.",
    "ask": "Перед сохранением появится окно с вопросом.",
}


def bind_tree(widget, seq, fn):
    widget.bind(seq, fn, add="+")
    for ch in widget.winfo_children():
        bind_tree(ch, seq, fn)


def set_bg_tree(widget, color):
    try:
        widget.configure(bg=color)
    except Exception:
        pass
    for ch in widget.winfo_children():
        if not isinstance(ch, (tk.Canvas, ttk.Combobox)):
            set_bg_tree(ch, color)


def icon_label(parent, glyph, bg, fg=MUTED, size=14):
    return tk.Label(parent, text=glyph, bg=bg, fg=fg, font=(ICONS, size))


def rounded_rect(canvas, x1, y1, x2, y2, radius, fill, outline=None, width=1):
    radius = max(2, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
              x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
              x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
    return canvas.create_polygon(points, smooth=True, splinesteps=16, fill=fill,
                                 outline=outline or fill, width=width)


def button(parent, text, command, primary=False, padx=22, pady=8, bg_parent=BG):
    base = ACCENT if primary else BTN
    hover = "#3b78ff" if primary else BTN_HOVER
    try:
        bg_parent = parent.cget("bg")
    except Exception:
        pass
    font = tkfont.Font(family=FONT, size=10)
    width = max(76, font.measure(text) + padx * 2)
    height = font.metrics("linespace") + pady * 2 + 4
    b = tk.Canvas(parent, width=width, height=height, bg=bg_parent, highlightthickness=0, bd=0, cursor="hand2")
    b._base = base
    b._hover = hover
    b._text = text
    b._font = font
    b._fg = "#ffffff"
    b._radius = min(12, height // 2)
    def draw(color):
        b.delete("all")
        rounded_rect(b, 1, 1, width - 1, height - 1, b._radius, color)
        b.create_text(width // 2, height // 2, text=b._text, fill=b._fg, font=b._font)
    b._draw = draw
    draw(base)
    b.bind("<Enter>", lambda e: draw(hover))
    b.bind("<Leave>", lambda e: draw(base))
    b.bind("<Button-1>", lambda e: command())
    return b


class RoundedCard(tk.Canvas):
    def __init__(self, parent, bg=PANEL, outline=LINE, radius=16, **kwargs):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, bd=0, **kwargs)
        self.card_bg = bg
        self.card_outline = outline
        self.radius = radius
        self.content = tk.Frame(self, bg=bg, bd=0, highlightthickness=0)
        self.window_id = self.create_window(radius, radius, anchor="nw", window=self.content)
        self.bind("<Configure>", self._resize)
        self.content.bind("<Configure>", self._content_resize)
        self.after_idle(self._sync_size)

    def _resize(self, event=None):
        w = max(1, self.winfo_width() - self.radius * 2)
        h = max(1, self.content.winfo_reqheight())
        self.coords(self.window_id, self.radius, self.radius)
        self.itemconfigure(self.window_id, width=w, height=h)
        self.delete("rounded-background")
        rounded_rect(self, 1, 1, max(2, self.winfo_width() - 1), max(2, self.winfo_height() - 1),
                     self.radius, self.card_bg, self.card_outline, 1)
        self.tag_lower("all")
        self.tag_raise(self.window_id)

    def _content_resize(self, event=None):
        self.after_idle(self._sync_size)

    def _sync_size(self):
        try:
            h = self.content.winfo_reqheight() + self.radius * 2
            w = max(self.winfo_width(), self.winfo_reqwidth() + self.radius * 2)
            self.configure(height=h)
            self.itemconfigure(self.window_id, width=max(1, w - self.radius * 2), height=self.content.winfo_reqheight())
            self._resize()
        except tk.TclError:
            pass


class RoundedEntry(tk.Frame):
    def __init__(self, parent, textvariable, **kwargs):
        super().__init__(parent, bg=FIELD, highlightthickness=1, highlightbackground=LINE,
                         highlightcolor=ACCENT, bd=0)
        self.entry = tk.Entry(self, textvariable=textvariable, bg=FIELD, fg=FG,
                              insertbackground=FG, relief="flat", bd=0, font=(FONT, 10),
                              highlightthickness=0, **kwargs)
        self.entry.pack(fill="both", expand=True, padx=10, pady=5)
    def pack(self, *args, **kwargs):
        return super().pack(*args, **kwargs)


class Toggle(tk.Canvas):
    W, H = 44, 24

    def __init__(self, parent, var, bg):
        super().__init__(parent, width=self.W, height=self.H, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.var = var
        self.bind("<Button-1>", lambda e: var.set(not var.get()))
        var.trace_add("write", lambda *a: self.draw())
        self.draw()

    def draw(self):
        self.delete("all")
        on = bool(self.var.get())
        col = ACCENT if on else "#33415f"
        r = self.H / 2
        self.create_oval(0, 0, self.H, self.H, fill=col, outline=col)
        self.create_oval(self.W - self.H, 0, self.W, self.H, fill=col, outline=col)
        self.create_rectangle(r, 0, self.W - r, self.H, fill=col, outline=col)
        kx = self.W - r if on else r
        self.create_oval(kx - 8, r - 8, kx + 8, r + 8, fill="#ffffff", outline="#ffffff")


class ShotFile:
    def __init__(self):
        self.cfg = load_config()
        self.q = queue.Queue()
        self.running = True
        self.armed_until = 0.0
        self.has_hotkey = False
        self.last_hash = None
        self.last_time = 0.0
        self.settings_win = None
        self.popup_win = None
        self.toast_win = None
        self.game_active = False
        self.game_shots = []
        self.game_last_check = 0.0
        self.online_update_prompt_open = False
        self.online_update_check_running = False
        self.online_update_checked_at = 0.0

        self.support_win = None
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.title(APP)
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.tray_img = make_icon(64)
        self.logo = ImageTk.PhotoImage(make_icon(88, dark=True))
        self.win_icon = ImageTk.PhotoImage(make_icon(48))
        self.small_icon = ImageTk.PhotoImage(make_icon(22))
        self.root.iconphoto(True, self.win_icon)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_main)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=FIELD, background=FIELD, foreground=FG, arrowcolor=FG,
                        bordercolor=LINE, lightcolor=FIELD, darkcolor=FIELD, padding=6, selectbackground=FIELD, selectforeground=FG)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", FG)], selectbackground=[("readonly", FIELD)])
        self.root.option_add("*TCombobox*Listbox.background", FIELD)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)

        self.build_main(self.chrome(self.root, APP, self.hide_main, self.hide_main))
        # The main screen contains four settings rows plus the bottom action bar.
        # Do not size the window from a clipped/early requested height: that hid
        # the lower half of the main menu on Windows.
        self.root.update_idletasks()
        screen_h = self.root.winfo_screenheight()
        wanted_h = max(650, self.root.winfo_reqheight())
        window_h = min(wanted_h, max(500, screen_h - 80))
        self.place(self.root, 560, None)
        appwindow(self.root, show=not self.cfg["start_minimized"])
        self.start_hotkey()
        self.start_tray()
        threading.Thread(target=self.watch, daemon=True).start()
        self.root.after(100, self.pump)
        self.root.after(8000, self.check_github_update)

    def check_github_update(self):
        if not self.running:
            return
        now = time.time()
        if not self.online_update_check_running and now - self.online_update_checked_at >= UPDATE_CHECK_INTERVAL:
            self.online_update_check_running = True
            threading.Thread(target=self._github_update_worker, daemon=True).start()
        self.root.after(UPDATE_CHECK_INTERVAL * 1000, self.check_github_update)

    def _github_update_worker(self):
        candidate = None
        release_version = None
        try:
            request = urllib.request.Request(
                GITHUB_RELEASE_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "ShotFile-Updater/1.0",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                release = json.loads(response.read().decode("utf-8"))
            if release.get("draft") or release.get("prerelease"):
                return
            assets = release.get("assets", [])
            asset = next((a for a in assets if a.get("name", "").lower() == "shotfile.py"), None)
            if asset is None:
                self.root.after(0, self._github_update_result, None, None, "В релизе latest не найден ShotFile.py. Добавь новый ShotFile.py в Assets релиза.")
                return
            download_url = asset.get("browser_download_url")
            if not download_url:
                return
            download_request = urllib.request.Request(download_url, headers={"User-Agent": "ShotFile-Updater/1.0"})
            with urllib.request.urlopen(download_request, timeout=25) as response:
                content = response.read(8 * 1024 * 1024 + 1)
            if len(content) > 8 * 1024 * 1024:
                raise ValueError("Файл обновления больше 8 МБ.")
            source = content.decode("utf-8-sig")
            compile(source, asset.get("name", "ShotFile.py"), "exec")
            match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', source, re.MULTILINE)
            build_match = re.search(r'^BUILD\s*=\s*["\']([^"\']+)["\']', source, re.MULTILINE)
            release_version = match.group(1) if match else release.get("tag_name", "unknown")
            remote_build = build_match.group(1) if build_match else ""
            if self._version_key(release_version) <= self._version_key(VERSION) and (not remote_build or remote_build <= BUILD):
                self.online_update_checked_at = time.time()
                return
            current = Path(__file__).resolve()
            if current.suffix.lower() != ".py":
                self.root.after(0, self._github_update_result, None, release_version, "Автообновление из GitHub сейчас поддерживается при запуске ShotFile.py. Для EXE понадобится отдельный установщик обновлений.")
                return
            update_path = current.parent / (".ShotFile_download_%s.py" % os.getpid())
            update_path.write_text(source, encoding="utf-8")
            candidate = str(update_path)
            self.root.after(0, self._github_update_result, candidate, release_version, None)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                self.root.after(0, self._github_update_result, None, None, "Не удалось прочитать релиз latest на GitHub. Проверь, что релиз опубликован и доступен публично.")
        except Exception:
            pass
        finally:
            self.online_update_checked_at = time.time()
            self.online_update_check_running = False

    @staticmethod
    def _version_key(value):
        parts = re.findall(r"\d+", str(value))
        return tuple(int(part) for part in parts) if parts else (0,)

    def _github_update_result(self, candidate, version, error):
        if not self.running:
            return
        if error:
            return
        if candidate and Path(candidate).is_file() and not self.online_update_prompt_open:
            self.online_update_prompt_open = True
            try:
                accepted = messagebox.askyesno(
                    "Доступно обновление ShotFile",
                    "На GitHub в релизе latest найдена версия %s.\n\nСкачать ShotFile.py, заменить текущий файл и перезапустить программу?\nРезервная копия будет сохранена рядом." % version,
                    parent=self.root,
                )
                if accepted:
                    self._install_update_file(Path(candidate))
                else:
                    try:
                        Path(candidate).unlink(missing_ok=True)
                    except Exception:
                        pass
            finally:
                self.online_update_prompt_open = False

    def _install_update_file(self, candidate):
        current = Path(__file__).resolve()
        if current.suffix.lower() != ".py":
            messagebox.showerror("Обновление ShotFile", "Автообновление поддерживается при запуске из .py файла.", parent=self.root)
            return
        helper = current.parent / "_shotfile_update_helper.py"
        helper.write_text(
            "import ctypes, os, shutil, subprocess, sys, time\n"
            "pid, source, target, backup = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]\n"
            "if os.name == 'nt':\n"
            "    handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)\n"
            "    if handle:\n"
            "        ctypes.windll.kernel32.WaitForSingleObject(handle, 0xFFFFFFFF)\n"
            "        ctypes.windll.kernel32.CloseHandle(handle)\n"
            "else:\n"
            "    while True:\n"
            "        try: os.kill(pid, 0); time.sleep(0.3)\n"
            "        except OSError: break\n"
            "try:\n"
            "    shutil.copy2(target, backup)\n"
            "    shutil.copy2(source, target)\n"
            "    os.remove(source)\n"
            "    subprocess.Popen([sys.executable, target], cwd=os.path.dirname(target))\n"
            "except Exception as exc:\n"
            "    try:\n"
            "        if os.path.exists(backup): shutil.copy2(backup, target)\n"
            "    except Exception: pass\n"
            "    raise exc\n"
            "finally:\n"
            "    try: os.remove(__file__)\n"
            "    except OSError: pass\n",
            encoding="utf-8",
        )
        backup = str(current.with_name(current.stem + "_backup" + current.suffix))
        subprocess.Popen([sys.executable, str(helper), str(os.getpid()), str(candidate), str(current), backup], cwd=str(current.parent), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.quit()

    def place(self, win, w, h):
        win.update_idletasks()
        h = h or win.winfo_reqheight()
        x = (win.winfo_screenwidth() - w) // 2
        y = max(20, (win.winfo_screenheight() - h) // 2 - 20)
        win.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def chrome(self, win, title, close, minimize=None):
        win.configure(bg=BG)
        card = tk.Frame(win, bg=BG)
        card.pack(fill="both", expand=True)
        head = tk.Frame(card, bg=BG)
        head.pack(fill="x")
        ic = tk.Label(head, image=self.small_icon, bg=BG)
        ic.pack(side="left", padx=(16, 10), pady=10)
        tt = tk.Label(head, text=title, bg=BG, fg=FG, font=(FONT, 11))
        tt.pack(side="left")

        def cbtn(glyph, cmd, hover):
            b = tk.Label(head, text=glyph, bg=BG, fg=FG, font=(ICONS, 10), width=5, pady=11, cursor="hand2")
            b.pack(side="right")
            b.bind("<Enter>", lambda e: b.config(bg=hover))
            b.bind("<Leave>", lambda e: b.config(bg=BG))
            b.bind("<Button-1>", lambda e: cmd())

        cbtn(G_WCLOSE, close, "#c42b1c")
        if minimize:
            cbtn(G_MIN, minimize, BTN_HOVER)
        drag = {}

        def start(e):
            drag["x"] = e.x_root - win.winfo_x()
            drag["y"] = e.y_root - win.winfo_y()

        def move(e):
            win.geometry("+%d+%d" % (e.x_root - drag["x"], e.y_root - drag["y"]))

        for wd in (head, ic, tt):
            wd.bind("<Button-1>", start)
            wd.bind("<B1-Motion>", move)
        body = tk.Frame(card, bg=BG)
        body.pack(fill="both", expand=True)
        return body

    def build_main(self, parent):
        pad = tk.Frame(parent, bg=BG)
        pad.pack(fill="both", expand=True, padx=34, pady=(34, 20))
        tk.Label(pad, image=self.logo, bg=BG).pack()
        tk.Label(pad, text=APP, bg=BG, fg=FG, font=(FONT, 28, "bold")).pack(pady=(10, 0))
        tk.Label(pad, text="Скриншотнул — сохранил.", bg=BG, fg=ACCENT_SOFT, font=(FONT, 13)).pack(pady=(2, 22))

        st = RoundedCard(pad)
        st.pack(fill="x")
        st_body = st.content
        st_body.pack_propagate(True)
        dot = tk.Canvas(st_body, width=14, height=14, bg=PANEL, highlightthickness=0)
        dot.create_oval(2, 2, 12, 12, fill=GOOD, outline=GOOD)
        dot.grid(row=0, column=0, rowspan=2, padx=(18, 12), pady=16)
        tk.Label(st_body, text="Работает в фоне", fg=FG, bg=PANEL, font=(FONT, 11), anchor="w").grid(row=0, column=1, sticky="w", pady=(14, 0))
        self.status_sub = tk.Label(st_body, fg=MUTED, bg=PANEL, font=(FONT, 10), anchor="w")
        self.status_sub.grid(row=1, column=1, sticky="w", pady=(0, 14))

        rows = RoundedCard(pad)
        rows.pack(fill="x", pady=16)
        rows_body = rows.content
        self.vals = {}
        items = [("mode", G_PASTE, "Режим сохранения", "save"), ("folder", G_FOLDER, "Папка сохранения", "save"),
                 ("format", G_PHOTO, "Формат файлов", "save"), ("template", G_PAGE, "Имя файла", "save")]
        for i, (key, glyph, label, page) in enumerate(items):
            row = tk.Frame(rows_body, bg=PANEL, cursor="hand2")
            row.pack(fill="x")
            inner = tk.Frame(row, bg=PANEL)
            inner.pack(fill="x", padx=16, pady=13)
            icon_label(inner, glyph, PANEL, FG, 14).pack(side="left", padx=(0, 14))
            tk.Label(inner, text=label, fg=FG, bg=PANEL, font=(FONT, 10)).pack(side="left")
            icon_label(inner, G_CHEV, PANEL, MUTED, 9).pack(side="right")
            v = tk.Label(inner, fg=MUTED, bg=PANEL, font=(FONT, 10))
            v.pack(side="right", padx=(0, 10))
            self.vals[key] = v
            target = "mode" if key == "mode" else "save"
            bind_tree(row, "<Button-1>", lambda e, t=target: self.open_settings(t))
            bind_tree(row, "<Enter>", lambda e, r=row: set_bg_tree(r, FIELD))
            bind_tree(row, "<Leave>", lambda e, r=row: set_bg_tree(r, PANEL))
            if i < len(items) - 1:
                tk.Frame(rows_body, bg=LINE, height=1).pack(fill="x", padx=16)

        tk.Frame(pad, bg=LINE, height=1).pack(fill="x", pady=(8, 0))
        bar = tk.Frame(pad, bg=BG)
        bar.pack(fill="x", pady=(14, 0))
        left = tk.Frame(bar, bg=BG, cursor="hand2")
        left.pack(side="left")
        icon_label(left, G_SETTINGS, BG, FG, 13).pack(side="left", padx=(0, 8))
        tk.Label(left, text="Настройки", bg=BG, fg=FG, font=(FONT, 10)).pack(side="left")
        bind_tree(left, "<Button-1>", lambda e: self.open_settings("general"))
        right = tk.Frame(bar, bg=BG, cursor="hand2")
        right.pack(side="right")
        icon_label(right, G_HEART, BG, ACCENT_SOFT, 13).pack(side="left", padx=(0, 8))
        tk.Label(right, text="Поддержать автора", bg=BG, fg=ACCENT_SOFT, font=(FONT, 10)).pack(side="left")
        bind_tree(right, "<Button-1>", lambda e: self.support())
        self.refresh_main()

    def refresh_main(self):
        c = self.cfg
        self.vals["mode"].config(text=MODE_TITLES.get(c["mode"], "Автоматически"))
        folder = str(c["folder"])
        parts = Path(folder).parts
        short = "/".join(parts[-2:]) if len(parts) > 2 else folder
        self.vals["folder"].config(text=short)
        self.vals["format"].config(text=str(c["format"]).upper())
        self.vals["template"].config(text=c["template"])
        if self.game_active:
            self.status_sub.config(text="Игровой режим активен · уведомления скрыты")
        elif c["watch_hotkey"] and self.has_hotkey:
            self.status_sub.config(text="Ожидает сочетание клавиш Win + Shift + S")
        else:
            self.status_sub.config(text="Следит за буфером обмена")

    def support(self):
        if self.support_win is not None and self.support_win.winfo_exists():
            self.support_win.lift()
            return
        d = tk.Toplevel(self.root)
        self.support_win = d
        d.overrideredirect(True)
        d.attributes("-topmost", True)
        body = self.chrome(d, "Поддержать автора", d.destroy)
        wrap = tk.Frame(body, bg=BG)
        wrap.pack(fill="both", expand=True, padx=28, pady=(10, 26))
        top = tk.Frame(wrap, bg=BG)
        top.pack(fill="x")
        icon_label(top, G_HEART, BG, ACCENT_SOFT, 20).pack(side="left", padx=(0, 12))
        tk.Label(top, text="Поддержать автора", bg=BG, fg=FG, font=(FONT, 16, "bold")).pack(side="left")
        tk.Label(wrap, text="Если ShotFile вам пригодился, можно отправить любую сумму в TON. Это добровольно: программа работает полностью и без этого.",
                 bg=BG, fg="#c5cde0", font=(FONT, 10), justify="left", anchor="w", wraplength=460).pack(fill="x", pady=(14, 18))
        tk.Label(wrap, text="Адрес кошелька TON", bg=BG, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x", pady=(0, 6))
        var = tk.StringVar(master=d, value=TON_ADDRESS)
        address = RoundedEntry(wrap, var, state="readonly", readonlybackground=FIELD, font=("Consolas", 10))
        address.pack(fill="x", ipady=3)
        btns = tk.Frame(wrap, bg=BG)
        btns.pack(fill="x", pady=(16, 0))

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(TON_ADDRESS)
            self.root.update()
            cp.config(text="Скопировано")
            d.after(2000, lambda: d.winfo_exists() and cp.config(text="Скопировать адрес"))

        def open_wallet():
            try:
                os.startfile("ton://transfer/" + TON_ADDRESS)
            except Exception:
                import webbrowser
                webbrowser.open("https://app.tonkeeper.com/transfer/" + TON_ADDRESS)

        cp = button(btns, "Скопировать адрес", copy, primary=True, padx=20)
        cp.pack(side="left")
        button(btns, "Открыть в кошельке", open_wallet, padx=20).pack(side="left", padx=(10, 0))
        tk.Label(wrap, text="Отправляйте только в сети TON (The Open Network).", bg=BG, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x", pady=(14, 0))
        d.update_idletasks()
        width = max(540, d.winfo_reqwidth())
        height = d.winfo_reqheight()
        x = max(0, (d.winfo_screenwidth() - width) // 2)
        y = max(0, (d.winfo_screenheight() - height) // 2)
        d.geometry(f"{width}x{height}+{x}+{y}")
        d.deiconify()
        d.lift()
        d.focus_force()

    def show_main(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_main(self):
        self.root.withdraw()

    def open_folder(self):
        try:
            Path(self.cfg["folder"]).mkdir(parents=True, exist_ok=True)
            os.startfile(self.cfg["folder"])
        except Exception as e:
            self.toast("Не удалось открыть папку", [str(e)])

    NAV = [("general", G_SETTINGS, "Основные"), ("save", G_FOLDER, "Сохранение"), ("mode", G_BOLT, "Режим работы"),
           ("notify", G_BELL, "Уведомления"), ("keys", G_KEYS, "Горячие клавиши"), ("about", G_INFO, "О программе")]
    PAGES = {"general": ["general", "mode", "save"], "save": ["save"], "mode": ["mode"],
             "notify": ["save"], "keys": ["general"], "about": ["about"]}

    def open_settings(self, page="general"):
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.lift()
            self.settings_win.focus_force()
            self.settings_show(page)
            return
        c = self.cfg
        w = tk.Toplevel(self.root)
        self.settings_win = w
        w.overrideredirect(True)
        body = self.chrome(w, APP + " — Настройки", w.destroy)
        self.v = {
            "autostart": tk.BooleanVar(master=w, value=c["autostart"]),
            "start_minimized": tk.BooleanVar(master=w, value=c["start_minimized"]),
            "watch_hotkey": tk.BooleanVar(master=w, value=c["watch_hotkey"]),
            "mode": tk.StringVar(master=w, value=MODE_TITLES.get(c["mode"], "Автоматически")),
            "folder": tk.StringVar(master=w, value=c["folder"]),
            "format": tk.StringVar(master=w, value=str(c["format"]).upper()),
            "template": tk.StringVar(master=w, value=c["template"]),
            "notify": tk.BooleanVar(master=w, value=c["notify"]),
            "gaming_mode": tk.BooleanVar(master=w, value=c.get("gaming_mode", True)),
        }

        side = tk.Frame(body, bg=BG_SIDE, width=210)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(body, bg=LINE, width=1).pack(side="left", fill="y")
        self.nav_items = {}
        tk.Frame(side, bg=BG_SIDE, height=12).pack()
        for key, glyph, label in self.NAV:
            it = tk.Frame(side, bg=BG_SIDE, cursor="hand2")
            it.pack(fill="x", padx=10, pady=2)
            inner = tk.Frame(it, bg=BG_SIDE)
            inner.pack(fill="x", padx=12, pady=10)
            icon_label(inner, glyph, BG_SIDE, FG, 13).pack(side="left", padx=(0, 12))
            tk.Label(inner, text=label, bg=BG_SIDE, fg=FG, font=(FONT, 10)).pack(side="left")
            bind_tree(it, "<Button-1>", lambda e, k=key: self.settings_show(k))
            self.nav_items[key] = it

        main = tk.Frame(body, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.s_content = tk.Frame(main, bg=BG)
        self.s_content.pack(fill="both", expand=True, padx=20, pady=(16, 0))
        self.s_err = tk.Label(main, text="", bg=BG, fg="#f87171", font=(FONT, 9), anchor="w")
        self.s_err.pack(fill="x", padx=22)
        bar = tk.Frame(main, bg=BG)
        bar.pack(fill="x", padx=20, pady=(6, 18))
        button(bar, "Сохранить", self.apply_settings, primary=True, padx=34).pack(side="right")
        button(bar, "Отмена", w.destroy, padx=34).pack(side="right", padx=(0, 12))

        self.secs = {}
        self.build_sections(self.s_content)
        self.settings_show("general")
        w.update_idletasks()
        self.place(w, 840, max(w.winfo_reqheight(), 600))
        self.settings_show(page)
        appwindow(w)

    def section(self, parent, key, title):
        outer = tk.Frame(parent, bg=BG)
        tk.Label(outer, text=title, bg=BG, fg=FG, font=(FONT, 12), anchor="w").pack(fill="x", pady=(0, 8))
        card = RoundedCard(outer)
        card.pack(fill="x")
        inner = card.content
        inner.pack(fill="x", padx=16, pady=12)
        self.secs[key] = outer
        return inner

    def toggle_row(self, parent, glyph, text, var):
        r = tk.Frame(parent, bg=PANEL)
        r.pack(fill="x", pady=7)
        icon_label(r, glyph, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r, text=text, bg=PANEL, fg=FG, font=(FONT, 10)).pack(side="left")
        Toggle(r, var, PANEL).pack(side="right")

    def entry(self, parent, var):
        return RoundedEntry(parent, var)

    def build_sections(self, parent):
        v = self.v
        g = self.section(parent, "general", "Основные")
        self.toggle_row(g, G_AUTO, "Запускать вместе с Windows", v["autostart"])
        self.toggle_row(g, G_TRAY, "Запускать свёрнутым в трей", v["start_minimized"])
        self.toggle_row(g, G_KEYS, "Отслеживать сочетание клавиш Win + Shift + S", v["watch_hotkey"])
        self.toggle_row(g, G_BOLT, "Игровой режим: скрывать уведомления во время игры", v["gaming_mode"])
        info = tk.Frame(g, bg=PANEL)
        info.pack(fill="x", pady=(6, 0))
        icon_label(info, G_INFO, PANEL, ACCENT_SOFT, 12).pack(side="left", anchor="n", padx=(0, 12))
        tk.Label(info, text="Приложение будет ждать, пока вы сделаете скриншот\nи Windows поместит его в буфер обмена.", bg=PANEL, fg=MUTED,
                 font=(FONT, 9), justify="left", anchor="w").pack(side="left")

        m = self.section(parent, "mode", "Режим работы")
        row = tk.Frame(m, bg=PANEL)
        row.pack(fill="x")
        icon_label(row, G_BOLT, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        cb = ttk.Combobox(row, textvariable=v["mode"], values=list(MODE_TITLES.values()), state="readonly", font=(FONT, 10))
        cb.pack(side="left", fill="x", expand=True)
        self.mode_hint = tk.Label(m, bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w")
        self.mode_hint.pack(fill="x", pady=(8, 0))

        def upd(*a):
            key = "ask" if v["mode"].get() == MODE_TITLES["ask"] else "auto"
            self.mode_hint.config(text=MODE_HINTS[key])
        cb.bind("<<ComboboxSelected>>", upd)
        upd()

        s = self.section(parent, "save", "Сохранение")
        r1 = tk.Frame(s, bg=PANEL)
        r1.pack(fill="x", pady=6)
        icon_label(r1, G_FOLDER, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r1, text="Папка сохранения", bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")

        def choose():
            p = filedialog.askdirectory(parent=self.settings_win, initialdir=v["folder"].get() or str(Path.home()))
            if p:
                v["folder"].set(os.path.normpath(p))
        button(r1, "Выбрать", choose, padx=16, pady=6).pack(side="right")
        self.entry(r1, v["folder"]).pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=5)

        r2 = tk.Frame(s, bg=PANEL)
        r2.pack(fill="x", pady=6)
        icon_label(r2, G_PHOTO, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r2, text="Формат файлов", bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")
        ttk.Combobox(r2, textvariable=v["format"], values=["PNG", "JPG"], state="readonly", font=(FONT, 10)).pack(side="left", fill="x", expand=True)

        r3 = tk.Frame(s, bg=PANEL)
        r3.pack(fill="x", pady=6)
        icon_label(r3, G_PAGE, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r3, text="Шаблон имени файла", bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")
        self.entry(r3, v["template"]).pack(side="left", fill="x", expand=True, ipady=5)
        tk.Label(s, text="yyyy год, MM месяц, dd день, HH час, mm минуты, ss секунды", bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x", pady=(0, 4))
        self.toggle_row(s, G_BELL, "Уведомлять после сохранения", v["notify"])

        a = self.section(parent, "about", "О программе")
        tk.Label(a, text="%s · версия %s" % (APP, VERSION), bg=PANEL, fg=FG, font=(FONT, 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(a, text="Сборка: %s\nСкриншотнул — сохранил.\nНастройки хранятся в:\n%s" % (BUILD, CONFIG_PATH), bg=PANEL, fg=MUTED, font=(FONT, 9),
                 justify="left", anchor="w", wraplength=520).pack(fill="x", pady=(6, 0))

    def settings_show(self, page):
        for key, it in self.nav_items.items():
            set_bg_tree(it, NAV_ON if key == page else BG_SIDE)
        for sec in self.secs.values():
            sec.pack_forget()
        for key in self.PAGES.get(page, ["general"]):
            self.secs[key].pack(fill="x", pady=(0, 14))

    def apply_settings(self):
        c, v = self.cfg, self.v
        folder = v["folder"].get().strip()
        if not folder:
            self.s_err.config(text="Укажи папку для сохранения.")
            return
        if not v["template"].get().strip():
            self.s_err.config(text="Шаблон имени не может быть пустым.")
            return
        c["autostart"] = bool(v["autostart"].get())
        c["start_minimized"] = bool(v["start_minimized"].get())
        c["watch_hotkey"] = bool(v["watch_hotkey"].get())
        c["mode"] = "ask" if v["mode"].get() == MODE_TITLES["ask"] else "auto"
        c["folder"] = folder
        c["format"] = v["format"].get()
        c["template"] = v["template"].get().strip()
        c["notify"] = bool(v["notify"].get())
        c["gaming_mode"] = bool(v["gaming_mode"].get())
        save_config(c)
        set_autostart(c["autostart"])
        self.refresh_main()
        try:
            self.tray.update_menu()
        except Exception:
            pass
        self.settings_win.destroy()


    def shell(self, title="ShotFile"):
        d = tk.Toplevel(self.root)
        d.overrideredirect(True)
        d.attributes("-topmost", True)
        d.configure(bg=LINE)
        card = tk.Frame(d, bg=BG)
        card.pack(padx=1, pady=1)
        head = tk.Frame(card, bg=BG)
        head.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(head, image=self.small_icon, bg=BG).pack(side="left")
        tk.Label(head, text=title, bg=BG, fg=FG, font=(FONT, 11)).pack(side="left", padx=(10, 0))
        x = icon_label(head, G_CLOSE, BG, MUTED, 10)
        x.pack(side="right")
        x.config(cursor="hand2")
        body = tk.Frame(card, bg=BG)
        body.pack(fill="x", padx=16, pady=(14, 16))
        return d, card, body, x

    def dock(self, d):
        d.update_idletasks()
        x = d.winfo_screenwidth() - d.winfo_reqwidth() - 24
        y = d.winfo_screenheight() - d.winfo_reqheight() - 64
        d.geometry("+%d+%d" % (x, y))

    def toast(self, title, lines, thumb=None, seconds=6):
        if self.toast_win is not None and self.toast_win.winfo_exists():
            self.toast_win.destroy()
        d, card, body, x = self.shell()
        self.toast_win = d
        if thumb is not None:
            t = thumb.copy()
            t.thumbnail((84, 64))
            d.ph = ImageTk.PhotoImage(with_check(t))
            tk.Label(body, image=d.ph, bg=BG, highlightbackground=LINE, highlightthickness=1).pack(side="left", padx=(0, 16))
        txt = tk.Frame(body, bg=BG)
        txt.pack(side="left")
        tk.Label(txt, text=title, bg=BG, fg=FG, font=(FONT, 11, "bold"), anchor="w").pack(fill="x")
        for ln in lines:
            tk.Label(txt, text=ln, bg=BG, fg=FG if False else "#c5cde0", font=(FONT, 9), anchor="w", justify="left").pack(fill="x", pady=(3, 0))
        card.configure(width=340)
        x.bind("<Button-1>", lambda e: d.destroy())
        self.dock(d)
        d.after(int(seconds * 1000), lambda: d.winfo_exists() and d.destroy())

    def ask(self, img):
        if self.popup_win is not None and self.popup_win.winfo_exists():
            self.popup_win.destroy()
        d, card, body, x = self.shell()
        self.popup_win = d
        thumb = img.copy()
        thumb.thumbnail((170, 130))
        d.ph = ImageTk.PhotoImage(thumb.convert("RGB"))
        tk.Label(body, image=d.ph, bg=BG, highlightbackground=LINE, highlightthickness=1).pack(side="left", padx=(0, 18), anchor="n")
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", anchor="n")
        tk.Label(right, text="Обнаружен скриншот!", bg=BG, fg=FG, font=(FONT, 14), anchor="w").pack(fill="x")
        tk.Label(right, text="Сохранить изображение в папку\n%s?" % "/".join(Path(self.cfg["folder"]).parts[-2:]), bg=BG, fg="#c5cde0",
                 font=(FONT, 10), justify="left", anchor="w").pack(fill="x", pady=(8, 14))
        btns = tk.Frame(right, bg=BG)
        btns.pack(fill="x")
        state = {"left": 15, "done": False}
        foot = tk.Frame(card, bg=BG)
        foot.pack(fill="x", padx=16, pady=(0, 14))
        tk.Frame(foot, bg=LINE, height=1).pack(fill="x", pady=(0, 10))
        icon_label(foot, G_CLOCK, BG, MUTED, 11).pack(side="left", padx=(0, 10))
        timer = tk.Label(foot, bg=BG, fg=MUTED, font=(FONT, 9))
        timer.pack(side="left")

        def finish(save):
            if state["done"]:
                return
            state["done"] = True
            d.destroy()
            if save:
                self.save_and_notify(img)

        button(btns, "Сохранить", lambda: finish(True), primary=True, padx=20, pady=7).pack(side="left")
        button(btns, "Не сохранять", lambda: finish(False), padx=20, pady=7).pack(side="left", padx=(10, 0))
        x.bind("<Button-1>", lambda e: finish(False))

        def tick():
            if state["done"] or not d.winfo_exists():
                return
            if state["left"] <= 0:
                finish(False)
                return
            n = state["left"]
            timer.config(text="Автоматически закроется через %d %s" % (n, plural(n, "секунду", "секунды", "секунд")))
            state["left"] -= 1
            d.after(1000, tick)

        tick()
        self.dock(d)


    def save_and_notify(self, img):
        try:
            path = save_image(img, self.cfg)
        except Exception as e:
            self.toast("Не удалось сохранить", [str(e)])
            return
        if self.cfg["notify"]:
            self.toast("Скриншот сохранён", ["Файл: %s" % path.name, "Папка: %s" % "/".join(path.parent.parts[-2:])], thumb=img)

    def handle_image(self, img):
        if self.cfg.get("gaming_mode", True) and self.game_active:
            try:
                path = save_image(img, self.cfg)
                self.game_shots.append(path)
            except Exception as e:
                self.toast("Не удалось сохранить", [str(e)])
            return
        if self.cfg["mode"] == "ask":
            self.ask(img)
        else:
            self.save_and_notify(img)

    def detect_game(self):
        names = {
            "cs2.exe", "csgo.exe", "valorant-win64-shipping.exe", "valorant.exe", "league of legends.exe",
            "leagueclient.exe", "dota2.exe", "gta5.exe", "gta5_enhanced.exe", "rdr2.exe", "minecraft.exe",
            "javaw.exe", "java.exe", "robloxplayerbeta.exe", "fortniteclient-win64-shipping.exe",
            "eldenring.exe", "eldenring.exe", "overwatch.exe", "overwatch 2.exe", "rocketleague.exe",
            "apex_legends.exe", "r5apex.exe", "destiny2.exe", "warframe.x64.exe", "standoff2.exe",
            "osu!.exe", "fallguys_client_game.exe", "among us.exe", "terraria.exe", "left4dead2.exe",
            "rainbowsix.exe", "rainbowsix_vulkan.exe", "thefinals.exe", "helldivers2.exe", "palworld-win64-shipping.exe"
        }
        try:
            import psutil
            for proc in psutil.process_iter(["name"]):
                try:
                    if (proc.info.get("name") or "").lower() in names:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            try:
                import subprocess
                output = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True, errors="ignore", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                for line in output.splitlines():
                    exe = line.split(",", 1)[0].strip('"').lower()
                    if exe in names:
                        return True
            except Exception:
                pass
        return False

    def check_gaming(self):
        now = time.time()
        if now - self.game_last_check < 2:
            return
        self.game_last_check = now
        active = bool(self.cfg.get("gaming_mode", True) and self.detect_game())
        if active and not self.game_active:
            self.game_active = True
            self.game_shots = []
            self.q.put(self.refresh_main)
        elif not active and self.game_active:
            self.game_active = False
            shots = list(self.game_shots)
            self.game_shots = []
            self.q.put(self.refresh_main)
            if shots:
                self.q.put(lambda items=shots: self.game_summary(items))

    def game_summary(self, shots):
        if not self.cfg.get("notify", True):
            return
        d, card, body, x = self.shell("Игровой режим")
        self.toast_win = d
        tk.Label(body, text="Вы вышли из игры!", bg=BG, fg=FG, font=(FONT, 12, "bold"), anchor="w").pack(fill="x")
        tk.Label(body, text="Во время игры вы сделали %d %s." % (len(shots), plural(len(shots), "скриншот", "скриншота", "скриншотов")), bg=BG, fg="#c5cde0", font=(FONT, 10), anchor="w").pack(fill="x", pady=(6, 12))
        buttons = tk.Frame(body, bg=BG)
        buttons.pack(fill="x")
        def view():
            d.destroy()
            try:
                os.startfile(str(shots[0].parent))
            except Exception as e:
                self.toast("Не удалось открыть папку", [str(e)])
        button(buttons, "Посмотреть", view, primary=True, padx=18, pady=6).pack(side="left")
        button(buttons, "Пропустить", d.destroy, padx=18, pady=6).pack(side="left", padx=(8, 0))
        x.bind("<Button-1>", lambda e: d.destroy())
        self.dock(d)


    def start_hotkey(self):
        try:
            import keyboard
            keyboard.add_hotkey("windows+shift+s", self.arm)
            self.has_hotkey = True
        except Exception:
            self.has_hotkey = False
        self.refresh_main()

    def arm(self):
        self.armed_until = time.time() + 60

    def watch(self):
        try:
            last = clipboard_seq()
        except Exception:
            return
        while self.running:
            self.check_gaming()
            time.sleep(0.25)
            try:
                seq = clipboard_seq()
            except Exception:
                continue
            if seq == last:
                continue
            last = seq
            if self.cfg["watch_hotkey"] and self.has_hotkey and time.time() > self.armed_until:
                continue
            time.sleep(0.15)
            img = grab_image()
            if img is None:
                continue
            digest = hashlib.md5(img.tobytes()).hexdigest()
            if digest == self.last_hash and time.time() - self.last_time < 3:
                continue
            self.last_hash, self.last_time = digest, time.time()
            self.armed_until = 0.0
            self.q.put(lambda im=img: self.handle_image(im))


    def start_tray(self):
        M, I = pystray.Menu, pystray.MenuItem

        def ui(fn):
            return lambda icon, item: self.q.put(fn)

        def set_mode(mode):
            def action(icon, item):
                self.cfg["mode"] = mode
                save_config(self.cfg)
                self.q.put(self.refresh_main)
            return action

        def toggle_autostart(icon, item):
            self.cfg["autostart"] = not self.cfg["autostart"]
            save_config(self.cfg)
            set_autostart(self.cfg["autostart"])

        menu = M(
            I("Открыть окно", ui(self.show_main), default=True),
            I("Открыть папку", ui(self.open_folder)),
            I("Настройки", ui(self.open_settings)),
            M.SEPARATOR,
            I(lambda item: "Режим: " + MODE_TITLES.get(self.cfg["mode"], "Автоматически"), M(
                I("Автоматически", set_mode("auto"), checked=lambda item: self.cfg["mode"] == "auto", radio=True),
                I("Спрашивать", set_mode("ask"), checked=lambda item: self.cfg["mode"] == "ask", radio=True),
            )),
            I("Игровой режим", lambda icon, item: self.toggle_gaming(), checked=lambda item: self.cfg.get("gaming_mode", True)),
            I("Запускать с Windows", toggle_autostart, checked=lambda item: self.cfg["autostart"]),
            M.SEPARATOR,
            I("О программе", ui(lambda: self.open_settings("about"))),
            I("Выход", ui(self.quit)),
        )
        self.tray = pystray.Icon(APP, self.tray_img, APP, menu)
        self.tray.run_detached()

    def toggle_gaming(self):
        self.cfg["gaming_mode"] = not self.cfg.get("gaming_mode", True)
        save_config(self.cfg)
        self.refresh_main()
        try:
            self.tray.update_menu()
        except Exception:
            pass

    def pump(self):
        try:
            while True:
                self.q.get_nowait()()
        except queue.Empty:
            pass
        if self.running:
            self.root.after(100, self.pump)

    def quit(self):
        self.running = False
        try:
            self.tray.stop()
        except Exception:
            pass
        self.root.destroy()


def main():
    if "--make-icon" in sys.argv:
        make_icon(256).save("icon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return
    if os.name != "nt":
        print("ShotFile requires Windows.")
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    if already_running():
        return
    load_gui()
    ShotFile().root.mainloop()


if __name__ == "__main__":
    main()
