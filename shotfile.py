import ctypes
import hashlib
import json
import os
import queue
import re
import sys
import threading
import time
from datetime import datetime
from ctypes import wintypes
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter import font as tkfont

try:
    from build_info import BUILD
except ImportError:
    BUILD = "dev"

try:
    from build_info import REPO
except ImportError:
    REPO = ""

APP = "ShotFile"
VERSION = "1.2"
AUTHORS = ("dimzoffc", "yorvex")
GAME_KEYS = {"Print Screen": "print screen", "F8": "f8", "F9": "f9", "F10": "f10",
             "Ctrl + F12": "ctrl+f12", "Ctrl + Shift + S": "ctrl+shift+s"}
IGNORED_PROCS = ("explorer", "shotfile", "python", "pythonw", "applicationframehost", "searchhost", "shellexperiencehost")
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
    "game_mode": True,
    "toast_seconds": 6,
    "lang": "auto",
    "check_updates": True,
    "game_shot": True,
    "game_key": "print screen",
    "game_folders": True,
    "game_sound": True,
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
WARN = "#f59e0b"
FONT = "Segoe UI"
ICONS = "Segoe MDL2 Assets"

G_SETTINGS, G_FOLDER, G_PHOTO, G_PAGE = "", "", "", ""
G_PASTE, G_HEART, G_BELL, G_KEYS = "", "", "", ""
G_INFO, G_BOLT, G_CLOSE, G_CHEV = "", "", "", ""
G_CLOCK, G_AUTO, G_TRAY = "", "", ""
G_MIN, G_WCLOSE, G_GAME = "", "", ""
G_LANG, G_SYNC = "\uE774", "\uE72C"
G_SHOT, G_SOUND = "\uE722", "\uE767"


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


LANG = "ru"
LANG_LABELS = {"auto": "Авто / Auto", "ru": "Русский", "en": "English"}


def detect_lang():
    try:
        import ctypes
        return "ru" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF == 0x19 else "en"
    except Exception:
        return "ru"


def set_lang(cfg):
    global LANG
    v = cfg.get("lang", "auto")
    LANG = detect_lang() if v == "auto" else ("en" if v == "en" else "ru")


EN = {
    "Автоматически": "Automatic",
    "Спрашивать": "Ask",
    "Скриншоты будут сохраняться сразу, без подтверждения.": "Screenshots are saved right away, without asking.",
    "Перед сохранением появится окно с вопросом.": "A confirmation window appears before saving.",
    "3 секунды": "3 seconds",
    "6 секунд": "6 seconds",
    "10 секунд": "10 seconds",
    "Скриншотнул — сохранил.": "Snap it. Saved.",
    "Работает в фоне": "Running in the background",
    "Режим сохранения": "Save mode",
    "Папка сохранения": "Save folder",
    "Формат файлов": "File format",
    "Имя файла": "File name",
    "Настройки": "Settings",
    "Поддержать автора": "Support the author",
    "Приостановлено": "Paused",
    "Скриншоты не сохраняются, пока вы не включите": "Screenshots are not saved until you turn it back on",
    "Игровой режим: сохраняю без окон и уведомлений": "Game mode: saving without windows or notifications",
    "Ожидает сочетание клавиш Win + Shift + S": "Waiting for Win + Shift + S",
    "Следит за буфером обмена": "Watching the clipboard",
    "Доступна версия %s": "Version %s is available",
    "Если ShotFile вам пригодился, можно отправить любую сумму в TON. Это добровольно: программа работает полностью и без этого.": "If ShotFile was useful to you, you can send any amount in TON. It is voluntary: the program works fully without it.",
    "Адрес кошелька TON": "TON wallet address",
    "Скопировано": "Copied",
    "Скопировать адрес": "Copy address",
    "Открыть в кошельке": "Open in wallet",
    "Отправляйте только в сети TON (The Open Network).": "Send only on the TON network (The Open Network).",
    "Не удалось открыть папку": "Could not open the folder",
    "Основные": "General",
    "Сохранение": "Saving",
    "Режим работы": "Mode",
    "Уведомления": "Notifications",
    "Горячие клавиши": "Hotkeys",
    "О программе": "About",
    " — Настройки": " — Settings",
    "Версия %s\nСборка %s": "Version %s\nBuild %s",
    "Сохранить": "Save",
    "Отмена": "Cancel",
    "Запускать вместе с Windows": "Start with Windows",
    "Запускать свёрнутым в трей": "Start minimized to tray",
    "Язык": "Language",
    "Проверять обновления при запуске": "Check for updates on startup",
    "Игровой режим": "Game mode",
    "В полноэкранных играх скриншоты сохраняются молча, без окон и уведомлений. После игры покажется итог.": "In fullscreen games, screenshots are saved silently, without windows or notifications. A summary appears after the game.",
    "Выбрать": "Browse",
    "Шаблон имени файла": "File name template",
    "yyyy год, MM месяц, dd день, HH час, mm минуты, ss секунды": "yyyy year, MM month, dd day, HH hour, mm minutes, ss seconds",
    "Уведомлять после сохранения": "Notify after saving",
    "Сколько показывать": "Show for",
    "Окно «Скриншот сохранён» появляется в правом нижнем углу и закрывается само. В игровом режиме уведомления не показываются.": "The \"Screenshot saved\" window appears in the bottom right corner and closes itself. Notifications are not shown in game mode.",
    "Отслеживать сочетание клавиш Win + Shift + S": "Watch the Win + Shift + S shortcut",
    "Сделать скриншот области": "Capture an area",
    "Приложение ждёт, пока вы сделаете скриншот, и Windows поместит его в буфер обмена. Если выключить, сохраняется любая картинка из буфера.": "The app waits for you to take a screenshot and for Windows to put it on the clipboard. If turned off, any image that lands on the clipboard is saved.",
    "Сборка: %s": "Build: %s",
    "Проверить обновления": "Check for updates",
    "Авторы": "Authors",
    "Настройки хранятся в:\n%s": "Settings are stored in:\n%s",
    "Укажи папку для сохранения.": "Choose a save folder.",
    "Шаблон имени не может быть пустым.": "The name template cannot be empty.",
    "Настройки сохранены": "Settings saved",
    "Вышла новая версия": "A new version is out",
    "Версия %s уже на GitHub": "Version %s is on GitHub",
    "Нажмите, чтобы открыть страницу загрузки": "Click to open the download page",
    "Не удалось проверить обновления": "Could not check for updates",
    "Доступна версия %s. Открыть страницу загрузки": "Version %s is available. Open the download page",
    "У вас последняя версия": "You have the latest version",
    "Проверяю…": "Checking…",
    "Обнаружен скриншот!": "Screenshot detected!",
    "Сохранить изображение в папку\n%s?": "Save the image to the folder\n%s?",
    "Не сохранять": "Don't save",
    "Автоматически закроется через %d %s": "Closes automatically in %d %s",
    "секунду": "second",
    "секунды": "seconds",
    "секунд": "seconds",
    "Не удалось сохранить": "Could not save",
    "Скриншот сохранён": "Screenshot saved",
    "Файл: %s": "File: %s",
    "Папка: %s": "Folder: %s",
    "Сохранено %d %s": "Saved %d %s",
    "скриншот": "screenshot",
    "скриншота": "screenshots",
    "скриншотов": "screenshots",
    "Открыть окно": "Open window",
    "Открыть папку": "Open folder",
    "Режим: ": "Mode: ",
    "Включить сохранение": "Resume saving",
    "Приостановить сохранение": "Pause saving",
    "Запускать с Windows": "Start with Windows",
    "Выход": "Exit",
    "Для игр": "Games",
    "Скриншот для игр": "Game screenshot",
    "Делать скриншот по клавише": "Capture on hotkey",
    "Клавиша": "Hotkey",
    "Отдельная папка для каждой игры": "Separate folder for each game",
    "Звук при сохранении": "Sound when saved",
    "Нажмите клавишу в игре, и экран сохранится сразу, без окон. Если вместо игры получается чёрный кадр, переведите игру в режим «Без рамки» или «В окне».": "Press the key in a game and the screen is saved at once, with no windows. If you get a black frame instead of the game, switch the game to borderless or windowed mode.",
    "Скриншот игры сохранён": "Game screenshot saved",
}


