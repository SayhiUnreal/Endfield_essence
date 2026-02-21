"""
游戏窗口管理模块
处理窗口查找、位置获取等
"""

import win32gui
import pygetwindow as gw
import ctypes

class RECT(ctypes.Structure):
    """Windows RECT结构体"""
    _fields_ = [("left", ctypes.c_int), ("top", ctypes.c_int),
                ("right", ctypes.c_int), ("bottom", ctypes.c_int)]

class GameWindow:
    """游戏窗口管理器"""
    
    def __init__(self, logger=None):
        """
        初始化窗口管理器
        
        Args:
            logger: 日志记录器
        """
        self.logger = logger
        self.hwnd = None
        self.title = None
        self.window_rect = None
        
    def find_window(self):
        """查找游戏窗口"""
        try:
            # 获取所有窗口
            all_windows = gw.getAllWindows()
            
            # 精确匹配游戏窗口
            for window in all_windows:
                title = window.title
                # 游戏窗口标题通常是 "Endfield" 或 "终末地"，不包含其他字符
                if title and (title.strip() == 'Endfield' or title.strip() == '终末地'):
                    self.hwnd = window._hWnd
                    self.title = title
                    self.window_rect = win32gui.GetWindowRect(self.hwnd)
                    
                    if self.logger:
                        self.logger.log(f"找到游戏窗口: {self.title}", "green")
                        self.logger.log(f"窗口位置: left={self.window_rect[0]}, top={self.window_rect[1]}", "black")
                    
                    return True
            
            # 如果没找到，尝试模糊匹配但排除文件资源管理器
            for window in all_windows:
                title = window.title
                if title and ('Endfield' in title or '终末地' in title):
                    # 排除文件资源管理器
                    if '文件资源管理器' not in title and 'explorer' not in title.lower():
                        self.hwnd = window._hWnd
                        self.title = title
                        self.window_rect = win32gui.GetWindowRect(self.hwnd)
                        
                        if self.logger:
                            self.logger.log(f"找到游戏窗口: {self.title}", "green")
                            self.logger.log(f"窗口位置: left={self.window_rect[0]}, top={self.window_rect[1]}", "black")
                        
                        return True
            
            if self.logger:
                self.logger.log("未找到游戏窗口", "red")
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"查找窗口失败: {e}", "red")
            return False
    
    def get_window_rect(self):
        """
        获取窗口位置
        
        Returns:
            (left, top, right, bottom) 或 None
        """
        if self.hwnd:
            try:
                return win32gui.GetWindowRect(self.hwnd)
            except:
                return None
        return None
    
    def get_client_rect(self):
        """
        获取客户区位置
        
        Returns:
            (left, top, right, bottom) 或 None
        """
        if self.hwnd:
            try:
                return win32gui.GetClientRect(self.hwnd)
            except:
                return None
        return None
    
    def get_window_center(self):
        """
        获取窗口中心点
        
        Returns:
            (x, y) 或 None
        """
        rect = self.get_window_rect()
        if rect:
            left, top, right, bottom = rect
            return (left + (right - left) // 2, top + (bottom - top) // 2)
        return None
    
    def is_valid(self):
        """检查窗口是否仍然有效"""
        if self.hwnd:
            return win32gui.IsWindow(self.hwnd)
        return False