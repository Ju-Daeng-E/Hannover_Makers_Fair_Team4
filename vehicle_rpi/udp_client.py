#!/usr/bin/env python3
"""
UDP Video Client for RC Car Vehicle
Test client for receiving UDP video stream
"""

import socket
import cv2
import numpy as np
import struct
import threading
import time
from collections import defaultdict
import argparse

class UDPVideoClient:
    """UDP 비디오 스트림 클라이언트"""
    
    def __init__(self, server_host: str = 'localhost', server_port: int = 9999):
        self.server_host = server_host
        self.server_port = server_port
        self.sock = None
        self.receiving = False
        
        # 프레임 재조립용
        self.frame_chunks = defaultdict(dict)  # frame_id -> {chunk_id: data}
        self.frame_info = {}  # frame_id -> {total_chunks, received_chunks}
        self.last_displayed_frame = 0
        
        # 성능 통계
        self.frames_received = 0
        self.bytes_received = 0
        self.start_time = None
        self.last_fps_time = time.time()
        self.fps_counter = 0
        
    def connect_to_server(self):
        """서버에 연결"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(5.0)  # 5초 타임아웃
            
            # 서버에 연결 요청
            self.sock.sendto(b'CONNECT', (self.server_host, self.server_port))
            
            # 연결 확인 응답 대기
            response, addr = self.sock.recvfrom(1024)
            if response == b'CONNECTED':
                print(f"✅ 서버 연결 성공: {addr}")
                self.sock.settimeout(1.0)  # 수신용 타임아웃
                return True
            else:
                print(f"❌ 서버 연결 실패: {response}")
                return False
                
        except Exception as e:
            print(f"❌ 연결 오류: {e}")
            return False
    
    def disconnect_from_server(self):
        """서버와 연결 해제"""
        if self.sock:
            try:
                self.sock.sendto(b'DISCONNECT', (self.server_host, self.server_port))
            except:
                pass
            self.sock.close()
            self.sock = None
    
    def receive_packets(self):
        """패킷 수신 스레드"""
        print("📡 패킷 수신 시작...")
        self.start_time = time.time()
        
        while self.receiving:
            try:
                data, addr = self.sock.recvfrom(2048)  # 충분한 버퍼 크기
                
                if data == b'STREAM_END':
                    print("🛑 서버에서 스트림 종료 알림")
                    break
                
                if len(data) < 8:  # 헤더 크기 체크
                    continue
                
                # 헤더 파싱: [frame_id:2][total_chunks:2][chunk_id:2][data_size:2]
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
                    self.bytes_received += len(chunk_data)
                
                # 프레임 완성 체크
                if (self.frame_info[frame_id]['received_chunks'] == 
                    self.frame_info[frame_id]['total_chunks']):
                    self.assemble_and_display_frame(frame_id)
                
                # 오래된 프레임 정리 (1초 이상)
                current_time = time.time()
                old_frames = [fid for fid, info in self.frame_info.items() 
                             if current_time - info['timestamp'] > 1.0]
                for fid in old_frames:
                    self.cleanup_frame(fid)
                
            except socket.timeout:
                # Keep-alive 전송
                try:
                    self.sock.sendto(b'PING', (self.server_host, self.server_port))
                except:
                    pass
                continue
            except Exception as e:
                if self.receiving:
                    print(f"⚠️ 수신 오류: {e}")
                break
        
        print("📡 패킷 수신 종료")
    
    def assemble_and_display_frame(self, frame_id: int):
        """프레임 조립 및 표시"""
        if frame_id <= self.last_displayed_frame:
            # 이미 처리된 프레임은 건너뛰기
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
                    print(f"⚠️ 프레임 {frame_id} 청크 {chunk_id} 누락")
                    self.cleanup_frame(frame_id)
                    return
            
            # JPEG 디코딩
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # FPS 계산
                self.fps_counter += 1
                current_time = time.time()
                if current_time - self.last_fps_time >= 1.0:
                    fps = self.fps_counter / (current_time - self.last_fps_time)
                    self.last_fps_time = current_time
                    self.fps_counter = 0
                    
                    # FPS 정보를 프레임에 표시
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                    # 통계 정보 표시
                    if self.start_time:
                        duration = current_time - self.start_time
                        avg_fps = self.frames_received / duration if duration > 0 else 0
                        bandwidth = (self.bytes_received / duration) / (1024 * 1024) if duration > 0 else 0
                        
                        cv2.putText(frame, f"Avg FPS: {avg_fps:.1f}", (10, 70), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                        cv2.putText(frame, f"Bandwidth: {bandwidth:.1f} MB/s", (10, 100), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # 프레임 표시
                cv2.imshow('UDP Video Stream', frame)
                
                self.frames_received += 1
                self.last_displayed_frame = frame_id
            
            # 프레임 정리
            self.cleanup_frame(frame_id)
            
        except Exception as e:
            print(f"❌ 프레임 조립 오류: {e}")
            self.cleanup_frame(frame_id)
    
    def cleanup_frame(self, frame_id: int):
        """프레임 데이터 정리"""
        if frame_id in self.frame_chunks:
            del self.frame_chunks[frame_id]
        if frame_id in self.frame_info:
            del self.frame_info[frame_id]
    
    def start_receiving(self):
        """스트림 수신 시작"""
        if not self.connect_to_server():
            return False
        
        self.receiving = True
        
        # 수신 스레드 시작
        receive_thread = threading.Thread(target=self.receive_packets, daemon=True)
        receive_thread.start()
        
        print("📺 비디오 스트림 시청 중...")
        print("ESC 키 또는 'q' 키를 눌러 종료")
        
        # OpenCV 윈도우 루프
        while self.receiving:
            key = cv2.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):  # ESC 또는 'q'
                break
            elif key == ord('r'):  # 'r' - 재연결
                print("🔄 서버 재연결 중...")
                self.disconnect_from_server()
                time.sleep(1)
                if self.connect_to_server():
                    print("✅ 재연결 성공")
                else:
                    break
        
        self.receiving = False
        
        # 통계 출력
        if self.start_time:
            duration = time.time() - self.start_time
            if duration > 0:
                avg_fps = self.frames_received / duration
                avg_bandwidth = (self.bytes_received / duration) / (1024 * 1024)
                
                print("\n📊 수신 통계:")
                print(f"  • 수신 프레임: {self.frames_received}")
                print(f"  • 평균 FPS: {avg_fps:.1f}")
                print(f"  • 평균 대역폭: {avg_bandwidth:.1f} MB/s")
                print(f"  • 총 수신량: {self.bytes_received / (1024*1024):.1f} MB")
        
        cv2.destroyAllWindows()
        self.disconnect_from_server()
        return True

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='UDP Video Stream Client')
    parser.add_argument('--host', default='localhost', help='Server host (default: localhost)')
    parser.add_argument('--port', type=int, default=9999, help='Server port (default: 9999)')
    
    args = parser.parse_args()
    
    print("📺 UDP 비디오 스트림 클라이언트")
    print("=" * 40)
    print(f"🌐 서버: {args.host}:{args.port}")
    print("=" * 40)
    
    client = UDPVideoClient(args.host, args.port)
    
    try:
        client.start_receiving()
    except KeyboardInterrupt:
        print("\n🛑 클라이언트 종료...")
        client.receiving = False
        client.disconnect_from_server()
    
    print("👋 UDP 클라이언트 종료")

if __name__ == "__main__":
    main()