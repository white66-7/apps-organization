import winreg
import sys
import os
import logging


APP_NAME = "DesktopIconHelper42"
LEGACY_APP_NAME = "DesktopIconHelper"   

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"


# 获取启动程序的完整命令
def get_app_command():
    # 获取可执行文件路径
    if getattr(sys, "frozen", False):
        # 如果是exe
        path = sys.executable
        return f'"{path}"'
    else:
        # 如果是python脚本
        python_exe = sys.executable
        script_path = os.path.abspath(sys.argv[0])
        return f'"{python_exe}" "{script_path}"'


def get_current_exe_path():
    """当前正在运行的（或将被启动的）可执行文件路径，用于校验自启动是否指向自身。"""
    return sys.executable


def _first_command_target(cmdline):
    """从启动命令行中提取第一个程序路径，用于校验目标是否仍存在。

    兼容带引号 / 不带引号，以及 “python.exe \"脚本.py\"” 这类多段命令
    （多段命令不能整体当成一个路径去 os.path.exists，否则必然误判为不存在）。
    """
    if not cmdline:
        return None
    import re
    m = re.match(r'\s*"([^"]+)"', cmdline)
    if m:
        return m.group(1)
    m = re.match(r'\s*(\S+)', cmdline)
    return m.group(1) if m else None


def _set_startup_approved(enabled):
    """写入 StartupApproved\\Run 的启用/禁用标记（Task Manager 与登录时以它为准）。

    Windows 状态字节的真实语义（注意与常见误解相反）：
      - 0x02 / 0x06 = 已启用；标准“启用”写法是 0x02 + 后 8 字节时间戳全 0
      - 0x03 / 0x07 = 已禁用；禁用时记录禁用时刻的 FILETIME
    若该值缺失，Windows 默认按“启用”处理。

    千万不要把 0x03 当成“启用”去写——那会让任务管理器显示“已禁用”且登录不启动，
    界面却仍显示已开启，正是历史上“UI 与实际不对应”的根因。
    """
    try:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0, winreg.KEY_SET_VALUE)
        except FileNotFoundError:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY)
        if enabled:
            # 标准“启用”标记：0x02 + 3 字节保留 + 8 字节时间戳（全 0）
            data = bytes([0x02]) + b"\x00\x00\x00" + b"\x00\x00\x00\x00\x00\x00\x00\x00"
        else:
            import struct, time as _time
            # 禁用标记：0x03 + 禁用时刻的 FILETIME（100ns 计数，自 1601-01-01）
            ft = int((_time.time() + 11644473600) * 10_000_000) & 0xFFFFFFFFFFFFFFFF
            data = bytes([0x03]) + b"\x00\x00\x00" + struct.pack("<Q", ft)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_BINARY, data)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logging.error(f"设置 StartupApproved 失败: {e}")
        return False


def _remove_startup_approved():
    """删除 StartupApproved\\Run 中本应用的标记。

    禁用自启动时 Run 值已删除，这里顺带清掉残留标记，
    避免任务管理器保留一条“已禁用”的幽灵启动项。
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        finally:
            winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        logging.error(f"清理 StartupApproved 失败: {e}")
        return False


def enable_auto_start():
    key_path = RUN_KEY
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_app_command())
        # 迁移：删除旧版本遗留的同应用注册表项，避免任务管理器出现重复的启动项
        try:
            winreg.DeleteValue(key, LEGACY_APP_NAME)
            logging.info(f"已清理旧版启动项 {LEGACY_APP_NAME}")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        # 同步 StartupApproved 为“启用”，确保任务管理器显示启用且登录真正生效
        _set_startup_approved(True)
        logging.info("已写入开机自启动注册表")
        return True
    except Exception as e:
        logging.error(f"写入启动注册表失败：{e}")
        return False


def disable_auto_start():
    key_path = RUN_KEY
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, APP_NAME)
        except FileNotFoundError:
            pass
        # 同时删除旧版遗留项，保持干净
        try:
            winreg.DeleteValue(key, LEGACY_APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        # 彻底清除 StartupApproved 残留：Run 已删除、批准标记也删掉，
        # 才是真正“关闭”，也不会留下任务管理器里的幽灵启动项
        _remove_startup_approved()
        return True
    except Exception as e:
        logging.error(f"关闭自启动失败: {e}")
        return False


def is_auto_start_enabled():
    """检查开机自启是否真正启用（以 Windows 实际生效的状态为准）。

    判定条件（全部满足才算启用）：
      1. Run 键里存在本应用（APP_NAME）的值；
      2. Run 值指向的程序路径仍然存在，避免把遗留的已删除路径误判为启用；
      3. StartupApproved 的标记不是“禁用”（首字节 0x03 / 0x07）；
         该标记缺失、或首字节为 0x02 / 0x06（启用）时保持启用（Windows 默认行为）。

    返回 True/False；遇到 IO 异常无法判断时返回 None（状态未知），
    避免把“查询失败”误报成“已禁用”。
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            found = True
        except FileNotFoundError:
            found = False
        finally:
            winreg.CloseKey(key)

        if not found:
            return False   # Run 中没有本应用 → 未启用

        # 条件2：Run 值指向的程序路径必须仍然存在，否则视为“死链”，不算启用。
        # 用 _first_command_target 提取第一个程序路径（兼容“python.exe \"main.py\"”多段命令），
        # 不能把整段命令当路径去判断，否则源码运行模式下必然误判为不存在。
        target = _first_command_target(val) if isinstance(val, str) else None
        if target and not os.path.exists(target):
            return False

        # 条件3：StartupApproved 若存在且首字节为 0x03 / 0x07（禁用），则按禁用处理。
        # 0x02 / 0x06（启用）、缺失、以及 0x00 等非明确禁用值都保持启用——
        # Windows 只会因 0x03 / 0x07 跳过该启动项。
        try:
            appr = winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY, 0, winreg.KEY_READ)
            try:
                bin_val, _ = winreg.QueryValueEx(appr, APP_NAME)
                if isinstance(bin_val, bytes) and len(bin_val) > 0 and bin_val[0] in (0x03, 0x07):
                    return False
            except FileNotFoundError:
                pass
            finally:
                winreg.CloseKey(appr)
        except FileNotFoundError:
            pass
        except OSError:
            pass

        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        logging.error(f"查询开机自启状态失败: {e}")
        return None
