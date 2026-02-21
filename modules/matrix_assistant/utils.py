"""
基质助手工具函数
"""

import cv2
import numpy as np
import mss

def is_gold(img):
    """
    判断是否为金色
    
    Args:
        img: OpenCV图像
        
    Returns:
        bool: 是否为金色
    """
    try:
        h, w = img.shape[:2]
        strip = img[int(h * 0.70):, :]
        hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([15, 100, 100]), np.array([35, 255, 255]))
        gold_ratio = np.sum(mask > 0) / mask.size
        return gold_ratio > 0.05
    except:
        return False


def is_operated(window_img, pos):
    """
    检查是否已操作（锁定或弃置）
    完全恢复原程序的判断逻辑
    
    Args:
        window_img: 窗口截图
        pos: 图标位置 (x, y)
        
    Returns:
        bool: 是否已操作
    """
    try:
        lx, ly = int(pos[0]), int(pos[1])
        
        # 原程序固定使用54像素
        icon_size = 54
        
        # 计算图标区域 - 完全按照原程序
        top = max(0, ly - icon_size//2)
        bottom = min(window_img.shape[0], ly + icon_size//2)
        left = max(0, lx - icon_size//2)
        right = min(window_img.shape[1], lx + icon_size//2)
        
        if bottom <= top or right <= left:
            return False
            
        region = window_img[top:bottom, left:right]
        
        # 转换为灰度图
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        
        # 原程序只使用阈值200
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        white_ratio = np.count_nonzero(binary) / binary.size
        
        # 原程序的判断条件
        return white_ratio < 0.2
        
    except Exception as e:
        print(f"检查操作状态失败: {e}")
        return False


def get_game_monitor(game_window):
    """
    获取游戏所在显示器
    
    Args:
        game_window: 游戏窗口管理器
        
    Returns:
        dict: 显示器信息
    """
    center = game_window.get_window_center()
    if center:
        monitors = mss.mss().monitors
        for mon in monitors[1:]:
            if (mon['left'] <= center[0] < mon['left'] + mon['width'] and
                mon['top'] <= center[1] < mon['top'] + mon['height']):
                return mon
    
    # 默认返回主显示器
    monitors = mss.mss().monitors
    return monitors[1] if len(monitors) > 1 else monitors[0]