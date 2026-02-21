"""
管理员权限管理模块
"""

import ctypes
import sys
import os

def run_as_admin():
    """
    检查并请求管理员权限
    
    原理：某些操作（如后台截图、模拟点击）需要管理员权限。
    如果当前不是管理员，会通过 ShellExecute 以管理员身份重启程序。
    
    Returns:
        True: 已经是管理员权限
        False: 请求管理员权限后退出当前进程
    """
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return True
            
        # 不是管理员，请求提升权限
        executable = sys.executable
        script = os.path.abspath(sys.argv[0])
        
        # 使用 ShellExecute 以管理员身份运行
        ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas",  # runas 表示以管理员身份运行
            executable, 
            script, 
            None, 
            1  # SW_SHOWNORMAL
        )
        return False
        
    except Exception as e:
        print(f"请求管理员权限失败: {e}")
        # 如果请求失败，询问是否继续
        try:
            response = input("无法获取管理员权限，是否以普通用户模式运行？(y/n): ")
            if response.lower() == 'y':
                return True
        except:
            pass
        return False

def set_dpi_aware():
    """设置DPI感知，确保在高DPI屏幕上坐标正确"""
    try:
        # Windows 8.1+ 的 DPI 感知设置
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        try:
            # Windows Vista/7 的 DPI 感知设置
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass