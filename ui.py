import tkinter as tk
from tkinter import ttk 
from auto_start import enable_auto_start, disable_auto_start,is_auto_start_enabled
import logging

class SettingsWindow:
    def __init__(self, engine, icon_path="resources/icon.ico"):
        self.engine = engine
        self.root = None
        self.icon_path = icon_path

    def _create_window(self):
        self.root = tk.Tk()
        self.root.withdraw() 
        self.root.title("设置")
        self.root.geometry("440x275")
        try:
            self.root.iconbitmap(self.icon_path)
        except:
            pass

        # 禁止改变高度和宽度
        self.root.resizable(False,False)
        # 关闭窗口关联函数
        self.root.protocol('WM_DELETE_WINDOW', self.hide)

        frame = ttk.Frame(self.root, padding="5")
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
        self.time_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.time_val_label = ttk.Label(time_frame, text=f"{self.time_var.get():.2f}s")
        self.time_val_label.pack(side=tk.RIGHT)


        ttk.Separator(frame, orient='horizontal').pack(fill='x', pady=10)

        
        content_box = ttk.Frame(frame)
        content_box.pack(fill=tk.X, pady=5)

        left_side = ttk.Frame(content_box)
        left_side.pack(side=tk.LEFT, fill=tk.Y)

        #开机自启动开关
        self.auto_start_var = tk.BooleanVar(value=is_auto_start_enabled())

        ttk.Checkbutton(left_side, text="开机自动启动", variable=self.auto_start_var,
                        command=self.update_auto_start_status).pack(pady=5, anchor="w")

        # 开关
        self.enabled_var = tk.BooleanVar(value=self.engine.enabled)
        ttk.Checkbutton(left_side,text="开启双击隐藏",variable=self.enabled_var,
                        command=self.update_engine_status).pack(pady=5,anchor="w")

        self.anim_var = tk.BooleanVar(value=self.engine.animation_enabled)
        ttk.Checkbutton(left_side, text="开启淡出动画效果", variable=self.anim_var,
                        command=self.update_animation_status).pack(pady=5, anchor="w")

        ttk.Label(frame, text="程序正在后台运行", foreground="gray").pack(side="bottom")

        right_side = ttk.Frame(content_box)
        right_side.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))

        btn_style = {"width": 18}

        self.log_btn_var = tk.StringVar()
        self.update_log_info_display() # 初始化文字

        self.btn_view_log = ttk.Button(
            right_side, 
            textvariable=self.log_btn_var, #绑定变量
            command=self.engine.open_dir, 
            **btn_style
        )
        self.btn_view_log.pack(pady=4)

        ttk.Button(
            right_side, 
            text="清空运行日志", 
            command=self.handle_clear_log, # 调用包装后的函数
            **btn_style
        ).pack(pady=4)

        ttk.Button(right_side,text="彻底退出程序",command=self.engine.app_quit_callback,**btn_style).pack(fill=tk.X,pady=4)

        
        self.root.attributes("-topmost", False)


    def update_log_info_display(self):
        """更新按钮上显示的日志大小"""
        size_str = self.engine.get_log_size_str()
        self.log_btn_var.set(f"查看运行日志 ({size_str})")

    def handle_clear_log(self):
        """清空日志并立即刷新显示"""
        self.engine.clear_log()
        # 给系统一点点响应时间后刷新
        self.root.after(100, self.update_log_info_display)

    def show(self):
        if self.root is None:
            self._create_window()
            self.root.mainloop()
        else:
            self.update_log_info_display()
            self.root.after(0, self._force_focus)

    def init_hidden(self):
        """新增：初始化但不显示窗口，仅启动 mainloop"""
        if self.root is None:
            self._create_window()
            self.root.withdraw() # 立即隐藏
            self.root.mainloop()

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


    def update_animation_status(self):
        self.engine.animation_enabled = self.anim_var.get()
        logging.info(f"用户更改动画设置: {self.engine.animation_enabled}")

    def update_time_value(self, val):
        try:
            float_val = float(val)
            # 更新界面显示
            self.time_val_label.config(text=f"{float_val:.2f}s")
            # 更新引擎中的数值
            self.engine.click_time_threshold = float_val
            logging.debug(f"双击阈值调整为: {float_val}s")
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