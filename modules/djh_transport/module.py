"""
帝江号搬货主模块
"""

import tkinter as tk
from pynput import keyboard
from .ui import DJHTransportUI
from .wizard import TransportWizard
from .transport_task import TransportTask


class DJHTransportModule:
    """帝江号搬货模块"""
    
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
        
        # 加载配置
        full_config = config_manager.load_config()
        self.config = full_config.get("djh_transport", {})
        
        # 运行状态
        self.running = False
        self.cached_item_image = None  # 缓存的货源物品图片
        
        # 创建UI
        self.ui = DJHTransportUI(parent, self)
        
        # 创建向导
        self.wizard = TransportWizard(self)
        
        # 创建任务
        self.transport_task = TransportTask(self)
        
        # 设置键盘监听
        self._setup_keyboard_listener()
        
        # 更新UI配置状态
        self._update_ui_status()
    
    def _setup_keyboard_listener(self):
        """设置键盘监听（B键停止）"""
        def on_press(key):
            if hasattr(key, 'char') and key.char == 'b' and self.running:
                self.logger.log("[停止] 任务已中止", "red")
                self.stop_transport()
        
        self.keyboard_listener = keyboard.Listener(on_press=on_press)
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()
    
    def _update_ui_status(self):
        """更新UI状态"""
        ready = all(self.config.get(k) is not None 
                   for k in ["switch_button", "popup_roi", "source_item", "deposit_button", "confirm_button"])
        self.ui.update_status(ready)
        
        # 更新参数显示（只保留可调的参数）
        self.ui.click_interval_var.set(self.config.get("click_interval", "0.3"))
        self.ui.confirm_wait_var.set(self.config.get("confirm_wait", "3.0"))
    
    def save_config(self):
        """保存配置"""
        # 保存可调参数
        self.config["click_interval"] = self.ui.click_interval_var.get()
        self.config["confirm_wait"] = self.ui.confirm_wait_var.get()
        
        # 固定参数（用户不可调，但保存到配置中供任务使用）
        self.config["switch_delay"] = "1.0"      # 切换等待固定1秒
        self.config["ctrl_hold"] = "0.5"         # Ctrl按住固定0.5秒
        self.config["fill_wait"] = "0.5"         # 填充等待固定0.5秒
        
        # 保存到文件
        full_config = self.config_manager.load_config()
        full_config["djh_transport"] = self.config
        self.config_manager.save_config(full_config)
        
        self._update_ui_status()
    
    # === 向导方法 ===
    def cancel_wizard(self):
        """取消当前向导步骤"""
        self.wizard.cancel_current()
    
    # === 向导步骤 ===
    def calibrate_switch_button(self):
        """校准仓库切换按钮"""
        self.wizard.calibrate_switch_button()
    
    def calibrate_popup_roi(self):
        """框选仓库名字区域"""
        self.wizard.calibrate_popup_roi()
    
    def calibrate_source_item(self):
        """框选货源物品"""
        self.wizard.calibrate_source_item()
    
    def calibrate_deposit_button(self):
        """校准一键存放按钮"""
        self.wizard.calibrate_deposit_button()
    
    def calibrate_confirm_button(self):
        """校准确认按钮"""
        self.wizard.calibrate_confirm_button()
    
    # === 搬货控制 ===
    def start_transport(self):
        """开始搬货"""
        required = ["switch_button", "popup_roi", "source_item", "deposit_button", "confirm_button"]
        
        if not all(self.config.get(k) is not None for k in required):
            self.logger.log("❌ 请先完成所有配置", "red")
            return
        
        if self.cached_item_image is None:
            self.logger.log("❌ 货源物品图片未缓存，请重新框选货源物品", "red")
            return
        
        self.save_config()
        
        self.logger.clear()
        self.logger.log("🚚 帝江号搬货模块启动", "blue")
        # self.logger.log("按 'B' 键可停止搬货", "blue")
        
        self.transport_task.start()
        self.running = True
        self.ui.set_button_state(True)
    
    def stop_transport(self):
        """停止搬货"""
        self.transport_task.stop()
        self.running = False
        self.ui.set_button_state(False)
        self.logger.log("正在停止搬货...", "orange")
    
    def set_cached_item_image(self, image):
        """设置缓存的物品图片"""
        self.cached_item_image = image
    
    def get_tab(self):
        """获取标签页"""
        return self.ui.get_tab()