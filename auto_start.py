import winreg
import sys
import os
import logging


APP_NAME = "DesktopIconHelper"

   # 获取启动程序的完整命令
def get_app_command():
    # 获取可执行文件路径
    if getattr(sys, 'frozen', False):
        # 如果是exe
        path = sys.executable
        return f'"{path}"'
    else:
        # 如果是python脚本
        python_exe = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        return f'"{python_exe}" "{script_path}"'

def enable_auto_start():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"  # 写入注册表
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_app_command())
        winreg.CloseKey(key)
        logging.error("成功写入启动注册表")
        return True
    except Exception as e:
        logging.error(f"写入启动注册表失败：{e}")
        return False

def disable_auto_start():
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"  #从注册表删除
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass      
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"关闭自启动失败: {e}")
        return False

def is_auto_start_enabled():
    """检查状态"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except:
        return False