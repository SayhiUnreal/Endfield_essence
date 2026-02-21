"""
日志管理模块
处理所有日志输出
"""

import tkinter as tk
from tkinter import scrolledtext
import time

class Logger:
    """日志管理器"""
    
    # 颜色定义
    COLORS = {
        "black": "black",
        "green": "#2E7D32",
        "gold": "#FF9800",
        "red": "#B71C1C",
        "blue": "blue",
        "orange": "#FF9800"
    }
    
    def __init__(self):
        self.log_widgets = []
        self.console_output = True
        
    def attach_log_widget(self, widget):
        """绑定日志显示控件"""
        self.log_widgets.append(widget)
        # 配置颜色标签
        for tag, color in self.COLORS.items():
            widget.tag_config(tag, foreground=color)
    
    def log(self, message, tag="black", to_console=True):
        """
        输出日志
        
        Args:
            message: 日志消息
            tag: 颜色标签
            to_console: 是否输出到控制台
        """
        timestamp = time.strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        
        # 输出到控制台
        if to_console and self.console_output:
            print(formatted_msg)
        
        # 输出到GUI
        for widget in self.log_widgets:
            try:
                widget.insert(tk.END, formatted_msg + "\n", tag)
                widget.see(tk.END)
            except:
                pass
    
    def clear(self):
        """清空所有日志"""
        for widget in self.log_widgets:
            try:
                widget.delete('1.0', tk.END)
            except:
                pass