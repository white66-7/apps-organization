import tkinter as tk
from tkinter import ttk 

class SettingsWindow:
    def __init__(self,engine):
        self.engine = engine
        self.root = None
        self.icon_path = "resources/icon.ico"

    def _create_window(self):
        self.root = tk.Tk()
        self.root.title("设置")
        self.root.geometry("640x480")
        try:
            self.root.iconbitmap(self.icon_path)
        except:
            pass

        # 禁止改变高度和宽度
        self.root.resizable(False,False)
        # 关闭窗口关联函数
        self.root.protocol('WM_DELETE_WINDOW', self.hide)

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH,expand=True)


        ttk.Label(frame,text="设置",font=("Microsoft YaHei",12,"bold")).pack(pady=(0,10))

        # 开关
        self.enabled_var = tk.BooleanVar(value=self.engine.enabled)
        ttk.Checkbutton(frame,text="开启双击隐藏",variable=self.enabled_var,
                        command=self.update_engine_status).pack(pady=5)

        ttk.Label(frame, text="程序正在后台运行", foreground="gray").pack(pady=10)

        ttk.Button(frame,text="彻底退出程序",command=self.engine.app_quit_callback).pack(side=tk.BOTTOM)

        self.root.attributes("-topmost", False)
        
    def show(self):
        if self.root is None:
            self._create_window()
            self.root.mainloop()
        else:
            self.root.after(0, self._force_focus)


    def _force_focus(self):
        if self.root:
            self.root.deiconify()
            self.root.state("normal")
            self.root.lift()
            self.root.focus_force()

            self.root.attributes("-topmost",True)
            self.root.after(10, lambda: self.root.attributes("-topmost",False))


    def update_engine_status(self):
        self.engine.enabled = self.enabled_var.get()

        
    def hide(self):
        if self.root:
            self.root.withdraw()

    def destroy(self):
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None