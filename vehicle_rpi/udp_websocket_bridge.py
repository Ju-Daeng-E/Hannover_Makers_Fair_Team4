#!/usr/bin/env python3
"""
UDP to WebSocket Bridge for RC Car Vehicle
UDP 비디오 스트림을 WebSocket으로 브릿지하여 웹브라우저에서 시청 가능
"""

import asyncio
import websockets
import socket
import threading
import time
import struct
import base64
import json
import logging
from collections import defaultdict
from typing import Set, Dict, Any
import numpy as np
import cv2
import concurrent.futures

class UDPWebSocketBridge:
    """UDP 비디오 스트림을 WebSocket으로 브릿지"""
    
    def __init__(self, udp_port: int = 9999, websocket_port: int = 8765):
        self.udp_port = udp_port
        self.websocket_port = websocket_port
        
        # UDP 클라이언트 설정
        self.udp_sock = None
        self.udp_connected = False
        
        # WebSocket 클라이언트 관리 (단일 클라이언트만 허용)
        self.websocket_clients: Set[websockets.WebSocketServerProtocol] = set()
        self.max_clients = 1
        
        # 프레임 재조립
        self.frame_chunks = defaultdict(dict)
        self.frame_info = {}
        self.last_frame_id = 0
        
        # 성능 통계
        self.frames_processed = 0
        self.frames_sent = 0
        self.start_time = None
        
        # 이벤트 루프 관리
        self.main_loop = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # 로깅 설정
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    async def connect_to_udp_server(self, server_host: str = 'localhost'):
        """UDP 서버에 연결"""
        try:
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.settimeout(5.0)
            
            # 서버에 연결 요청
            self.udp_sock.sendto(b'CONNECT', (server_host, self.udp_port))
            
            # 연결 확인 응답 대기
            response, addr = self.udp_sock.recvfrom(1024)
            if response == b'CONNECTED':
                self.logger.info(f"✅ UDP 서버 연결: {addr}")
                self.udp_sock.settimeout(1.0)
                self.udp_connected = True
                return True
            else:
                self.logger.error(f"❌ UDP 연결 실패: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ UDP 연결 오류: {e}")
            return False
    
    def disconnect_from_udp(self):
        """UDP 연결 해제"""
        if self.udp_sock and self.udp_connected:
            try:
                self.udp_sock.sendto(b'DISCONNECT', ('localhost', self.udp_port))
            except:
                pass
            self.udp_sock.close()
            self.udp_sock = None
            self.udp_connected = False
    
    def receive_udp_frames(self):
        """UDP 프레임 수신 스레드"""
        self.logger.info("📡 UDP 프레임 수신 시작...")
        self.start_time = time.time()
        
        while self.udp_connected:
            try:
                data, addr = self.udp_sock.recvfrom(2048)
                
                if data == b'STREAM_END':
                    self.logger.info("🛑 UDP 스트림 종료")
                    break
                
                if len(data) < 8:
                    continue
                
                # 헤더 파싱
                header = struct.unpack('!HHHH', data[:8])
                frame_id, total_chunks, chunk_id, data_size = header
                chunk_data = data[8:8+data_size]
                
                # 프레임 정보 업데이트
                if frame_id not in self.frame_info:
                    self.frame_info[frame_id] = {
                        'total_chunks': total_chunks,
                        'received_chunks': 0,
                        'timestamp': time.time()
                    }
                
                # 청크 저장
                if chunk_id not in self.frame_chunks[frame_id]:
                    self.frame_chunks[frame_id][chunk_id] = chunk_data
                    self.frame_info[frame_id]['received_chunks'] += 1
                
                # 프레임 완성 체크
                if (self.frame_info[frame_id]['received_chunks'] == 
                    self.frame_info[frame_id]['total_chunks']):
                    # 메인 이벤트 루프에서 안전하게 처리
                    if self.main_loop and not self.main_loop.is_closed():
                        asyncio.run_coroutine_threadsafe(
                            self.process_complete_frame(frame_id), 
                            self.main_loop
                        )
                    else:
                        # 메인 루프가 없으면 동기 방식으로 처리
                        self.executor.submit(self.process_frame_sync, frame_id)
                
                # 오래된 프레임 정리
                current_time = time.time()
                old_frames = [fid for fid, info in self.frame_info.items() 
                             if current_time - info['timestamp'] > 2.0]
                for fid in old_frames:
                    self.cleanup_frame(fid)
                
            except socket.timeout:
                # Keep-alive 전송
                try:
                    self.udp_sock.sendto(b'PING', ('localhost', self.udp_port))
                except:
                    pass
                continue
            except Exception as e:
                if self.udp_connected:
                    self.logger.warning(f"⚠️ UDP 수신 오류: {e}")
                break
        
        self.logger.info("📡 UDP 프레임 수신 종료")
    
    def process_frame_sync(self, frame_id: int):
        """동기 프레임 처리 (스레드에서 실행) - WebSocket 없이 처리"""
        try:
            # 프레임이 이미 처리되었거나 너무 오래되었으면 건너뛰기
            if frame_id <= self.last_frame_id:
                self.cleanup_frame(frame_id)
                return
            
            # 청크들을 순서대로 조립
            chunks = self.frame_chunks[frame_id]
            total_chunks = self.frame_info[frame_id]['total_chunks']
            
            frame_data = b''
            for chunk_id in range(total_chunks):
                if chunk_id in chunks:
                    frame_data += chunks[chunk_id]
                else:
                    # 청크 누락 시 건너뛰기
                    self.cleanup_frame(frame_id)
                    return
            
            # Base64 인코딩
            frame_b64 = base64.b64encode(frame_data).decode('utf-8')
            
            # WebSocket 메시지 생성
            message = {
                'type': 'video_frame',
                'data': f'data:image/jpeg;base64,{frame_b64}',
                'frame_id': frame_id,
                'timestamp': time.time()
            }
            
            # 메인 루프에서 WebSocket 전송 실행
            if self.main_loop and not self.main_loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    self.broadcast_to_websockets(json.dumps(message)), 
                    self.main_loop
                )
            
            self.frames_processed += 1
            self.last_frame_id = frame_id
            
        except Exception as e:
            self.logger.error(f"❌ 동기 프레임 처리 오류: {e}")
        finally:
            self.cleanup_frame(frame_id)
    
    async def process_complete_frame(self, frame_id: int):
        """완성된 프레임 처리 및 WebSocket 전송"""
        if frame_id <= self.last_frame_id:
            self.cleanup_frame(frame_id)
            return
        
        try:
            # 청크들을 순서대로 조립
            chunks = self.frame_chunks[frame_id]
            total_chunks = self.frame_info[frame_id]['total_chunks']
            
            frame_data = b''
            for chunk_id in range(total_chunks):
                if chunk_id in chunks:
                    frame_data += chunks[chunk_id]
                else:
                    # 청크 누락 시 건너뛰기
                    self.cleanup_frame(frame_id)
                    return
            
            # Base64 인코딩
            frame_b64 = base64.b64encode(frame_data).decode('utf-8')
            
            # WebSocket 메시지 생성
            message = {
                'type': 'video_frame',
                'data': f'data:image/jpeg;base64,{frame_b64}',
                'frame_id': frame_id,
                'timestamp': time.time()
            }
            
            # 모든 WebSocket 클라이언트에게 전송
            if self.websocket_clients:
                await self.broadcast_to_websockets(json.dumps(message))
                self.frames_sent += 1
            
            self.frames_processed += 1
            self.last_frame_id = frame_id
            
        except Exception as e:
            self.logger.error(f"❌ 프레임 처리 오류: {e}")
        finally:
            self.cleanup_frame(frame_id)
    
    async def broadcast_to_websockets(self, message: str):
        """WebSocket 클라이언트들에게 브로드캐스트"""
        if not self.websocket_clients:
            return
        
        # 연결이 끊긴 클라이언트 제거
        disconnected = set()
        
        for client in self.websocket_clients.copy():
            try:
                # WebSocket 연결 상태 확인 (안전한 방식)
                if hasattr(client, 'closed') and client.closed:
                    disconnected.add(client)
                    continue
                elif hasattr(client, 'open') and not client.open:
                    disconnected.add(client)
                    continue
                    
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except websockets.exceptions.InvalidState:
                disconnected.add(client)
            except AttributeError as e:
                self.logger.warning(f"⚠️ WebSocket 속성 오류: {e}")
                disconnected.add(client)
            except Exception as e:
                self.logger.warning(f"⚠️ WebSocket 전송 오류: {e}")
                disconnected.add(client)
        
        # 끊긴 연결 정리
        if disconnected:
            for client in disconnected:
                self.websocket_clients.discard(client)
            self.logger.info(f"📡 끊긴 WebSocket 연결 {len(disconnected)}개 정리됨 (활성 연결: {len(self.websocket_clients)}개)")
    
    def cleanup_frame(self, frame_id: int):
        """프레임 데이터 정리"""
        if frame_id in self.frame_chunks:
            del self.frame_chunks[frame_id]
        if frame_id in self.frame_info:
            del self.frame_info[frame_id]
    
    async def websocket_handler(self, websocket):
        """WebSocket 연결 핸들러 (websockets 10.0+ 호환)"""
        client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        # 기존 연결이 있으면 모두 정리 (새로운 연결을 위해)
        if len(self.websocket_clients) >= self.max_clients:
            self.logger.info(f"🔄 새 클라이언트 연결을 위해 기존 연결 정리: {client_addr}")
            
            # 기존 클라이언트들을 모두 종료
            disconnected = set()
            for existing_client in self.websocket_clients.copy():
                try:
                    await existing_client.close(code=1000, reason="New client connecting")
                    disconnected.add(existing_client)
                    self.logger.info(f"📡 기존 클라이언트 연결 종료: {existing_client.remote_address[0]}:{existing_client.remote_address[1]}")
                except Exception as e:
                    self.logger.warning(f"⚠️ 기존 클라이언트 종료 오류: {e}")
                    disconnected.add(existing_client)
            
            # 클라이언트 목록에서 제거
            for client in disconnected:
                self.websocket_clients.discard(client)
        
        self.logger.info(f"✅ WebSocket 클라이언트 연결: {client_addr}")
        self.websocket_clients.add(websocket)
        
        try:
            # 환영 메시지 전송
            welcome_msg = {
                'type': 'connection',
                'status': 'connected',
                'message': 'UDP video stream connected'
            }
            await websocket.send(json.dumps(welcome_msg))
            
            # 클라이언트 메시지 대기 (keep-alive)
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get('type') == 'ping':
                        pong_msg = {'type': 'pong', 'timestamp': time.time()}
                        await websocket.send(json.dumps(pong_msg))
                except json.JSONDecodeError:
                    pass
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"📡 WebSocket 클라이언트 정상 연결 해제: {client_addr}")
        except websockets.exceptions.InvalidHandshake as e:
            self.logger.warning(f"⚠️ WebSocket 핸드셰이크 오류: {e}")
        except websockets.exceptions.InvalidState as e:
            self.logger.warning(f"⚠️ WebSocket 상태 오류: {e}")
        except ConnectionResetError:
            self.logger.info(f"📡 WebSocket 연결 재설정: {client_addr}")
        except Exception as e:
            self.logger.error(f"❌ WebSocket 처리 오류: {type(e).__name__}: {e}")
        finally:
            self.websocket_clients.discard(websocket)
            self.logger.info(f"🧹 WebSocket 클라이언트 정리 완료: {client_addr} (남은 연결: {len(self.websocket_clients)}개)")
    
    async def start_bridge(self, udp_host: str = 'localhost'):
        """브릿지 시작"""
        self.logger.info(f"🌉 UDP-WebSocket 브릿지 시작...")
        
        # 메인 이벤트 루프 저장
        self.main_loop = asyncio.get_running_loop()
        self.logger.info(f"📊 메인 이벤트 루프 설정 완료")
        
        # UDP 서버 연결
        if not await self.connect_to_udp_server(udp_host):
            return False
        
        # UDP 수신 스레드 시작
        udp_thread = threading.Thread(target=self.receive_udp_frames, daemon=True)
        udp_thread.start()
        
        # WebSocket 서버 시작
        self.logger.info(f"🌐 WebSocket 서버 시작: ws://0.0.0.0:{self.websocket_port}")
        self.logger.info(f"📊 연결 제한: 최대 {self.max_clients}개 클라이언트")
        
        start_server = websockets.serve(
            self.websocket_handler,
            "0.0.0.0",
            self.websocket_port,
            ping_interval=20,  # 20초마다 ping (안정성 향상)
            ping_timeout=10,   # 10초 ping 타임아웃
            close_timeout=10   # 10초 연결 종료 타임아웃
        )
        
        await start_server
        
        self.logger.info("✅ UDP-WebSocket 브릿지 준비 완료")
        self.logger.info(f"📡 UDP 소스: localhost:{self.udp_port}")
        self.logger.info(f"🌐 WebSocket 출력: ws://[ip]:{self.websocket_port}")
        
        # 무한 실행
        try:
            await asyncio.Future()  # 무한 대기
        except KeyboardInterrupt:
            self.logger.info("🛑 브릿지 종료...")
        finally:
            await self.stop_bridge()
    
    async def stop_bridge(self):
        """브릿지 중지"""
        self.udp_connected = False
        self.disconnect_from_udp()
        
        # 모든 WebSocket 클라이언트에게 종료 알림
        if self.websocket_clients:
            close_msg = {
                'type': 'connection',
                'status': 'closing',
                'message': 'Stream ending'
            }
            await self.broadcast_to_websockets(json.dumps(close_msg))
        
        # 리소스 정리
        if self.executor:
            self.executor.shutdown(wait=False)
            self.logger.info("🧹 Executor 정리 완료")
        
        # 통계 출력
        if self.start_time:
            duration = time.time() - self.start_time
            if duration > 0:
                avg_fps = self.frames_processed / duration
                self.logger.info(f"📊 브릿지 통계:")
                self.logger.info(f"  • 처리 프레임: {self.frames_processed}")
                self.logger.info(f"  • 전송 프레임: {self.frames_sent}")
                self.logger.info(f"  • 평균 FPS: {avg_fps:.1f}")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='UDP to WebSocket Video Bridge')
    parser.add_argument('--udp-host', default='localhost', help='UDP server host (default: localhost)')
    parser.add_argument('--udp-port', type=int, default=9999, help='UDP server port (default: 9999)')
    parser.add_argument('--websocket-port', type=int, default=8765, help='WebSocket server port (default: 8765)')
    
    args = parser.parse_args()
    
    print("🌉 UDP to WebSocket Video Bridge")
    print("=" * 40)
    print(f"📡 UDP 소스: {args.udp_host}:{args.udp_port}")
    print(f"🌐 WebSocket 서버: ws://[ip]:{args.websocket_port}")
    print("=" * 40)
    
    bridge = UDPWebSocketBridge(args.udp_port, args.websocket_port)
    
    try:
        asyncio.run(bridge.start_bridge(args.udp_host))
    except KeyboardInterrupt:
        print("\n🛑 브릿지 종료...")

if __name__ == "__main__":
    main()