from ui import SettingsWindow
from engine import DesktopEngine
import pystray

class DesktopAPP:
    def __init__(self):
        self.engine = DesktopEngine()
        self.ui = SettingsWindow(self.engine)
        self.icon = None
    def run(self):
        def setup_tray():
            menu = pystray.Menu(
                pystray.MenuItem('设置'),
                pystray.MenuItem('手动切换'),
                pystray.MenuItem('退出'),
            )
            self.icon = pystray.Icon('DesktopAPP',self.icon,menu)
            self.icon.run()


        


if __name__ == "__main__":
    app = DesktopAPP()