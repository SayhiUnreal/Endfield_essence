"""
基质助手UI界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext


class MatrixAssistantUI:
    """基质助手UI类"""
    
    def __init__(self, parent, module):
        """
        初始化UI
        
        Args:
            parent: 父窗口
            module: 模块实例（用于回调）
        """
        self.parent = parent
        self.module = module
        self.tab = ttk.Frame(parent)
        
        # UI组件引用
        self.status_var = None
        self.speed_var = None
        self.dist_var = None
        self.gold_only_var = None
        self.run_btn = None
        self.lock_list = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """创建UI"""
        # === 顶部状态栏 ===
        header = ttk.Frame(self.tab)
        header.pack(fill="x", padx=10, pady=5)
        
        # 左侧
        left_frame = ttk.Frame(header)
        left_frame.pack(side="left", fill="y")
        
        self.status_var = tk.StringVar(value="❌ 配置不全")
        tk.Label(left_frame, textvariable=self.status_var, 
                font=("微软雅黑", 9), fg="green").pack(anchor="w")
        
        # 配置按钮
        tk.Button(left_frame, text="添加错字纠正", 
                 command=self.module.show_correction_dialog).pack(anchor="w", pady=2)
        tk.Button(left_frame, text="修改武器数据", 
                 command=self.module.show_weapon_editor).pack(anchor="w", pady=2)
        
        # 仅扫描金色选项
        self.gold_only_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left_frame, text="仅扫描金色基质", 
                      variable=self.gold_only_var).pack(anchor="w", pady=2)
        
        # 右侧参数
        right_frame = ttk.Frame(header)
        right_frame.pack(side="right", fill="y")
        
        param_frame = ttk.Frame(right_frame)
        param_frame.pack(anchor="e")
        
        tk.Label(param_frame, text="速度:").pack(side="left")
        self.speed_var = tk.StringVar(value="0.2")
        tk.Entry(param_frame, textvariable=self.speed_var, width=5).pack(side="left", padx=2)
        
        tk.Label(param_frame, text="翻页距离:").pack(side="left")
        self.dist_var = tk.StringVar(value="90")
        tk.Entry(param_frame, textvariable=self.dist_var, width=5).pack(side="left", padx=2)
        
        # 参数说明
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(anchor="e", pady=2)
        tk.Label(info_frame, text="推荐 0.2-0.5", 
                font=("微软雅黑", 8), fg="gray").pack(side="left")
        tk.Label(info_frame, text="1080p推荐90", 
                font=("微软雅黑", 8), fg="gray").pack(side="left", padx=5)
        
        # 开始按钮
        self.run_btn = tk.Button(right_frame, text="▶ 开始自动扫描",
                                command=self.module.start_scan,
                                bg="#2E7D32", fg="white",
                                font=("微软雅黑", 12, "bold"),
                                width=15, height=1)
        self.run_btn.pack(anchor="e", pady=5)
        
        tk.Label(right_frame, text="（开始扫描后，按 'B' 键可停止）",
                font=("微软雅黑", 9), fg="#B71C1C").pack(anchor="e")
        
        # === 配置按钮区 ===
        config_frame = ttk.Frame(self.tab)
        config_frame.pack(pady=10)
        
        # 第一行
        tk.Button(config_frame, text="基质框选", 
                 command=self.module.set_matrix_roi, width=12).grid(row=0, column=0, padx=5, pady=5)
        tk.Button(config_frame, text="框选识别区", 
                 command=self.module.set_roi, width=12).grid(row=0, column=1, padx=5, pady=5)
        
        # 第二行
        tk.Button(config_frame, text="校准网格", 
                 command=self.module.set_grid, width=12).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(config_frame, text="校准锁定键", 
                 command=self.module.set_lock, width=12).grid(row=1, column=1, padx=5, pady=5)
        
        # 第三行
        tk.Button(config_frame, text="校准弃置", 
                 command=self.module.set_discard, width=12, bg="#FF9800", fg="white").grid(
                     row=2, column=0, columnspan=2, padx=5, pady=5)
        
        # === 锁定列表 ===
        tk.Label(self.tab, text="已锁定列表:", font=("微软雅黑", 11, "bold"),
                fg="#B71C1C").pack(anchor="w", padx=10)
        
        self.lock_list = scrolledtext.ScrolledText(
            self.tab, height=8, font=("微软雅黑", 10), bg="#F9F9F9"
        )
        self.lock_list.pack(fill="x", padx=10, pady=5)
        
        # 配置列表颜色
        self.lock_list.tag_config("red_text", foreground="#B71C1C")
        self.lock_list.tag_config("gold_text", foreground="#FF9800")
        self.lock_list.tag_config("green_text", foreground="#2E7D32")
        self.lock_list.tag_config("black_text", foreground="black")
    
    def update_status(self, is_ready):
        """更新配置状态"""
        self.status_var.set("✅ 配置已就绪" if is_ready else "❌ 配置不全")
    
    def set_button_state(self, running):
        """设置按钮状态"""
        if running:
            self.run_btn.config(state="disabled", text="正在扫描...")
        else:
            self.run_btn.config(state="normal", text="▶ 开始自动扫描")
    
    def add_to_lock_list(self, weapon, position):
        """添加到锁定列表"""
        name = weapon.get('武器', '未知')
        attrs = [weapon.get(f'毕业词条{i}', '') for i in range(1, 4) 
                if weapon.get(f'毕业词条{i}', '')]
        
        color = "red_text" if "6" in weapon.get('星级', '') else "gold_text"
        self.lock_list.insert(tk.END, f"{name} ", color)
        self.lock_list.insert(tk.END, " " + "，".join(attrs) + " ", "green_text")
        self.lock_list.insert(tk.END, f"坐标{position}\n", "black_text")
        self.lock_list.see(tk.END)
    
    def clear_lock_list(self):
        """清空锁定列表"""
        self.lock_list.delete('1.0', tk.END)
    
    def get_tab(self):
        """获取标签页"""
        return self.tab