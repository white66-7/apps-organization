from pynput import mouse
import ctypes
import ctypes.wintypes
import time
import threading
from queue import Queue
import logging
import os

user32 = ctypes.windll.user32    # 窗口管理dll
kernel32 = ctypes.windll.kernel32  # 进程管理dll

gdi32 = ctypes.windll.gdi32 # 新增：绘图库

# 新增窗口回调函数类型定义
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.wintypes.HWND, ctypes.wintypes.UINT, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)

# 新增绘图相关结构体
class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [("hdc", ctypes.wintypes.HDC), ("fErase", ctypes.wintypes.BOOL), ("rcPaint", RECT), 
                ("fRestore", ctypes.wintypes.BOOL), ("fIncUpdate", ctypes.wintypes.BOOL), ("rgbReserved", ctypes.c_byte * 32)]

class WNDCLASSW(ctypes.Structure):
    _fields_ = [("style", ctypes.wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int), 
                ("cbWndExtra", ctypes.c_int), ("hInstance", ctypes.wintypes.HINSTANCE), ("hIcon", ctypes.wintypes.HICON),
                ("hCursor", ctypes.wintypes.HANDLE), ("hbrBackground", ctypes.wintypes.HBRUSH),
                ("lpszMenuName", ctypes.wintypes.LPCWSTR), ("lpszClassName", ctypes.wintypes.LPCWSTR)]


class POINT(ctypes.Structure):
    _fields_ = [("x",ctypes.wintypes.LONG),("y",ctypes.wintypes.LONG)]

