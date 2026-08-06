from ui import SettingsWindow
from engine import DesktopEngine
import pystray
import threading
import os


class DesktopAPP:
    def __init__(self):
        self.engine = DesktopEngine()
        self.ui = SettingsWindow(self.engine)
        self.icon = "resources/icon.ico"
    def run(self):
        # 主监视引擎
        self.engine.start()

        # 创造托盘图标
        def setup_tray():
            menu = pystray.Menu(
                pystray.MenuItem('设置'),
                pystray.MenuItem('手动切换'),
                pystray.MenuItem('退出'),
            )
            self.icon = pystray.Icon('DesktopHelper',self.icon,'mouse42',menu)
            self.icon.run()
        tray_thread = threading.Thread(target=setup_tray,daemon=True)
        tray_thread.start()

        #主设置界面-图形化界面
        self.ui.show()

    def quit_all(self,icon=None,item=None):
        self.engine.stop()
        if self.icon:
            self.icon.stop()
        os._exit(0)
        


if __name__ == "__main__":
    app = DesktopAPP()
    app.run()