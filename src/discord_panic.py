"""Discord Panic Button
Minimize (and restore) every Discord window with one global hotkey or key chord.

Settings: %APPDATA%\\DiscordPanic\\config.json
Command line:
  DiscordPanic.exe            start in the background (single instance)
  DiscordPanic.exe --stop     stop the running instance
  DiscordPanic.exe --restart  restart (apply config changes)
  DiscordPanic.exe --config   open the config file in Notepad
"""
import ctypes, ctypes.wintypes as wt, json, os, sys, logging, subprocess, time

APP = "Discord Panic Button"
DATA = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "DiscordPanic")
CFG = os.path.join(DATA, "config.json")
PIDFILE = os.path.join(DATA, "running.pid")
os.makedirs(DATA, exist_ok=True)
logging.basicConfig(filename=os.path.join(DATA, "discord_panic.log"), level=logging.INFO,
                    format="%(asctime)s %(message)s")

DEFAULT = {
    "hotkey": "num1+num3+num5",
    "toggle_restore": True,
    "swallow_trigger_key": True,
    "process_names": ["discord.exe", "discordptb.exe", "discordcanary.exe"],
}

user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
kernel32.GetModuleHandleW.restype = wt.HMODULE
kernel32.OpenProcess.restype = wt.HANDLE

WM_QUIT, WM_HOTKEY, WM_APP_TRIGGER = 0x0012, 0x0312, 0x8001


def msgbox(text, icon=0x30):
    user32.MessageBoxW(None, text, APP, icon)


# ---------------------------------------------------------------- config
def load_cfg():
    if not os.path.exists(CFG):
        with open(CFG, "w") as f:
            json.dump(DEFAULT, f, indent=2)
    with open(CFG) as f:
        return {**DEFAULT, **json.load(f)}


MODS = {"alt": 0x1, "ctrl": 0x2, "control": 0x2, "shift": 0x4, "win": 0x8}
NAMED = {**{f"f{i}": 0x6F + i for i in range(1, 25)}, "`": 0xC0, "space": 0x20, "esc": 0x1B,
         "pause": 0x13, "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
         "pageup": 0x21, "pagedown": 0x22, "-": 0xBD, "=": 0xBB, "[": 0xDB, "]": 0xDD,
         ";": 0xBA, "'": 0xDE, ",": 0xBC, ".": 0xBE, "/": 0xBF, "\\": 0xDC,
         "numplus": 0x6B, "numminus": 0x6D, "nummul": 0x6A, "numdiv": 0x6F}
# numpad digit scan codes (non-extended): same with NumLock on or off
NUM_SC = {0: 0x52, 1: 0x4F, 2: 0x50, 3: 0x51, 4: 0x4B, 5: 0x4C, 6: 0x4D, 7: 0x47, 8: 0x48, 9: 0x49}


def key_id(p):
    if p.startswith("num") and p[3:].isdigit():
        return ("sc", NUM_SC[int(p[3:])])
    if p in NAMED:
        return ("vk", NAMED[p])
    if len(p) == 1 and p.isalnum():
        return ("vk", ord(p.upper()))
    raise ValueError(f"unknown key '{p}'")


def parse(hk):
    mods, keys = 0, []
    for p in hk.lower().replace(" ", "").split("+"):
        if p in MODS:
            mods |= MODS[p]
        elif p:
            keys.append(key_id(p))
    if not keys:
        raise ValueError("hotkey needs at least one non-modifier key")
    return mods, keys


# ---------------------------------------------------------------- windows
def proc_name(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)
    if not h:
        return ""
    buf = ctypes.create_unicode_buffer(520)
    n = wt.DWORD(520)
    ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
    kernel32.CloseHandle(h)
    return os.path.basename(buf.value).lower() if ok else ""


def discord_windows(names):
    out = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0 \
                and user32.GetWindow(hwnd, 4) == 0 and proc_name(hwnd) in names:
            out.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return out


def bring_to_front(hwnd):
    fg = user32.GetForegroundWindow()
    a = user32.GetWindowThreadProcessId(fg, None)
    b = kernel32.GetCurrentThreadId()
    attached = a and a != b and user32.AttachThreadInput(b, a, True)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    if attached:
        user32.AttachThreadInput(b, a, False)


_last_minimized = []


def toggle(cfg, names):
    global _last_minimized
    wins = discord_windows(names)
    shown = [w for w in wins if not user32.IsIconic(w)]
    if shown or not cfg["toggle_restore"]:
        for w in shown:
            user32.ShowWindow(w, 6)  # SW_MINIMIZE
        _last_minimized = shown or _last_minimized
        logging.info("minimized %d window(s)", len(shown))
    else:
        targets = [w for w in _last_minimized if user32.IsWindow(w) and user32.IsIconic(w)] or wins
        for w in targets:
            user32.ShowWindow(w, 9)  # SW_RESTORE
        if targets:
            bring_to_front(targets[0])
        logging.info("restored %d window(s)", len(targets))


