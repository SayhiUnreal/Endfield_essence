"""
帝江号搬货配置向导
"""

import time
import tkinter as tk
from tkinter import messagebox
import pydirectinput

from ui.selection_canvas import SelectionCanvas
from modules.matrix_assistant.config_handlers import ClickWindow


class TransportWizard:
    """帝江号搬货配置向导"""
    
    def __init__(self, module):
        """
        初始化向导
        
        Args:
            module: 主模块实例
        """
        self.module = module
        self.current_window = None
        self.current_step = None
    
    def cancel_current(self):
        """取消当前步骤"""
        if self.current_window:
            try:
                self.current_window.close()
            except:
                pass
            self.current_window = None
        self.module.logger.log("已取消当前配置步骤", "orange")
    
    def _get_monitor(self):
        """获取游戏所在显示器"""
        center = self.module.game_window.get_window_center()
        if center:
            import mss
            monitors = mss.mss().monitors
            for mon in monitors[1:]:
                if (mon['left'] <= center[0] < mon['left'] + mon['width'] and
                    mon['top'] <= center[1] < mon['top'] + mon['height']):
                    return mon
        import mss
        monitors = mss.mss().monitors
        return monitors[1] if len(monitors) > 1 else monitors[0]
    
    def calibrate_switch_button(self):
        """校准仓库切换按钮"""
        self.module.logger.log("请点击仓库切换按钮", "blue")
        self.module.logger.log("提示：如果误操作可按右键或ESC取消", "orange")
        
        monitor = self._get_monitor()
        
        def callback(x, y):
            try:
                window_rect = self.module.game_window.get_window_rect()
                if window_rect:
                    rel_x = x - window_rect[0]
                    rel_y = y - window_rect[1]
                    self.module.config["switch_button"] = (rel_x, rel_y)
                    self.module.save_config()
                    self.module.logger.log("✅ 仓库切换按钮已校准", "green")
                self.current_window = None
            except Exception as e:
                self.module.logger.log(f"校准失败: {e}", "red")
        
        self.current_window = ClickWindow(
            self.module.root,
            callback,
            "点击仓库切换按钮中心\n(右键或ESC取消)",
            None,
            monitor
        )
    
    def calibrate_popup_roi(self):
        """框选仓库名字区域（只框选两个仓库的名字）"""
        self.module.logger.log("请框选两个仓库名字的区域", "blue")
        self.module.logger.log("提示：点击切换按钮后，框选包含'四号谷地'和'武陵仓库'名字的区域", "blue")
        
        monitor = self._get_monitor()
        
        # 先点击切换按钮，让弹出界面显示
        if "switch_button" in self.module.config:
            btn_x, btn_y = self.module.config["switch_button"]
            self.module.click.click_relative(btn_x, btn_y)
            self.module.logger.log("已点击切换按钮，请等待弹出界面...", "black")
            time.sleep(1.0)
        
        def callback(x, y, w, h):
            try:
                window_rect = self.module.game_window.get_window_rect()
                if window_rect:
                    rel_x = x - window_rect[0]
                    rel_y = y - window_rect[1]
                    self.module.config["popup_roi"] = (rel_x, rel_y, w, h)
                    self.module.save_config()
                    self.module.logger.log("✅ 仓库名字区域已设置", "green")
                    
                    # 关闭弹出界面
                    pydirectinput.press('esc')
                    time.sleep(0.5)
                self.current_window = None
            except Exception as e:
                self.module.logger.log(f"框选失败: {e}", "red")
        
        self.current_window = SelectionCanvas(
            self.module.root,
            callback,
            "请框选包含两个仓库名字的区域\n(右键或ESC取消)",
            None,
            monitor
        )
    
    def calibrate_source_item(self):
        """框选货源物品"""
        self.module.logger.log("请框选要搬运的货物", "blue")
        
        monitor = self._get_monitor()
        
        def callback(x, y, w, h):
            try:
                window_rect = self.module.game_window.get_window_rect()
                if window_rect:
                    rel_x = x - window_rect[0]
                    rel_y = y - window_rect[1]
                    self.module.config["source_item"] = (rel_x, rel_y, w, h)
                    
                    # 立即截图并缓存
                    item_img = self.module.screenshot.capture_region(rel_x, rel_y, w, h)
                    if item_img is not None:
                        self.module.set_cached_item_image(item_img.copy())
                        self.module.logger.log("✅ 货源物品图片已缓存", "green")
                    else:
                        self.module.logger.log("⚠️ 截图失败，无法缓存物品图片", "orange")
                    
                    self.module.save_config()
                    self.module.logger.log("✅ 货源物品已设置", "green")
                self.current_window = None
            except Exception as e:
                self.module.logger.log(f"框选失败: {e}", "red")
        
        self.current_window = SelectionCanvas(
            self.module.root,
            callback,
            "请框选要搬运的货物（包含整个图标）\n(右键或ESC取消)",
            None,
            monitor
        )
    
    def calibrate_deposit_button(self):
        """校准一键存放按钮"""
        self.module.logger.log("请点击一键存放按钮", "blue")
        
        monitor = self._get_monitor()
        
        def callback(x, y):
            try:
                window_rect = self.module.game_window.get_window_rect()
                if window_rect:
                    rel_x = x - window_rect[0]
                    rel_y = y - window_rect[1]
                    self.module.config["deposit_button"] = (rel_x, rel_y)
                    self.module.save_config()
                    self.module.logger.log("✅ 一键存放按钮已校准", "green")
                    
                    # 检查配置是否完整
                    self.module._update_ui_status()
                self.current_window = None
            except Exception as e:
                self.module.logger.log(f"校准失败: {e}", "red")
        
        self.current_window = ClickWindow(
            self.module.root,
            callback,
            "点击一键存放按钮中心\n(右键或ESC取消)",
            None,
            monitor
        )
    
    def calibrate_confirm_button(self):
        """校准确认按钮"""
        self.module.logger.log("请点击仓库选择界面上的确认按钮", "blue")
        self.module.logger.log("提示：先点击切换按钮，然后在弹出的界面上点击确认按钮", "blue")
        
        monitor = self._get_monitor()
        
        # 先点击切换按钮，让弹出界面显示
        if "switch_button" in self.module.config:
            btn_x, btn_y = self.module.config["switch_button"]
            self.module.click.click_relative(btn_x, btn_y)
            self.module.logger.log("已点击切换按钮，请等待弹出界面...", "black")
            time.sleep(1.0)
        
        def callback(x, y):
            try:
                window_rect = self.module.game_window.get_window_rect()
                if window_rect:
                    rel_x = x - window_rect[0]
                    rel_y = y - window_rect[1]
                    self.module.config["confirm_button"] = (rel_x, rel_y)
                    self.module.save_config()
                    self.module.logger.log("✅ 确认按钮已校准", "green")
                    
                    # 关闭弹出界面
                    pydirectinput.press('esc')
                    time.sleep(0.5)
                    
                    # 检查配置是否完整
                    self.module._update_ui_status()
                self.current_window = None
            except Exception as e:
                self.module.logger.log(f"校准失败: {e}", "red")
        
        self.current_window = ClickWindow(
            self.module.root,
            callback,
            "点击确认按钮中心\n(右键或ESC取消)",
            None,
            monitor
        )