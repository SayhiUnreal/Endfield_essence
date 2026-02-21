"""
OCR识别模块
封装 RapidOCR 功能
"""

import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR
from opencc import OpenCC
import re
import difflib

class OCRHelper:
    """OCR识别助手"""
    
    def __init__(self, corrections=None, logger=None):
        """
        初始化OCR
        
        Args:
            corrections: 错字纠正字典
            logger: 日志记录器
        """
        self.logger = logger
        self.ocr = RapidOCR(intra_op_num_threads=4)
        self.cc = OpenCC('t2s')  # 繁转简
        self.corrections = corrections or {}
    
    def recognize(self, image):
        """
        识别图像中的文字
        
        Args:
            image: OpenCV图像
            
        Returns:
            识别出的文字列表
        """
        if image is None:
            return []
        
        try:
            # 预处理：灰度化、放大
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            enlarged = cv2.resize(gray, None, fx=1.5, fy=1.5, 
                                 interpolation=cv2.INTER_NEAREST)
            
            # OCR识别
            result, _ = self.ocr(cv2.cvtColor(enlarged, cv2.COLOR_GRAY2BGR))
            
            if result:
                return [line[1] for line in result]
            return []
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"OCR识别失败: {e}", "red")
            return []
    
    def recognize_text(self, image):
        """
        识别并返回合并的文本
        
        Returns:
            合并后的文本
        """
        lines = self.recognize(image)
        return "，".join(lines) if lines else ""
    
    def clean_text(self, raw_text):
        """
        清理文本：繁转简、去除非中文、错字纠正
        
        Args:
            raw_text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not raw_text:
            return ""
        
        # 繁转简
        text = self.cc.convert(str(raw_text))
        
        # 去除非中文和逗号
        text = re.sub(r'[^\u4e00-\u9fff，]', '', text)
        
        # 错字纠正（按长度降序替换）
        if self.corrections:
            for wrong in sorted(self.corrections.keys(), key=len, reverse=True):
                if wrong in text:
                    text = text.replace(wrong, self.corrections[wrong])
        
        return text
    
    def match_attributes(self, weapon_attrs, ocr_text, threshold_high=0.85, threshold_low=0.6):
        """
        匹配武器词条
        
        Args:
            weapon_attrs: 武器的毕业词条列表
            ocr_text: OCR识别的文本
            threshold_high: 高置信度阈值
            threshold_low: 低置信度阈值
            
        Returns:
            (是否匹配, 高置信度匹配数, 中置信度匹配数)
        """
        # 清理词条
        target_attrs = [self.clean_text(attr) for attr in weapon_attrs if attr]
        recognized = [self.clean_text(p) for p in ocr_text.split("，") if p.strip()]
        
        if not target_attrs or not recognized:
            return False, 0, 0
        
        high_hits = 0
        low_hits = 0
        matched_indices = set()
        
        for target in target_attrs:
            target_clean = target.replace("提升", "")
            best_ratio = 0
            best_idx = -1
            
            for i, rec in enumerate(recognized):
                if i in matched_indices:
                    continue
                rec_clean = rec.replace("提升", "")
                ratio = difflib.SequenceMatcher(None, target_clean, rec_clean).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = i
            
            if best_ratio >= threshold_high:
                high_hits += 1
                matched_indices.add(best_idx)
            elif best_ratio >= threshold_low:
                low_hits += 1
                matched_indices.add(best_idx)
        
        # 匹配条件：所有词条都高置信度，或缺失一个但其他匹配
        is_match = (high_hits == len(target_attrs)) or \
                   (high_hits >= len(target_attrs) - 1 and (high_hits + low_hits) >= len(target_attrs))
        
        return is_match, high_hits, low_hits