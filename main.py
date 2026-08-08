from ui import SettingsWindow
from engine import DesktopEngine
import pystray
import threading
import sys
from PIL import Image
import ctypes


class DesktopAPP:
    def __init__(self):
        myappid = 'mycompany.desktophelper.subversion.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.engine = DesktopEngine()
        self.engine.app_quit_callback = self.quit_all
        self.ui = SettingsWindow(self.engine)
        self.icon_path = "resources/icon.ico"
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
        self.ui.show()



    def show_ui(self,icon=None,item=None):
        if self.ui:
            self.ui.show()


    def quit_all(self,icon=None,item=None):
        self.engine.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        if hasattr(self,'ui') and self.ui:
            self.ui.destroy()
        sys.exit(0)
        

if __name__ == "__main__":
    import os
    import sys
    if getattr(sys, 'frozen', False):
        # 获取 EXE 所在的目录
        current_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 获取脚本所在的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 强制将工作目录切换到程序所在目录
    os.chdir(current_dir)
    app = DesktopAPP()
    app.run()