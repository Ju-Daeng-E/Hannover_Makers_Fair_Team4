#!/usr/bin/env python3
"""
BMW Lever Controller - BMW F-Series Gear Lever Control System
BMW F-Series 기어 레버 제어 시스템
"""

import can
import time
import crccheck
from typing import Dict, Callable, Optional
from data_models import BMWState
from logger import Logger

class BMW3FDCRC(crccheck.crc.Crc8Base):
    """BMW 3FD CRC 계산 클래스"""
    _poly = 0x1D
    _initvalue = 0x0
    _xor_output = 0x70

class BMW197CRC(crccheck.crc.Crc8Base):
    """BMW 197 CRC 계산 클래스"""
    _poly = 0x1D
    _initvalue = 0x0
    _xor_output = 0x53

class BMWLeverController:
    """BMW 레버 제어 로직 클래스"""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        
        # 레버 위치 매핑
        self.lever_position_map = {
            0x0E: 'Center',
            0x1E: 'Up (R)', 
            0x2E: 'Up+ (Beyond R)',
            0x3E: 'Down (D)',
            0x7E: 'Side (S)',
            0x5E: 'Manual Down (-)',
            0x6E: 'Manual Up (+)'
        }
        
        # 토글 제어 변수들
        self.current_lever_position = 0x0E
        self.previous_lever_position = 0x0E
        self.lever_returned_to_center = True
        self.lever_returned_to_manual_center = True
        self.last_toggle_time = 0
        self.toggle_timeout = 0.5  # 500ms
        
        # CRC 계산기
        self.crc_3fd = BMW3FDCRC()
        self.crc_197 = BMW197CRC()
        
        # LED 제어를 위한 카운터
        self.gws_counter = 0x01
        
        self.logger.info("BMW Lever Controller initialized")
        
    def decode_lever_message(self, msg: can.Message, bmw_state: BMWState) -> bool:
        """레버 메시지 디코딩"""
        if len(msg.data) < 4:
            self.logger.warning(f"Invalid message length: {len(msg.data)}")
            return False
            
        try:
            crc = msg.data[0]
            counter = msg.data[1]
            lever_pos = msg.data[2]
            park_btn = msg.data[3]
            
            self.logger.debug(f"Raw data: CRC=0x{crc:02X}, Counter=0x{counter:02X}, Lever=0x{lever_pos:02X}, Buttons=0x{park_btn:02X}")
            
            # 레버 위치 매핑
            bmw_state.lever_position = self.lever_position_map.get(
                lever_pos, f'Unknown (0x{lever_pos:02X})'
            )
            
            # 버튼 상태
            bmw_state.park_button = 'Pressed' if (park_btn & 0x01) != 0 else 'Released'
            bmw_state.unlock_button = 'Pressed' if (park_btn & 0x02) != 0 else 'Released'
            
            self.logger.debug(f"Lever: {bmw_state.lever_position}, Park: {bmw_state.park_button}, Unlock: {bmw_state.unlock_button}")
            
            # 토글 처리
            self.previous_lever_position = self.current_lever_position
            self.current_lever_position = lever_pos
            self._handle_toggle_action(lever_pos, park_btn, bmw_state)
            
            bmw_state.update_timestamp()
            return True
            
        except Exception as e:
            self.logger.error(f"Lever message decode error: {e}")
            return False
    
    def _handle_toggle_action(self, lever_pos: int, park_btn: int, bmw_state: BMWState):
        """토글 방식 기어 전환 처리"""
        current_time = time.time()
        unlock_pressed = (park_btn & 0x02) != 0
        
        # Unlock 버튼 처리 (Park에서 Neutral로)
        if unlock_pressed and bmw_state.current_gear == 'P' and lever_pos == 0x0E:
            bmw_state.current_gear = 'N'
            self.logger.info("🔓 Unlock: PARK → NEUTRAL")
            return
        
        # Park 버튼 처리 (어디서든 Park로)
        if (park_btn & 0x01) != 0 and lever_pos == 0x0E:
            bmw_state.current_gear = 'P'
            self.logger.info("🅿️ Park Button → PARK")
            return
        
        # 토글 타임아웃 체크
        if current_time - self.last_toggle_time < self.toggle_timeout:
            return
        
        # 센터 복귀 토글 처리
        if lever_pos == 0x0E and not self.lever_returned_to_center:
            self.lever_returned_to_center = True
            self._process_toggle_transition(bmw_state)
            self.last_toggle_time = current_time
        elif lever_pos != 0x0E:
            self.lever_returned_to_center = False

        # 수동 센터 복귀 토글 처리 (Side position)
        if lever_pos == 0x7E and not self.lever_returned_to_manual_center:
            self.lever_returned_to_manual_center = True
            self._process_toggle_manual_transition(bmw_state)
            self.last_toggle_time = current_time
        elif lever_pos != 0x7E:
            self.lever_returned_to_manual_center = False
    
    def _process_toggle_transition(self, bmw_state: BMWState):
        """토글 전환 처리"""
        transitions = {
            0x1E: self._handle_up_toggle,      # UP (R)
            0x2E: lambda bs: self._set_gear(bs, 'P', "🎯 UP+ → PARK"),  # UP+
            0x3E: self._handle_down_toggle,    # DOWN (D)
            0x7E: self._handle_side_toggle,    # SIDE (S)
        }
        
        handler = transitions.get(self.previous_lever_position)
        if handler:
            handler(bmw_state)
        else:
            self.logger.debug(f"No transition handler for position 0x{self.previous_lever_position:02X}")
    
    def _process_toggle_manual_transition(self, bmw_state: BMWState):
        """수동 토글 전환 처리"""
        transitions = {
            0x5E: self._handle_manual_down_toggle,  # Manual Down
            0x6E: self._handle_manual_up_toggle,    # Manual Up
        }
        
        handler = transitions.get(self.previous_lever_position)
        if handler:
            handler(bmw_state)
        else:
            self.logger.debug(f"No manual transition handler for position 0x{self.previous_lever_position:02X}")
    
    def _handle_up_toggle(self, bmw_state: BMWState):
        """위 토글 처리 (R 방향)"""
        if bmw_state.current_gear == 'N':
            self._set_gear(bmw_state, 'R', "🎯 N → REVERSE")
        elif bmw_state.current_gear == 'D':
            self._set_gear(bmw_state, 'N', "🎯 D → NEUTRAL")
        else:
            self._set_gear(bmw_state, 'N', "🎯 UP → NEUTRAL")
    
    def _handle_down_toggle(self, bmw_state: BMWState):
        """아래 토글 처리 (D 방향)"""
        if bmw_state.current_gear == 'N':
            self._set_gear(bmw_state, 'D', "🎯 N → DRIVE")
        elif bmw_state.current_gear == 'R':
            self._set_gear(bmw_state, 'N', "🎯 R → NEUTRAL")
        else:
            self._set_gear(bmw_state, 'D', "🎯 DOWN → DRIVE")
    
    def _handle_side_toggle(self, bmw_state: BMWState):
        """사이드 토글 처리 (Sport/Manual)"""
        if bmw_state.current_gear == 'D':
            bmw_state.manual_gear = 1
            self._set_gear(bmw_state, f'M{bmw_state.manual_gear}', f"🎯 D → MANUAL M{bmw_state.manual_gear}")
        elif bmw_state.current_gear.startswith('M'):
            self._set_gear(bmw_state, 'D', "🎯 Manual → DRIVE")
        else:
            self._set_gear(bmw_state, 'D', "🎯 SIDE → DRIVE")
    
    def _handle_manual_up_toggle(self, bmw_state: BMWState):
        """수동 업 토글 처리 (기어 업)"""
        if bmw_state.current_gear.startswith('M') and bmw_state.manual_gear < 8:
            bmw_state.manual_gear += 1
            self._set_gear(bmw_state, f'M{bmw_state.manual_gear}', f"🔼 Manual → M{bmw_state.manual_gear}")
        else:
            self.logger.debug("Manual gear up ignored - not in manual mode or at max gear")
    
    def _handle_manual_down_toggle(self, bmw_state: BMWState):
        """수동 다운 토글 처리 (기어 다운)"""
        if bmw_state.current_gear.startswith('M') and bmw_state.manual_gear > 1:
            bmw_state.manual_gear -= 1
            self._set_gear(bmw_state, f'M{bmw_state.manual_gear}', f"🔽 Manual → M{bmw_state.manual_gear}")
        else:
            self.logger.debug("Manual gear down ignored - not in manual mode or at min gear")
    
    def _set_gear(self, bmw_state: BMWState, gear: str, message: str):
        """기어 설정 헬퍼 메서드"""
        old_gear = bmw_state.current_gear
        bmw_state.current_gear = gear
        self.logger.info(f"{message} (was: {old_gear})")
        
    def send_gear_led(self, can_bus: can.interface.Bus, gear: str):
        """기어 LED 전송 (개선된 버전)"""
        try:
            gear_led_codes = {
                'P': 0x20, 'R': 0x40, 'N': 0x60, 'D': 0x80
            }
            
            # Manual gear는 Sport LED 사용
            if gear.startswith('M'):
                led_code = 0x81
            elif gear in gear_led_codes:
                led_code = gear_led_codes[gear]
            else:
                return
            
            # 카운터 업데이트 (0x01-0x0E 순환)
            self.gws_counter = (self.gws_counter + 1) if self.gws_counter < 0x0E else 0x01
            
            # LED 메시지 구성 (실제 차량 포맷에 맞춤)
            payload_without_crc = [self.gws_counter, led_code, 0x00, 0x00]
            crc = self.crc_3fd.calc(payload_without_crc) & 0xFF
            payload = [crc] + payload_without_crc
            
            message = can.Message(
                arbitration_id=0x3FD,
                data=payload,
                is_extended_id=False
            )
            
            can_bus.send(message)
            self.logger.debug(f"LED sent for gear {gear}: Counter=0x{self.gws_counter:02X}, Code=0x{led_code:02X}, CRC=0x{crc:02X}")
            
        except Exception as e:
            self.logger.error(f"LED send error: {e}")
    
    def send_backlight_control(self, can_bus: can.interface.Bus, brightness: int = 0xFF):
        """기어 레버 백라이트 제어"""
        try:
            # Brightness: 0x00 (off) to 0xFF (full brightness)
            payload = [brightness, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
            
            message = can.Message(
                arbitration_id=0x202,
                data=payload,
                is_extended_id=False
            )
            
            can_bus.send(message)
            self.logger.debug(f"Backlight sent: Brightness=0x{brightness:02X}")
            
        except Exception as e:
            self.logger.error(f"Backlight send error: {e}")
    
    def send_initialization_messages(self, can_bus: can.interface.Bus):
        """BMW 시스템 초기화 메시지들 전송"""
        try:
            self.logger.info("Sending BMW initialization messages...")
            
            # 초기화 시퀀스 1: 시스템 웨이크업
            init_messages = [
                # Wake up message
                (0x55E, [0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x5E]),
                # GWS initialization  
                (0x3FD, [0x70, 0x01, 0x00, 0x00, 0x00]),
                (0x3FD, [0x71, 0x02, 0x00, 0x00, 0x00]),
                # Neutral LED as default
                (0x3FD, [0x72, 0x03, 0x60, 0x00, 0x00]),
            ]
            
            for msg_id, data in init_messages:
                message = can.Message(
                    arbitration_id=msg_id,
                    data=data,
                    is_extended_id=False
                )
                can_bus.send(message)
                self.logger.debug(f"Init message sent: ID=0x{msg_id:03X}, Data={bytes(data).hex().upper()}")
                time.sleep(0.1)  # 100ms 간격
            
            # Enable backlight at full brightness
            self.send_backlight_control(can_bus, 0xFF)
            time.sleep(0.1)
            
            # Send initial gear LED (Neutral)
            self.send_gear_led(can_bus, 'N')
            
            self.logger.info("BMW initialization messages sent")
            
        except Exception as e:
            self.logger.error(f"Initialization send error: {e}")