class DesktopEngine:
    def __init__(self,log_path, data_dir):
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

        self.animation_enabled = True

        self.fade_steps = 15      # 动画帧数
        self.is_animating = False # 防止动画冲突
        self.registered = False   # 窗口类注册标志
        self.hdc_mem = 0          # 内存画板
        self.v_w = 0              # 屏幕宽
        self.v_h = 0              # 屏幕高
        
        # 保持对回调函数的引用，防止被 Python 垃圾回收导致崩溃
        self.wnd_proc_delegate = WNDPROC(self._static_wnd_proc)

        self.log_path = log_path
        self.data_dir = data_dir
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
                        logging.info(f"成功获取桌面句柄: LV={hex(lv)}, PID={self.explorer_pid}")
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
        # 新增：释放绘图资源
        if self.hdc_mem:
            gdi32.DeleteDC(self.hdc_mem)
            self.hdc_mem = 0

    def _worker_loop(self):
        """后台逻辑处理线程"""
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

                # PID 校验
                if t_pid.value == self.explorer_pid:
                    buf = ctypes.create_unicode_buffer(256)
                    user32.GetClassNameW(target, buf, 256)
                    if buf.value in ["SysListView32", "SHELLDLL_DefView", "WorkerW", "Progman"]:
                        # 图标校验
                        if not self.is_on_icon(x, y):
                            if self.animation_enabled:
                                threading.Thread(target=self.run_fade_animation, daemon=True).start()
                            else:
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
            logging.error(f"Engine Error: {e}",exc_info=True)
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

    def _static_wnd_proc(self, hwnd, msg, wp, lp):
        """遮罩窗口的绘图回调"""
        if msg == 0x000F: # WM_PAINT
            ps = PAINTSTRUCT()
            hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
            if self.hdc_mem:
                # 将截好的屏幕图贴到遮罩窗口上
                gdi32.BitBlt(hdc, 0, 0, self.v_w, self.v_h, self.hdc_mem, 0, 0, 0x00CC0020)
            user32.EndPaint(hwnd, ctypes.byref(ps))
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    def run_fade_animation(self):
        """核心动画流程"""
        if self.is_animating: return
        self.is_animating = True
        
        # 获取全屏尺寸（支持多屏）
        v_left = user32.GetSystemMetrics(76)
        v_top = user32.GetSystemMetrics(77)
        self.v_w = user32.GetSystemMetrics(78)
        self.v_h = user32.GetSystemMetrics(79)
        
        try:
            # 1. 抓取切换前的屏幕快照
            hdc_screen = user32.GetDC(0)
            if not self.hdc_mem:
                self.hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            
            new_hbm = gdi32.CreateCompatibleBitmap(hdc_screen, self.v_w, self.v_h)
            old_hbm = gdi32.SelectObject(self.hdc_mem, new_hbm)
            if old_hbm: gdi32.DeleteObject(old_hbm)
            
            gdi32.BitBlt(self.hdc_mem, 0, 0, self.v_w, self.v_h, hdc_screen, v_left, v_top, 0x00CC0020)
            user32.ReleaseDC(0, hdc_screen)

            # 2. 注册并创建全屏遮罩窗口
            cls_name = "DesktopFadeMask"
            if not self.registered:
                wc = WNDCLASSW()
                wc.lpfnWndProc = self.wnd_proc_delegate
                wc.lpszClassName = cls_name
                wc.hInstance = kernel32.GetModuleHandleW(None)
                wc.hCursor = user32.LoadCursorW(0, 32512)
                user32.RegisterClassW(ctypes.byref(wc))
                self.registered = True

            hwnd_mask = user32.CreateWindowExW(
                0x80000 | 0x8 | 0x20 | 0x80, # WS_EX_LAYERED | TOPMOST | TRANSPARENT
                cls_name, None, 0x80000000, 
                v_left, v_top, self.v_w, self.v_h, 0, 0, kernel32.GetModuleHandleW(None), 0
            )
            
            user32.SetLayeredWindowAttributes(hwnd_mask, 0, 255, 0x2)
            user32.ShowWindow(hwnd_mask, 5)
            user32.UpdateWindow(hwnd_mask) # 强制立即显示截图
            time.sleep(0.01) # 微小停顿确保视觉覆盖

            # 3. 此时屏幕已被截图遮盖，现在静默切换真实的图标显隐
            self.refresh_desktop()

            # 4. 遮罩层平滑淡出，露出下方切换后的桌面
            for i in range(self.fade_steps):
                alpha = int(255 * (1 - (i / self.fade_steps)**2))
                user32.SetLayeredWindowAttributes(hwnd_mask, 0, max(0, alpha), 0x2)
                
                # 维持窗口消息循环，防止白屏
                msg = ctypes.wintypes.MSG()
                while user32.PeekMessageW(ctypes.byref(msg), hwnd_mask, 0, 0, 1):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.01)
            
            user32.DestroyWindow(hwnd_mask)
            
        finally:
            self.is_animating = False

    def get_log_size_str(self):
        """获取日志文件大小"""
        if not os.path.exists(self.log_path):
            return "0 B"
        try:
            size_bytes = os.path.getsize(self.log_path)
            if size_bytes < 1024:
                return f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                return f"{size_bytes / 1024:.1f} KB"
            else:
                return f"{size_bytes / (1024 * 1024):.1f} MB"
        except:
            return "未知"

    def open_dir(self):
        def _async_open():
            try:
                if os.path.exists(self.log_path) and os.path.getsize(self.log_path) > 0:
                    # 直接用记事本打开日志文件
                    os.startfile(self.log_path)
                else:
                    # 如果文件没生成，打开当前程序所在的文件夹
                    os.startfile(self.data_dir)
            except Exception as e:
                logging.error(f"无法打开日志文件: {e}")
        threading.Thread(target=_async_open, daemon=True).start()


    def clear_log(self):
        """清空日志内容"""
        def _async_clear():
            try:
                # truncate 是稳妥的
                with open(self.log_path, 'w', encoding='utf-8') as f:
                    f.truncate()
            except Exception as e:
                logging.error(f"清空日志失败: {e}")
        
        threading.Thread(target=_async_clear, daemon=True).start()