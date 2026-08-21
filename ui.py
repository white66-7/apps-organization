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

        #开机自启动开关（初值先给 False，随后由 poller 在后台异步校准真实注册表状态，避免启动卡顿）
        initial = is_auto_start_enabled()
        self.auto_start_var = tk.BooleanVar(value=bool(initial))

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

        # 启动“实时同步”轮询：定时回读自启动与日志状态，消除界面滞后
        self.poller_after_id = None
        self._start_poller()


    def update_log_info_display(self):
        """更新按钮上显示的日志大小（poller 会定时调用，需容忍控件未就绪）"""
        if not hasattr(self, 'log_btn_var'):
            return
        try:
            size_str = self.engine.get_log_size_str()
            self.log_btn_var.set(f"查看运行日志 ({size_str})")
        except Exception as e:
            logging.debug(f"刷新日志显示失败: {e}")

    def handle_clear_log(self):
        """清空日志并立即刷新显示"""
        self.engine.clear_log()
        # 给系统一点点响应时间后刷新
        self.root.after(100, self.update_log_info_display)

    def show(self):
        """线程安全的显示入口：把真正的工作调度到 Tk 主线程执行。

        本方法可能从托盘线程、套接字监听线程或 Tk 主线程被调用。
        Tkinter 非线程安全，任何对控件/root 的访问都应回到主线程，
        这里统一通过 after 委托给 show_sync。
        """
        if self.root is None:
            return  # 罕见竞态：拒绝在非主线程创建窗口，由 init_hidden 兜底
        try:
            self.root.after(0, self.show_sync)
        except Exception as e:
            logging.error(f"调度显示窗口失败: {e}")

    def show_sync(self):
        """必须在 Tk 主线程内调用：显示窗口，必要时先创建。"""
        if self.root is None:
            self._create_window()
            self.root.deiconify()
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

    # UI复选框点击时触发：执行写入后回读注册表，用真实结果校准勾选状态
    def update_auto_start_status(self):
        want = self.auto_start_var.get()
        try:
            ok = enable_auto_start() if want else disable_auto_start()
            if not ok:
                logging.error("自启动开关写入注册表失败")
        except Exception as e:
            ok = False
            logging.error(f"自启动开关操作异常: {e}")
        # 回读注册表真实状态并据此强制校正勾选，避免界面与实际情况脱节
        self.root.after(0, lambda: self._apply_auto_start_state(force=not ok))

    def _apply_auto_start_state(self, force=False):
        """把自启动实际注册表状态同步到复选框。force=True 时无条件强制校正。"""
        if not self.root or not hasattr(self, 'auto_start_var'):
            return
        state = is_auto_start_enabled()
        checked = self.auto_start_var.get()
        if force or state is not None and bool(state) != checked:
            # 仅当用户没有正在操作开关时自动纠正
            actual = True if state is True else False
            if actual != checked:
                self.auto_start_var.set(actual)
                logging.info(f"开机自启动状态已同步为: {'启用' if actual else '关闭'}")

    def _start_poller(self):
        """启动主线程内的定时轮询，实时同步自启动与日志状态。"""
        self._poll_tick()

    def _poll_tick(self):
        if not self.root:
            return
        try:
            # 回读自启动状态（异步校正，不阻塞）
            self._apply_auto_start_state(force=False)
            # 实时刷新日志大小显示
            self.update_log_info_display()
        except Exception as e:
            logging.debug(f"实时同步刷新失败: {e}")
        # 每隔 2 秒再同步一次
        try:
            self.poller_after_id = self.root.after(2000, self._poll_tick)
        except Exception:
            self.poller_after_id = None

    def hide(self):
        if self.root:
            self.root.withdraw()

    def destroy(self):
        if self.root:
            poller_id = getattr(self, 'poller_after_id', None)
            if poller_id is not None:
                try:
                    self.root.after_cancel(poller_id)
                except Exception:
                    pass
            self.poller_after_id = None
            self.root.quit()
            self.root.destroy()
            self.root = None