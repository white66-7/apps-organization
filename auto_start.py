import winreg
import sys
import os
import logging


APP_NAME = "DesktopIconHelper42"

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
        logging.info("已写入开机自启动注册表")
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
        logging.error(f"关闭自启动失败: {e}")
        return False

def is_auto_start_enabled():
    """检查开机自启是否已启用（基于注册表真实状态）

    返回 True/False；当遇到权限等 IO 异常时返回 None（状态未知），
    避免把“查询失败”误报成“已关闭”。"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            found = True
        except FileNotFoundError:
            found = False
        finally:
            winreg.CloseKey(key)
        return found
    except FileNotFoundError:
        # Run 键本身不存在 → 必然未启用
        return False
    except OSError as e:
        logging.error(f"查询开机自启状态失败: {e}")
        return None