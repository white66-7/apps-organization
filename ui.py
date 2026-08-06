import tkinter as tk
from tkinter import ttk 

class SettingsWindow:
    def __init__(self,engine):
        self.engine = engine
        self.root = None

    def show(self):
        if self.root:
            self.root.deiconify()
            self.root.lift()
            return
        self.root = tk.Tk()
        self.root.title("设置")
        self.root.geometry("640x480")
        # 禁止改变高度和宽度
        self.root.resizable(False,False)
        # 关闭窗口关联函数
        self.root.protocol('WM_DELETE_WINDOW', self.hide)

        frame = ttk.Frame(self.root, padding="20")

        ttk.Label(frame,text="设置",font=("289-上首江湖书法体",12,"bold")).pack(pady=(0,10))

        # 开关
        self.enabled_var = tk.BooleanVar(value=self.engine.enabled)
        ttk.Checkbutton(frame,text="开启双击隐藏",variable=self.enabled_var,
                        command=self.update_engine_status).pack(pady=5)

        ttk.Label(frame, text="程序正在后台运行", foreground="gray", font=("289-上首江湖书法体", 9)).pack(pady=10)

        self.root.mainloop()

    def update_engine_status(self):
        self.engine.enabled = self.enabled_var.get()

        
    def hide(self):
        if self.root:
            self.root.withdraw()