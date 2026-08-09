import tkinter as tk
from tkinter import ttk 
from auto_start import enable_auto_start, disable_auto_start,is_auto_start_enabled


class SettingsWindow:
    def __init__(self, engine, icon_path="resources/icon.ico"):
        self.engine = engine
        self.root = None
        self.icon_path = icon_path

    def _create_window(self):
        self.root = tk.Tk()
        self.root.title("设置")
        self.root.geometry("400x350")
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

        ttk.Label(frame, text="双击判定时间 (秒):").pack(pady=(15, 0), anchor="w")
        
        #时间条
        time_frame = ttk.Frame(frame)
        time_frame.pack(fill=tk.X, pady=5)
        self.time_var = tk.DoubleVar(value=self.engine.click_time_threshold)
        self.time_scale = tk.Scale(
            time_frame, 
            from_=0.1, 
            to_=1.0, 
            resolution=0.01,    # 允许小数
            variable=self.time_var, 
            orient=tk.HORIZONTAL,
            showvalue=0,        # 隐藏自带数值
            command=self.update_time_value,
            bg="#f0f0f0",       # 匹配背景颜色
            highlightthickness=0,
            borderwidth=1
        )
        self.time_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.time_val_label = ttk.Label(time_frame, text=f"{self.time_var.get():.2f}s")
        self.time_val_label.pack(side=tk.RIGHT)


        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=20)

        ttk.Label(frame,text="设置",font=("Microsoft YaHei",12,"bold")).pack(pady=(0,10))

        #开机自启动开关
        self.auto_start_var = tk.BooleanVar(value=is_auto_start_enabled())
        ttk.Checkbutton(frame, text="开机自动启动", variable=self.auto_start_var,
                        command=self.update_auto_start_status).pack(pady=5, anchor="w")

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


    def update_time_value(self, val):
        try:
            float_val = float(val)
            # 更新界面显示
            self.time_val_label.config(text=f"{float_val:.2f}s")
            # 更新引擎中的数值
            self.engine.click_time_threshold = float_val
        except:
            pass

    # UI复选框点击时触发
    def update_auto_start_status(self):
        if self.auto_start_var.get():
            enable_auto_start()
        else:
            disable_auto_start()

    def hide(self):
        if self.root:
            self.root.withdraw()

    def destroy(self):
        if self.root:
            self.root.quit()
            self.root.destroy()
            self.root = None