def tr(s):
    return EN.get(s, s) if LANG == "en" else s


def parse_version(text):
    return tuple(int(x) for x in re.findall(r"\d+", text)) or (0,)


def fetch_latest(repo):
    import urllib.request
    req = urllib.request.Request("https://api.github.com/repos/%s/releases/latest" % repo,
                                 headers={"User-Agent": APP, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=8) as r:
        data = json.loads(r.read().decode("utf-8"))
    return str(data.get("tag_name", "")), str(data.get("html_url", ""))


def plural(n, a, b, c):
    if LANG == "en":
        return a if abs(n) == 1 else c
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


def round_image(img, radius):
    from PIL import Image, ImageDraw
    img = img.convert("RGBA")
    s = 4
    mask = Image.new("L", (img.width * s, img.height * s), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width * s - 1, img.height * s - 1), radius=radius * s, fill=255)
    img.putalpha(mask.resize(img.size, Image.LANCZOS))
    return img


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


class MonitorInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


SHELL_CLASSES = ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd", "ScreenClippingHost")
SHELL_TITLES = ("Snipping Tool Overlay", "Program Manager")


def fullscreen_active():
    import ctypes
    from ctypes import wintypes
    user = ctypes.windll.user32
    hwnd = user.GetForegroundWindow()
    if not hwnd:
        return False
    cls = ctypes.create_unicode_buffer(128)
    user.GetClassNameW(hwnd, cls, 128)
    if cls.value in SHELL_CLASSES:
        return False
    title = ctypes.create_unicode_buffer(256)
    user.GetWindowTextW(hwnd, title, 256)
    if title.value in SHELL_TITLES:
        return False

    rect = wintypes.RECT()
    user.GetWindowRect(hwnd, ctypes.byref(rect))
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    if not user.GetMonitorInfoW(user.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
        return False
    m = info.rcMonitor
    return rect.left <= m.left and rect.top <= m.top and rect.right >= m.right and rect.bottom >= m.bottom


def foreground_info():
    user = ctypes.windll.user32
    kernel = ctypes.windll.kernel32
    hwnd = user.GetForegroundWindow()
    rect, name = None, ""
    if not hwnd:
        return rect, name
    info = MonitorInfo()
    info.cbSize = ctypes.sizeof(MonitorInfo)
    if user.GetMonitorInfoW(user.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
        m = info.rcMonitor
        rect = (m.left, m.top, m.right, m.bottom)
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel.OpenProcess(0x1000, False, pid.value)
    if handle:
        buf = ctypes.create_unicode_buffer(520)
        size = wintypes.DWORD(520)
        if kernel.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            name = Path(buf.value).stem
        kernel.CloseHandle(handle)
    return rect, name


def game_folder(cfg, name):
    base = Path(cfg["folder"])
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    if cfg["game_folders"] and safe and safe.lower() not in IGNORED_PROCS:
        return base / "Games" / safe
    return base


def round_window(win, radius=16):
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        last = [None]

        def apply(e=None):
            size = (win.winfo_width(), win.winfo_height())
            if size == last[0] or size[0] < 20:
                return
            last[0] = size
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, size[0] + 1, size[1] + 1, radius * 2, radius * 2)
            ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)

        apply()
        win.bind("<Configure>", lambda e: e.widget is win and apply(), add="+")
    except Exception:
        pass


def appwindow(win, show=True, radius=16):
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id()) or win.winfo_id()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        style = (style & ~0x80) | 0x40000
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        round_window(win, radius)
    except Exception:
        pass
    if show:
        win.deiconify()


pystray = ImageTk = None


def load_gui():
    global pystray, ImageTk
    from PIL import ImageTk as _it
    import pystray as _ps
    pystray, ImageTk = _ps, _it


def mode_titles():
    return {"auto": tr("Автоматически"), "ask": tr("Спрашивать")}


def mode_hints():
    return {
        "auto": tr("Скриншоты будут сохраняться сразу, без подтверждения."),
        "ask": tr("Перед сохранением появится окно с вопросом."),
    }


def toast_choices():
    return {tr("3 секунды"): 3, tr("6 секунд"): 6, tr("10 секунд"): 10}


