from pynput import mouse

class DesktopEngine:
    def __init__(self):
        self.clicks = []
        self.enabled = True

    def start(self):
        self.listener = mouse.Listener(on_click=self.onclick)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()

    def onclick(self, x, y, button, pressed):
        pass