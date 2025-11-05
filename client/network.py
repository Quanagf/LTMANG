# Client/network.py

import websocket # Thư viện: websocket-client
import threading
import json
import queue
import time

class Network:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.thread = None
        self.is_connected = False
        
        # Queue để nhận tin nhắn từ luồng mạng một cách an toàn
        self.message_queue = queue.Queue()

    def start(self):
        """Khởi động kết nối trong một luồng riêng biệt."""
        self.thread = threading.Thread(target=self._run_forever)
        self.thread.daemon = True # Tự động tắt thread khi chương trình chính tắt
        self.thread.start()

    def _run_forever(self):
        """Hàm này chạy trong luồng riêng, kết nối và lắng nghe mãi mãi."""
        while True:
            try:
                # Tạo kết nối
                self.ws = websocket.WebSocketApp(self.url,
                                                 on_open=self._on_open,
                                                 on_message=self._on_message,
                                                 on_error=self._on_error,
                                                 on_close=self._on_close)
                self.ws.run_forever()
            except Exception as e:
                print(f"[Network Thread] Lỗi: {e}. Đang thử kết nối lại sau 5 giây...")
                self.is_connected = False
                time.sleep(5)

    def _on_open(self, ws):
        """Được gọi khi kết nối thành công."""
        print("[Network] Đã kết nối tới Server!")
        self.is_connected = True

    def _on_message(self, ws, message):
        """Được gọi khi nhận được tin nhắn từ Server."""
        try:
            # Phân tích JSON
            data = json.loads(message)
            # Bỏ tin nhắn vào hàng đợi để luồng game chính xử lý
            self.message_queue.put(data)
        except json.JSONDecodeError:
            print(f"[Network] Nhận được tin nhắn không phải JSON: {message}")

    def _on_error(self, ws, error):
        """Được gọi khi có lỗi mạng."""
        print(f"[Network Error] {error}")
        self.is_connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """Được gọi khi kết nối bị đóng."""
        print("[Network] Đã đóng kết nối.")
        self.is_connected = False

    def send_message(self, data_dict):
        """
        Gửi một tin nhắn (dạng dict) cho Server.
        Hàm này được gọi từ luồng game chính.
        """
        if self.is_connected and self.ws:
            try:
                # Chuyển dict thành chuỗi JSON và gửi đi
                self.ws.send(json.dumps(data_dict))
            except Exception as e:
                print(f"[Network Send Error] {e}")
        else:
            print("[Network] Không thể gửi tin: Chưa kết nối.")

    def get_message(self):
        """
V)
        Lấy một tin nhắn từ hàng đợi.
        Hàm này được gọi từ luồng game chính (trong vòng lặp).
        """
        try:
            # get_nowait() sẽ không làm "đứng" game nếu hàng đợi rỗng
            return self.message_queue.get_nowait()
        except queue.Empty:
            # Hàng đợi rỗng, không có tin nhắn mới
            return None