#!/usr/bin/env python3
"""
BMW Data Models - Data structures for BMW gear system
BMW 기어 시스템용 데이터 구조체들
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class BMWState:
    """BMW 상태 데이터 클래스"""
    current_gear: str = 'N'  # 현재 기어 (P/R/N/D/M1-M8)
    manual_gear: int = 1     # 수동 기어 단수
    lever_position: str = 'Unknown'  # 레버 위치
    park_button: str = 'Released'    # 파크 버튼 상태
    unlock_button: str = 'Released'  # 언락 버튼 상태
    last_update: Optional[str] = None  # 마지막 업데이트 시간
    
    def update_timestamp(self):
        """타임스탬프 업데이트"""
        self.last_update = datetime.now().strftime("%H:%M:%S")
        
    def is_valid_gear(self) -> bool:
        """유효한 기어인지 확인"""
        valid_gears = ['P', 'R', 'N', 'D']
        manual_gears = [f'M{i}' for i in range(1, 9)]  # M1-M8
        return self.current_gear in valid_gears + manual_gears