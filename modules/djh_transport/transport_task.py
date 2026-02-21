"""
帝江号搬货任务
"""

import time
import threading
import traceback
import cv2
import numpy as np
import pydirectinput
import difflib
import os
from datetime import datetime


class TransportTask:
    """帝江号搬货任务"""
    
    def __init__(self, module):
        """
        初始化任务
        
        Args:
            module: 主模块实例
        """
        self.module = module
        self.running = False
        self.task_thread = None
        self.stop_requested = False
        self.debug_dir = "debug_images"  # 调试图片保存目录
        
        # 创建调试目录
        try:
            if not os.path.exists(self.debug_dir):
                os.makedirs(self.debug_dir)
        except:
            pass
    
    def start(self):
        """开始搬货"""
        if self.task_thread and self.task_thread.is_alive():
            self.module.logger.log("正在停止当前任务，请稍候...", "orange")
            self.stop_requested = True
            self.running = False
            
            wait_count = 0
            while self.task_thread.is_alive() and wait_count < 30:
                time.sleep(0.1)
                wait_count += 1
        
        self.running = True
        self.stop_requested = False
        
        # 更新UI
        self.module.ui.set_button_state(True)
        self.module.logger.clear()
        self.module.logger.log("🚚 帝江号搬货任务启动", "blue")
        
        # 启动新线程
        self.task_thread = threading.Thread(target=self._run, daemon=True)
        self.task_thread.start()
    
    def stop(self):
        """停止搬货"""
        self.module.logger.log("正在停止搬货...", "orange")
        self.stop_requested = True
        self.running = False
    
    def _run(self):
        """搬货主循环"""
        try:
            # 解析参数
            try:
                rounds = int(self.module.ui.rounds_var.get())
                if rounds < 0:
                    rounds = 10
            except:
                rounds = 10
            
            # 从配置获取所有参数
            switch_delay = float(self.module.config.get("switch_delay", "1.0"))
            ctrl_hold = float(self.module.config.get("ctrl_hold", "0.5"))
            click_interval = float(self.module.ui.click_interval_var.get())
            fill_wait = float(self.module.config.get("fill_wait", "0.5"))
            confirm_wait = float(self.module.ui.confirm_wait_var.get())
            
            # 根据方向确定源仓库和目标仓库
            direction = self.module.ui.direction_var.get()
            if direction == "四号谷地→武陵仓库":
                source_warehouse = "四号谷地"
                target_warehouse = "武陵仓库"
                source_match = "四号"
                target_match = "武陵"
            else:
                source_warehouse = "武陵仓库"
                target_warehouse = "四号谷地"
                source_match = "武陵"
                target_match = "四号"
            
            self.module.logger.log(f"搬运方向: {source_warehouse} → {target_warehouse}", "blue")
            self.module.logger.log(f"计划搬货轮数: {rounds if rounds > 0 else '无限'}", "blue")
            
            # 第一步：先将背包中的所有物品存入目标仓库
            self.module.logger.log(f"\n📦 正在将背包物品存入 {target_warehouse}...", "blue")
            
            # 切换到目标仓库
            if not self._switch_warehouse(target_match, target_warehouse, switch_delay, confirm_wait):
                self.module.logger.log("❌ 无法切换到目标仓库", "red")
                return
            
            time.sleep(click_interval)
            
            # 点击一键存放
            deposit_x, deposit_y = self.module.config["deposit_button"]
            self.module.click.click_relative(deposit_x, deposit_y)
            self.module.logger.log(f"✅ 背包物品已存入 {target_warehouse}", "green")
            time.sleep(1.0)
            
            # 切换到源仓库，准备开始搬货循环
            if not self._switch_warehouse(source_match, source_warehouse, switch_delay, confirm_wait):
                self.module.logger.log("❌ 无法切换到源仓库", "red")
                return
            
            # 开始搬货循环
            round_count = 0
            while self.running and not self.stop_requested:
                # 检查轮数限制
                if rounds > 0 and round_count >= rounds:
                    self.module.logger.log(f"\n✅ 已完成指定 {rounds} 轮搬货", "green")
                    break
                
                round_count += 1
                self.module.logger.log(f"\n========== 第 {round_count} 轮 ==========", "blue")
                
                # 每轮开始时已经在源仓库（因为上一轮结束后切回了源仓库）
                # 检查货物是否还存在
                item_exists, debug_info = self._check_item_exists_debug(round_count)
                if not item_exists:
                    if debug_info.get("error"):
                        self.module.logger.log(f"❌ 物品检查出错: {debug_info['error']}", "red")
                    else:
                        self.module.logger.log(f"⚠️ 货源物品可能已搬空 (边缘相似度: {debug_info.get('edge_similarity', '0')})", "orange")
                        # 输出详细调试信息
                        self.module.logger.log(f"  配置位置: {debug_info.get('config_pos')}", "black")
                        self.module.logger.log(f"  窗口位置: {debug_info.get('window_rect')}", "black")
                        self.module.logger.log(f"  绝对坐标: {debug_info.get('abs_pos')}", "black")
                        self.module.logger.log(f"  截图尺寸: {debug_info.get('current_shape')}", "black")
                        self.module.logger.log(f"  缓存尺寸: {debug_info.get('cached_shape')}", "black")
                        self.module.logger.log(f"  边缘相似度: {debug_info.get('edge_similarity')}", "black")
                        
                        if debug_info.get("saved_images"):
                            self.module.logger.log(f"  [调试] 图片已保存: {debug_info['saved_images']}", "orange")
                        
                        # 如果是第1轮且相似度低，可能是误判，我们继续执行而不是停止
                        if round_count == 1 and float(debug_info.get('edge_similarity', '0')) < 0.8:
                            self.module.logger.log("  ⚠️ 第1轮检测到低相似度，可能是误判，继续执行...", "orange")
                            # 不跳出循环，继续执行
                        else:
                            break
                
                # 按住Ctrl点击货物
                self.module.logger.log(f"正在从 {source_warehouse} 取货...", "black")
                item_x, item_y, item_w, item_h = self.module.config["source_item"]
                item_center_x = item_x + item_w // 2
                item_center_y = item_y + item_h // 2
                
                # 模拟按住Ctrl点击
                pydirectinput.keyDown('ctrl')
                time.sleep(0.1)
                self.module.click.click_relative(item_center_x, item_center_y)
                time.sleep(ctrl_hold)  # 按住Ctrl的时间
                pydirectinput.keyUp('ctrl')
                
                self.module.logger.log(f"✅ 已取货", "green")
                time.sleep(fill_wait)  # 等待填充完成
                
                # 切换到目标仓库
                if not self._switch_warehouse(target_match, target_warehouse, switch_delay, confirm_wait):
                    self.module.logger.log("❌ 无法切换到目标仓库", "red")
                    break
                
                # 点击一键存放
                self.module.logger.log(f"正在存入 {target_warehouse}...", "black")
                self.module.click.click_relative(deposit_x, deposit_y)
                self.module.logger.log(f"✅ 第 {round_count} 轮搬货完成", "green")
                time.sleep(click_interval)
                
                # 切回源仓库准备下一轮
                if self.running and not self.stop_requested:
                    self.module.logger.log(f"切回 {source_warehouse} 准备下一轮...", "black")
                    if not self._switch_warehouse(source_match, source_warehouse, switch_delay, confirm_wait):
                        self.module.logger.log("❌ 无法切回源仓库", "red")
                        break
            
            self.module.logger.log("\n🎉 搬货任务完成", "green")
            
        except Exception as e:
            self.module.logger.log(f"❌ 搬货异常: {e}", "red")
            traceback.print_exc()
        finally:
            self.running = False
            self.stop_requested = False
            # 搬货结束后重置货源物品配置
            self.module.root.after(0, self._reset_source_item)
            self.module.root.after(0, self._reset_ui)
    
    def _switch_warehouse(self, match_text, display_name, switch_delay, confirm_wait):
        """
        切换到指定仓库
        
        Args:
            match_text: 用于匹配的文字（"四号"或"武陵"）
            display_name: 用于显示的名称（"四号谷地"或"武陵仓库"）
            switch_delay: 点击切换按钮后的等待时间
            confirm_wait: 点击确认后的等待时间
            
        Returns:
            bool: 是否成功切换
        """
        if "switch_button" not in self.module.config or "popup_roi" not in self.module.config:
            self.module.logger.log("❌ 缺少切换配置", "red")
            return False
        
        # 点击切换按钮
        btn_x, btn_y = self.module.config["switch_button"]
        self.module.click.click_relative(btn_x, btn_y)
        self.module.logger.log("已点击切换按钮", "black")
        time.sleep(switch_delay)  # 等待弹出界面显示
        
        # 截图弹出区域
        popup_x, popup_y, popup_w, popup_h = self.module.config["popup_roi"]
        popup_img = self.module.screenshot.capture_region(popup_x, popup_y, popup_w, popup_h)
        
        if popup_img is None:
            self.module.logger.log("❌ 无法截图弹出界面", "red")
            pydirectinput.press('esc')
            return False
        
        # 在弹出界面中查找目标文字，获取精确坐标
        text_pos = self._find_text_position(popup_img, match_text)
        
        if text_pos is None:
            self.module.logger.log(f"❌ 在弹出界面中未找到 '{match_text}'", "red")
            pydirectinput.press('esc')
            return False
        
        # 计算屏幕坐标并点击文字位置
        name_x, name_y = text_pos
        screen_x = popup_x + name_x
        screen_y = popup_y + name_y
        
        window_rect = self.module.game_window.get_window_rect()
        if window_rect:
            abs_x = window_rect[0] + screen_x
            abs_y = window_rect[1] + screen_y
            pydirectinput.click(abs_x, abs_y)
            self.module.logger.log(f"已点击 {display_name}", "green")
        else:
            self.module.click.click_relative(screen_x, screen_y)
            self.module.logger.log(f"已点击 {display_name}", "green")
        
        # 等待1秒再点击确认按钮
        time.sleep(1.0)
        
        # 点击确认按钮
        if "confirm_button" in self.module.config:
            confirm_x, confirm_y = self.module.config["confirm_button"]
            self.module.click.click_relative(confirm_x, confirm_y)
            self.module.logger.log("已点击确认按钮", "green")
            
            # 等待确认后的加载时间
            time.sleep(confirm_wait)
            
            # 点击ESC关闭仓库选择界面
            pydirectinput.press('esc')
            self.module.logger.log("已关闭仓库选择界面", "black")
            time.sleep(0.5)
        else:
            self.module.logger.log("⚠️ 未配置确认按钮", "orange")
        
        return True
    
    def _find_text_position(self, popup_img, target_text):
        """
        在弹出界面截图中查找指定文字的位置，返回精确坐标
        
        Args:
            popup_img: 弹出界面的截图
            target_text: 要查找的文字（"四号"或"武陵"）
            
        Returns:
            (x, y) 文字中心坐标，找不到返回 None
        """
        if popup_img is None:
            return None
        
        # 使用OCR识别所有文字，获取完整结果（包含坐标）
        result, _ = self.module.ocr.ocr(popup_img)
        
        if not result:
            return None
        
        best_match = None
        best_ratio = 0
        best_box = None
        
        for line in result:
            box = line[0]  # 坐标框 [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = line[1][0]  # 识别出的文字
            confidence = line[1][1]  # 置信度
            
            # 清理文字
            cleaned = self.module.ocr.clean_text(text)
            
            # 计算相似度
            ratio = difflib.SequenceMatcher(None, target_text, cleaned).ratio()
            
            if ratio > best_ratio and ratio > 0.6:  # 阈值60%
                best_ratio = ratio
                best_match = text
                best_box = box
        
        if best_box:
            # 计算文字区域的中心坐标
            x_coords = [p[0] for p in best_box]
            y_coords = [p[1] for p in best_box]
            center_x = int(sum(x_coords) / 4)
            center_y = int(sum(y_coords) / 4)
            
            self.module.logger.log(f"找到 '{target_text}' (相似度: {best_ratio:.2f})", "black")
            return (center_x, center_y)
        
        return None
    
    def _check_item_exists_debug(self, round_num):
        """
        检查货源物品是否还存在（使用边缘检测）
        
        Args:
            round_num: 当前轮数
            
        Returns:
            (bool, dict): (是否存在, 调试信息字典)
        """
        debug_info = {
            "round": round_num,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "config_pos": None,
            "window_rect": None,
            "abs_pos": None,
            "current_shape": None,
            "cached_shape": None,
            "edge_similarity": None,
            "error": None
        }
        
        # 检查配置
        if "source_item" not in self.module.config:
            debug_info["error"] = "source_item 配置不存在"
            return False, debug_info
        
        if self.module.cached_item_image is None:
            debug_info["error"] = "缓存图片不存在"
            return False, debug_info
        
        # 获取配置的坐标
        x, y, w, h = self.module.config["source_item"]
        debug_info["config_pos"] = f"({x}, {y}, {w}, {h})"
        
        # 获取当前窗口位置
        window_rect = self.module.game_window.get_window_rect()
        if window_rect:
            debug_info["window_rect"] = f"left={window_rect[0]}, top={window_rect[1]}, right={window_rect[2]}, bottom={window_rect[3]}"
            abs_x = window_rect[0] + x
            abs_y = window_rect[1] + y
            debug_info["abs_pos"] = f"({abs_x}, {abs_y})"
        
        # 截图当前区域
        current_img = self.module.screenshot.capture_region(x, y, w, h)
        
        if current_img is None:
            debug_info["error"] = "截图失败"
            return False, debug_info
        
        # 记录图片尺寸
        debug_info["current_shape"] = f"{current_img.shape}"
        debug_info["cached_shape"] = f"{self.module.cached_item_image.shape}"
        
        # 检查尺寸是否匹配
        if current_img.shape != self.module.cached_item_image.shape:
            debug_info["error"] = f"尺寸不匹配: 当前{current_img.shape} vs 缓存{self.module.cached_item_image.shape}"
            
            # 保存两张图片供分析
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f"{self.debug_dir}/cached_{timestamp}.png", self.module.cached_item_image)
                cv2.imwrite(f"{self.debug_dir}/current_{timestamp}.png", current_img)
                debug_info["saved_images"] = f"cached_{timestamp}.png, current_{timestamp}.png"
            except:
                pass
            
            return False, debug_info
        
        try:
            # 转换为灰度图
            gray_cached = cv2.cvtColor(self.module.cached_item_image, cv2.COLOR_BGR2GRAY)
            gray_current = cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY)
            
            # 使用Canny边缘检测
            edges_cached = cv2.Canny(gray_cached, 50, 150)
            edges_current = cv2.Canny(gray_current, 50, 150)
            
            # 计算边缘相似度
            # 两个边缘图都是二值图像（0或255），差异像素就是值不同的像素
            diff_pixels = np.count_nonzero(cv2.absdiff(edges_cached, edges_current))
            total_pixels = edges_cached.size
            edge_similarity = 1 - (diff_pixels / total_pixels)
            
            debug_info["edge_similarity"] = f"{edge_similarity:.3f}"
            
            # 输出调试信息
            self.module.logger.log(f"  [调试] 边缘相似度: {edge_similarity:.3f}", "black")
            
            # 如果边缘相似度很低，保存图片供分析
            if edge_similarity < 0.8:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cache_path = f"{self.debug_dir}/cached_{timestamp}.png"
                current_path = f"{self.debug_dir}/current_{timestamp}.png"
                edges_cache_path = f"{self.debug_dir}/edges_cached_{timestamp}.png"
                edges_current_path = f"{self.debug_dir}/edges_current_{timestamp}.png"
                
                cv2.imwrite(cache_path, self.module.cached_item_image)
                cv2.imwrite(current_path, current_img)
                cv2.imwrite(edges_cache_path, edges_cached)
                cv2.imwrite(edges_current_path, edges_current)
                
                debug_info["saved_images"] = f"cached_{timestamp}.png, current_{timestamp}.png, edges_cached_{timestamp}.png, edges_current_{timestamp}.png"
                self.module.logger.log(f"  [调试] 已保存调试图片到 {self.debug_dir} 目录", "orange")
            
            # 判断标准：边缘相似度大于0.8认为货物还在
            return edge_similarity > 0.8, debug_info
            
        except Exception as e:
            debug_info["error"] = str(e)
            return False, debug_info
    
    def _reset_source_item(self):
        """重置货源物品配置"""
        self.module.ui.reset_source_item()
    
    def _reset_ui(self):
        """重置UI"""
        self.module.ui.set_button_state(False)