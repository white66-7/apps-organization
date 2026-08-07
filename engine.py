from pynput import mouse
import ctypes
import ctypes.wintypes
import time
import threading

user32 = ctypes.windll.user32    # 窗口管理dll
kernel32 = ctypes.windll.kernel32  # 进程管理dll


class POINT(ctypes.Structure):
    _fields_ = [("x",ctypes.wintypes.LONG),("y",ctypes.wintypes.LONG)]


class DesktopEngine:
    def __init__(self):
        self.clicks = []
        self.enabled = True
        self.listener = None
        self.app_quit_callback = None

    #前置判断
    def get_deskop_handles(self):
        for root in ["Progman","WorkerW"]:
            hwnd = user32.FindWindowW(root,None)
            while hwnd:
                # 拿桌面视图权限
                sv = user32.FindWindowExW(hwnd,0,"SHELLDLL_DefView",None)
                if sv:
                    # 拿程序选中，刷新权限
                    lv = user32.FindWindowExW(sv, 0, 'SysListView32',None)
                    return sv, lv
                # 继续找下一个
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

    # 图标判断函数
    def is_on_icon(self, x, y):
        # 只要第二个值lv
        _, lv = self.get_deskop_handles()

        # 判断是否拿到与可见
        if not lv or not user32.IsWindowVisible(lv):
            return False
            
        # 判断点击位置是否在图标区域
        target_hwnd = user32.WindowFromPoint(POINT(int(x), int(y)))
        if target_hwnd != lv:
            return False

        # 查询explore.exe进程判断是否确实点击某个图标
        pid = ctypes.wintypes.DWORD()    # 创建unsigned long对象
        user32.GetWindowThreadProcessId(lv, ctypes.byref(pid))  # SysListView32的explore.exe进程ID写在pid地址里

        # 通过pid拿到explore.exe句柄
        h_proc = kernel32.OpenProcess(0x0038, False, pid) 

        #权限不足或没拿到直接退出
        if not h_proc:
            return False
            
        mem = None
        try:
            mem = kernel32.VirtualAllocEx(h_proc, None, 16, 0x1000, 0x04) # 在explore.exe申请16字节的地址
            if not mem: return False
            
            pt = POINT(int(x), int(y))
            user32.ScreenToClient(lv, ctypes.byref(pt))  #绝对坐标转为相对坐标

            #测试点击位置
            kernel32.WriteProcessMemory(h_proc, mem, ctypes.byref(pt), 8, None)

            res = user32.SendMessageW(lv, 0x1012, 0, mem) 
            return res != -1
        
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
        sv, _ = self.get_deskop_handles()
        if sv:
            user32.PostMessageW(sv, 0x0111, 0x7402, 0)

    # 点击查询函数
    def onclick(self, x, y, button, pressed):
        if not self.enabled: return
        if button == mouse.Button.left and pressed:
            now = time.time()
            # 点击事件处理
            self.clicks = [t for t in self.clicks if now - t < 0.4]
            self.clicks.append(now)
            
            if len(self.clicks) >= 2:
                # 检测点击区域是否为桌面窗口相关类名
                target = user32.WindowFromPoint(POINT(int(x), int(y)))
                buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(target, buf, 256)
                
                if buf.value in ["SysListView32", "SHELLDLL_DefView", "WorkerW", "Progman"]:
                    # 检验是否点击图标
                    if not self.is_on_icon(x, y):
                        threading.Thread(target=self.refresh_desktop).start()
                # 刷新检测数据
                self.clicks = []