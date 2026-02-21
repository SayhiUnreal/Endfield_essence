"""
模拟点击模块
封装 pydirectinput 和 pyautogui
"""

import pydirectinput
import pyautogui
import time

class ClickHelper:
    """模拟点击助手"""
    
    def __init__(self, game_window, logger=None):
        """
        初始化点击助手
        
        Args:
            game_window: 游戏窗口管理器
            logger: 日志记录器
        """
        self.game_window = game_window
        self.logger = logger
        
        # 设置参数
        pydirectinput.PAUSE = 0.01
        pyautogui.FAILSAFE = False
    
    def click_relative(self, x, y, button='left', clicks=1, interval=0.0):
        """
        点击相对窗口的坐标
        
        Args:
            x, y: 相对窗口的坐标
            button: 鼠标按键
            clicks: 点击次数
            interval: 点击间隔
        """
        window_rect = self.game_window.get_window_rect()
        if window_rect:
            screen_x = window_rect[0] + x
            screen_y = window_rect[1] + y
            self.click_absolute(screen_x, screen_y, button, clicks, interval)
    
    def click_absolute(self, x, y, button='left', clicks=1, interval=0.0):
        """
        点击屏幕绝对坐标
        
        Args:
            x, y: 屏幕绝对坐标
            button: 鼠标按键
            clicks: 点击次数
            interval: 点击间隔
        """
        try:
            pydirectinput.click(x, y, button=button, clicks=clicks, interval=interval)
            if self.logger:
                self.logger.log(f"点击: ({x}, {y})", "black", to_console=True)
        except Exception as e:
            if self.logger:
                self.logger.log(f"点击失败: {e}", "red")
    
    def move_relative(self, x, y):
        """
        移动鼠标到相对窗口位置
        
        Args:
            x, y: 相对窗口的坐标
        """
        window_rect = self.game_window.get_window_rect()
        if window_rect:
            screen_x = window_rect[0] + x
            screen_y = window_rect[1] + y
            self.move_absolute(screen_x, screen_y)
    
    def move_absolute(self, x, y):
        """
        移动鼠标到屏幕绝对坐标
        """
        try:
            pydirectinput.moveTo(x, y)
        except Exception as e:
            if self.logger:
                self.logger.log(f"移动失败: {e}", "red")
    
    def move_relative_smooth(self, start_x, start_y, end_x, end_y, steps=16):
        """
        平滑移动鼠标
        
        Args:
            start_x, start_y: 起始坐标（相对窗口）
            end_x, end_y: 结束坐标（相对窗口）
            steps: 移动步数
        """
        window_rect = self.game_window.get_window_rect()
        if window_rect:
            start_sx = window_rect[0] + start_x
            start_sy = window_rect[1] + start_y
            end_sx = window_rect[0] + end_x
            end_sy = window_rect[1] + end_y
            self.move_absolute_smooth(start_sx, start_sy, end_sx, end_sy, steps)
    
    def move_absolute_smooth(self, start_x, start_y, end_x, end_y, steps=16):
        """
        平滑移动鼠标（屏幕绝对坐标）
        """
        try:
            self.move_absolute(start_x, start_y)
            pydirectinput.mouseDown()
            
            for i in range(steps + 1):
                progress = i / steps
                current_x = int(start_x + (end_x - start_x) * progress)
                current_y = int(start_y + (end_y - start_y) * progress)
                pydirectinput.moveTo(current_x, current_y)
                time.sleep(0.01)
            
            pydirectinput.mouseUp()
        except Exception as e:
            if self.logger:
                self.logger.log(f"平滑移动失败: {e}", "red")
            pydirectinput.mouseUp()  # 确保鼠标释放