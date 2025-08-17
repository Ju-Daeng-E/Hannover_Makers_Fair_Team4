#!/usr/bin/env python3
"""
BMW Logger - Simple logging system for BMW gear control
BMW 기어 제어용 단순 로깅 시스템
"""

import logging
import os
from datetime import datetime
from typing import Optional

class Logger:
    """BMW 제어용 로거 클래스"""
    
    def __init__(self, name: str, level: str = 'INFO', log_file: Optional[str] = None):
        self.name = name
        self.level = getattr(logging, level.upper(), logging.INFO)
        
        # 로거 설정
        self.logger = logging.getLogger(f"BMW_{name}")
        self.logger.setLevel(self.level)
        
        # 기존 핸들러 제거 (중복 방지)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 포매터 설정
        formatter = logging.Formatter(
            '[%(asctime)s] BMW_%(name)s - %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 파일 핸들러 (옵션)
        if log_file:
            try:
                # 로그 디렉토리 생성
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"Failed to create log file {log_file}: {e}")
    
    def debug(self, message: str):
        self.logger.debug(f"🔍 {message}")
    
    def info(self, message: str):
        self.logger.info(f"ℹ️ {message}")
    
    def warning(self, message: str):
        self.logger.warning(f"⚠️ {message}")
    
    def error(self, message: str):
        self.logger.error(f"❌ {message}")
    
    def critical(self, message: str):
        self.logger.critical(f"🚨 {message}")