def rr_points(w, h, r):
    x1, y1, x2, y2 = 1, 1, w - 1, h - 1
    r = max(1, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    return [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2,
            x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]


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


class Round(tk.Frame):
    def __init__(self, parent, fill=PANEL, outline=LINE, radius=12, bg=None, padx=None, pady=None):
        bg = bg or parent.cget("bg")
        super().__init__(parent, bg=bg)
        self.fill = fill
        self.outline = outline
        self.radius = radius
        self.flat = fill == outline
        self.size = None
        self.shape = None
        self.cv = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.cv.place(x=0, y=0, relwidth=1, relheight=1)
        self.inner = tk.Frame(self, bg=fill)
        base = max(3, int(radius * 0.4))
        self.inner.pack(fill="both", expand=True, padx=base if padx is None else padx, pady=base if pady is None else pady)
        self.cv.bind("<Configure>", self.redraw)
        self.cv.bind("<Map>", lambda e: self.draw(self.cv.winfo_width(), self.cv.winfo_height()))

    def draw(self, w, h):
        if (w, h) == self.size or w < 4 or h < 4:
            return
        self.size = (w, h)
        self.cv.delete("all")
        self.shape = self.cv.create_polygon(rr_points(w, h, self.radius), smooth=True, fill=self.fill, outline=self.outline)

    def redraw(self, e):
        self.draw(e.width, e.height)

    def set_fill(self, color):
        self.fill = color
        if self.flat:
            self.outline = color
        if self.shape:
            self.cv.itemconfig(self.shape, fill=color, outline=self.outline)
        set_bg_tree(self.inner, color)


class RoundButton(tk.Canvas):
    def __init__(self, parent, text, command, primary=False, padx=22, pady=8):
        self.base = ACCENT if primary else BTN
        self.hover = "#3b78ff" if primary else BTN_HOVER
        f = tkfont.Font(family=FONT, size=10)
        w = f.measure(text) + 2 * padx
        h = f.metrics("linespace") + 2 * pady
        super().__init__(parent, width=w, height=h, bg=parent.cget("bg"), highlightthickness=0, bd=0, cursor="hand2")
        self.shape = self.create_polygon(rr_points(w, h, 11), smooth=True, fill=self.base, outline=self.base)
        self.label = self.create_text(w / 2, h / 2, text=text, fill="#ffffff", font=(FONT, 10))
        self.bind("<Enter>", lambda e: self.itemconfig(self.shape, fill=self.hover, outline=self.hover))
        self.bind("<Leave>", lambda e: self.itemconfig(self.shape, fill=self.base, outline=self.base))
        self.bind("<Button-1>", lambda e: command())

    def config(self, **kw):
        if "text" in kw:
            self.itemconfig(self.label, text=kw.pop("text"))
        if kw:
            super().config(**kw)

    configure = config


def button(parent, text, command, primary=False, padx=22, pady=8):
    return RoundButton(parent, text, command, primary, padx, pady)


class Toggle(tk.Canvas):
    W, H = 44, 24

    def __init__(self, parent, var, bg):
        super().__init__(parent, width=self.W, height=self.H, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.var = var
        self.bind("<Button-1>", lambda e: var.set(not var.get()))
        self.tid = var.trace_add("write", lambda *a: self.draw())
        self.bind("<Destroy>", lambda e: self.release())
        self.draw()

    def release(self):
        try:
            self.var.trace_remove("write", self.tid)
        except Exception:
            pass

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
        set_lang(self.cfg)
        self.q = queue.Queue()
        self.running = True
        self.armed_until = 0.0
        self.has_hotkey = False
        self.last_hash = None
        self.last_time = 0.0
        self.in_game = False
        self.paused = False
        self.update_info = None
        self.update_announced = False
        self.suppress_until = 0.0
        self.game_hook = None
        self.game_saved = 0
        self.settings_win = None
        self.popup_win = None
        self.toast_win = None
        self.support_win = None

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.title(APP)
        self.root.resizable(False, False)
        self.enabled_var = tk.BooleanVar(master=self.root, value=True)
        self.enabled_var.trace_add("write", lambda *a: self.on_enabled())
        self.tray_img = make_icon(64)
        self.logo = ImageTk.PhotoImage(make_icon(88, dark=True))
        self.win_icon = ImageTk.PhotoImage(make_icon(48))
        self.small_icon = ImageTk.PhotoImage(make_icon(22))
        self.root.iconphoto(True, self.win_icon)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_main)

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Flat.TCombobox", fieldbackground=FIELD, background=FIELD, foreground=FG, arrowcolor=FG,
                        bordercolor=FIELD, lightcolor=FIELD, darkcolor=FIELD, borderwidth=0, padding=6,
                        selectbackground=FIELD, selectforeground=FG)
        style.map("Flat.TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", FG)],
                  selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", FG)],
                  bordercolor=[("focus", FIELD)], lightcolor=[("focus", FIELD)])
        self.root.option_add("*TCombobox*Listbox.background", FIELD)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT)

        self.build_main(self.chrome(self.root, APP, self.hide_main, self.hide_main))
        self.place(self.root, 560, None)
        appwindow(self.root, show=not self.cfg["start_minimized"])
        self.start_hotkey()
        self.start_tray()
        threading.Thread(target=self.watch, daemon=True).start()
        self.root.after(100, self.pump)
        if REPO and self.cfg["check_updates"]:
            self.root.after(6000, self.check_updates)

    def place(self, win, w, h):
        win.update_idletasks()
        h = min(h or win.winfo_reqheight(), win.winfo_screenheight() - 80)
        x = (win.winfo_screenwidth() - w) // 2
        y = max(20, (win.winfo_screenheight() - h) // 2 - 20)
        win.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def chrome(self, win, title, close, minimize=None):
        win.configure(bg=LINE)
        card = tk.Frame(win, bg=BG)
        card.pack(fill="both", expand=True, padx=1, pady=1)
        head = tk.Frame(card, bg=BG)
        head.pack(fill="x", padx=(0, 6), pady=(6, 0))
        ic = tk.Label(head, image=self.small_icon, bg=BG)
        ic.pack(side="left", padx=(16, 10), pady=8)
        tt = tk.Label(head, text=title, bg=BG, fg=FG, font=(FONT, 11))
        tt.pack(side="left")

        def cbtn(glyph, cmd, hover):
            b = tk.Label(head, text=glyph, bg=BG, fg=FG, font=(ICONS, 10), width=5, pady=9, cursor="hand2")
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
        pad.pack(fill="both", expand=True, padx=34, pady=(22, 22))
        tk.Label(pad, image=self.logo, bg=BG).pack()
        tk.Label(pad, text=APP, bg=BG, fg=FG, font=(FONT, 28, "bold")).pack(pady=(10, 0))
        tk.Label(pad, text=tr("Скриншотнул — сохранил."), bg=BG, fg=ACCENT_SOFT, font=(FONT, 13)).pack(pady=(2, 22))

        st = Round(pad, radius=14, padx=10, pady=6)
        st.pack(fill="x")
        sc = st.inner
        self.dot = tk.Canvas(sc, width=14, height=14, bg=PANEL, highlightthickness=0)
        self.dot_item = self.dot.create_oval(2, 2, 12, 12, fill=GOOD, outline=GOOD)
        self.dot.grid(row=0, column=0, rowspan=2, padx=(10, 12), pady=12)
        self.status_title = tk.Label(sc, text=tr("Работает в фоне"), fg=FG, bg=PANEL, font=(FONT, 11), anchor="w")
        self.status_title.grid(row=0, column=1, sticky="w", pady=(10, 0))
        self.status_sub = tk.Label(sc, fg=MUTED, bg=PANEL, font=(FONT, 10), anchor="w")
        self.status_sub.grid(row=1, column=1, sticky="w", pady=(0, 10))
        sc.columnconfigure(1, weight=1)
        Toggle(sc, self.enabled_var, PANEL).grid(row=0, column=2, rowspan=2, padx=(10, 8))

        rows = Round(pad, radius=14, padx=8, pady=6)
        rows.pack(fill="x", pady=16)
        self.vals = {}
        items = [("mode", G_PASTE, tr("Режим сохранения")), ("folder", G_FOLDER, tr("Папка сохранения")),
                 ("format", G_PHOTO, tr("Формат файлов")), ("template", G_PAGE, tr("Имя файла"))]
        for i, (key, glyph, label) in enumerate(items):
            row = tk.Frame(rows.inner, bg=PANEL, cursor="hand2")
            row.pack(fill="x")
            inner = tk.Frame(row, bg=PANEL)
            inner.pack(fill="x", padx=10, pady=12)
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
                tk.Frame(rows.inner, bg=LINE, height=1).pack(fill="x", padx=12)

        tk.Frame(pad, bg=LINE, height=1).pack(fill="x", pady=(8, 0))
        bar = tk.Frame(pad, bg=BG)
        bar.pack(fill="x", pady=(14, 0))
        left = tk.Frame(bar, bg=BG, cursor="hand2")
        left.pack(side="left")
        icon_label(left, G_SETTINGS, BG, FG, 13).pack(side="left", padx=(0, 8))
        tk.Label(left, text=tr("Настройки"), bg=BG, fg=FG, font=(FONT, 10)).pack(side="left")
        bind_tree(left, "<Button-1>", lambda e: self.open_settings("general"))
        right = tk.Frame(bar, bg=BG, cursor="hand2")
        right.pack(side="right")
        icon_label(right, G_HEART, BG, ACCENT_SOFT, 13).pack(side="left", padx=(0, 8))
        tk.Label(right, text=tr("Поддержать автора"), bg=BG, fg=ACCENT_SOFT, font=(FONT, 10)).pack(side="left")
        bind_tree(right, "<Button-1>", lambda e: self.support())
        self.update_label = tk.Label(bar, bg=BG, fg=GOOD, font=(FONT, 10), cursor="hand2")
        self.update_label.bind("<Button-1>", lambda e: self.open_update())
        self.refresh_main()

    def rebuild_main(self):
        for ch in self.root.winfo_children():
            ch.destroy()
        self.build_main(self.chrome(self.root, APP, self.hide_main, self.hide_main))
        self.root.update_idletasks()
        self.root.geometry("560x%d" % self.root.winfo_reqheight())

    def refresh_main(self):
        c = self.cfg
        self.vals["mode"].config(text=mode_titles().get(c["mode"], tr("Автоматически")))
        folder = str(c["folder"])
        parts = Path(folder).parts
        short = "/".join(parts[-2:]) if len(parts) > 2 else folder
        self.vals["folder"].config(text=short)
        self.vals["format"].config(text=str(c["format"]).upper())
        self.vals["template"].config(text=c["template"])
        color = WARN if self.paused else GOOD
        self.dot.itemconfig(self.dot_item, fill=color, outline=color)
        self.status_title.config(text=tr("Приостановлено") if self.paused else tr("Работает в фоне"))
        if self.paused:
            self.status_sub.config(text=tr("Скриншоты не сохраняются, пока вы не включите"))
        elif self.in_game:
            self.status_sub.config(text=tr("Игровой режим: сохраняю без окон и уведомлений"))
        elif c["watch_hotkey"] and self.has_hotkey:
            self.status_sub.config(text=tr("Ожидает сочетание клавиш Win + Shift + S"))
        else:
            self.status_sub.config(text=tr("Следит за буфером обмена"))
        if self.update_info:
            self.update_label.config(text=tr("Доступна версия %s") % self.update_info[0])
            self.update_label.pack(side="left", padx=18)
        else:
            self.update_label.pack_forget()

    def field(self, parent, var, readonly=False, font=(FONT, 10)):
        box = Round(parent, fill=FIELD, outline=LINE, radius=10, padx=10, pady=7)
        e = tk.Entry(box.inner, textvariable=var, bg=FIELD, fg=FG, insertbackground=FG, relief="flat", font=font,
                     highlightthickness=0, bd=0, readonlybackground=FIELD, state="readonly" if readonly else "normal")
        e.pack(fill="x")
        return box

    def combo(self, parent, var, values):
        box = Round(parent, fill=FIELD, outline=LINE, radius=10, padx=6, pady=2)
        cb = ttk.Combobox(box.inner, textvariable=var, values=values, state="readonly", font=(FONT, 10), style="Flat.TCombobox", width=20)
        cb.pack(fill="x")
        return box, cb

    def support(self):
        if self.support_win is not None and self.support_win.winfo_exists():
            self.support_win.lift()
            return
        d = tk.Toplevel(self.root)
        self.support_win = d
        d.withdraw()
        d.overrideredirect(True)
        body = self.chrome(d, tr("Поддержать автора"), d.destroy)
        wrap = tk.Frame(body, bg=BG)
        wrap.pack(fill="both", expand=True, padx=28, pady=(10, 26))
        top = tk.Frame(wrap, bg=BG)
        top.pack(fill="x")
        icon_label(top, G_HEART, BG, ACCENT_SOFT, 20).pack(side="left", padx=(0, 12))
        tk.Label(top, text=tr("Поддержать автора"), bg=BG, fg=FG, font=(FONT, 16, "bold")).pack(side="left")
        tk.Label(wrap, text=tr("Если ShotFile вам пригодился, можно отправить любую сумму в TON. Это добровольно: программа работает полностью и без этого."),
                 bg=BG, fg="#c5cde0", font=(FONT, 10), justify="left", anchor="w", wraplength=460).pack(fill="x", pady=(14, 18))
        tk.Label(wrap, text=tr("Адрес кошелька TON"), bg=BG, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x", pady=(0, 6))
        var = tk.StringVar(master=d, value=TON_ADDRESS)
        self.field(wrap, var, readonly=True, font=("Consolas", 10)).pack(fill="x")
        btns = tk.Frame(wrap, bg=BG)
        btns.pack(fill="x", pady=(16, 0))

        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(TON_ADDRESS)
            self.root.update()
            cp.config(text=tr("Скопировано"))
            d.after(2000, lambda: d.winfo_exists() and cp.config(text=tr("Скопировать адрес")))

        def open_wallet():
            try:
                os.startfile("ton://transfer/" + TON_ADDRESS)
            except Exception:
                import webbrowser
                webbrowser.open("https://app.tonkeeper.com/transfer/" + TON_ADDRESS)

        cp = button(btns, tr("Скопировать адрес"), copy, primary=True, padx=20)
        cp.pack(side="left")
        button(btns, tr("Открыть в кошельке"), open_wallet, padx=20).pack(side="left", padx=(10, 0))
        tk.Label(wrap, text=tr("Отправляйте только в сети TON (The Open Network)."), bg=BG, fg=MUTED, font=(FONT, 9), anchor="w").pack(fill="x", pady=(14, 0))
        self.place(d, 540, None)
        appwindow(d)

    def on_enabled(self):
        self.paused = not self.enabled_var.get()
        self.refresh_main()
        try:
            self.tray.update_menu()
        except Exception:
            pass

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
            self.toast(tr("Не удалось открыть папку"), [str(e)])

    def nav(self):
        return [("general", G_SETTINGS, tr("Основные")),
                ("save", G_FOLDER, tr("Сохранение")),
                ("mode", G_BOLT, tr("Режим работы")),
                ("notify", G_BELL, tr("Уведомления")),
                ("game", G_GAME, tr("Для игр")),
                ("keys", G_KEYS, tr("Горячие клавиши")),
                ("about", G_INFO, tr("О программе"))]

    PAGES = {"general": ["general"], "save": ["save"], "mode": ["mode"],
             "notify": ["notify"], "game": ["gamemode", "gameshot"],
             "keys": ["keys"], "about": ["about"]}

    def open_settings(self, page="general"):
        if self.settings_win is not None and self.settings_win.winfo_exists():
            self.settings_win.lift()
            self.settings_win.focus_force()
            self.settings_show(page)
            return
        c = self.cfg
        w = tk.Toplevel(self.root)
        self.settings_win = w
        w.withdraw()
        w.overrideredirect(True)
        body = self.chrome(w, APP + tr(" — Настройки"), w.destroy)
        self.v = {
            "autostart": tk.BooleanVar(master=w, value=c["autostart"]),
            "start_minimized": tk.BooleanVar(master=w, value=c["start_minimized"]),
            "watch_hotkey": tk.BooleanVar(master=w, value=c["watch_hotkey"]),
            "game_mode": tk.BooleanVar(master=w, value=c["game_mode"]),
            "check_updates": tk.BooleanVar(master=w, value=c["check_updates"]),
            "game_shot": tk.BooleanVar(master=w, value=c["game_shot"]),
            "game_key": tk.StringVar(master=w, value=next((k for k, x in GAME_KEYS.items() if x == c["game_key"]), "Print Screen")),
            "game_folders": tk.BooleanVar(master=w, value=c["game_folders"]),
            "game_sound": tk.BooleanVar(master=w, value=c["game_sound"]),
            "lang": tk.StringVar(master=w, value=LANG_LABELS.get(c["lang"], LANG_LABELS["auto"])),
            "mode": tk.StringVar(master=w, value=mode_titles().get(c["mode"], tr("Автоматически"))),
            "folder": tk.StringVar(master=w, value=c["folder"]),
            "format": tk.StringVar(master=w, value=str(c["format"]).upper()),
            "template": tk.StringVar(master=w, value=c["template"]),
            "notify": tk.BooleanVar(master=w, value=c["notify"]),
            "toast": tk.StringVar(master=w, value=next((k for k, x in toast_choices().items() if x == c["toast_seconds"]), tr("6 секунд"))),
        }
        self.cur_page = page

        side = tk.Frame(body, bg=BG_SIDE, width=210)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Frame(body, bg=LINE, width=1).pack(side="left", fill="y")
        self.nav_items = {}
        tk.Frame(side, bg=BG_SIDE, height=10).pack()
        for key, glyph, label in self.nav():
            it = Round(side, fill=BG_SIDE, outline=BG_SIDE, radius=10, padx=12, pady=9, bg=BG_SIDE)
            it.pack(fill="x", padx=10, pady=2)
            it.configure(cursor="hand2")
            icon_label(it.inner, glyph, BG_SIDE, FG, 13).pack(side="left", padx=(0, 12))
            tk.Label(it.inner, text=label, bg=BG_SIDE, fg=FG, font=(FONT, 10)).pack(side="left")
            bind_tree(it, "<Button-1>", lambda e, k=key: self.settings_show(k))
            bind_tree(it, "<Enter>", lambda e, k=key, r=it: self.cur_page != k and r.set_fill(BTN))
            bind_tree(it, "<Leave>", lambda e, k=key, r=it: self.cur_page != k and r.set_fill(BG_SIDE))
            self.nav_items[key] = it
        tk.Label(side, text=tr("Версия %s\nСборка %s") % (VERSION, BUILD), bg=BG_SIDE, fg=MUTED, font=(FONT, 9), justify="left", anchor="w").pack(side="bottom", anchor="w", padx=22, pady=18)

        main = tk.Frame(body, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.s_content = tk.Frame(main, bg=BG)
        self.s_content.pack(fill="both", expand=True, padx=20, pady=(12, 0))
        self.s_err = tk.Label(main, text="", bg=BG, fg="#f87171", font=(FONT, 9), anchor="w")
        self.s_err.pack(fill="x", padx=22)
        bar = tk.Frame(main, bg=BG)
        bar.pack(fill="x", padx=20, pady=(6, 18))
        button(bar, tr("Сохранить"), self.apply_settings, primary=True, padx=34).pack(side="right")
        button(bar, tr("Отмена"), w.destroy, padx=34).pack(side="right", padx=(0, 12))

        self.secs = {}
        self.build_sections(self.s_content)
        heights = []
        for pg in self.PAGES:
            self.settings_show(pg)
            w.update_idletasks()
            heights.append(w.winfo_reqheight())
        self.place(w, 840, max(max(heights), 500))
        self.settings_show(page)
        appwindow(w)

    def section(self, parent, key, title):
        outer = tk.Frame(parent, bg=BG)
        tk.Label(outer, text=title, bg=BG, fg=FG, font=(FONT, 12), anchor="w").pack(fill="x", pady=(0, 8))
        card = Round(outer, radius=14, padx=14, pady=8)
        card.pack(fill="x")
        self.secs[key] = outer
        return card.inner

    def toggle_row(self, parent, glyph, text, var):
        r = tk.Frame(parent, bg=PANEL)
        r.pack(fill="x", pady=6)
        icon_label(r, glyph, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r, text=text, bg=PANEL, fg=FG, font=(FONT, 10)).pack(side="left")
        Toggle(r, var, PANEL).pack(side="right")

    def hint(self, parent, text, glyph=None, pady=(6, 2)):
        r = tk.Frame(parent, bg=PANEL)
        r.pack(fill="x", pady=pady)
        if glyph:
            icon_label(r, glyph, PANEL, ACCENT_SOFT, 12).pack(side="left", anchor="n", padx=(0, 12))
        tk.Label(r, text=text, bg=PANEL, fg=MUTED, font=(FONT, 9), justify="left", anchor="w", wraplength=520).pack(side="left", fill="x")
        return r

    def keycaps(self, parent, keys):
        r = tk.Frame(parent, bg=PANEL)
        for i, k in enumerate(keys):
            if i:
                tk.Label(r, text="+", bg=PANEL, fg=MUTED, font=(FONT, 10)).pack(side="left", padx=6)
            cap = Round(r, fill=FIELD, outline=LINE, radius=8, padx=10, pady=5)
            cap.pack(side="left")
            tk.Label(cap.inner, text=k, bg=FIELD, fg=FG, font=(FONT, 10, "bold")).pack()
        return r

    def open_telegram(self, handle):
        try:
            os.startfile("tg://resolve?domain=" + handle)
        except Exception:
            import webbrowser
            webbrowser.open("https://t.me/" + handle)

    def author_row(self, parent, handle):
        row = tk.Frame(parent, bg=PANEL, cursor="hand2")
        row.pack(fill="x", pady=2)
        av = tk.Canvas(row, width=36, height=36, bg=PANEL, highlightthickness=0)
        av.create_oval(1, 1, 35, 35, fill=ACCENT, outline=ACCENT)
        av.create_text(18, 18, text=handle[0].upper(), fill="#ffffff", font=(FONT, 12, "bold"))
        av.pack(side="left", padx=(6, 12), pady=6)
        tk.Label(row, text="@" + handle, bg=PANEL, fg=FG, font=(FONT, 11)).pack(side="left")
        icon_label(row, G_CHEV, PANEL, MUTED, 9).pack(side="right", padx=(8, 8))
        tk.Label(row, text="Telegram", bg=PANEL, fg=ACCENT_SOFT, font=(FONT, 10)).pack(side="right")

        def paint(color):
            set_bg_tree(row, color)
            av.configure(bg=color)

        bind_tree(row, "<Button-1>", lambda e: self.open_telegram(handle))
        bind_tree(row, "<Enter>", lambda e: paint(FIELD))
        bind_tree(row, "<Leave>", lambda e: paint(PANEL))

    def build_sections(self, parent):
        v = self.v
        g = self.section(parent, "general", tr("Основные"))
        self.toggle_row(g, G_AUTO, tr("Запускать вместе с Windows"), v["autostart"])
        self.toggle_row(g, G_TRAY, tr("Запускать свёрнутым в трей"), v["start_minimized"])
        r6 = tk.Frame(g, bg=PANEL)
        r6.pack(fill="x", pady=6)
        icon_label(r6, G_LANG, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r6, text=tr("Язык"), bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")
        lbox, _ = self.combo(r6, v["lang"], list(LANG_LABELS.values()))
        lbox.pack(side="left", fill="x", expand=True)
        if REPO:
            self.toggle_row(g, G_SYNC, tr("Проверять обновления при запуске"), v["check_updates"])

        m = self.section(parent, "mode", tr("Режим работы"))
        row = tk.Frame(m, bg=PANEL)
        row.pack(fill="x", pady=(4, 0))
        icon_label(row, G_BOLT, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        box, cb = self.combo(row, v["mode"], list(mode_titles().values()))
        box.pack(side="left", fill="x", expand=True)
        self.mode_hint = tk.Label(m, bg=PANEL, fg=MUTED, font=(FONT, 9), anchor="w")
        self.mode_hint.pack(fill="x", pady=(8, 4))

        def upd(*a):
            key = "ask" if v["mode"].get() == mode_titles()["ask"] else "auto"
            self.mode_hint.config(text=mode_hints()[key])

        cb.bind("<<ComboboxSelected>>", upd)
        upd()

        s = self.section(parent, "save", tr("Сохранение"))
        r1 = tk.Frame(s, bg=PANEL)
        r1.pack(fill="x", pady=6)
        icon_label(r1, G_FOLDER, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r1, text=tr("Папка сохранения"), bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")

        def choose():
            p = filedialog.askdirectory(parent=self.settings_win, initialdir=v["folder"].get() or str(Path.home()))
            if p:
                v["folder"].set(os.path.normpath(p))

        button(r1, tr("Выбрать"), choose, padx=16, pady=6).pack(side="right", padx=(10, 0))
        self.field(r1, v["folder"]).pack(side="left", fill="x", expand=True)

        r2 = tk.Frame(s, bg=PANEL)
        r2.pack(fill="x", pady=6)
        icon_label(r2, G_PHOTO, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r2, text=tr("Формат файлов"), bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")
        fbox, _ = self.combo(r2, v["format"], ["PNG", "JPG"])
        fbox.pack(side="left", fill="x", expand=True)

        r3 = tk.Frame(s, bg=PANEL)
        r3.pack(fill="x", pady=6)
        icon_label(r3, G_PAGE, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r3, text=tr("Шаблон имени файла"), bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")
        self.field(r3, v["template"]).pack(side="left", fill="x", expand=True)
        self.hint(s, tr("yyyy год, MM месяц, dd день, HH час, mm минуты, ss секунды"), pady=(0, 4))

        n = self.section(parent, "notify", tr("Уведомления"))
        self.toggle_row(n, G_BELL, tr("Уведомлять после сохранения"), v["notify"])
        r4 = tk.Frame(n, bg=PANEL)
        r4.pack(fill="x", pady=6)
        icon_label(r4, G_CLOCK, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r4, text=tr("Сколько показывать"), bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")
        nbox, _ = self.combo(r4, v["toast"], list(toast_choices()))
        nbox.pack(side="left", fill="x", expand=True)
        self.hint(n, tr("Окно «Скриншот сохранён» появляется в правом нижнем углу и закрывается само. В игровом режиме уведомления не показываются."), G_INFO, pady=(6, 4))

        gm = self.section(parent, "gamemode", tr("Игровой режим"))
        self.toggle_row(gm, G_GAME, tr("Игровой режим"), v["game_mode"])
        self.hint(gm, tr("В полноэкранных играх скриншоты сохраняются молча, без окон и уведомлений. После игры покажется итог."), G_INFO, pady=(4, 4))

        gs = self.section(parent, "gameshot", tr("Скриншот для игр"))
        self.toggle_row(gs, G_SHOT, tr("Делать скриншот по клавише"), v["game_shot"])
        r7 = tk.Frame(gs, bg=PANEL)
        r7.pack(fill="x", pady=6)
        icon_label(r7, G_KEYS, PANEL, FG, 13).pack(side="left", padx=(0, 12))
        tk.Label(r7, text=tr("Клавиша"), bg=PANEL, fg=FG, font=(FONT, 10), width=18, anchor="w").pack(side="left")
        kbox, _ = self.combo(r7, v["game_key"], list(GAME_KEYS))
        kbox.pack(side="left", fill="x", expand=True)
        self.toggle_row(gs, G_FOLDER, tr("Отдельная папка для каждой игры"), v["game_folders"])
        self.toggle_row(gs, G_SOUND, tr("Звук при сохранении"), v["game_sound"])
        self.hint(gs, tr("Нажмите клавишу в игре, и экран сохранится сразу, без окон. Если вместо игры получается чёрный кадр, переведите игру в режим «Без рамки» или «В окне»."), G_INFO, pady=(4, 4))

        k = self.section(parent, "keys", tr("Горячие клавиши"))
        self.toggle_row(k, G_KEYS, tr("Отслеживать сочетание клавиш Win + Shift + S"), v["watch_hotkey"])
        r5 = tk.Frame(k, bg=PANEL)
        r5.pack(fill="x", pady=8)
        tk.Label(r5, text=tr("Сделать скриншот области"), bg=PANEL, fg=FG, font=(FONT, 10)).pack(side="left", padx=(30, 0))
        self.keycaps(r5, ["Win", "Shift", "S"]).pack(side="right")
        self.hint(k, tr("Приложение ждёт, пока вы сделаете скриншот, и Windows поместит его в буфер обмена. Если выключить, сохраняется любая картинка из буфера."), G_INFO, pady=(4, 4))

        a = self.section(parent, "about", tr("О программе"))
        tk.Label(a, text="%s %s" % (APP, VERSION), bg=PANEL, fg=FG, font=(FONT, 14, "bold"), anchor="w").pack(fill="x", pady=(6, 0))
        tk.Label(a, text=tr("Сборка: %s") % BUILD, bg=PANEL, fg=ACCENT_SOFT, font=(FONT, 10), anchor="w").pack(fill="x", pady=(4, 0))
        tk.Label(a, text=tr("Скриншотнул — сохранил."), bg=PANEL, fg=MUTED, font=(FONT, 10), anchor="w").pack(fill="x", pady=(8, 0))
        if REPO:
            ur = tk.Frame(a, bg=PANEL)
            ur.pack(fill="x", pady=(14, 0))
            button(ur, tr("Проверить обновления"), self.manual_check, padx=16, pady=6).pack(side="left")
            self.upd_status = tk.Label(ur, text="", bg=PANEL, fg=MUTED, font=(FONT, 10), anchor="w")
            self.upd_status.pack(side="left", padx=14)
            self.upd_status.bind("<Button-1>", lambda e: self.open_update())
            if self.update_info:
                self.show_update_status(True, True)
        tk.Frame(a, bg=LINE, height=1).pack(fill="x", pady=(12, 10))
        tk.Label(a, text=tr("Авторы"), bg=PANEL, fg=FG, font=(FONT, 11, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        for h in AUTHORS:
            self.author_row(a, h)
        tk.Frame(a, bg=LINE, height=1).pack(fill="x", pady=(10, 8))
        tk.Label(a, text=tr("Настройки хранятся в:\n%s") % CONFIG_PATH, bg=PANEL, fg=MUTED, font=(FONT, 9), justify="left", anchor="w", wraplength=520).pack(fill="x", pady=(0, 6))

    def settings_show(self, page):
        self.cur_page = page
        for key, it in self.nav_items.items():
            it.set_fill(NAV_ON if key == page else BG_SIDE)
        for sec in self.secs.values():
            sec.pack_forget()
        for key in self.PAGES.get(page, ["general"]):
            self.secs[key].pack(fill="x", pady=(0, 12))

    def apply_settings(self):
        c, v = self.cfg, self.v
        folder = v["folder"].get().strip()
        if not folder:
            self.s_err.config(text=tr("Укажи папку для сохранения."))
            return
        if not v["template"].get().strip():
            self.s_err.config(text=tr("Шаблон имени не может быть пустым."))
            return
        c["autostart"] = bool(v["autostart"].get())
        c["start_minimized"] = bool(v["start_minimized"].get())
        c["watch_hotkey"] = bool(v["watch_hotkey"].get())
        c["game_mode"] = bool(v["game_mode"].get())
        c["game_shot"] = bool(v["game_shot"].get())
        c["game_key"] = GAME_KEYS.get(v["game_key"].get(), "print screen")
        c["game_folders"] = bool(v["game_folders"].get())
        c["game_sound"] = bool(v["game_sound"].get())
        c["mode"] = "ask" if v["mode"].get() == mode_titles()["ask"] else "auto"
        c["folder"] = folder
        c["format"] = v["format"].get()
        c["template"] = v["template"].get().strip()
        c["notify"] = bool(v["notify"].get())
        c["toast_seconds"] = toast_choices().get(v["toast"].get(), 6)
        c["check_updates"] = bool(v["check_updates"].get())
        c["lang"] = next((k for k, x in LANG_LABELS.items() if x == v["lang"].get()), "auto")
        save_config(c)
        set_autostart(c["autostart"])
        self.register_game_hotkey()
        old_lang = LANG
        set_lang(c)
        if LANG != old_lang:
            self.rebuild_main()
        self.refresh_main()
        try:
            self.tray.update_menu()
        except Exception:
            pass
        self.settings_win.destroy()
        self.toast(tr("Настройки сохранены"), [], seconds=2)

    def shell(self, title="ShotFile"):
        d = tk.Toplevel(self.root)
        d.withdraw()
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
        round_window(d, 14)
        d.deiconify()

    def open_update(self):
        if self.update_info:
            import webbrowser
            webbrowser.open(self.update_info[1])

    def check_updates(self, manual=False):
        if not REPO:
            return

        def work():
            try:
                tag, url = fetch_latest(REPO)
                ok = True
            except Exception:
                tag, url, ok = "", "", False
            self.q.put(lambda: self.on_update_result(ok, tag, url, manual))

        threading.Thread(target=work, daemon=True).start()

    def on_update_result(self, ok, tag, url, manual):
        newer = ok and parse_version(tag) > parse_version(VERSION)
        if newer:
            self.update_info = (tag.lstrip("vV"), url or "https://github.com/%s/releases" % REPO)
        elif ok:
            self.update_info = None
        self.refresh_main()
        if newer and not manual and not self.update_announced and not self.in_game:
            self.update_announced = True
            self.toast(tr("Вышла новая версия"), [tr("Версия %s уже на GitHub") % self.update_info[0], tr("Нажмите, чтобы открыть страницу загрузки")],
                       seconds=10, link=self.update_info[1])
        self.show_update_status(ok, newer)

    def show_update_status(self, ok, newer):
        lab = getattr(self, "upd_status", None)
        try:
            if lab is None or not lab.winfo_exists():
                return
        except Exception:
            return
        if not ok:
            lab.config(text=tr("Не удалось проверить обновления"), fg=MUTED, cursor="")
        elif newer:
            lab.config(text=tr("Доступна версия %s. Открыть страницу загрузки") % self.update_info[0], fg=GOOD, cursor="hand2")
        else:
            lab.config(text=tr("У вас последняя версия"), fg=MUTED, cursor="")

    def manual_check(self):
        self.upd_status.config(text=tr("Проверяю…"), fg=MUTED, cursor="")
        self.check_updates(manual=True)

    def toast(self, title, lines, thumb=None, seconds=6, link=None):
        if self.toast_win is not None and self.toast_win.winfo_exists():
            self.toast_win.destroy()
        d, card, body, x = self.shell()
        self.toast_win = d
        if thumb is not None:
            t = thumb.copy()
            t.thumbnail((84, 64))
            d.ph = ImageTk.PhotoImage(round_image(with_check(t), 8))
            tk.Label(body, image=d.ph, bg=BG).pack(side="left", padx=(0, 16))
        txt = tk.Frame(body, bg=BG)
        txt.pack(side="left")
        tk.Label(txt, text=title, bg=BG, fg=FG, font=(FONT, 11, "bold"), anchor="w").pack(fill="x")
        for ln in lines:
            tk.Label(txt, text=ln, bg=BG, fg="#c5cde0", font=(FONT, 9), anchor="w", justify="left").pack(fill="x", pady=(3, 0))
        if link:
            def go(e):
                import webbrowser
                webbrowser.open(link)
                d.destroy()
            bind_tree(txt, "<Button-1>", go)
            txt.configure(cursor="hand2")
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
        d.ph = ImageTk.PhotoImage(round_image(thumb, 10))
        tk.Label(body, image=d.ph, bg=BG).pack(side="left", padx=(0, 18), anchor="n")
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", anchor="n")
        tk.Label(right, text=tr("Обнаружен скриншот!"), bg=BG, fg=FG, font=(FONT, 14), anchor="w").pack(fill="x")
        tk.Label(right, text=tr("Сохранить изображение в папку\n%s?") % "/".join(Path(self.cfg["folder"]).parts[-2:]), bg=BG, fg="#c5cde0",
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

        button(btns, tr("Сохранить"), lambda: finish(True), primary=True, padx=20, pady=7).pack(side="left")
        button(btns, tr("Не сохранять"), lambda: finish(False), padx=20, pady=7).pack(side="left", padx=(10, 0))
        x.bind("<Button-1>", lambda e: finish(False))

        def tick():
            if state["done"] or not d.winfo_exists():
                return
            if state["left"] <= 0:
                finish(False)
                return
            n = state["left"]
            timer.config(text=tr("Автоматически закроется через %d %s") % (n, plural(n, tr("секунду"), tr("секунды"), tr("секунд"))))
            state["left"] -= 1
            d.after(1000, tick)

        tick()
        self.dock(d)

    def save_and_notify(self, img):
        try:
            path = save_image(img, self.cfg)
        except Exception as e:
            self.toast(tr("Не удалось сохранить"), [str(e)])
            return
        if self.cfg["notify"]:
            self.toast(tr("Скриншот сохранён"), [tr("Файл: %s") % path.name, tr("Папка: %s") % "/".join(path.parent.parts[-2:])], thumb=img, seconds=self.cfg["toast_seconds"])

    def save_silent(self, img):
        try:
            save_image(img, self.cfg)
            self.game_saved += 1
        except Exception:
            pass

    def handle_image(self, img):
        if self.in_game and self.cfg["game_mode"]:
            self.save_silent(img)
        elif self.cfg["mode"] == "ask":
            self.ask(img)
        else:
            self.save_and_notify(img)

    def on_game_change(self):
        self.refresh_main()
        if not self.in_game and self.game_saved:
            n = self.game_saved
            self.game_saved = 0
            self.toast(tr("Игровой режим"), [tr("Сохранено %d %s") % (n, plural(n, tr("скриншот"), tr("скриншота"), tr("скриншотов"))),
                                         tr("Папка: %s") % "/".join(Path(self.cfg["folder"]).parts[-2:])])

    def start_hotkey(self):
        try:
            import keyboard
            keyboard.add_hotkey("windows+shift+s", self.arm)
            self.has_hotkey = True
        except Exception:
            self.has_hotkey = False
        self.register_game_hotkey()
        self.refresh_main()

    def arm(self):
        self.armed_until = time.time() + 60

    def register_game_hotkey(self):
        try:
            import keyboard
        except Exception:
            return
        if self.game_hook is not None:
            try:
                keyboard.remove_hotkey(self.game_hook)
            except Exception:
                pass
            self.game_hook = None
        if self.cfg["game_shot"]:
            try:
                self.game_hook = keyboard.add_hotkey(self.cfg["game_key"], self.game_shot)
            except Exception:
                self.game_hook = None

    def game_shot(self):
        if self.paused or not self.cfg["game_shot"]:
            return
        self.suppress_until = time.time() + 2.5
        threading.Thread(target=self.game_shot_work, daemon=True).start()

    def game_shot_work(self):
        try:
            from PIL import ImageGrab
            rect, name = foreground_info()
            img = ImageGrab.grab(bbox=rect, all_screens=True) if rect else ImageGrab.grab()
            path = save_image(img, dict(self.cfg, folder=str(game_folder(self.cfg, name))))
        except Exception as e:
            err = str(e)
            self.q.put(lambda: self.toast(tr("Не удалось сохранить"), [err]) if not self.in_game else None)
            return
        if self.cfg["game_sound"]:
            try:
                import winsound
                winsound.Beep(1200, 60)
            except Exception:
                pass
        self.q.put(lambda: self.on_game_shot(path, img))

    def on_game_shot(self, path, img):
        if self.in_game and self.cfg["game_mode"]:
            self.game_saved += 1
        elif self.cfg["notify"]:
            self.toast(tr("Скриншот игры сохранён"), [tr("Файл: %s") % path.name, tr("Папка: %s") % "/".join(path.parent.parts[-2:])],
                       thumb=img, seconds=self.cfg["toast_seconds"])

    def watch(self):
        try:
            last = clipboard_seq()
        except Exception:
            return
        fs_since = None
        last_check = 0.0
        while self.running:
            time.sleep(0.25)
            now = time.time()
            if now - last_check >= 1.0:
                last_check = now
                try:
                    fs = bool(self.cfg["game_mode"]) and fullscreen_active()
                except Exception:
                    fs = False
                if fs:
                    fs_since = fs_since or now
                else:
                    fs_since = None
                game = fs_since is not None and now - fs_since >= 3
                if game != self.in_game:
                    self.in_game = game
                    self.q.put(self.on_game_change)
            try:
                seq = clipboard_seq()
            except Exception:
                continue
            if seq == last:
                continue
            last = seq
            if self.paused or time.time() < self.suppress_until:
                continue
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

        def toggle_pause(icon, item):
            self.q.put(lambda: self.enabled_var.set(not self.enabled_var.get()))

        def toggle_game(icon, item):
            self.cfg["game_mode"] = not self.cfg["game_mode"]
            save_config(self.cfg)

        def toggle_gameshot(icon, item):
            self.cfg["game_shot"] = not self.cfg["game_shot"]
            save_config(self.cfg)
            self.q.put(self.register_game_hotkey)

        menu = M(
            I(lambda item: tr("Открыть окно"), ui(self.show_main), default=True),
            I(lambda item: tr("Открыть папку"), ui(self.open_folder)),
            I(lambda item: tr("Настройки"), ui(self.open_settings)),
            M.SEPARATOR,
            I(lambda item: tr("Режим: ") + mode_titles().get(self.cfg["mode"], tr("Автоматически")), M(
                I(lambda item: tr("Автоматически"), set_mode("auto"), checked=lambda item: self.cfg["mode"] == "auto", radio=True),
                I(lambda item: tr("Спрашивать"), set_mode("ask"), checked=lambda item: self.cfg["mode"] == "ask", radio=True),
            )),
            I(lambda item: tr("Включить сохранение") if self.paused else tr("Приостановить сохранение"), toggle_pause),
            I(lambda item: tr("Игровой режим"), toggle_game, checked=lambda item: self.cfg["game_mode"]),
            I(lambda item: tr("Скриншот для игр"), toggle_gameshot, checked=lambda item: self.cfg["game_shot"]),
            I(lambda item: tr("Запускать с Windows"), toggle_autostart, checked=lambda item: self.cfg["autostart"]),
            M.SEPARATOR,
            I(lambda item: tr("О программе"), ui(lambda: self.open_settings("about"))),
            I(lambda item: tr("Выход"), ui(self.quit)),
        )
        self.tray = pystray.Icon(APP, self.tray_img, APP, menu)
        self.tray.run_detached()

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
