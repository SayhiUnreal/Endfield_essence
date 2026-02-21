"""
点击窗口 - 用于记录鼠标点击位置
"""

import tkinter as tk
from PIL import Image, ImageTk


class ClickWindow:
    """点击窗口 - 用于记录鼠标点击位置，带有白色半透明背景和十字准星"""
    
    def __init__(self, root, callback, prompt, guide_image=None, monitor=None):
        """
        初始化点击窗口
        
        Args:
            root: 主窗口
            callback: 点击完成回调，接收 (x, y)
            prompt: 提示文字
            guide_image: 引导图片路径
            monitor: 指定显示器
        """
        self.root = root
        self.callback = callback
        self.monitor = monitor
        self.guide_window = None
        self.is_cancelled = False
        
        # 创建覆盖层 - 白色半透明
        self.top = tk.Toplevel(root)
        self.top.attributes("-alpha", 0.6, "-topmost", True)
        self.top.geometry(f"{monitor['width']}x{monitor['height']}+"
                         f"{monitor['left']}+{monitor['top']}")
        self.top.overrideredirect(True)
        self.top.configure(bg="white")
        
        # 创建画布用于显示十字准星
        self.canvas = tk.Canvas(self.top, cursor="crosshair", bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # 显示提示文字
        self.canvas.create_text(monitor['width']//2, 50, 
                               text=prompt, font=("微软雅黑", 24, "bold"), 
                               fill="red")
        
        # 显示引导图片
        if guide_image:
            self._show_guide(guide_image)
        
        # 绑定点击事件
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Button-3>", lambda e: self.close())
        self.top.bind("<Escape>", lambda e: self.close())
    
    def _show_guide(self, image_path):
        """显示引导图片"""
        try:
            img = Image.open(image_path)
            img.thumbnail((700, 500))
            self.guide_image = ImageTk.PhotoImage(img)
            
            self.guide_window = tk.Toplevel(self.root)
            self.guide_window.attributes("-topmost", True)
            self.guide_window.overrideredirect(True)
            
            x = self.monitor['left'] + (self.monitor['width'] - img.width) // 2
            y = self.monitor['top'] + (self.monitor['height'] - img.height) // 2
            
            self.guide_window.geometry(f"{img.width}x{img.height}+{x}+{y}")
            tk.Label(self.guide_window, image=self.guide_image, 
                    bg="white", relief="solid", bd=2).pack()
            
            # 3秒后自动关闭
            self.root.after(3000, self._close_guide)
        except Exception as e:
            print(f"显示引导图片失败: {e}")
    
    def _close_guide(self):
        """关闭引导图片"""
        if self.guide_window and self.guide_window.winfo_exists():
            self.guide_window.destroy()
            self.guide_window = None
    
    def _on_click(self, event):
        """点击事件处理"""
        # 转换为屏幕绝对坐标
        screen_x = event.x_root
        screen_y = event.y_root
        
        # 保存回调引用
        callback = self.callback
        
        # 关闭窗口
        self.close()
        
        # 调用回调
        if callback and not self.is_cancelled:
            callback(screen_x, screen_y)
    
    def close(self):
        """关闭窗口"""
        self.is_cancelled = True
        self._close_guide()
        if hasattr(self, 'top') and self.top and self.top.winfo_exists():
            self.top.destroy()
            self.top = None