#!/usr/bin/env python3
"""
UDP Video Streaming for RC Car Vehicle
Ultra-low latency video streaming using UDP protocol
"""

import socket
import cv2
import numpy as np
import threading
import time
import struct
import logging
from datetime import datetime
from typing import Tuple, Set
import queue

class UDPVideoStreamer:
    """High-performance UDP video streaming with frame chunking"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 9999, 
                 quality: int = 30, chunk_size: int = 1400, max_fps: int = 60):
        self.host = host
        self.port = port
        self.quality = quality
        self.chunk_size = chunk_size  # MTU safe size (1500 - UDP header)
        self.max_fps = max_fps
        self.frame_time = 1.0 / max_fps
        
        # Socket setup
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)  # 1MB send buffer
        
        # Client management
        self.clients: Set[Tuple[str, int]] = set()
        self.client_lock = threading.Lock()
        self.last_frame_id = 0
        
        # Streaming state
        self.streaming = False
        self.camera_source = None
        
        # Performance stats
        self.frames_sent = 0
        self.bytes_sent = 0
        self.start_time = None
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def add_client(self, client_addr: Tuple[str, int]):
        """클라이언트 추가"""
        with self.client_lock:
            self.clients.add(client_addr)
            self.logger.info(f"✅ UDP 클라이언트 연결: {client_addr} (총 {len(self.clients)}개)")
    
    def remove_client(self, client_addr: Tuple[str, int]):
        """클라이언트 제거"""
        with self.client_lock:
            self.clients.discard(client_addr)
            self.logger.info(f"❌ UDP 클라이언트 연결 해제: {client_addr} (남은 {len(self.clients)}개)")
    
    def compress_frame(self, frame: np.ndarray) -> bytes:
        """초고속 프레임 압축"""
        # 크기 조정으로 데이터량 줄이기 (옵션)
        height, width = frame.shape[:2]
        if width > 640:
            scale = 640 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # 초고속 JPEG 압축
        encode_params = [
            cv2.IMWRITE_JPEG_QUALITY, self.quality,
            cv2.IMWRITE_JPEG_OPTIMIZE, 0,  # 최적화 비활성화
            cv2.IMWRITE_JPEG_PROGRESSIVE, 0,  # 프로그레시브 비활성화
            cv2.IMWRITE_JPEG_RST_INTERVAL, 0,  # 재시작 마커 비활성화
        ]
        
        ret, encoded = cv2.imencode('.jpg', frame, encode_params)
        if not ret:
            return b''
        
        return encoded.tobytes()
    
    def send_frame(self, frame_data: bytes, client_addr: Tuple[str, int]):
        """프레임을 청크로 분할하여 전송"""
        if not frame_data:
            return False
        
        frame_id = (self.last_frame_id + 1) % 65536
        self.last_frame_id = frame_id
        
        data_size = len(frame_data)
        num_chunks = (data_size + self.chunk_size - 1) // self.chunk_size
        
        try:
            for chunk_id in range(num_chunks):
                start_pos = chunk_id * self.chunk_size
                end_pos = min(start_pos + self.chunk_size, data_size)
                chunk_data = frame_data[start_pos:end_pos]
                
                # 패킷 헤더: [frame_id:2][total_chunks:2][chunk_id:2][data_size:2]
                header = struct.pack('!HHHH', 
                                   frame_id, 
                                   num_chunks, 
                                   chunk_id, 
                                   len(chunk_data))
                
                packet = header + chunk_data
                self.sock.sendto(packet, client_addr)
                
                # 패킷 간 최소 간격 (네트워크 폭주 방지)
                if num_chunks > 10 and chunk_id % 5 == 0:
                    time.sleep(0.0001)  # 0.1ms
            
            self.bytes_sent += data_size
            return True
            
        except Exception as e:
            self.logger.warning(f"⚠️ 전송 오류 to {client_addr}: {e}")
            self.remove_client(client_addr)
            return False
    
    def broadcast_frame(self, frame: np.ndarray):
        """모든 클라이언트에게 프레임 브로드캐스트"""
        if not self.clients:
            return
        
        # 프레임 압축
        frame_data = self.compress_frame(frame)
        if not frame_data:
            return
        
        # 모든 클라이언트에게 전송
        failed_clients = []
        with self.client_lock:
            clients_copy = self.clients.copy()
        
        for client_addr in clients_copy:
            if not self.send_frame(frame_data, client_addr):
                failed_clients.append(client_addr)
        
        # 실패한 클라이언트 제거
        for client_addr in failed_clients:
            self.remove_client(client_addr)
        
        self.frames_sent += 1
    
    def handle_client_connections(self):
        """클라이언트 연결 관리"""
        while self.streaming:
            try:
                # 클라이언트 연결 요청 수신 (비차단)
                self.sock.settimeout(1.0)
                data, addr = self.sock.recvfrom(1024)
                
                if data == b'CONNECT':
                    self.add_client(addr)
                    # 연결 확인 응답
                    self.sock.sendto(b'CONNECTED', addr)
                elif data == b'DISCONNECT':
                    self.remove_client(addr)
                elif data == b'PING':
                    # Keep-alive 응답
                    self.sock.sendto(b'PONG', addr)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.streaming:
                    self.logger.warning(f"⚠️ 클라이언트 관리 오류: {e}")
    
    def streaming_loop(self):
        """메인 스트리밍 루프"""
        self.logger.info(f"🚀 UDP 스트리밍 시작: {self.max_fps}fps, 품질: {self.quality}")
        self.start_time = time.time()
        last_frame_time = 0
        
        while self.streaming:
            current_time = time.time()
            
            # 프레임레이트 제어
            if current_time - last_frame_time < self.frame_time:
                time.sleep(0.001)  # 1ms 대기
                continue
            
            if self.camera_source and self.clients:
                frame = self.camera_source.capture_frame()
                if frame is not None:
                    # 오버레이 추가 (옵션)
                    frame = self.camera_source.add_overlay(frame)
                    
                    # BGR 형식 확인 및 변환
                    if len(frame.shape) == 3 and frame.shape[2] == 3:
                        # RGB to BGR 변환 (OpenCV JPEG 인코딩용)
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    self.broadcast_frame(frame)
                    last_frame_time = current_time
            else:
                time.sleep(0.01)  # 10ms 대기
    
    def start_streaming(self, camera_source):
        """스트리밍 시작"""
        self.camera_source = camera_source
        self.streaming = True
        
        try:
            # 서버 소켓 바인드
            self.sock.bind((self.host, self.port))
            self.logger.info(f"🌐 UDP 서버 바인드: {self.host}:{self.port}")
            
            # 클라이언트 관리 스레드 시작
            client_thread = threading.Thread(target=self.handle_client_connections, daemon=True)
            client_thread.start()
            
            # 스트리밍 루프 시작
            self.streaming_loop()
            
        except Exception as e:
            self.logger.error(f"❌ UDP 스트리밍 오류: {e}")
            self.streaming = False
            raise
    
    def stop_streaming(self):
        """스트리밍 중지"""
        self.streaming = False
        
        # 모든 클라이언트에게 종료 알림
        with self.client_lock:
            for client_addr in self.clients.copy():
                try:
                    self.sock.sendto(b'STREAM_END', client_addr)
                except:
                    pass
        
        self.clients.clear()
        
        # 성능 통계 출력
        if self.start_time:
            duration = time.time() - self.start_time
            if duration > 0:
                avg_fps = self.frames_sent / duration
                avg_bandwidth = (self.bytes_sent / duration) / (1024 * 1024)  # MB/s
                
                self.logger.info(f"📊 UDP 스트리밍 통계:")
                self.logger.info(f"  • 전송 프레임: {self.frames_sent}")
                self.logger.info(f"  • 평균 FPS: {avg_fps:.1f}")
                self.logger.info(f"  • 평균 대역폭: {avg_bandwidth:.1f} MB/s")
                self.logger.info(f"  • 총 전송량: {self.bytes_sent / (1024*1024):.1f} MB")
        
        try:
            self.sock.close()
        except:
            pass
        
        self.logger.info("🛑 UDP 스트리밍 중지")

def main():
    """UDP 스트리머 독립 실행"""
    import argparse
    from camera_stream import CameraStreamer
    
    parser = argparse.ArgumentParser(description='UDP Video Streaming Server')
    parser.add_argument('--port', type=int, default=9999, help='UDP port (default: 9999)')
    parser.add_argument('--quality', type=int, default=30, help='JPEG quality 1-100 (default: 30)')
    parser.add_argument('--fps', type=int, default=60, help='Max FPS (default: 60)')
    parser.add_argument('--chunk-size', type=int, default=1400, help='Chunk size (default: 1400)')
    
    args = parser.parse_args()
    
    print("🚀 UDP 비디오 스트리밍 서버")
    print("=" * 40)
    print(f"🌐 포트: {args.port}")
    print(f"📹 최대 FPS: {args.fps}")
    print(f"🎨 JPEG 품질: {args.quality}")
    print(f"📦 청크 크기: {args.chunk_size}")
    print("=" * 40)
    print("클라이언트 연결 방법:")
    print(f"  UDP 주소: [vehicle-ip]:{args.port}")
    print("  연결 메시지: b'CONNECT' 전송")
    print("=" * 40)
    
    # 카메라 소스 생성
    camera = CameraStreamer(enable_speed_sensor=False)
    
    # UDP 스트리머 생성
    udp_streamer = UDPVideoStreamer(
        port=args.port,
        quality=args.quality,
        max_fps=args.fps,
        chunk_size=args.chunk_size
    )
    
    try:
        udp_streamer.start_streaming(camera)
    except KeyboardInterrupt:
        print("\n🛑 UDP 스트리밍 중지...")
        udp_streamer.stop_streaming()
        camera.stop_streaming()

if __name__ == "__main__":
    main()