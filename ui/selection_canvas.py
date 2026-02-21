"""
屏幕选区工具
用于在屏幕上框选区域
"""

import tkinter as tk
from PIL import Image, ImageTk
import mss

class SelectionCanvas:
    """屏幕选区工具"""
    
    def __init__(self, root, callback, prompt="请框选区域", guide_image=None, monitor=None):
        """
        初始化选区工具
        
        Args:
            root: 主窗口
            callback: 选区完成回调，接收 (x, y, w, h)
            prompt: 提示文字
            guide_image: 引导图片路径
            monitor: 指定显示器，None则使用主显示器
        """
        print(f"SelectionCanvas初始化: prompt={prompt}")  # 调试输出
        self.root = root
        self.callback = callback
        self.guide_window = None
        self.selected = False  # 标记是否已选择
        
        # 获取显示器信息
        self.monitor = monitor or self._get_primary_monitor()
        print(f"显示器: left={self.monitor['left']}, top={self.monitor['top']}, width={self.monitor['width']}, height={self.monitor['height']}")
        
        # 创建覆盖层
        self.top = tk.Toplevel(root)
        self.top.attributes("-alpha", 0.6, "-topmost", True)
        self.top.geometry(f"{self.monitor['width']}x{self.monitor['height']}+"
                         f"{self.monitor['left']}+{self.monitor['top']}")
        self.top.overrideredirect(True)
        self.top.configure(bg="white")
        
        # 确保窗口获得焦点
        self.top.focus_force()
        
        # 创建画布
        self.canvas = tk.Canvas(self.top, cursor="crosshair", bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # 显示提示文字
        self.canvas.create_text(self.monitor['width']//2, 50, 
                               text=prompt, font=("微软雅黑", 24, "bold"), 
                               fill="red")
        
        # 显示引导图片
        if guide_image:
            self._show_guide(guide_image)
        
        # 绑定事件
        self.start_x = self.start_y = self.rect = None
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", lambda e: self.close())
        self.top.bind("<Escape>", lambda e: self.close())
        
        # 绑定窗口关闭事件
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        
        print("SelectionCanvas初始化完成")
    
    def _get_primary_monitor(self):
        """获取主显示器"""
        monitors = mss.mss().monitors
        return monitors[1] if len(monitors) > 1 else monitors[0]
    
    def _show_guide(self, image_path):
        """显示引导图片"""
        try:
            print(f"显示引导图片: {image_path}")
            img = Image.open(image_path)
            img.thumbnail((700, 500))
            self.guide_image = ImageTk.PhotoImage(img)
            
            self.guide_window = tk.Toplevel(self.root)
            self.guide_window.attributes("-topmost", True)
            self.guide_window.overrideredirect(True)
            
            # 居中显示
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
            print("关闭引导图片")
            self.guide_window.destroy()
            self.guide_window = None
    
    def _on_press(self, event):
        """鼠标按下"""
        print(f"鼠标按下: ({event.x}, {event.y})")
        self._close_guide()
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="blue", width=4
        )
    
    def _on_drag(self, event):
        """鼠标拖动"""
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)
    
    def _on_release(self, event):
        """鼠标释放"""
        print(f"鼠标释放: ({event.x}, {event.y})")
        if self.selected:  # 防止重复触发
            return
            
        x1, x2 = min(self.start_x, event.x), max(self.start_x, event.x)
        y1, y2 = min(self.start_y, event.y), max(self.start_y, event.y)
        
        # 检查最小尺寸
        if (x2 - x1) > 10 and (y2 - y1) > 10:
            self.selected = True
            screen_x = x1 + self.monitor['left']
            screen_y = y1 + self.monitor['top']
            
            print(f"选区完成: 屏幕坐标({screen_x}, {screen_y}), 尺寸({x2-x1}, {y2-y1})")
            
            # 保存回调引用
            callback = self.callback
            
            # 先关闭窗口
            self.close()
            
            # 再调用回调
            if callback:
                print("调用回调函数")
                callback(screen_x, screen_y, x2 - x1, y2 - y1)
        else:
            # 选区太小，删除矩形让用户重新选择
            print("选区太小，请重新选择")
            self.canvas.delete(self.rect)
            self.start_x = self.start_y = self.rect = None
    
    def close(self):
        """关闭选区"""
        print("关闭SelectionCanvas")
        self._close_guide()
        if hasattr(self, 'top') and self.top and self.top.winfo_exists():
            self.top.destroy()
            self.top = None