from pynput import mouse

class DesktopEngine:
    def __init__(self):
        self.clicks = []

    def start(self):
        self.listener = mouse.Listener(on_click=self.onclick)
        self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()