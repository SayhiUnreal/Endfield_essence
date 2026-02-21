"""
帝江号搬货UI界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext


class DJHTransportUI:
    """帝江号搬货UI类"""
    
    def __init__(self, parent, module):
        """
        初始化UI
        
        Args:
            parent: 父窗口
            module: 模块实例
        """
        self.parent = parent
        self.module = module
        self.tab = ttk.Frame(parent)
        
        # UI组件引用
        self.status_var = None
        self.direction_var = None
        self.rounds_var = None
        self.click_interval_var = None
        self.confirm_wait_var = None
        self.run_btn = None
        self.stop_btn = None
        self.fixed_buttons = []  # 固定配置按钮（不会重置）
        self.source_item_btn = None  # 货源物品按钮（会重置）
        
        self._setup_ui()
    
    def _setup_ui(self):
        """创建UI"""
        # === 标题和状态 ===
        title_frame = ttk.Frame(self.tab)
        title_frame.pack(fill="x", padx=5, pady=2)
        
        tk.Label(title_frame, text="帝江号搬货助手", 
                font=("微软雅黑", 14, "bold")).pack(side="left")
        
        self.status_var = tk.StringVar(value="⚪ 配置不完整")
        tk.Label(title_frame, textvariable=self.status_var, 
                font=("微软雅黑", 9), fg="blue").pack(side="right")
        
        # === 搬运方向选择 ===
        direction_frame = ttk.LabelFrame(self.tab, text="搬运方向", padding=2)
        direction_frame.pack(fill="x", padx=5, pady=2)
        
        self.direction_var = tk.StringVar(value="四号谷地→武陵仓库")
        dir_inner = ttk.Frame(direction_frame)
        dir_inner.pack(fill="x", padx=5, pady=2)
        
        tk.Radiobutton(dir_inner, text="四号谷地 → 武陵仓库", 
                      variable=self.direction_var, value="四号谷地→武陵仓库").pack(side="left", padx=5)
        tk.Radiobutton(dir_inner, text="武陵仓库 → 四号谷地", 
                      variable=self.direction_var, value="武陵仓库→四号谷地").pack(side="left", padx=5)
        
        # === 搬货轮数和操作参数 ===
        params_frame = ttk.Frame(self.tab)
        params_frame.pack(fill="x", padx=5, pady=2)
        
        # 搬货轮数
        rounds_frame = ttk.LabelFrame(params_frame, text="搬货轮数", padding=2)
        rounds_frame.pack(side="left", fill="x", expand=True, padx=(0,2))
        
        rounds_inner = ttk.Frame(rounds_frame)
        rounds_inner.pack(fill="x", padx=5, pady=2)
        
        self.rounds_var = tk.StringVar(value="10")
        tk.Entry(rounds_inner, textvariable=self.rounds_var, width=8).pack(side="left", padx=2)
        tk.Label(rounds_inner, text="(0=无限)", font=("微软雅黑", 8), fg="gray").pack(side="left", padx=2)
        
        # 操作参数
        op_frame = ttk.LabelFrame(params_frame, text="操作参数", padding=2)
        op_frame.pack(side="left", fill="x", expand=True, padx=(2,0))
        
        op_inner = ttk.Frame(op_frame)
        op_inner.pack(fill="x", padx=5, pady=2)
        
        # 点击间隔参数
        tk.Label(op_inner, text="点击间隔:", font=("微软雅黑", 8)).pack(side="left")
        self.click_interval_var = tk.StringVar(value="0.3")
        tk.Entry(op_inner, textvariable=self.click_interval_var, width=4).pack(side="left", padx=1)
        tk.Label(op_inner, text="s", font=("微软雅黑", 8)).pack(side="left", padx=(0,10))
        
        # 确认等待参数
        tk.Label(op_inner, text="确认等待:", font=("微软雅黑", 8)).pack(side="left")
        self.confirm_wait_var = tk.StringVar(value="3.0")
        tk.Entry(op_inner, textvariable=self.confirm_wait_var, width=4).pack(side="left", padx=1)
        tk.Label(op_inner, text="s", font=("微软雅黑", 8)).pack(side="left")
        
        # 提示文字 - 固定参数说明
        param_hint = ttk.Frame(self.tab)
        param_hint.pack(fill="x", padx=5, pady=1)
        tk.Label(param_hint, text="固定参数: 切换等待1s | Ctrl按住0.5s | 填充等待0.5s", 
                font=("微软雅黑", 8), fg="gray").pack(anchor="w")
        
        # === 固定配置按钮区域（4个按钮，不会重置）===
        fixed_config_frame = ttk.LabelFrame(self.tab, text="固定配置（一次设置永久有效）", padding=2)
        fixed_config_frame.pack(fill="x", padx=5, pady=2)
        
        fixed_btn_inner = ttk.Frame(fixed_config_frame)
        fixed_btn_inner.pack(fill="x", padx=5, pady=2)
        
        fixed_configs = [
            ("校准切换按钮", self.module.calibrate_switch_button),
            ("框选仓库名字", self.module.calibrate_popup_roi),
            ("校准一键存放", self.module.calibrate_deposit_button),
            ("校准确认按钮", self.module.calibrate_confirm_button)
        ]
        
        # 一行四个按钮
        for text, cmd in fixed_configs:
            btn = tk.Button(fixed_btn_inner, text=text, command=cmd,
                          width=15, bg="#E3F2FD", height=1)
            btn.pack(side="left", padx=2, expand=True, fill="x")
            self.fixed_buttons.append(btn)
        
        # === 货源物品配置和搬货控制放在同一行 ===
        control_row = ttk.Frame(self.tab)
        control_row.pack(fill="x", padx=5, pady=5)
        
        # 货源物品按钮（每次都需要重新配置）
        self.source_item_btn = tk.Button(control_row, text="框选货源物品（每次搬货前必点）", 
                                        command=self.module.calibrate_source_item,
                                        width=25, bg="#FF9800", fg="white", height=1)
        self.source_item_btn.pack(side="left", padx=2, expand=True, fill="x")
        
        # 控制按钮
        btn_container = ttk.Frame(control_row)
        btn_container.pack(side="right")
        
        self.run_btn = tk.Button(btn_container, text="▶ 开始搬货",
                                command=self.module.start_transport,
                                bg="#2E7D32", fg="white",
                                font=("微软雅黑", 11, "bold"),
                                width=12, state="disabled")
        self.run_btn.pack(side="left", padx=5)
        
        self.stop_btn = tk.Button(btn_container, text="■ 停止搬货",
                                 command=self.module.stop_transport,
                                 bg="#B71C1C", fg="white",
                                 font=("微软雅黑", 11, "bold"),
                                 width=12, state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        # === 提示信息区域（两行合并为一行）===
        hint_frame = ttk.Frame(self.tab)
        hint_frame.pack(fill="x", padx=5, pady=1)
        
        # 左侧：配置取消提示
        tk.Label(hint_frame, text="配置过程中可按右键或ESC取消当前步骤", 
                font=("微软雅黑", 8), fg="orange").pack(side="left")
        
        # 右侧：停止快捷键提示
        tk.Label(hint_frame, text="搬货过程中按 B 键可停止", 
                font=("微软雅黑", 8), fg="#B71C1C").pack(side="right")
        
        # === 当前配置显示 ===
        config_frame = ttk.LabelFrame(self.tab, text="当前配置", padding=2)
        config_frame.pack(fill="x", padx=5, pady=2)
        
        self.config_text = tk.Text(config_frame, height=3, font=("微软雅黑", 8))
        self.config_text.pack(fill="x", padx=5, pady=2)
        
        # === 运行日志 ===
        log_frame = ttk.LabelFrame(self.tab, text="运行日志", padding=2)
        log_frame.pack(fill="both", expand=True, padx=5, pady=2)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=8, font=("微软雅黑", 9))
        self.log_area.pack(fill="both", expand=True, padx=5, pady=2)
        
        # 配置日志颜色标签
        for t, c in [("black", "black"), ("green", "#2E7D32"), ("red", "#B71C1C"),
                     ("blue", "blue"), ("orange", "#FF9800")]:
            self.log_area.tag_config(t, foreground=c)
        
        # 绑定日志控件
        self.module.logger.attach_log_widget(self.log_area)
        
        # 更新配置显示
        self._update_config_display()
    
    def _update_config_display(self):
        """更新配置显示"""
        self.config_text.delete('1.0', tk.END)
        
        direction = self.direction_var.get()
        rounds = self.rounds_var.get()
        config = self.module.config
        
        # 根据方向确定源仓库和目标仓库的显示
        if direction == "四号谷地→武陵仓库":
            source = "四号谷地"
            target = "武陵仓库"
        else:
            source = "武陵仓库"
            target = "四号谷地"
        
        switch = "✓" if config.get('switch_button') else "✗"
        popup = "✓" if config.get('popup_roi') else "✗"
        item = "✓" if config.get('source_item') else "✗"
        deposit = "✓" if config.get('deposit_button') else "✗"
        confirm = "✓" if config.get('confirm_button') else "✗"
        
        config_str = f"{source} → {target} | 轮数:{rounds}\n切换按钮:{switch} 仓库名字:{popup} 货源:{item} 一键存放:{deposit} 确认按钮:{confirm}"
        
        self.config_text.insert('1.0', config_str)
    
    def update_status(self, is_ready):
        """更新配置状态"""
        self.status_var.set("✅ 配置已就绪" if is_ready else "⚪ 配置不完整")
        self._update_config_display()
        
        # 当配置就绪时启用开始按钮
        if is_ready:
            self.run_btn.config(state="normal")
        else:
            self.run_btn.config(state="disabled")
    
    def reset_source_item(self):
        """重置货源物品配置（每次搬货结束后调用）"""
        if "source_item" in self.module.config:
            del self.module.config["source_item"]
        self.module.cached_item_image = None
        self.module.save_config()
        self._update_config_display()
        self.module.logger.log("货源物品配置已重置，请重新框选", "orange")
    
    def set_button_state(self, running):
        """设置按钮状态"""
        if running:
            self.run_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.source_item_btn.config(state="disabled")
            for btn in self.fixed_buttons:
                btn.config(state="disabled")
        else:
            self.run_btn.config(state="normal" if self._is_config_complete() else "disabled")
            self.stop_btn.config(state="disabled")
            self.source_item_btn.config(state="normal")
            for btn in self.fixed_buttons:
                btn.config(state="normal")
    
    def _is_config_complete(self):
        """检查配置是否完整"""
        return all(self.module.config.get(k) is not None 
                   for k in ["switch_button", "popup_roi", "source_item", "deposit_button", "confirm_button"])
    
    def get_tab(self):
        """获取标签页"""
        return self.tab