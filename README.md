# 🎮 CARO GAME ONLINE

Một game Cờ Caro (Tic-tac-toe) trực tuyến đa người chơi được xây dựng với Python, Pygame và WebSocket.

## ✨ Tính năng chính

### 🎯 Gameplay
- **4 chế độ chơi**: 3x3 (3 quân), 6x6 (4 quân), 9x9 (5 quân), 12x12 (6 quân)
- **Realtime multiplayer** với WebSocket
- **Timer system**: 30 giây/lượt với timeout handling
- **Multiple win conditions**: thắng thường, timeout, đầu hàng, disconnect

### 👥 Hệ thống người dùng
- Đăng ký/Đăng nhập với mã hóa bcrypt
- Thống kê thắng/thua cá nhân
- Bảng xếp hạng toàn server
- Lịch sử trận đấu với phân trang

### 🏠 Hệ thống phòng chơi
- **Tạo phòng** với mật khẩu tùy chọn
- **Tìm phòng** theo game mode
- **Quick Join** - matchmaking thông minh
- **Nhập mã phòng** trực tiếp (5 ký tự)

### 🎨 Giao diện
- UI hiện đại với theme nhất quán
- Support font tiếng Việt đầy đủ
- Responsive design với hover effects
- Multiple screens với smooth transitions

## 🏗️ Kiến trúc

```
📁 LTMANG1/
├── 🎮 client/              # Game client (Pygame)
│   ├── main.py            # Game loop chính & UI
│   ├── network.py         # WebSocket client
│   ├── theme.py           # Theme & colors
│   ├── ui_components.py   # UI components
│   └── assets/            # Fonts & resources
│
├── 🖥️ server/             # Game server (AsyncIO)
│   ├── server.py          # WebSocket server
│   ├── game_logic.py      # Game logic & rooms
│   ├── database_manager.py # MySQL operations
│   └── config.py          # Server configuration
│
├── 📚 docs/               # Documentation
├── 🧪 tests/              # Test files
└── 🔧 scripts/            # Utility scripts
```

## 🚀 Quick Start

### 1. Cài đặt Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
```bash
# Tạo database MySQL
mysql -u root -p -e "CREATE DATABASE caro;"

# Cấu hình trong server/config.py
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root', 
    'password': 'your_password',
    'database': 'caro'
}
```

### 3. Chạy Server
```bash
cd server
python server.py
```

### 4. Chạy Client
```bash
cd client  
python main.py
```

## 📖 Documentation

- [📋 Setup Guide](docs/SETUP.md) - Hướng dẫn cài đặt chi tiết
- [🏗️ Architecture](docs/ARCHITECTURE.md) - Kiến trúc hệ thống
- [🔌 API Reference](docs/API.md) - WebSocket API documentation
- [🎮 Game Rules](docs/GAME_RULES.md) - Luật chơi và mechanics
- [🔧 Configuration](docs/CONFIGURATION.md) - Cấu hình và settings

## 🛠️ Development

### Code Structure
- **Client**: Event-driven với Pygame, state machine cho UI
- **Server**: AsyncIO WebSocket với room-based architecture
- **Database**: MySQL với bcrypt authentication
- **Protocol**: JSON-based WebSocket messages

### Adding Features
1. **New Game Mode**: Modify `_get_board_size()` in `game_logic.py`
2. **New UI Screen**: Add state to `main.py` và handler tương ứng
3. **New API**: Add action handler trong `server.py` và `game_logic.py`

## 🧪 Testing

```bash
# Run tests (when available)
python -m pytest tests/

# Manual testing
python scripts/test_server.py
```

## 📦 Deployment

### Production Setup
1. Cấu hình MySQL cho production
2. Set proper `SERVER_HOST` và `SERVER_PORT`
3. Use reverse proxy (nginx) cho WebSocket
4. Setup SSL/TLS certificates

### Docker (Optional)
```bash
# Build và run với Docker
docker-compose up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature-name`
5. Submit Pull Request

## 📝 License

Dự án học tập - UTH PMHDT LTMANG1

## 👨‍💻 Authors

- **Quanagf** - Initial work

---

## 📞 Support

Nếu gặp vấn đề, hãy tạo issue hoặc liên hệ qua:
- GitHub Issues
- Email: [your-email@example.com]
