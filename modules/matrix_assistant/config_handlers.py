"""
基质助手配置处理
"""

import tkinter as tk
from .utils import get_game_monitor


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
            from PIL import Image, ImageTk
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
        
        print(f"点击屏幕坐标: ({screen_x}, {screen_y})")
        
        # 保存回调引用
        callback = self.callback
        
        # 关闭窗口
        self.close()
        
        # 调用回调
        if callback:
            callback(screen_x, screen_y)
    
    def close(self):
        """关闭窗口"""
        self._close_guide()
        if hasattr(self, 'top') and self.top and self.top.winfo_exists():
            self.top.destroy()
            self.top = None


class ConfigHandlers:
    """配置处理器"""
    
    def __init__(self, module):
        """
        初始化
        
        Args:
            module: 主模块实例
        """
        self.module = module
        self.current_window = None
    
    def _get_monitor(self):
        """获取游戏所在显示器"""
        from .utils import get_game_monitor
        return get_game_monitor(self.module.game_window)
    
    def set_matrix_roi(self):
        """设置基质框选 - 需要框选"""
        from ui.selection_canvas import SelectionCanvas
        
        monitor = self._get_monitor()
        
        def callback(x, y, w, h):
            self.module.config["matrix_size"] = (w, h)
            self.module.save_config()
            self.module.logger.log(f"基质框选完成: 尺寸 ({w}, {h})", "green")
        
        self.current_window = SelectionCanvas(
            self.module.root,
            callback,
            "请框选一个基质的完整区域",
            self.module.resource_path("img/guide_matrix.png"),
            monitor
        )
    
    def set_roi(self):
        """设置识别区域 - 需要框选"""
        from ui.selection_canvas import SelectionCanvas
        
        monitor = self._get_monitor()
        
        def callback(x, y, w, h):
            window_rect = self.module.game_window.get_window_rect()
            if window_rect:
                rel_x = x - window_rect[0]
                rel_y = y - window_rect[1]
                self.module.config["roi"] = (rel_x, rel_y, w, h)
                self.module.save_config()
                self.module.logger.log(f"识别区域设置完成: ({rel_x}, {rel_y}, {w}, {h})", "green")
            else:
                self.module.config["roi"] = (x, y, w, h)
                self.module.save_config()
                self.module.logger.log(f"警告：使用绝对坐标设置识别区域 ({x}, {y}, {w}, {h})", "orange")
        
        self.current_window = SelectionCanvas(
            self.module.root,
            callback,
            "请框选词条识别区域",
            self.module.resource_path("img/guide_roi.png"),
            monitor
        )
    
    def set_grid(self):
        """校准网格 - 需要点击3次"""
        self.module.logger.log("校准网格：请点击 (1,1) 位置的中心", "blue")
        self._grid_step1()
    
    def _grid_step1(self):
        """第一步：点击 (1,1)"""
        monitor = self._get_monitor()
        
        def callback(x, y):
            print(f"第一步点击: ({x}, {y})")
            window_rect = self.module.game_window.get_window_rect()
            if window_rect:
                rel_x = x - window_rect[0]
                rel_y = y - window_rect[1]
                
                if "grid" not in self.module.config or self.module.config["grid"] is None:
                    self.module.config["grid"] = {}
                
                self.module.config["grid"]["p11"] = (rel_x, rel_y)
                self.module.logger.log(f"第一个点已记录: ({rel_x}, {rel_y})", "green")
                
                # 进入第二步
                self.module.root.after(100, self._grid_step2)
            else:
                self.module.logger.log("错误：无法获取游戏窗口位置", "red")
        
        self.current_window = ClickWindow(
            self.module.root,
            callback,
            "点击 (1,1) 位置的中心",
            self.module.resource_path("img/guide_grid.png"),
            monitor
        )
    
    def _grid_step2(self):
        """第二步：点击 (1,2)"""
        self.module.logger.log("请点击 (1,2) 位置的中心", "blue")
        monitor = self._get_monitor()
        
        def callback(x, y):
            print(f"第二步点击: ({x}, {y})")
            window_rect = self.module.game_window.get_window_rect()
            if window_rect:
                rel_x = x - window_rect[0]
                rel_y = y - window_rect[1]
                
                self.module.config["grid"]["p12"] = (rel_x, rel_y)
                self.module.logger.log(f"第二个点已记录: ({rel_x}, {rel_y})", "green")
                
                # 进入第三步
                self.module.root.after(100, self._grid_step3)
            else:
                self.module.logger.log("错误：无法获取游戏窗口位置", "red")
        
        self.current_window = ClickWindow(
            self.module.root,
            callback,
            "点击 (1,2) 位置的中心",
            None,
            monitor
        )
    
    def _grid_step3(self):
        """第三步：点击 (2,1) 并计算"""
        self.module.logger.log("请点击 (2,1) 位置的中心", "blue")
        monitor = self._get_monitor()
        
        def callback(x, y):
            print(f"第三步点击: ({x}, {y})")
            window_rect = self.module.game_window.get_window_rect()
            if window_rect:
                rel_x = x - window_rect[0]
                rel_y = y - window_rect[1]
                
                p11 = self.module.config["grid"]["p11"]
                p12 = self.module.config["grid"]["p12"]
                
                rdx = p12[0] - p11[0]
                rdy = rel_y - p11[1]
                
                self.module.config["grid"].update({
                    "rx": p11[0],
                    "ry": p11[1],
                    "rdx": rdx,
                    "rdy": rdy
                })
                
                self.module.save_config()
                self.module.logger.log("网格校准完成！", "green")
                self.module.logger.log(f"基准点: ({p11[0]}, {p11[1]})", "black")
                self.module.logger.log(f"X间距: {rdx}, Y间距: {rdy}", "black")
            else:
                self.module.logger.log("错误：无法获取游戏窗口位置", "red")
        
        self.current_window = ClickWindow(
            self.module.root,
            callback,
            "点击 (2,1) 位置的中心",
            None,
            monitor
        )
    
    def set_lock(self):
        """设置锁定键 - 需要点击"""
        monitor = self._get_monitor()
        
        def callback(x, y):
            window_rect = self.module.game_window.get_window_rect()
            if window_rect:
                rel_x = x - window_rect[0]
                rel_y = y - window_rect[1]
                self.module.config["lock"] = (rel_x, rel_y)
                self.module.save_config()
                self.module.logger.log("锁定键校准完成", "green")
            else:
                self.module.config["lock"] = (x, y)
                self.module.save_config()
                self.module.logger.log("警告：使用绝对坐标设置锁定键", "orange")
        
        self.current_window = ClickWindow(
            self.module.root,
            callback,
            "点击锁定图标中心",
            self.module.resource_path("img/guide_lock.png"),
            monitor
        )
    
    def set_discard(self):
        """设置弃置键 - 需要点击"""
        monitor = self._get_monitor()
        
        def callback(x, y):
            window_rect = self.module.game_window.get_window_rect()
            if window_rect:
                rel_x = x - window_rect[0]
                rel_y = y - window_rect[1]
                self.module.config["discard"] = (rel_x, rel_y)
                self.module.save_config()
                self.module.logger.log("弃置键校准完成", "green")
            else:
                self.module.config["discard"] = (x, y)
                self.module.save_config()
                self.module.logger.log("警告：使用绝对坐标设置弃置键", "orange")
        
        self.current_window = ClickWindow(
            self.module.root,
            callback,
            "点击弃置图标中心",
            None,
            monitor
        )