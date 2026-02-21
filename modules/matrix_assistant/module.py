"""
基质助手主模块
"""

import tkinter as tk
from pynput import keyboard

from .ui import MatrixAssistantUI
from .config_handlers import ConfigHandlers
from .scan_task import ScanTask


class MatrixAssistantModule:
    """基质自动识别模块"""
    
    def __init__(self, parent, game_window, screenshot, click_helper, ocr_helper, 
                 config_manager, logger, resource_path):
        """
        初始化模块
        
        Args:
            parent: 父窗口
            game_window: 游戏窗口管理器
            screenshot: 截图器
            click_helper: 点击助手
            ocr_helper: OCR助手
            config_manager: 配置管理器
            logger: 日志记录器
            resource_path: 资源路径函数
        """
        self.parent = parent
        self.root = parent.winfo_toplevel()
        self.game_window = game_window
        self.screenshot = screenshot
        self.click = click_helper
        self.ocr = ocr_helper
        self.config_manager = config_manager
        self.logger = logger
        self.resource_path = resource_path
        
        # 加载数据
        self.config = config_manager.load_config()
        self.weapon_list = config_manager.load_weapon_data()
        self.corrections = config_manager.load_corrections()
        self.ocr.corrections = self.corrections
        
        # 创建UI
        self.ui = MatrixAssistantUI(parent, self)
        
        # 创建配置处理器
        self.config_handlers = ConfigHandlers(self)
        
        # 创建扫描任务
        self.scan_task = ScanTask(self)
        
        # 键盘监听
        self.keyboard_listener = None
        self._setup_keyboard_listener()
        
        # 更新UI配置状态
        self._update_ui_status()
    
    def _setup_keyboard_listener(self):
        """设置键盘监听"""
        def on_press(key):
            if hasattr(key, 'char') and key.char == 'b' and self.scan_task.running:
                self.logger.log("[停止] 任务已中止", "red")
                self.stop_scan()
        
        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()
    
    def _update_ui_status(self):
        """更新UI状态"""
        ready = all(self.config.get(k) is not None 
                   for k in ["roi", "grid", "lock", "discard", "matrix_size"])
        self.ui.update_status(ready)
        
        # 更新参数显示
        self.ui.speed_var.set(self.config.get("speed", "0.2"))
        self.ui.dist_var.set(self.config.get("scroll_pixel_dist", "90"))
    
    def save_config(self):
        """保存配置"""
        self.config["speed"] = self.ui.speed_var.get()
        self.config["scroll_pixel_dist"] = self.ui.dist_var.get()
        self.config_manager.save_config(self.config)
        self._update_ui_status()
    
    # === 配置方法 ===
    def set_matrix_roi(self):
        self.config_handlers.set_matrix_roi()
    
    def set_roi(self):
        self.config_handlers.set_roi()
    
    def set_grid(self):
        self.config_handlers.set_grid()
    
    def set_lock(self):
        self.config_handlers.set_lock()
    
    def set_discard(self):
        self.config_handlers.set_discard()
    
    # === 对话框 ===
    def show_correction_dialog(self):
        """显示错字纠正对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加错字纠正")
        dialog.geometry("300x180")
        dialog.attributes("-topmost", True)
        
        tk.Label(dialog, text="错误文字").grid(row=0, column=0, padx=10, pady=10)
        tk.Label(dialog, text="正确文字").grid(row=0, column=1, padx=10, pady=10)
        
        wrong_entry = tk.Entry(dialog, width=15)
        correct_entry = tk.Entry(dialog, width=15)
        wrong_entry.grid(row=1, column=0, padx=10)
        correct_entry.grid(row=1, column=1, padx=10)
        
        def save():
            wrong = wrong_entry.get().strip()
            correct = correct_entry.get().strip()
            if wrong and correct:
                self.corrections[wrong] = correct
                self.config_manager.save_corrections(self.corrections)
                self.ocr.corrections = self.corrections
                dialog.destroy()
                self.logger.log(f"添加纠正: {wrong} -> {correct}", "green")
        
        tk.Button(dialog, text="确认添加", command=save,
                 bg="#2E7D32", fg="white", width=15).grid(row=2, column=0, columnspan=2, pady=20)
    
    def show_weapon_editor(self):
        """显示武器数据编辑器"""
        self.logger.log("武器数据编辑器功能待完善", "orange")
    
    # === 扫描控制 ===
    def start_scan(self):
        """开始扫描"""
        if not all(self.config.get(k) is not None 
                  for k in ["roi", "grid", "lock", "discard", "matrix_size"]):
            self.logger.log("请先完成所有配置", "red")
            return
        
        self.save_config()
        self.corrections = self.config_manager.load_corrections()
        self.ocr.corrections = self.corrections
        
        self.logger.clear()
        self.logger.log("扫描启动，按 'B' 键停止", "blue")
        
        self.scan_task.start()
    
    def stop_scan(self):
        """停止扫描"""
        self.scan_task.stop()
        self.logger.log("正在停止扫描...", "orange")
    
    # === 获取UI ===
    def get_tab(self):
        """获取标签页"""
        return self.ui.get_tab()