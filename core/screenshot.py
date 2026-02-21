"""
后台截图模块
使用 PrintWindow API 实现后台截图
"""

import cv2
import numpy as np
import win32gui
import win32ui
import win32con
import ctypes

class Screenshot:
    """后台截图器"""
    
    def __init__(self, game_window, logger=None):
        """
        初始化截图器
        
        Args:
            game_window: 游戏窗口管理器
            logger: 日志记录器
        """
        self.game_window = game_window
        self.logger = logger
    
    def capture_window(self):
        """
        捕获整个窗口
        
        Returns:
            OpenCV图像或None
        """
        if not self.game_window.hwnd:
            if self.logger:
                self.logger.log("窗口句柄无效", "red")
            return None
        
        try:
            # 获取客户区大小
            l, t, r, b = win32gui.GetClientRect(self.game_window.hwnd)
            w, h = r - l, b - t
            
            if w <= 0 or h <= 0:
                return None
            
            # 获取窗口DC
            hDC = win32gui.GetWindowDC(self.game_window.hwnd)
            mDC = win32ui.CreateDCFromHandle(hDC)
            sDC = mDC.CreateCompatibleDC()
            
            # 创建位图
            sBM = win32ui.CreateBitmap()
            sBM.CreateCompatibleBitmap(mDC, w, h)
            sDC.SelectObject(sBM)
            
            # 使用 PrintWindow 捕获
            ctypes.windll.user32.PrintWindow(self.game_window.hwnd, sDC.GetSafeHdc(), 2)
            
            # 转换位图为数组
            bits = sBM.GetBitmapBits(True)
            img = np.frombuffer(bits, dtype='uint8')
            img.shape = (h, w, 4)  # BGRA
            
            # 清理资源
            win32gui.DeleteObject(sBM.GetHandle())
            sDC.DeleteDC()
            mDC.DeleteDC()
            win32gui.ReleaseDC(self.game_window.hwnd, hDC)
            
            # 转换为BGR
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"截图失败: {e}", "red")
            return None
    
    def capture_region(self, x, y, w, h):
        """
        捕获指定区域
        
        Args:
            x, y: 相对窗口的坐标
            w, h: 区域宽高
            
        Returns:
            区域图像或None
        """
        full_img = self.capture_window()
        if full_img is not None:
            h_img, w_img = full_img.shape[:2]
            # 确保区域在图像范围内
            x = max(0, min(x, w_img - 1))
            y = max(0, min(y, h_img - 1))
            w = min(w, w_img - x)
            h = min(h, h_img - y)
            
            if w > 0 and h > 0:
                return full_img[y:y+h, x:x+w]
        return None
    
    def capture_absolute_region(self, screen_x, screen_y, w, h):
        """
        捕获屏幕绝对坐标区域
        
        Args:
            screen_x, screen_y: 屏幕绝对坐标
            w, h: 区域宽高
            
        Returns:
            区域图像或None
        """
        window_rect = self.game_window.get_window_rect()
        if window_rect:
            # 转换为相对窗口坐标
            rel_x = screen_x - window_rect[0]
            rel_y = screen_y - window_rect[1]
            return self.capture_region(rel_x, rel_y, w, h)
        return None