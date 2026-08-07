from ui import SettingsWindow
from engine import DesktopEngine
import pystray
import threading
import os
from PIL import Image
import ctypes


class DesktopAPP:
    def __init__(self):
        myappid = 'mycompany.desktophelper.subversion.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        self.engine = DesktopEngine()
        self.ui = SettingsWindow(self.engine)
        self.icon_path = "resources/icon.ico"
        self.tray_icon = None

    def run(self):
        # 主监视引擎
        self.engine.start()

        # 创造托盘图标
        def setup_tray():
            image = Image.open(self.icon_path)
            menu = pystray.Menu(
                pystray.MenuItem('设置', lambda: self.ui.show()),
                pystray.MenuItem('手动切换', lambda: threading.Thread(target=self.engine.run_fade_animation).start()),
                pystray.MenuItem('退出', self.quit_all),
            )
            self.tray_icon = pystray.Icon('DesktopHelper', image, '桌面助手', menu)
            self.tray_icon.run()
        tray_thread = threading.Thread(target=setup_tray,daemon=True)
        tray_thread.start()

        #主设置界面-图形化界面
        self.ui.show()

    def quit_all(self,icon=None,item=None):
        self.engine.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        os._exit(0)
        

if __name__ == "__main__":
    app = DesktopAPP()
    app.run()