# ---------------------------------------------------------------- instance control
def read_pid():
    try:
        pid, tid = map(int, open(PIDFILE).read().split())
        return pid, tid
    except Exception:
        return None, None


def stop_running(wait=3.0):
    pid, tid = read_pid()
    if not pid:
        return False
    h = kernel32.OpenProcess(0x00101001, False, pid)  # SYNCHRONIZE|TERMINATE|QUERY_LIMITED
    if h:
        buf = ctypes.create_unicode_buffer(520)
        n = wt.DWORD(520)
        kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n))
        exe = os.path.basename(buf.value).lower()
        if exe not in ("discordpanic.exe", "pythonw.exe", "python.exe"):
            kernel32.CloseHandle(h)  # stale pid reused by something else - leave it alone
            h = None
    if h:
        user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
        if kernel32.WaitForSingleObject(h, int(wait * 1000)) != 0:
            kernel32.TerminateProcess(h, 0)
        kernel32.CloseHandle(h)
    try:
        os.remove(PIDFILE)
    except OSError:
        pass
    return True


def launch_detached():
    args = [sys.executable] if getattr(sys, "frozen", False) else \
        [sys.executable.replace("python.exe", "pythonw.exe"), os.path.abspath(__file__)]
    subprocess.Popen(args, creationflags=0x00000008 | 0x00000200, close_fds=True)


# ---------------------------------------------------------------- main loop
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


def run():
    mutex = kernel32.CreateMutexW(None, False, "Local\\DiscordPanicButton")
    if kernel32.GetLastError() == 183:
        return  # already running
    try:
        cfg = load_cfg()
        mods, keys = parse(cfg["hotkey"])
    except Exception as e:
        logging.error("bad config: %s", e)
        msgbox(f"Config error: {e}\n\nEdit {CFG} and start the app again.")
        return
    names = {n.lower() for n in cfg["process_names"]}
    tid = kernel32.GetCurrentThreadId()

    if mods and len(keys) == 1 and keys[0][0] == "vk":
        if not user32.RegisterHotKey(None, 1, mods | 0x4000, keys[0][1]):
            logging.error("RegisterHotKey failed for %s", cfg["hotkey"])
            msgbox(f"Hotkey '{cfg['hotkey']}' is already used by another app.\n\nEdit {CFG}")
            return
    else:
        want, down = set(keys), set()
        mod_vks = {0x1: (0x12,), 0x2: (0x11,), 0x4: (0x10,), 0x8: (0x5B, 0x5C)}

        def mods_ok():
            return all(any(user32.GetAsyncKeyState(v) & 0x8000 for v in vks)
                       for m, vks in mod_vks.items() if mods & m)

        @ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wt.WPARAM, wt.LPARAM)
        def hook(n, wp, lp):
            if n == 0:
                k = ctypes.cast(lp, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                ids = {("vk", k.vkCode)}
                if not (k.flags & 0x01):
                    ids.add(("sc", k.scanCode))
                hit = ids & want
                if hit:
                    kid = hit.pop()
                    if wp in (0x100, 0x104):
                        fresh = kid not in down
                        down.add(kid)
                        if fresh and down >= want and mods_ok():
                            user32.PostThreadMessageW(tid, WM_APP_TRIGGER, 0, 0)
                            if cfg["swallow_trigger_key"]:
                                return 1
                    elif wp in (0x101, 0x105):
                        down.discard(kid)
            return user32.CallNextHookEx(None, n, wp, lp)

        run.hook = hook  # keep the callback alive
        if not user32.SetWindowsHookExW(13, hook, kernel32.GetModuleHandleW(None), 0):
            logging.error("SetWindowsHookEx failed")
            return

    with open(PIDFILE, "w") as f:
        f.write(f"{os.getpid()} {tid}")
    logging.info("running, hotkey=%s toggle=%s", cfg["hotkey"], cfg["toggle_restore"])
    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message in (WM_HOTKEY, WM_APP_TRIGGER):
            try:
                toggle(cfg, names)
            except Exception:
                logging.exception("toggle failed")
    logging.info("stopped")


def main():
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if arg == "--stop":
        stop_running()
    elif arg == "--restart":
        stop_running()
        time.sleep(0.3)
        launch_detached()
    elif arg == "--config":
        load_cfg()
        subprocess.Popen(["notepad.exe", CFG])
    else:
        run()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("crash")
