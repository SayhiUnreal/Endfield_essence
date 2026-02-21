"""
资源路径管理模块
处理打包后的资源路径问题
"""

import os
import sys

def resource_path(relative_path):
    """
    获取资源的绝对路径，兼容 PyInstaller 打包后的环境
    
    原理：PyInstaller 打包后会将资源文件解压到临时目录，
    sys._MEIPASS 指向这个临时目录。开发环境下直接返回相对路径。
    
    Args:
        relative_path: 相对路径
        
    Returns:
        资源的绝对路径
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)