from pynput import mouse
import ctypes
import ctypes.wintypes
import time
import threading
from queue import Queue

user32 = ctypes.windll.user32    # 窗口管理dll
kernel32 = ctypes.windll.kernel32  # 进程管理dll


class POINT(ctypes.Structure):
    _fields_ = [("x",ctypes.wintypes.LONG),("y",ctypes.wintypes.LONG)]


class DesktopEngine:
    def __init__(self):
        ctypes.windll.shcore.SetProcessDpiAwareness(1)

        self.click_time_threshold = 0.3

        self.click_queue = Queue()
        self.last_click_time = 0
        self.enabled = True
        self.running = False
        self.listener = None

        self.desktop_lv = 0
        self.desktop_sv = 0
        self.explorer_pid = 0

    #前置判断
    def get_desktop_info(self):
        for root in ["Progman","WorkerW"]:
            hwnd = user32.FindWindowW(root,None)
            while hwnd:
                # 拿桌面视图权限
                sv = user32.FindWindowExW(hwnd,0,"SHELLDLL_DefView",None)
                if sv:
                    # 拿程序选中，刷新权限
                    lv = user32.FindWindowExW(sv, 0, 'SysListView32',None)
                    if lv:
                        self.desktop_lv = lv
                        self.desktop_sv = sv
                        pid = ctypes.wintypes.DWORD()
                        user32.GetWindowThreadProcessId(lv,ctypes.byref(pid))
                        self.explorer_pid = pid.value
                        return True
                # 继续找下一个
                hwnd = user32.FindWindowExW(0,hwnd,root,None)
        return False


    def start(self):
        self.running = True
        self.get_desktop_info()
        threading.Thread(target=self._worker_loop, daemon=True).start()
        self.listener = mouse.Listener(on_click=self.onclick)
        self.listener.start()

    def stop(self):
        self.running = False
        if self.listener:
            self.listener.stop()

    def _worker_loop(self):
        """关键：这是你漏掉的后台逻辑处理线程"""
        while self.running:
            try:
                # 获取双击坐标（等待1秒超时，方便循环退出）
                x, y = self.click_queue.get(timeout=1)
                
                # 更新/校验句柄
                if not user32.IsWindow(self.desktop_lv):
                    self.get_desktop_info()

                target = user32.WindowFromPoint(POINT(x, y))
                t_pid = ctypes.wintypes.DWORD()
                user32.GetWindowThreadProcessId(target, ctypes.byref(t_pid))

                # PID 校验（核心：解决其他程序误触发）
                if t_pid.value == self.explorer_pid:
                    buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(target, buf, 256)
                    if buf.value in ["SysListView32", "SHELLDLL_DefView", "WorkerW", "Progman"]:
                        # 图标校验
                        if not self.is_on_icon(x, y):
                            self.refresh_desktop()
            except: # 队列为空
                continue

    # 图标判断函数
    def is_on_icon(self, x, y):
        # 判断是否拿到与可见
        if not self.desktop_lv or not user32.IsWindowVisible(self.desktop_lv):
            return False
            
        # 通过pid拿到explore.exe句柄
        h_proc = kernel32.OpenProcess(0x0038, False, self.explorer_pid) 

        #权限不足或没拿到直接退出
        if not h_proc:
            return False
            
        mem = None
        try:
            mem = kernel32.VirtualAllocEx(h_proc, None, 16, 0x1000, 0x04) # 在explore.exe申请16字节的地址
            if not mem: return False
            
            pt = POINT(int(x), int(y))
            user32.ScreenToClient(self.desktop_lv, ctypes.byref(pt))  #绝对坐标转为相对坐标

            #测试点击位置
            kernel32.WriteProcessMemory(h_proc, mem, ctypes.byref(pt), 8, None)

            res = ctypes.wintypes.DWORD()
            user32.SendMessageTimeoutW(self.desktop_lv, 0x1012, 0, mem, 0x0002, 100, ctypes.byref(res))
            return res.value != 4294967295
        
        except Exception as e:
            print(f"Engine Error: {e}")
            return False
        finally:
            if mem:
                # 删去申请的地址
                kernel32.VirtualFreeEx(h_proc, mem, 0, 0x8000)
            #关闭句柄
            kernel32.CloseHandle(h_proc)


    # 刷新函数
    def refresh_desktop(self):
        if not self.desktop_sv:
            self.get_desktop_info()
        if self.desktop_sv:
            user32.PostMessageW(self.desktop_sv, 0x0111, 0x7402, 0)

    # 点击查询函数
    def onclick(self, x, y, button, pressed):
        if not self.enabled: return
        if button == mouse.Button.left and pressed:
            now = time.time()
            # 点击事件处理
            if now - self.last_click_time < self.click_time_threshold:
                self.click_queue.put((int(x),int(y)))
                self.last_click_time = 0
            else:
                self.last_click_time = now