"""
基质助手扫描任务
"""

import time
import traceback
import threading
from .utils import is_gold, is_operated


class ScanTask:
    """扫描任务类"""
    
    def __init__(self, module):
        """
        初始化
        
        Args:
            module: 主模块实例
        """
        self.module = module
        self.running = False
        self.scan_thread = None
        self.stop_requested = False  # 是否请求停止
        self.reset_needed = False    # 是否需要完全重置
    
    def start(self):
        """开始扫描"""
        # 如果已有扫描线程在运行，先请求停止
        if self.scan_thread and self.scan_thread.is_alive():
            self.module.logger.log("正在停止当前扫描，请稍候...", "orange")
            self.stop_requested = True
            self.running = False
            
            # 等待线程结束，最多等3秒
            wait_count = 0
            while self.scan_thread.is_alive() and wait_count < 30:
                time.sleep(0.1)
                wait_count += 1
            
            if self.scan_thread.is_alive():
                self.module.logger.log("警告：旧扫描线程未完全退出", "red")
        
        # 重置所有状态
        self.running = True
        self.stop_requested = False
        self.reset_needed = False
        
        # 更新UI
        self.module.ui.set_button_state(True)
        self.module.ui.clear_lock_list()
        self.module.logger.clear()
        self.module.logger.log("扫描启动，按 'B' 键停止", "blue")
        
        # 启动新线程
        self.scan_thread = threading.Thread(target=self._run, daemon=True)
        self.scan_thread.start()
    
    def stop(self):
        """请求停止扫描"""
        self.module.logger.log("正在停止扫描...", "orange")
        self.stop_requested = True
        self.running = False
        self.reset_needed = True
    
    def _run(self):
        """运行扫描"""
        try:
            config = self.module.config
            roi = config["roi"]
            grid = config["grid"]
            lock = config["lock"]
            discard = config["discard"]
            matrix_size = config.get("matrix_size", (100, 100))
            
            current_row = 0  # 当前扫描的行数（从0开始，0表示第1行）
            scan_round = 1   # 扫描轮次
            last_position = None  # 记录上一个基质的位置，用于添加空行
            
            while self.running and not self.stop_requested:
                # 每行开始前检查停止标志
                if self.stop_requested:
                    break
                
                time.sleep(0.01)
                speed = float(self.module.ui.speed_var.get() or 0.3)
                scroll_dist = int(self.module.ui.dist_var.get() or 200)
                
                # 截图
                window_img = self.module.screenshot.capture_window()
                if window_img is None:
                    self.module.logger.log("截图失败", "red")
                    break
                
                self.module.logger.log(f"========== 开始扫描第 {current_row + 1} 行 (第 {scan_round} 轮) ==========", "black")
                
                # 遍历当前行的9个基质
                for col in range(9):
                    # 每个基质前检查停止标志
                    if self.stop_requested:
                        break
                    
                    # 计算当前基质的位置标识
                    current_position = f"{current_row+1}-{col+1}"
                    
                    # 如果不是第一个基质，添加空行分隔
                    if last_position is not None:
                        self.module.logger.log("", "black")  # 空行
                    
                    # 计算坐标
                    rx = int(grid["rx"] + col * grid["rdx"])
                    ry = int(grid["ry"] + min(current_row, 4) * grid["rdy"])
                    
                    # 检查金色
                    if self.module.ui.gold_only_var.get():
                        matrix_img = window_img[
                            max(0, ry - matrix_size[1]//2):ry + matrix_size[1]//2,
                            max(0, rx - matrix_size[0]//2):rx + matrix_size[0]//2
                        ]
                        if not is_gold(matrix_img):
                            self.module.logger.log(f"⚠️ 在第 {current_row + 1} 行遇到非金色基质，扫描结束", "orange")
                            self.module.logger.log("如需重新扫描，请再次点击开始按钮", "blue")
                            self.running = False
                            self.stop_requested = True
                            break
                    
                    # 点击基质前检查停止
                    if self.stop_requested:
                        break
                    
                    time.sleep(0.1)
                    self.module.click.click_relative(rx, ry)
                    
                    # 等待展开
                    time.sleep(speed)
                    
                    # 识别前检查停止
                    if self.stop_requested:
                        break
                    
                    region = self.module.screenshot.capture_region(
                        int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3])
                    )
                    
                    operation_performed = False
                    
                    if region is not None and not self.stop_requested:
                        text = self.module.ocr.recognize_text(region)
                        
                        # 检查匹配
                        matched = False
                        for weapon in self.module.weapon_list:
                            if self.stop_requested:
                                break
                            attrs = [weapon.get(f'毕业词条{i}', '') for i in range(1, 4)]
                            is_match, _, _ = self.module.ocr.match_attributes(attrs, text)
                            if is_match:
                                matched = True
                                self._handle_match(weapon, current_position)
                                break
                        
                        if matched and not self.stop_requested:
                            if not is_operated(window_img, lock):
                                self.module.click.click_relative(lock[0], lock[1])
                                self.module.logger.log(f"[{current_position}] ✅ 锁定毕业基质", "green")
                                operation_performed = True
                            else:
                                self.module.logger.log(f"[{current_position}] 🔒 已锁定", "blue")
                        elif not self.stop_requested:
                            if not is_operated(window_img, discard):
                                self.module.click.click_relative(discard[0], discard[1])
                                self.module.logger.log(f"[{current_position}] ❌ 弃置非毕业", "orange")
                                operation_performed = True
                            else:
                                self.module.logger.log(f"[{current_position}] ⚪ 已弃置", "gray")
                    
                    # 操作后等待
                    if operation_performed:
                        time.sleep(0.5)
                    
                    time.sleep(0.2)
                    
                    # 记录当前基质位置
                    last_position = current_position
                
                # 一行结束后，添加行分隔线
                if self.running and not self.stop_requested:
                    self.module.logger.log("----------------------------------------", "black")
                    
                    # 检查是否需要翻页
                    if current_row >= 4:
                        self.module.logger.log(f"📄 第 {current_row + 1} 行扫描完成，向上翻页", "black")
                        self._scroll_page(scroll_dist)
                        time.sleep(1.2)
                    
                    current_row += 1
                    
                    # 每5行算一轮，用于日志显示
                    if current_row % 5 == 0:
                        scan_round += 1
                    elif current_row > 0:
                        # 重置last_position，新的一行开始
                        last_position = None
                
            # 正常退出循环
            if self.stop_requested:
                self.module.logger.log("🛑 扫描已手动停止", "orange")
            elif not self.running:
                self.module.logger.log("🛑 扫描已自动停止", "orange")
                
        except Exception as e:
            self.module.logger.log(f"❌ 扫描异常: {e}", "red")
            traceback.print_exc()
        finally:
            # 确保所有状态都被重置
            self.running = False
            self.stop_requested = False
            self.reset_needed = False
            self.module.root.after(0, self._reset_ui)
            self.module.logger.log("扫描线程已结束", "orange")
    
    def _handle_match(self, weapon, position):
        """处理匹配结果"""
        self.module.root.after(0, self.module.ui.add_to_lock_list, weapon, position)
    
    def _scroll_page(self, distance):
        """翻页"""
        window_rect = self.module.game_window.get_window_rect()
        if not window_rect:
            return
        
        grid = self.module.config["grid"]
        
        # 计算滑动起始点（当前行的中间位置）
        start_x = window_rect[0] + grid["rx"] + 4 * grid["rdx"]
        start_y = window_rect[1] + grid["ry"] + 4 * grid["rdy"]
        
        self.module.click.move_absolute(start_x, start_y)
        self.module.click.move_absolute_smooth(start_x, start_y, start_x, start_y - distance, steps=16)
    
    def _reset_ui(self):
        """重置UI"""
        self.module.ui.set_button_state(False)