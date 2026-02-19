"""
终末地小助手 - 毕业基质自动识别工具
作者：洁柔厨 & 断绫
版本：beta1.0

核心功能：
1. 自动识别游戏中的毕业基质
2. 自动锁定符合条件的基质
3. 自动弃置不符合条件的基质
4. 支持多显示器环境
5. 后台截图识别（窗口被遮挡也能工作）

技术原理：
- 使用 win32gui 进行后台截图
- 使用 RapidOCR 进行文字识别
- 使用 OpenCC 进行简繁转换
- 使用 difflib 进行模糊匹配
"""

import os
import cv2
import numpy as np
import pydirectinput
import pyautogui
import mss
import time
import json
import csv
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox
from PIL import Image, ImageTk
from rapidocr_onnxruntime import RapidOCR
from opencc import OpenCC
from pynput import keyboard
import pygetwindow as gw
import ctypes
import threading
import difflib
import sys
import traceback

import win32gui
import win32ui
import win32con


# --- PyInstaller 路径适配函数 ---
def resource_path(relative_path):
    """
    获取资源的绝对路径，兼容 PyInstaller 打包后的环境
    
    原理：PyInstaller 打包后会将资源文件解压到临时目录，
    sys._MEIPASS 指向这个临时目录。开发环境下直接返回相对路径。
    
    Args:
        relative_path: 相对路径
        
    Returns:
        资源的绝对路径
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# --- 窗口矩形结构体，用于获取窗口位置 ---
class RECT(ctypes.Structure):
    """
    Windows RECT 结构体的 Python 实现
    用于存储窗口的边界坐标
    """
    _fields_ = [("left", ctypes.c_int), ("top", ctypes.c_int),
                ("right", ctypes.c_int), ("bottom", ctypes.c_int)]


def run_as_admin():
    """
    检查并请求管理员权限
    
    原理：某些操作（如后台截图、模拟点击）需要管理员权限。
    如果当前不是管理员，会通过 ShellExecute 以管理员身份重启程序。
    
    Returns:
        True: 已经是管理员权限
        False: 请求管理员权限后退出当前进程
    """
    try:
        if ctypes.windll.shell32.IsUserAnAdmin(): 
            return True
        executable = sys.executable
        if executable.endswith("python.exe"): 
            executable = executable.replace("python.exe", "pythonw.exe")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, __file__, None, 1)
        return False
    except:
        return False


# 设置 DPI 感知，确保在高 DPI 屏幕上坐标正确
try:
    # Windows 8.1+ 的 DPI 感知设置（2 = PerMonitorV2）
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try:
        # Windows Vista/7 的 DPI 感知设置
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# 设置模拟输入的参数
pydirectinput.PAUSE = 0.01  # 每次操作后的暂停时间
pyautogui.FAILSAFE = False   # 禁用 FAILSAFE（鼠标移动到角落不会触发异常）


class SelectionCanvas:
    """
    屏幕选区类 - 用于在屏幕上框选区域
    
    原理：创建一个半透明的全屏窗口，捕获鼠标事件，让用户框选区域。
    关键改进：自动检测游戏所在的显示器，只在该显示器上显示选区窗口。
    """
    
    def __init__(self, root, img_name, callback):
        """
        初始化选区界面
        
        Args:
            root: 主窗口
            img_name: 引导图片文件名
            callback: 选区完成后的回调函数，接收参数 (x, y, w, h)
        """
        self.root = root
        self.callback = callback
        
        # 获取游戏窗口所在的显示器
        self.target_monitor = self.get_game_monitor()
        
        # 如果没有找到游戏窗口，提示并退出
        if not self.target_monitor:
            messagebox.showerror("错误", "未检测到游戏窗口，请先启动游戏！")
            root.quit()  # 关闭主程序
            return
        
        print(f"使用显示器: left={self.target_monitor['left']}, top={self.target_monitor['top']}, "
              f"width={self.target_monitor['width']}, height={self.target_monitor['height']}")

        # 创建半透明覆盖层，只覆盖游戏所在的显示器
        self.top = tk.Toplevel(root)
        self.top.attributes("-alpha", 0.6, "-topmost", True)
        self.top.geometry(f"{self.target_monitor['width']}x{self.target_monitor['height']}+"
                         f"{self.target_monitor['left']}+{self.target_monitor['top']}")
        self.top.overrideredirect(True)  # 无边框窗口
        self.top.configure(bg="white")
        
        # 创建画布用于绘制选区矩形
        self.canvas = tk.Canvas(self.top, cursor="crosshair", bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # 显示引导图片（如果有）
        self.img_win = None
        img_path = resource_path(os.path.join("img", img_name))
        if os.path.exists(img_path):
            self.img_win = tk.Toplevel(root)
            self.img_win.attributes("-topmost", True)
            self.img_win.overrideredirect(True)
            img = Image.open(img_path)
            img.thumbnail((700, 500))
            self.tk_img = ImageTk.PhotoImage(img)

            # 在目标显示器中央显示引导图
            pos_x = self.target_monitor['left'] + (self.target_monitor['width'] - img.width) // 2
            pos_y = self.target_monitor['top'] + (self.target_monitor['height'] - img.height) // 2

            self.img_win.geometry(f"{img.width}x{img.height}+{pos_x}+{pos_y}")
            tk.Label(self.img_win, image=self.tk_img, bg="white", relief="solid", bd=2).pack()
            self.img_win.update_idletasks()
            self.root.after(50, lambda: self.img_win.lift() if self.img_win else None)
            self.root.after(3000, self.safe_destroy_img)  # 3秒后自动关闭引导图

        # 绑定鼠标事件
        self.start_x = self.start_y = self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)    # 鼠标按下
        self.canvas.bind("<B1-Motion>", self.on_drag)         # 鼠标拖动
        self.canvas.bind("<ButtonRelease-1>", self.on_release) # 鼠标释放
        self.canvas.bind("<Button-3>", lambda e: self.close()) # 右键取消
        self.top.bind("<Escape>", lambda e: self.close())      # ESC取消

    def get_game_monitor(self):
        """
        获取游戏窗口所在的显示器信息
        
        原理：先获取游戏窗口的位置，然后遍历所有显示器，
        找到包含窗口中心的显示器。
        
        Returns:
            显示器信息字典，包含 left, top, width, height
            如果找不到则返回 None
        """
        try:
            # 查找游戏窗口
            wins = gw.getWindowsWithTitle('Endfield') or gw.getWindowsWithTitle('终末地')
            if not wins:
                print("未找到游戏窗口")
                return None
            
            hwnd = wins[0]._hWnd
            
            # 获取游戏窗口位置
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            window_center_x = left + (right - left) // 2
            window_center_y = top + (bottom - top) // 2
            
            print(f"游戏窗口: left={left}, top={top}, right={right}, bottom={bottom}")
            
            # 获取所有显示器
            monitors = mss.mss().monitors
            
            # 找到包含窗口中心的显示器
            for i, mon in enumerate(monitors[1:], 1):  # 跳过 monitors[0]（虚拟桌面）
                if (mon['left'] <= window_center_x < mon['left'] + mon['width'] and
                    mon['top'] <= window_center_y < mon['top'] + mon['height']):
                    print(f"游戏窗口在显示器 {i} 上")
                    return mon
            
            print("未找到包含游戏窗口的显示器")
            return None
            
        except Exception as e:
            print(f"获取游戏显示器失败: {e}")
            return None

    def safe_destroy_img(self):
        """安全地销毁引导图片窗口"""
        if self.img_win and self.img_win.winfo_exists():
            self.img_win.destroy()
            self.img_win = None

    def on_press(self, event):
        """
        鼠标按下事件处理
        开始绘制选区矩形
        """
        self.safe_destroy_img()  # 开始选择时关闭引导图
        self.start_x, self.start_y = event.x, event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y, 
            outline="blue", width=4
        )

    def on_drag(self, event):
        """
        鼠标拖动事件处理
        更新选区矩形大小
        """
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        """
        鼠标释放事件处理
        计算选区坐标并调用回调
        """
        x1, x2 = min(self.start_x, event.x), max(self.start_x, event.x)
        y1, y2 = min(self.start_y, event.y), max(self.start_y, event.y)
        self.close()
        
        # 确保选区大于最小尺寸（防止误触）
        if (x2 - x1) > 10 and (y2 - y1) > 10:
            # 转换为屏幕绝对坐标
            screen_x = x1 + self.target_monitor['left']
            screen_y = y1 + self.target_monitor['top']
            self.callback(screen_x, screen_y, x2 - x1, y2 - y1)

    def close(self):
        """关闭选区窗口"""
        self.safe_destroy_img()
        if self.top.winfo_exists(): 
            self.top.destroy()


class Matrixassistant:
    """
    主程序类 - 负责所有核心功能
    
    功能模块：
    1. 配置文件管理
    2. 武器数据管理
    3. 错字纠正管理
    4. 屏幕识别与自动点击
    5. GUI界面管理
    """
    
    # ==================== 初始化与配置管理 ====================
    
    def __init__(self, root):
        """
        初始化主程序
        
        原理：
        1. 检查游戏窗口是否存在
        2. 加载配置文件
        3. 初始化OCR引擎
        4. 创建GUI界面
        """
        self.root = root
        self.root.title("终末地小助手beta1.0 by洁柔厨&断绫")
        self.root.geometry("690x880")
        self.root.attributes("-topmost", True)
        
        # 设置任务栏图标
        try:
            myappid = 'jierouchu.matrix.assistant.v17'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except:
            pass
        
        # 加载程序图标
        icon_path = resource_path(os.path.join("img", "jizhi.ico"))
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                self.tk_icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self.tk_icon)
            except:
                pass

        # === 检查游戏是否已启动 ===
        if not self.is_game_running():
            messagebox.showerror("错误", "未检测到游戏窗口，请先启动游戏！")
            root.quit()
            return

        # 文件路径
        self.config_file = resource_path("config.json")
        self.csv_file = resource_path("weapon_data.csv")
        self.corrections_file = resource_path("Jiucuo.json")
        
        # 初始化OCR引擎
        try:
            self.ocr = RapidOCR(intra_op_num_threads=4)  # 使用4线程加速
            self.cc = OpenCC('t2s')  # 繁转简转换器
        except Exception as e:
            messagebox.showerror("初始化失败", str(e))

        # 加载数据
        self.running = False
        self.data = self.load_config()
        self.weapon_list = self.load_weapon_csv()
        self.corrections = self.load_corrections()

        # 打印调试信息
        monitors = mss.mss().monitors
        print("=== 显示器信息 ===")
        for i, mon in enumerate(monitors):
            print(f"monitors[{i}]: left={mon['left']}, top={mon['top']}, "
                  f"width={mon['width']}, height={mon['height']}")
        
        game_pos = self.get_game_window_rect()
        print(f"游戏窗口位置: {game_pos}")

        # 创建GUI界面
        self.setup_gui()
        
        # 启动键盘监听（用于B键停止）
        self.kb = keyboard.Listener(on_press=self.on_press)
        self.kb.start()

    def is_game_running(self):
        """
        检查游戏窗口是否存在
        
        Returns:
            True: 游戏窗口存在
            False: 游戏窗口不存在
        """
        wins = gw.getWindowsWithTitle('Endfield') or gw.getWindowsWithTitle('终末地')
        return len(wins) > 0

    def load_config(self):
        """
        加载配置文件 config.json
        
        如果文件不存在或损坏，返回默认配置
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                return json.load(open(self.config_file, 'r', encoding='utf-8'))
            except:
                pass
        return {
            "roi": None, 
            "grid": None, 
            "lock": None,
            "discard": None,  # 新增：弃置按钮位置
            "matrix_size": None, 
            "speed": "0.2", 
            "scroll_pixel_dist": "90"
        }

    def load_corrections(self):
        """
        加载错字纠正库 Jiucuo.json
        
        Returns:
            错字纠正字典
        """
        if os.path.exists(self.corrections_file):
            try:
                return json.load(open(self.corrections_file, 'r', encoding='utf-8'))
            except:
                return {}
        return {}

    def load_weapon_csv(self):
        """
        加载武器数据 CSV 文件
        
        Returns:
            武器数据列表，每个元素为字典
        """
        ws = []
        if not os.path.exists(self.csv_file):
            print(f"当前工作目录: {os.getcwd()}")
            print(f"CSV文件路径: {self.csv_file}")
            print(f"文件是否存在: {os.path.exists(self.csv_file)}")
            messagebox.showwarning("缺少必要文件", f"未检测到武器文件：{self.csv_file}\n请确保文件在程序根目录下！")
            return ws
        try:
            with open(self.csv_file, 'r', encoding='utf-8-sig') as f:
                r = csv.DictReader(f)
                if r.fieldnames and "武器" in r.fieldnames:
                    for row in r: 
                        ws.append({k.strip(): v.strip() for k, v in row.items() if k})
                else:
                    messagebox.showerror("文件格式错误", "CSV格式不正确")
        except Exception as e:
            messagebox.showerror("读取失败", str(e))
        return ws

    def save_config(self):
        """
        保存配置到 config.json
        """
        try:
            self.data.update({
                "speed": self.speed_var.get(), 
                "scroll_pixel_dist": self.dist_var.get()
            })
        except:
            pass
        json.dump(self.data, open(self.config_file, 'w', encoding='utf-8'), 
                 ensure_ascii=False, indent=4)
        self.update_config_status()

    def update_config_status(self):
        """
        更新配置状态显示
        """
        ready = all(self.data.get(k) is not None for k in ["roi", "grid", "lock", "discard", "matrix_size"])
        if hasattr(self, 'top_status_var'): 
            self.top_status_var.set("✅ 配置已就绪" if ready else "❌ 配置不全")

    def get_game_window_rect(self):
        """
        获取游戏窗口的左上角坐标（绝对坐标）
        
        原理：使用 win32gui.GetWindowRect 获取窗口在屏幕上的实际位置
        
        Returns:
            (left, top) 元组，如果找不到窗口则返回 None
        """
        try:
            wins = gw.getWindowsWithTitle('Endfield') or gw.getWindowsWithTitle('终末地')
            if not wins: 
                print("未找到游戏窗口")
                return None
            
            hwnd = wins[0]._hWnd
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            print(f"游戏窗口位置: left={left}, top={top}, right={right}, bottom={bottom}")
            return (left, top)
        except Exception as e:
            print(f"获取窗口位置失败: {e}")
            return None

    # ==================== GUI 界面设置 ====================
    
    def setup_gui(self):
        """
        创建程序的主界面
        
        包含：
        1. 顶部状态栏
        2. 配置按钮区域
        3. 日志显示区域
        4. 已锁定列表区域
        """
        # UI 颜色定义
        MUTED_RED = "#B71C1C"
        GREEN = "#2E7D32"
        GOLD = "#FF9800"

        # === 顶部状态栏 ===
        header = tk.Frame(self.root)
        header.pack(anchor="nw", padx=10, pady=5, fill="x")
        
        # 左侧：配置状态和功能按钮
        lf = tk.Frame(header)
        lf.pack(side="left", anchor="nw")
        
        self.top_status_var = tk.StringVar()
        self.update_config_status()
        tk.Label(lf, textvariable=self.top_status_var, font=("微软雅黑", 9), fg="green").pack(anchor="w")
        
        tk.Button(lf, text="添加错字纠正", command=self.add_correction_popup, 
                 font=("微软雅黑", 8), bg="#F5F5F5", padx=2, pady=0).pack(anchor="w", pady=(2, 0))
        tk.Button(lf, text="修改武器数据", command=self.edit_weapon_popup, 
                 font=("微软雅黑", 8), bg="#F5F5F5", padx=2, pady=0).pack(anchor="w", pady=(2, 0))
        
        # 仅扫描金色基质选项
        self.gold_only_var = tk.BooleanVar(value=True)  # 默认勾选
        tk.Checkbutton(lf, text="仅扫描金色基质", variable=self.gold_only_var, 
                      font=("微软雅黑", 8)).pack(anchor="w", pady=(2, 0))

        # 右侧：参数设置和开始按钮
        rf = tk.Frame(header)
        rf.pack(side="left", anchor="nw", padx=(35, 0))
        
        r1 = tk.Frame(rf)
        r1.pack(anchor="w")
        tk.Label(r1, text="| 速度:").pack(side="left")
        self.speed_var = tk.StringVar(value=self.data.get("speed", "0.2"))
        tk.Entry(r1, textvariable=self.speed_var, width=5).pack(side="left", padx=0)
        tk.Label(r1, text=" | 翻页距离:").pack(side="left")
        self.dist_var = tk.StringVar(value=self.data.get("scroll_pixel_dist", "90"))
        tk.Entry(r1, textvariable=self.dist_var, width=5).pack(side="left", padx=0)
        
        r2 = tk.Frame(rf)
        r2.pack(anchor="w", pady=(2, 0))
        tk.Label(r2, text="推荐 0.2-0.5", font=("微软雅黑", 8), fg="#888888").pack(side="left", padx=(0, 0))
        tk.Label(r2, text="1080p推荐90 2k推荐140", font=("微软雅黑", 8), fg="#888888").pack(side="left", padx=(5, 0))
        
        self.run_btn = tk.Button(rf, text="▶ 开始自动扫描", command=self.start_thread, 
                                bg=GREEN, fg="white", font=("微软雅黑", 12, "bold"), width=15, height=1)
        self.run_btn.pack(anchor="center", pady=(5, 0))
        
        tk.Label(rf, text="（开始扫描后，按 'B' 键可停止）", 
                font=("微软雅黑", 9), fg=MUTED_RED).pack(anchor="center")

        # === 中间：配置按钮区域 ===
        mid = tk.Frame(self.root)
        mid.pack(pady=5)
        
        # 第一行配置按钮
        tk.Button(mid, text="基质框选", command=self.set_matrix_roi, width=12).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(mid, text="框选识别区", command=self.set_roi, width=12).grid(row=0, column=1, padx=5, pady=5)
        tk.Button(mid, text="校准网格", command=self.set_grid, width=12).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(mid, text="校准锁定键", command=self.set_lock, width=12).grid(row=1, column=1, padx=5, pady=5)
        
        # 第二行新增的校准弃置按钮
        tk.Button(mid, text="校准弃置", command=self.set_discard, width=12, bg="#FF9800", fg="white").grid(row=2, column=0, columnspan=2, padx=5, pady=5)

        # === 实时日志区域 ===
        tk.Label(self.root, text="实时日志:", font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=10)
        self.log_area = scrolledtext.ScrolledText(self.root, height=10, width=60, font=("微软雅黑", 12))
        self.log_area.pack(padx=10, pady=5)
        
        # 配置日志颜色标签
        for t, c in [("black", "black"), ("green", GREEN), ("gold", GOLD), 
                     ("red", MUTED_RED), ("blue", "blue"), ("orange", "#FF9800")]: 
            self.log_area.tag_config(t, foreground=c)

        # === 已锁定列表区域 ===
        tk.Label(self.root, text="已锁定列表:", font=("微软雅黑", 11, "bold"), fg=MUTED_RED).pack(anchor="w", padx=10)
        self.lock_list_area = scrolledtext.ScrolledText(self.root, height=8, width=60, 
                                                        font=("微软雅黑", 12), bg="#F9F9F9")
        self.lock_list_area.pack(padx=10, pady=5, fill="x")
        
        # 配置列表颜色标签
        for t, c in [("red_text", MUTED_RED), ("gold_text", GOLD), 
                     ("green_text", GREEN), ("black_text", "black"), ("orange_text", "#FF9800")]: 
            self.lock_list_area.tag_config(t, foreground=c)

    # ==================== 配置校准功能 ====================
    
    def set_matrix_roi(self):
        """
        基质框选功能
        
        让用户框选一个基质的完整区域，用于后续的金色识别
        """
        SelectionCanvas(self.root, "guide_matrix.png",
                       lambda x, y, w, h: self._handle_matrix_roi_selection(x, y, w, h))

    def _handle_matrix_roi_selection(self, x, y, w, h):
        """
        处理基质框选结果
        
        Args:
            x, y: 选区左上角屏幕绝对坐标
            w, h: 选区宽度和高度
        """
        self.data.update({"matrix_size": (w, h)})
        self.save_config()
        print(f"基质框选完成: 尺寸 ({w}, {h})")

    def set_roi(self):
        """
        框选识别区功能
        
        让用户框选词条识别区域
        """
        SelectionCanvas(self.root, "guide_roi.png", 
                       lambda x, y, w, h: self._handle_roi_selection(x, y, w, h))

    def _handle_roi_selection(self, x, y, w, h):
        """
        处理识别区框选结果
        
        原理：将屏幕绝对坐标转换为相对于游戏窗口的坐标
        这样即使游戏窗口移动，配置依然有效
        
        Args:
            x, y: 选区左上角屏幕绝对坐标
            w, h: 选区宽度和高度
        """
        print(f"点击屏幕坐标: ({x}, {y})")
        game_pos = self.get_game_window_rect()
        print(f"游戏窗口左上角: {game_pos}")
        
        # 转换为相对坐标
        rel_x = x - game_pos[0] if game_pos else x
        rel_y = y - game_pos[1] if game_pos else y
        print(f"相对坐标: ({rel_x}, {rel_y})")
        
        self.data.update({"roi": (rel_x, rel_y, w, h)})
        self.save_config()

    def set_grid(self):
        """
        校准网格功能
        
        需要用户依次点击三个点来确定网格布局：
        点1: (1,1) 位置的中心
        点2: (1,2) 位置的中心  
        点3: (2,1) 位置的中心
        
        原理：通过三个点计算出所有基质的位置网格
        """
        self.get_click("点：(1, 1)中心", self._handle_grid_p1, "guide_grid.png")

    def _handle_grid_p1(self, rx, ry):
        """
        处理第一个网格点
        
        Args:
            rx, ry: 点击位置的屏幕绝对坐标
        """
        self.data["grid"] = {"p11": (rx, ry)}
        self.get_click("点：(1, 2)中心", self._handle_grid_p2, None)

    def _handle_grid_p2(self, rx, ry):
        """
        处理第二个网格点
        
        Args:
            rx, ry: 点击位置的屏幕绝对坐标
        """
        self.data["grid"]["p12"] = (rx, ry)
        self.get_click("点：(2, 1)中心", self._handle_grid_p3, None)

    def _handle_grid_p3(self, rx, ry):
        """
        处理第三个网格点，并计算网格参数
        
        原理：
        rx = p11.x - 游戏窗口.x  (基准点相对游戏窗口的X偏移)
        ry = p11.y - 游戏窗口.y  (基准点相对游戏窗口的Y偏移)
        rdx = p12.x - p11.x      (相邻基质间的X方向距离)
        rdy = 第三个点.y - p11.y  (相邻基质间的Y方向距离)
        
        Args:
            rx, ry: 点击位置的屏幕绝对坐标
        """
        game_pos = self.get_game_window_rect()
        if not game_pos:
            messagebox.showerror("错误", "未找到游戏窗口")
            return
        
        gx, gy = game_pos
        p11 = self.data["grid"]["p11"]
        
        # 计算网格参数
        self.data["grid"].update({
            "rx": p11[0] - gx,           # 基准点相对X偏移
            "ry": p11[1] - gy,           # 基准点相对Y偏移
            "rdx": self.data["grid"]["p12"][0] - p11[0],  # X方向间距
            "rdy": ry - p11[1]            # Y方向间距
        })
        self.save_config()

    def set_lock(self):
        """
        校准锁定键功能
        
        让用户点击游戏中锁定图标的中心位置
        """
        self.get_click("点击锁定图标中心", self._handle_lock_selection, "guide_lock.png")

    def _handle_lock_selection(self, rx, ry):
        """
        处理锁定键校准结果
        
        原理：将屏幕绝对坐标转换为相对于游戏窗口的坐标
        
        Args:
            rx, ry: 点击位置的屏幕绝对坐标
        """
        print(f"锁定图标屏幕坐标: ({rx}, {ry})")
        game_pos = self.get_game_window_rect()
        print(f"游戏窗口左上角: {game_pos}")
        
        rel_x = rx - game_pos[0] if game_pos else rx
        rel_y = ry - game_pos[1] if game_pos else ry
        print(f"相对坐标: ({rel_x}, {rel_y})")
        
        self.data.update({"lock": (rel_x, rel_y)})
        self.save_config()

    def set_discard(self):
        """
        校准弃置键功能
        
        让用户点击游戏中弃置图标的中心位置
        """
        self.get_click("点击弃置图标中心", self._handle_discard_selection, None)

    def _handle_discard_selection(self, rx, ry):
        """
        处理弃置键校准结果
        
        原理：将屏幕绝对坐标转换为相对于游戏窗口的坐标
        
        Args:
            rx, ry: 点击位置的屏幕绝对坐标
        """
        print(f"弃置图标屏幕坐标: ({rx}, {ry})")
        game_pos = self.get_game_window_rect()
        print(f"游戏窗口左上角: {game_pos}")
        
        rel_x = rx - game_pos[0] if game_pos else rx
        rel_y = ry - game_pos[1] if game_pos else ry
        print(f"相对坐标: ({rel_x}, {rel_y})")
        
        self.data.update({"discard": (rel_x, rel_y)})
        self.save_config()

    def get_click(self, prompt, callback, img_name=None):
        """
        通用点击获取函数
        
        原理：创建一个半透明覆盖层，提示用户点击某个位置
        
        Args:
            prompt: 提示文字
            callback: 点击后的回调函数，接收参数 (x, y)
            img_name: 可选的引导图片文件名
        """
        # 获取游戏窗口所在的显示器
        target_monitor = None
        try:
            wins = gw.getWindowsWithTitle('Endfield') or gw.getWindowsWithTitle('终末地')
            if wins:
                hwnd = wins[0]._hWnd
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                window_center_x = left + (right - left) // 2
                window_center_y = top + (bottom - top) // 2
                
                monitors = mss.mss().monitors
                for mon in monitors[1:]:
                    if (mon['left'] <= window_center_x < mon['left'] + mon['width'] and
                        mon['top'] <= window_center_y < mon['top'] + mon['height']):
                        target_monitor = mon
                        break
        except:
            pass
        
        if not target_monitor:
            monitors = mss.mss().monitors
            target_monitor = monitors[1] if len(monitors) > 1 else monitors[0]
        
        # 创建覆盖层
        ov = tk.Toplevel(self.root)
        ov.attributes("-alpha", 0.6, "-topmost", True)
        ov.geometry(f"{target_monitor['width']}x{target_monitor['height']}+"
                   f"{target_monitor['left']}+{target_monitor['top']}")
        ov.overrideredirect(True)
        ov.configure(bg="white")
        
        # 显示引导图
        img_w = None
        if img_name:
            img_path = resource_path(os.path.join("img", img_name))
            if os.path.exists(img_path):
                img_w = tk.Toplevel(self.root)
                img_w.attributes("-topmost", True)
                img_w.overrideredirect(True)
                pi = Image.open(img_path)
                pi.thumbnail((700, 500))
                tki = ImageTk.PhotoImage(pi)
                
                # 在目标显示器中央显示
                pos_x = target_monitor['left'] + (target_monitor['width'] - pi.width) // 2
                pos_y = target_monitor['top'] + (target_monitor['height'] - pi.height) // 2
                
                img_w.geometry(f"{pi.width}x{pi.height}+{pos_x}+{pos_y}")
                tk.Label(img_w, image=tki, bg="white", relief="solid", bd=2).pack()
                img_w.image = tki
                self.root.after(50, lambda: img_w.lift() if img_w else None)

                def safe_close_img():
                    if img_w and img_w.winfo_exists():
                        img_w.destroy()

                self.root.after(3000, safe_close_img)

        def on_click(event):
            """点击事件处理"""
            if img_w and img_w.winfo_exists():
                img_w.destroy()
            ov.destroy()
            # 转换为屏幕绝对坐标
            screen_x = event.x_root
            screen_y = event.y_root
            print(f"点击屏幕坐标: ({screen_x}, {screen_y})")
            callback(screen_x, screen_y)

        ov.bind("<Button-1>", on_click)
        tk.Label(ov, text=prompt, font=("微软雅黑", 22, "bold"), 
                fg="red", bg="white").pack(expand=True)

    # ==================== 辅助功能 ====================
    
    def edit_weapon_popup(self):
        """
        武器数据编辑器
        
        提供一个表格界面，让用户可以增删改武器数据
        """
        editor_win = tk.Toplevel(self.root)
        editor_win.title("武器数据编辑器")
        editor_win.geometry("900x650")
        editor_win.minsize(1150, 500)
        editor_win.attributes("-topmost", True)

        # 顶部固定区：说明与搜索
        top_bar = tk.Frame(editor_win)
        top_bar.pack(fill="x", padx=10, pady=5)

        # 搜索框区域
        search_frame = tk.Frame(top_bar, pady=10)
        search_frame.pack(side="bottom", fill="x")
        tk.Label(search_frame, text="搜索武器:", font=("微软雅黑", 10, "bold")).pack(side="left", padx=(0, 5))

        search_var = tk.StringVar()
        search_ent = tk.Entry(search_frame, textvariable=search_var, font=("微软雅黑", 10), width=30)
        search_ent.pack(side="left")
        tk.Label(search_frame, text="(支持模糊匹配)", fg="#999", font=("微软雅黑", 8)).pack(side="left", padx=5)

        # 滚动区域
        container = tk.Frame(editor_win)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_frame = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def configure_canvas(event):
            if scrollable_frame.winfo_reqwidth() < event.width:
                canvas.itemconfigure(canvas_frame, width=event.width)

        canvas.bind("<Configure>", configure_canvas)
        canvas.configure(yscrollcommand=scrollbar.set)

        # 滚轮支持
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 表头
        headers = ["武器名称", "星级", "毕业词条1", "毕业词条2", "毕业词条3", "管理操作"]
        header_widths = [20, 10, 18, 18, 18, 10]
        for i, h in enumerate(headers):
            tk.Label(scrollable_frame, text=h, font=("微软雅黑", 10, "bold"), 
                    width=header_widths[i]).grid(row=0, column=i, padx=2, pady=5)

        self.table_rows = []

        # 搜索过滤逻辑
        def do_search(*args):
            query = search_var.get().strip().lower()
            for row_list in self.table_rows:
                weapon_name = row_list[0].get().strip().lower()
                if query in weapon_name:
                    for widget in row_list:
                        widget.grid()
                else:
                    for widget in row_list:
                        widget.grid_remove()

        search_var.trace_add("write", do_search)

        def add_row_ui(data=None):
            """添加一行编辑控件"""
            row_idx = len(self.table_rows) + 1
            row_widgets = []
            default_vals = data if data else {"武器": "", "星级": "", "毕业词条1": "", 
                                             "毕业词条2": "", "毕业词条3": ""}

            fields = ["武器", "星级", "毕业词条1", "毕业词条2", "毕业词条3"]
            widths = [18, 8, 16, 16, 16]
            for col, field in enumerate(fields):
                e = tk.Entry(scrollable_frame, width=widths[col], font=("微软雅黑", 10))
                e.insert(0, default_vals.get(field, ""))
                e.grid(row=row_idx, column=col, padx=5, pady=2, sticky="ew")
                row_widgets.append(e)

            # 删除按钮
            btn_del = tk.Button(scrollable_frame, text="删除", fg="white", bg="#d32f2f",
                               command=lambda r=row_widgets: remove_row(r))
            btn_del.grid(row=row_idx, column=5, padx=10, pady=2)
            row_widgets.append(btn_del)

            self.table_rows.append(row_widgets)

        def remove_row(row_widgets):
            """删除一行"""
            for w in row_widgets: 
                w.destroy()
            if row_widgets in self.table_rows:
                self.table_rows.remove(row_widgets)

        # 加载现有数据
        for weapon in self.weapon_list:
            add_row_ui(weapon)

        # 底部按钮区
        footer = tk.Frame(editor_win)
        footer.pack(fill="x", pady=15)

        def save_all():
            """保存所有修改"""
            new_data = []
            for row in self.table_rows:
                try:
                    if not row[0].winfo_exists(): 
                        continue
                    vals = [row[i].get().strip() for i in range(5)]
                    if not vals[0]: 
                        continue
                    new_data.append({
                        "武器": vals[0], 
                        "星级": vals[1] if "星" in vals[1] else f"{vals[1]}星",
                        "毕业词条1": vals[2], 
                        "毕业词条2": vals[3], 
                        "毕业词条3": vals[4]
                    })
                except:
                    continue

            try:
                with open(self.csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=["武器", "星级", "毕业词条1", "毕业词条2", "毕业词条3"])
                    writer.writeheader()
                    writer.writerows(new_data)
                self.weapon_list = new_data
                messagebox.showinfo("成功", "数据已保存！")
                editor_win.destroy()
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

        tk.Button(footer, text="+ 新增一行", command=add_row_ui, 
                 bg="#f0f0f0", width=15).pack(side="left", padx=30)
        tk.Button(footer, text="💾 保存所有修改", command=save_all, 
                 bg="#2E7D32", fg="white", font=("微软雅黑", 10, "bold"), 
                 width=20).pack(side="right", padx=30)

    def add_correction_popup(self):
        """
        添加错字纠正
        
        弹窗让用户输入错误文字和正确文字
        """
        p = tk.Toplevel(self.root)
        p.title("错字纠正")
        p.geometry("300x180")
        p.attributes("-topmost", True)
        
        w_ent = tk.Entry(p, width=15)
        r_ent = tk.Entry(p, width=15)
        
        tk.Label(p, text="错误文字").grid(row=0, column=0, padx=10, pady=10)
        tk.Label(p, text="正确文字").grid(row=0, column=1, padx=10, pady=10)
        w_ent.grid(row=1, column=0, padx=10, pady=5)
        r_ent.grid(row=1, column=1, padx=10, pady=5)

        def confirm():
            w = w_ent.get().strip()
            r = r_ent.get().strip()
            if w and r:
                self.corrections[w] = r
                json.dump(self.corrections, open(self.corrections_file, 'w', encoding='utf-8'),
                         ensure_ascii=False, indent=4)
                p.destroy()

        tk.Button(p, text="确认添加", command=confirm, 
                 bg="#2E7D32", fg="white", width=15).grid(row=2, column=0, columnspan=2, pady=20)

    # ==================== 截图与图像处理 ====================
    
    def capture_window_bg(self, hwnd):
        """
        后台截图函数
        
        原理：使用 PrintWindow API 捕获窗口内容，即使窗口被遮挡也能正常工作
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            OpenCV 格式的图像 (BGR)，失败时返回 None
        """
        try:
            # 获取客户区大小
            l, t, r, b = win32gui.GetClientRect(hwnd)
            w, h = r - l, b - t
            
            # 获取窗口DC
            hDC = win32gui.GetWindowDC(hwnd)
            mDC = win32ui.CreateDCFromHandle(hDC)
            sDC = mDC.CreateCompatibleDC()
            
            # 创建位图
            sBM = win32ui.CreateBitmap()
            sBM.CreateCompatibleBitmap(mDC, w, h)
            sDC.SelectObject(sBM)
            
            # 使用 PrintWindow 捕获窗口内容
            ctypes.windll.user32.PrintWindow(hwnd, sDC.GetSafeHdc(), 2)
            
            # 转换位图为 numpy 数组
            bits = sBM.GetBitmapBits(True)
            img = np.frombuffer(bits, dtype='uint8')
            img.shape = (h, w, 4)  # BGRA 格式
            
            # 清理资源
            win32gui.DeleteObject(sBM.GetHandle())
            sDC.DeleteDC()
            mDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hDC)
            
            # 转换为 BGR 格式（OpenCV 使用）
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        except Exception as e:
            print(f"截图失败: {e}")
            return None

    def is_gold(self, bgr):
        """
        判断基质是否为金色（毕业品质）
        
        原理：检查基质底部的颜色是否在金色的HSV范围内
        金色在HSV中的范围：Hue 15-35，Saturation > 100，Value > 100
        
        Args:
            bgr: OpenCV BGR 图像
            
        Returns:
            True: 是金色基质
            False: 不是金色基质
        """
        try:
            h, w = bgr.shape[:2]
            # 只检查底部30%区域
            strip = bgr[int(h * 0.70):, :]
            
            # 转换为HSV颜色空间
            hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
            
            # 创建金色掩码
            mask = cv2.inRange(hsv, np.array([15, 100, 100]), np.array([35, 255, 255]))
            
            # 计算金色像素占比
            gold_ratio = np.sum(mask > 0) / mask.size
            return gold_ratio > 0.05
        except:
            return False

    def is_already_locked(self, window_img, pos):
        """
        检查基质是否已经锁定
        
        原理：锁定后图标会变成深色，检查锁定图标区域的白色像素比例
        
        Args:
            window_img: 游戏窗口截图
            pos: 图标位置（相对游戏窗口的坐标）
            
        Returns:
            True: 已锁定
            False: 未锁定
        """
        try:
            lx, ly = int(pos[0]), int(pos[1])
            icon_size = 54  # 4K屏幕下图标大小
            
            # 计算检测区域
            top = max(0, ly - icon_size//2)
            bottom = min(window_img.shape[0], ly + icon_size//2)
            left = max(0, lx - icon_size//2)
            right = min(window_img.shape[1], lx + icon_size//2)
            
            search_scope = window_img[top:bottom, left:right]
            
            # 转换为灰度图并二值化
            gray = cv2.cvtColor(search_scope, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
            
            # 计算白色像素占比
            white_ratio = np.count_nonzero(binary) / binary.size
            # 白色像素少说明已操作
            return white_ratio < 0.2
            
        except Exception as e:
            self.gui_log(f"[状态检测异常] {e}", "red")
            return False

    # ==================== 文字识别与处理 ====================
    
    def clean_text(self, raw):
        """
        清理OCR识别出的文本
        
        步骤：
        1. 繁转简
        2. 去除非中文字符
        3. 应用错字纠正
        
        Args:
            raw: 原始文本
            
        Returns:
            清理后的文本
        """
        if not raw: 
            return ""
        
        # 繁转简
        txt = self.cc.convert(str(raw))
        
        # 只保留中文和逗号
        txt = re.sub(r'[^\u4e00-\u9fff，]', '', txt)
        
        # 应用错字纠正（按长度降序替换，避免部分替换）
        if self.corrections:
            for w in sorted(self.corrections.keys(), key=len, reverse=True):
                txt = txt.replace(w, self.corrections[w])
        
        return txt

    def check_all_attributes(self, weapon, ocr_full):
        """
        检查OCR结果是否匹配武器的毕业词条
        
        原理：使用模糊匹配，计算每个词条的相似度
        
        Args:
            weapon: 武器数据字典
            ocr_full: OCR识别的完整文本（逗号分隔）
            
        Returns:
            True: 匹配毕业词条
            False: 不匹配
        """
        # 获取武器的毕业词条
        ts = [self.clean_text(weapon.get(f'毕业词条{i}', '')) for i in range(1, 4) 
              if weapon.get(f'毕业词条{i}', '')]
        
        # 获取OCR识别的词条
        pts = [self.clean_text(p) for p in ocr_full.split("，") if p.strip()]
        
        if not ts or not pts:
            return False
        
        h_hits = 0  # 高置信度匹配
        p_hits = 0  # 中置信度匹配
        m_idx = set()  # 已匹配的词条索引
        
        for t in ts:
            t_c = t.replace("提升", "")  # 移除"提升"二字，提高匹配率
            best_r = 0
            b_idx = -1
            
            for i, p in enumerate(pts):
                if i in m_idx:
                    continue
                # 计算相似度
                r = difflib.SequenceMatcher(None, t_c, p.replace("提升", "")).ratio()
                if r > best_r:
                    best_r = r
                    b_idx = i
            
            if best_r >= 0.85:
                h_hits += 1
                m_idx.add(b_idx)
            elif best_r >= 0.6:
                p_hits += 1
                m_idx.add(b_idx)
        
        # 匹配条件：
        # 1. 所有词条都高置信度匹配
        # 2. 或缺失一个但其他匹配（包括中置信度）
        return (h_hits == len(ts)) or (h_hits >= len(ts) - 1 and (h_hits + p_hits) >= len(ts))

    # ==================== 自动扫描核心逻辑 ====================
    
    def start_thread(self):
        """
        启动扫描线程
        
        检查配置是否完整，然后在后台线程中运行扫描任务
        """
        if not all(self.data.get(k) is not None for k in ["roi", "grid", "lock", "discard", "matrix_size"]):
            messagebox.showwarning("提示", "首次运行请完成配置")
            return
        
        self.save_config()
        self.corrections = self.load_corrections()
        self.log_area.delete('1.0', tk.END)
        self.lock_list_area.delete('1.0', tk.END)
        self.gui_log("[系统] 扫描启动，按 'B' 键停止", "blue")
        
        self.running = True
        self.run_btn.config(state="disabled", text="正在扫描...")
        threading.Thread(target=self.run_task, daemon=True).start()

    def run_task(self):
        """
        扫描任务主循环
        
        流程：
        1. 获取配置参数
        2. 循环遍历所有基质位置
        3. 对每个位置判断是否为金色（如果启用了仅扫描金色）
        4. 点击基质并截图识别词条
        5. 如果匹配武器库且未锁定，点击锁定
        6. 如果不匹配武器库且未弃置，点击弃置
        7. 翻页继续扫描
        """
        try:
            roi = self.data["roi"]
            grid = self.data["grid"]
            lock = self.data["lock"]
            discard = self.data["discard"]
            ms = self.data.get("matrix_size", (100, 100))
            
            hwnd = win32gui.FindWindow(None, 'Endfield') or win32gui.FindWindow(None, '终末地')
            curr_row = 0
            
            while self.running:
                time.sleep(0.01)
                spd = float(self.speed_var.get() or 0.3)
                dist = int(self.dist_var.get() or 200)
                
                # 截图
                win_img = self.capture_window_bg(hwnd)
                if win_img is None:
                    self.gui_log("[错误] 后台截图失败", "red")
                    break
                
                # 遍历当前行的9个位置
                for c in range(9):
                    if not self.running:
                        break
                    
                    # 计算当前基质的坐标（相对游戏窗口）
                    rx = int(grid["rx"] + c * grid["rdx"])
                    ry = int(grid["ry"] + min(curr_row, 4) * grid["rdy"])
                    
                    # 检查是否为金色（如果需要）
                    check_gold = self.is_gold(win_img[
                        max(0, ry - int(ms[1] / 2)):ry + int(ms[1] / 2),
                        max(0, rx - int(ms[0] / 2)):rx + int(ms[0] / 2)
                    ])
                    
                    if self.gold_only_var.get() and not check_gold:
                        # 启用了仅扫描金色，但当前不是金色，停止扫描
                        self.gui_log(f"非金色基质，停止扫描")
                        self.running = False
                        break
                    
                    # 获取游戏窗口位置
                    wr = self.get_game_window_rect()
                    if not wr:
                        self.gui_log("[错误] 无法获取游戏窗口位置", "red")
                        break
                    
                    # 点击基质
                    pydirectinput.click(int(wr[0] + rx), int(wr[1] + ry))
                    time.sleep(spd)
                    
                    # 截图识别区域
                    scr = self.capture_window_bg(hwnd)
                    o_img = scr[
                        int(roi[1]):int(roi[1] + roi[3]),
                        int(roi[0]):int(roi[0] + roi[2])
                    ]
                    
                    # OCR识别
                    gray = cv2.cvtColor(o_img, cv2.COLOR_BGR2GRAY)
                    enlarged = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_NEAREST)
                    res, _ = self.ocr(cv2.cvtColor(enlarged, cv2.COLOR_GRAY2BGR))
                    
                    ft = "，".join([line[1] for line in res]) if res else ""
                    
                    # 准备日志信息
                    log_parts = [f"[{curr_row + 1}-{c + 1}]"]
                    
                    if ft:
                        cleaned_text = self.clean_text(ft)
                        log_parts.append(f"识别: {cleaned_text}")
                        
                        # 检查是否匹配武器库
                        matches = [w for w in self.weapon_list if self.check_all_attributes(w, ft)]
                        
                        if matches:
                            log_parts.append("✅ 毕业基质")
                            
                            # 检查是否已锁定
                            if self.is_already_locked(scr, lock):
                                log_parts.append("已锁定")
                            else:
                                # 点击锁定
                                pydirectinput.click(int(wr[0] + lock[0]), int(wr[1] + lock[1]))
                                log_parts.append("执行锁定")
                                time.sleep(0.2)
                                pydirectinput.moveRel(50, 50)
                            
                            # 记录到已锁定列表
                            self.add_to_lock_list(matches, f"{curr_row + 1}-{c + 1}")
                        else:
                            log_parts.append("❌ 非毕业")
                            
                            # 检查是否已弃置
                            if self.is_already_locked(scr, discard):
                                log_parts.append("已弃置")
                            else:
                                # 点击弃置
                                pydirectinput.click(int(wr[0] + discard[0]), int(wr[1] + discard[1]))
                                log_parts.append("执行弃置")
                                time.sleep(0.2)
                                pydirectinput.moveRel(50, 50)
                    else:
                        log_parts.append("识别失败")
                    
                    # 输出合并后的日志
                    self.gui_log(" ".join(log_parts), "black")
                
                if not self.running:
                    break
                
                # 检查是否需要翻页（每5行翻一页）
                if curr_row >= 4:
                    self.gui_log(f"[翻页] 向上滑动 {dist} 像素...", "black")
                    
                    wr = self.get_game_window_rect()
                    if not wr:
                        self.gui_log("[错误] 无法获取游戏窗口位置", "red")
                        break
                    
                    # 计算滑动起始位置（最后一行的最后一个基质）
                    sx = int(wr[0] + grid["rx"] + 4 * grid["rdx"])
                    sy = int(wr[1] + grid["ry"] + 4 * grid["rdy"])
                    
                    # 执行滑动操作
                    pydirectinput.moveTo(sx, sy)
                    pydirectinput.mouseDown()
                    time.sleep(0.1)
                    
                    # 平滑滑动
                    for s in range(16):
                        pydirectinput.moveTo(sx, int(sy - (dist * (s / 15))))
                        time.sleep(0.01)
                    
                    pydirectinput.mouseUp()
                    time.sleep(1.2)  # 等待翻页动画完成
                
                curr_row += 1
                
        except Exception as e:
            self.gui_log(f"[异常] {e}", "red")
            traceback.print_exc()
        finally:
            self.root.after(0, lambda: self.run_btn.config(state="normal", text="▶ 开始自动扫描"))

    def gui_log(self, message, tag="black"):
        """
        在日志区域显示消息
        
        Args:
            message: 要显示的消息
            tag: 颜色标签
        """
        self.log_area.insert(tk.END, message + "\n", tag)
        self.log_area.see(tk.END)

    def add_to_lock_list(self, matches, position):
        """
        将锁定的基质添加到已锁定列表
        
        Args:
            matches: 匹配的武器列表
            position: 位置坐标（行-列）
        """
        # 显示武器名称
        for w in matches:
            color = "red_text" if "6" in w.get('星级', '6') else "gold_text"
            self.lock_list_area.insert(tk.END, f"{w.get('武器', '未知')} ", color)
        
        # 显示词条
        words = [matches[0].get(f'毕业词条{i}', '') for i in range(1, 4) 
                if matches[0].get(f'毕业词条{i}', '')]
        self.lock_list_area.insert(tk.END, " " + "，".join(words) + " ", "green_text")
        
        # 显示坐标
        self.lock_list_area.insert(tk.END, "坐标" + position + "\n", "black_text")
        self.lock_list_area.see(tk.END)

    def on_press(self, key):
        """
        键盘按下事件处理
        
        按 'B' 键停止扫描
        
        Args:
            key: 按下的键
        """
        if hasattr(key, 'char') and key.char == 'b' and self.running:
            self.gui_log("[停止] 任务已中止", "red")
            self.running = False


if __name__ == "__main__":
    """
    程序入口点
    """
    if run_as_admin():
        root = tk.Tk()

        def handle_exception(exc_type, exc_value, exc_traceback):
            """全局异常处理"""
            error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            messagebox.showerror("运行错误", error_msg)

        sys.excepthook = handle_exception
        app = Matrixassistant(root)
        root.mainloop()