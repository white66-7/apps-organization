from pynput import mouse
import ctypes
import ctypes.wintypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class POINT(ctypes.Structure):
    _fields_ = [("x",ctypes.wintypes.LONG),("y",ctypes.wintypes.LONG)]


class DesktopEngine:
    def __init__(self):
        self.clicks = []
        self.enabled = True
        self.listener = None

    #前置判断
    def get_deskop_handles(self):
        for root in ["Progman","Workerw"]:
            hwnd = user32.FindWindowW(root,None)
            while hwnd:
                sv = user32.FindWindowExW(hwnd,0,"SHELLDLL_DefView",None)
                if sv:
                    lv = user32.FindWindowExW(sv, 0, 'SysListView32',None)
                    return sv, lv
                hwnd = user32.FindWindowExW(0,hwnd,root,None)
        return 0, 0


    def start(self):
        if self.listener is None:
            # 点击绑定事件
            self.listener = mouse.Listener(on_click=self.onclick)
            self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
            self.listener = None

    # 判断函数
    def is_on_icon(self,x,y):
        _, lv = self.get_deskop_handles()
        if not lv or not user32.IsWindowVisible(lv):
            return False
        if user32.WindowFromPoint(POINT(int(x),int(y))) != lv:
            return False
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(lv,ctypes.byref(pid))
        h_proc = kernel32.OpenProcess(0x0038,False,pid)
        if not h_proc:
            return False
        try:
            mem = kernel32.VirtualAllocEx(h_proc,None,16,0x1000,0x04)
            pt = POINT(int(x),int(y))
            user32.ScreenToClient(lv, ctypes.byref(pt))
            kernel32.WriteProcessMemory(h_proc, mem, ctypes.byref(pt)),
            res = user32.SendMessageW(lv,0x1000 + 18, 0, mem)
            kernel32.VirtualFreeEx(h_proc, mem, 0, 0x8000)
            return res != -1
        finally:
            kernel32.CloseHandle(h_proc)


    # 刷新函数
    def refresh_desktop(self):
        sv, _ = self.get_deskop_handles()
        if sv:
            user32.SendMessageW(sv,0x0111, 0x7402, 0)

    # 点击查询函数
    def onclick(self, x, y, button, pressed):
        if not self.enabled: return
        if button == mouse.Button.left and pressed:
            now = time.time()
            self.clicks = [t for t in self.clicks if now -t < 0.4]
            self.clicks.append(now)
            if len(self.clicks) >= 2:
                target = user32.WindowFromPoint(POINT(int(x), int(y)))
                buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(target, buf, 256)
                if buf.value in ["SysListView32", "SHELLDLL_DefView", "WorkerW", "Progman"]:
                    if not self.is_on_icon(x,y):
                        self.refresh_desktop()
                self.clicks = []

    def toggle(self):
        pass

    def run_fade_animation(self):
        pass