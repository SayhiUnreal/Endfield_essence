"""
配置管理模块
处理所有配置文件的读写
"""

import os
import json
import csv

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, resource_path_func):
        """
        初始化配置管理器
        
        Args:
            resource_path_func: 资源路径处理函数
        """
        self.resource_path = resource_path_func
        self.config_file = self.resource_path("config.json")
        self.csv_file = self.resource_path("weapon_data.csv")
        self.corrections_file = self.resource_path("Jiucuo.json")
        
        # 默认配置
        self.default_config = {
            "roi": None,
            "grid": None,
            "lock": None,
            "discard": None,
            "matrix_size": None,
            "speed": "0.2",
            "scroll_pixel_dist": "90",
            # 大厅抢单配置预留
            "hall_order": {
                "roi": None,
                "order_button": None,
                "refresh_button": None
            },
            # 帝江号搬货配置预留
            "djh_transport": {
                "pickup_points": [],
                "delivery_points": []
            }
        }
    
    def load_config(self):
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        if os.path.exists(self.config_file):
            try:
                config = json.load(open(self.config_file, 'r', encoding='utf-8'))
                # 合并默认配置，确保新配置项存在
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except:
                return self.default_config.copy()
        return self.default_config.copy()
    
    def save_config(self, config):
        """
        保存配置
        
        Args:
            config: 配置字典
        """
        try:
            json.dump(config, open(self.config_file, 'w', encoding='utf-8'),
                     ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def load_corrections(self):
        """
        加载错字纠正库
        
        Returns:
            错字纠正字典
        """
        if os.path.exists(self.corrections_file):
            try:
                return json.load(open(self.corrections_file, 'r', encoding='utf-8'))
            except:
                return {}
        return {}
    
    def save_corrections(self, corrections):
        """
        保存错字纠正
        
        Args:
            corrections: 错字纠正字典
        """
        try:
            json.dump(corrections, open(self.corrections_file, 'w', encoding='utf-8'),
                     ensure_ascii=False, indent=4)
            return True
        except:
            return False
    
    def load_weapon_data(self):
        """
        加载武器数据
        
        Returns:
            武器数据列表
        """
        weapons = []
        if not os.path.exists(self.csv_file):
            return weapons
        
        try:
            with open(self.csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames and "武器" in reader.fieldnames:
                    for row in reader:
                        weapons.append({k.strip(): v.strip() for k, v in row.items() if k})
        except Exception as e:
            print(f"读取武器数据失败: {e}")
        
        return weapons
    
    def save_weapon_data(self, weapons):
        """
        保存武器数据
        
        Args:
            weapons: 武器数据列表
        """
        try:
            with open(self.csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                fieldnames = ["武器", "星级", "毕业词条1", "毕业词条2", "毕业词条3"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(weapons)
            return True
        except Exception as e:
            print(f"保存武器数据失败: {e}")
            return False