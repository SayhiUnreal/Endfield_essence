"""
主窗口界面
包含模块切换和公共控件
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading

class MainWindow:
    """主窗口"""
    
    def __init__(self, root, game_window, config_manager, logger):
        """
        初始化主窗口
        
        Args:
            root: tkinter根窗口
            game_window: 游戏窗口管理器
            config_manager: 配置管理器
            logger: 日志记录器
        """
        self.root = root
        self.game_window = game_window
        self.config = config_manager
        self.logger = logger
        
        self.root.title("终末地小助手beta1.0 by洁柔厨&断绫")
        self.root.geometry("750x900")
        self.root.attributes("-topmost", True)
        
        # 当前活动模块
        self.current_module = None
        self.modules = {}
        
        self._setup_ui()
        self._load_icon()
    
    def _load_icon(self):
        """加载程序图标"""
        try:
            from utils.resource import resource_path
            import ctypes
            myappid = 'jierouchu.matrix.assistant.v17'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            
            icon_path = resource_path("img/jizhi.ico")
            if icon_path:
                from PIL import Image, ImageTk
                img = Image.open(icon_path)
                self.tk_icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self.tk_icon)
        except:
            pass
    
    def _setup_ui(self):
        """设置UI"""
        
        # === 顶部：模块切换 ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # === 公共日志区域 ===
        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        tk.Label(log_frame, text="运行日志:", font=("微软雅黑", 11, "bold")).pack(anchor="w")
        
        self.log_area = scrolledtext.ScrolledText(
            log_frame, height=10, font=("微软雅黑", 10)
        )
        self.log_area.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 配置日志颜色标签
        self.log_area.tag_config("black", foreground="black")
        self.log_area.tag_config("green", foreground="#2E7D32")  # 深绿色
        self.log_area.tag_config("gold", foreground="#FF9800")   # 金色
        self.log_area.tag_config("red", foreground="#B71C1C")    # 深红色
        self.log_area.tag_config("blue", foreground="blue")
        self.log_area.tag_config("orange", foreground="#FF9800") # 橙色
        self.log_area.tag_config("gray", foreground="#888888")   # 灰色
        
        # 绑定日志控件
        self.logger.attach_log_widget(self.log_area)
    
    def register_module(self, name, tab, module_instance):
        """
        注册功能模块
        
        Args:
            name: 模块名称
            tab: 模块的标签页
            module_instance: 模块实例
        """
        self.notebook.add(tab, text=name)
        self.modules[name] = module_instance
    
    def get_current_tab(self):
        """获取当前选中的标签页"""
        return self.notebook.select()