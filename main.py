"""
终末地小助手 - 主程序入口
版本：beta2.1（稳定版）
"""

import tkinter as tk
import sys
import traceback
import time
from tkinter import messagebox

# 导入工具模块
from utils.resource import resource_path
from utils.admin import run_as_admin, set_dpi_aware
from utils.config import ConfigManager
from utils.logger import Logger

# 导入核心模块
from core.game_window import GameWindow
from core.screenshot import Screenshot
from core.click_helper import ClickHelper
from core.ocr_helper import OCRHelper

# 导入UI
from ui.main_window import MainWindow

# 导入功能模块
from modules.matrix_assistant import MatrixAssistantModule
from modules.hall_order import HallOrderModule
from modules.djh_transport import DJHTransportModule


class Application:
    """应用程序主类"""
    
    def __init__(self):
        """初始化应用程序"""
        self.root = tk.Tk()
        
        # 设置DPI感知
        set_dpi_aware()
        
        # 初始化日志
        self.logger = Logger()
        self.logger.log("程序启动中...", "blue")
        
        # 初始化配置管理器
        self.config_manager = ConfigManager(resource_path)
        
        # 检查游戏窗口
        self.game_window = GameWindow(self.logger)
        if not self.game_window.find_window():
            messagebox.showerror("错误", "未检测到游戏窗口，请先启动游戏！")
            sys.exit(1)
        
        # 初始化核心组件
        self.screenshot = Screenshot(self.game_window, self.logger)
        self.click_helper = ClickHelper(self.game_window, self.logger)
        self.ocr_helper = OCRHelper(
            corrections=self.config_manager.load_corrections(),
            logger=self.logger
        )
        
        # 创建主窗口
        self.main_window = MainWindow(
            self.root,
            self.game_window,
            self.config_manager,
            self.logger
        )
        
        # 注册功能模块
        self._register_modules()
        
        # 设置退出处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.logger.log("程序初始化完成", "green")
    
    def _register_modules(self):
        """注册所有功能模块"""
        
        # 基质助手模块
        matrix_module = MatrixAssistantModule(
            self.main_window.notebook,
            self.game_window,
            self.screenshot,
            self.click_helper,
            self.ocr_helper,
            self.config_manager,
            self.logger,
            resource_path
        )
        self.main_window.register_module("基质识别", matrix_module.get_tab(), matrix_module)
        
        # 大厅抢单模块（预留）
        hall_module = HallOrderModule(
            self.main_window.notebook,
            self.game_window,
            self.screenshot,
            self.click_helper,
            self.ocr_helper,
            self.config_manager,
            self.logger,
            resource_path
        )
        self.main_window.register_module("大厅抢单", hall_module.get_tab(), hall_module)
        
        # 帝江号搬货模块（预留）
        djh_module = DJHTransportModule(
            self.main_window.notebook,
            self.game_window,
            self.screenshot,
            self.click_helper,
            self.ocr_helper,
            self.config_manager,
            self.logger,
            resource_path
        )
        self.main_window.register_module("帝江搬货", djh_module.get_tab(), djh_module)
    
    def _on_closing(self):
        """关闭程序时的处理"""
        self.logger.log("正在关闭程序...", "orange")
        
        # 停止所有运行中的模块
        for name, module in self.main_window.modules.items():
            if hasattr(module, 'stop'):
                try:
                    module.stop()
                except Exception as e:
                    print(f"停止模块 {name} 时出错: {e}")
        
        # 给线程一点时间退出
        time.sleep(0.5)
        
        # 销毁窗口
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        
        print("程序已正常退出")
        sys.exit(0)
    
    def run(self):
        """运行程序"""
        self.root.mainloop()


def global_exception_handler(exc_type, exc_value, exc_traceback):
    """全局异常处理"""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"程序错误:\n{error_msg}")
    
    # 尝试显示错误对话框
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("程序错误", f"发生未处理的异常:\n\n{error_msg}")
    except:
        pass
    
    # 等待用户确认
    input("按回车退出...")
    sys.exit(1)


if __name__ == "__main__":
    # 设置全局异常处理
    sys.excepthook = global_exception_handler
    
    # 检查管理员权限
    if run_as_admin():
        app = Application()
        app.run()
    else:
        # 如果不是管理员，程序会在这里退出（因为run_as_admin会启动新进程）
        pass