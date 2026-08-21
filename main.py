from ui import SettingsWindow
from engine import DesktopEngine
import pystray
import threading
import sys
import os
from PIL import Image
import ctypes
import logging
from logging.handlers import RotatingFileHandler 
import socket


# 定义一个唯一的端口号
INSTANCE_PORT = 49542

def wake_up_existing_instance():
    """尝试连接已有的实例并发送唤醒信号"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            s.connect(('127.0.0.1', INSTANCE_PORT))
            s.sendall(b"show_ui")
        return True
    except:
        return False

def start_instance_listener(app_instance):
    """后台线程：监听来自新实例的唤醒信号"""
    def _listen():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', INSTANCE_PORT))
                s.listen(1)
                while True:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024)
                        if data == b"show_ui":
                            # 使用 after 确保在 Tkinter 主线程中执行 UI 操作
                            root = getattr(app_instance.ui, "root", None)
                            if root is not None:
                                root.after(0, app_instance.show_ui)
                            else:
                                # root 尚未创建（启动初期竞态的极端情况），直接显示
                                app_instance.show_ui()
        except Exception as e:
            logging.error(f"单实例监听服务启动失败: {e}")

    threading.Thread(target=_listen, daemon=True).start()

def get_log_path():
    """获取日志及数据目录的完整路径（位于 %APPDATA%）"""
    appdata = os.getenv('APPDATA')
    if not appdata:
        appdata = os.path.expanduser('~\\AppData\\Roaming')  # 兜底
    data_dir = os.path.join(appdata, "DesktopHelper")
    try:
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
    except Exception as e:
        data_dir = os.getcwd()  # 无法创建时退回当前目录，避免程序崩溃
        logging.error(f"创建数据目录失败，已退回当前目录: {e}")
    
    # 保持你的日志文件名
    log_path = os.path.join(data_dir, "日志.log")
    return data_dir, log_path

DATA_DIR, LOG_PATH = get_log_path()

def resource_path(relative_path):
    """ 获取资源绝对路径 """
    try:
        # PyInstaller 创建临时文件夹并把路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境下，使用当前文件所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)

def setup_logging():
    # 文件处理器（始终保留）
    file_handler = RotatingFileHandler(
        LOG_PATH, 
        maxBytes=1*1024*1024, 
        backupCount=1, 
        encoding='utf-8'
    )
    handlers = [file_handler]
    # 仅在非打包环境添加控制台输出
    if not getattr(sys, 'frozen', False):
        handlers.append(logging.StreamHandler())
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=handlers
    )


class DesktopAPP:
    def __init__(self):
        myappid = 'mycompany.desktophelper.subversion.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.engine = DesktopEngine(log_path=LOG_PATH, data_dir=DATA_DIR)
        self.engine.app_quit_callback = self.quit_all
        self.icon_path = resource_path("resources/icon.ico")
        self.ui = SettingsWindow(self.engine, icon_path=self.icon_path)
        self.tray_icon = None



    # 创造托盘图标
    def setup_tray(self):
        try:
            image = Image.open(self.icon_path)
        except:
            image = Image.new('RGB', (64, 64), color=(73, 109, 137))

            
        menu = pystray.Menu(
            pystray.MenuItem('设置', self.show_ui,default=True),
            pystray.MenuItem('手动刷新', lambda: self.engine.refresh_desktop()),
            pystray.MenuItem('退出', self.quit_all),
            )
        self.tray_icon = pystray.Icon('DesktopHelper', image, '桌面助手', menu,
                                      on_activate=self.show_ui)

        self.tray_icon.run()

    def run(self):
        # 主监视引擎
        self.engine.start()


        tray_thread = threading.Thread(target=self.setup_tray,daemon=True)
        tray_thread.start()

        #主设置界面-图形化界面
        self.ui.init_hidden()



    def show_ui(self,icon=None,item=None):
        if self.ui:
            self.ui.show()   # show() 内部已线程安全地调度到 Tk 主线程


    def quit_all(self,icon=None,item=None):
        self.engine.stop()
        logging.info("收到退出信号，正在关闭程序...")
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception as e:
                logging.error(f"停止托盘异常: {e}")
        # 无论从托盘线程还是 UI 主线程调用，都确保真正退出进程。
        # sys.exit 在非主线程中只会终止当前线程，无法结束整个进程。
        os._exit(0)
        


if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        # 获取 EXE 所在的目录
        current_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 获取脚本所在的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))

    # 强制将工作目录切换到程序所在目录
    os.chdir(current_dir)

    if wake_up_existing_instance():
        logging.info("程序已运行，正在唤醒原窗口...")
        sys.exit(0)


    setup_logging()
    

    logging.info("程序启动...")

    app = DesktopAPP()

    start_instance_listener(app)

    app.run()