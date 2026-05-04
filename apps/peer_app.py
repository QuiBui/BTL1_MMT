import json
import asyncio
from daemon import AsynapRous

app = AsynapRous()

# Chỉ lưu tin nhắn trên máy của peer này, không lưu active_peers nữa
channels = {
    "general": [],  
    "hcmut": []     
}
logged_in_users = []

# Khai báo cứng IP và Port của Tracker để Peer biết đường tìm đến
TRACKER_HOST = "127.0.0.1" 
TRACKER_PORT = 9000

@app.route('/login', methods=['POST'])
async def login(headers="guest", body="anonymous"):
    try:
        data = json.loads(body)
        username = data.get("username", "")
        password = data.get("password", "")
        
        if password == "123456":
            if username in logged_in_users:
                return json.dumps({"status": "error", "message": "Tên này đã có người sử dụng!"}).encode("utf-8")
            
            logged_in_users.append(username)
            return json.dumps({"status": "success", "message": "Đăng nhập thành công"}).encode("utf-8")
        else:
            return json.dumps({"status": "error", "message": "Sai mật khẩu!"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"status": "error", "message": "Request không hợp lệ"}).encode("utf-8")



@app.route('/local-register', methods=['POST'])
async def local_register(headers, body):
    if headers != 'authenticated_user':
        return json.dumps({"status": "error", "message": "Unauthorized: Yêu cầu đăng nhập!"}).encode("utf-8")
    try:
        # Backend tự động báo danh lên Tracker bằng Non-blocking TCP Socket
        tracker_reader, tracker_writer = await asyncio.open_connection(TRACKER_HOST, TRACKER_PORT)
        
        # Lấy IP và Port hiện tại của chính Backend này
        my_info = {
            "ip": app.ip if app.ip != '0.0.0.0' else '127.0.0.1', 
            "port": app.port
        }
        body_bytes = json.dumps(my_info).encode('utf-8')
        
        # Đóng gói HTTP Request thuần
        req_tracker = (
            f"POST /submit-info HTTP/1.1\r\n"
            f"Host: {TRACKER_HOST}:{TRACKER_PORT}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body_bytes)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode('utf-8') + body_bytes
        
        tracker_writer.write(req_tracker)
        await tracker_writer.drain()
        tracker_writer.close()
        
        print(f"[Peer Node] Đã báo danh thành công lên Tracker tại {TRACKER_HOST}:{TRACKER_PORT}")
        return json.dumps({"status": "success"}).encode("utf-8")
    
    except Exception as e:
        print(f"[Peer Error] Lỗi khi báo danh lên Tracker: {e}")
        return json.dumps({"error": str(e)}).encode("utf-8")
@app.route('/send-peer', methods=['POST'])
async def send_peer(headers, body):
    try:
        clean_body = body.strip("\x00").strip()
        msg = json.loads(clean_body)
        channel = msg.get("channel", "general")
        
        if channel not in channels:
            channels[channel] = []
        channels[channel].append(msg)
        print(f"[P2P] Nhận tin nhắn trực tiếp từ {msg.get('sender')}: {msg.get('text')}")
        
        return json.dumps({"status": "received"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)}).encode("utf-8")

@app.route('/broadcast-peer', methods=['POST'])
async def broadcast_peer(headers, body):
    if headers != 'authenticated_user':
        return json.dumps({"status": "error", "message": "Unauthorized: Yêu cầu đăng nhập!"}).encode("utf-8")
    try:
        clean_body = body.strip("\x00").strip()
        msg = json.loads(clean_body)
        channel = msg.get("channel", "general")
        
        # 1. Lưu tin nhắn vào kênh của chính mình trước
        if channel not in channels:
            channels[channel] = []
        channels[channel].append(msg)
        
        # 2. Lấy danh sách peers từ Tracker bằng Non-blocking TCP Socket
        try:
            tracker_reader, tracker_writer = await asyncio.open_connection(TRACKER_HOST, TRACKER_PORT)
            req_tracker = f"GET /get-list HTTP/1.1\r\nHost: {TRACKER_HOST}:{TRACKER_PORT}\r\nConnection: close\r\n\r\n"
            tracker_writer.write(req_tracker.encode('utf-8'))
            await tracker_writer.drain()
            
            tracker_res_bytes = await tracker_reader.read()
            tracker_writer.close()
            
            # Phân tách HTTP Header và Body
            tracker_res_str = tracker_res_bytes.decode('utf-8', errors='ignore')
            res_body_str = tracker_res_str.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in tracker_res_str else "{}"
            
            active_peers = json.loads(res_body_str).get("peers", [])
        except Exception as e:
            print(f"[P2P Error] Không thể kết nối Tracker: {e}")
            active_peers = []
            
        print(f"[P2P] Đang broadcast tin nhắn của {msg.get('sender')} cho {len(active_peers)} peers...")

        # 3. Gửi tin nhắn P2P trực tiếp tới các Peer khác (Non-blocking)
        clean_body_bytes = clean_body.encode('utf-8')
        for peer in active_peers:
            # Bỏ qua chính bản thân mình
            is_self_ip = peer['ip'] in [app.ip, '127.0.0.1', 'localhost', '0.0.0.0']
            if is_self_ip and int(peer['port']) == int(app.port):
                continue
            
            try:
                # Mở socket trực tiếp tới peer
                peer_reader, peer_writer = await asyncio.open_connection(peer['ip'], int(peer['port']))
                
                req_p2p = (
                    f"POST /send-peer HTTP/1.1\r\n"
                    f"Host: {peer['ip']}:{peer['port']}\r\n"
                    f"Content-Type: application/json\r\n"
                    f"Content-Length: {len(clean_body_bytes)}\r\n"
                    f"Connection: close\r\n\r\n"
                ).encode('utf-8') + clean_body_bytes
                
                peer_writer.write(req_p2p)
                await peer_writer.drain()
                peer_writer.close()
            except Exception as e:
                print(f"[P2P Warning] Không thể gửi đến peer {peer['ip']}:{peer['port']} - {e}")
                
        return json.dumps({"status": "broadcasted"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)}).encode("utf-8")

@app.route('/get-messages', methods=['POST'])
async def get_messages(headers, body):
    if headers != 'authenticated_user':
        return json.dumps({"messages": [{"sender": "Hệ thống", "text": "Lỗi xác thực, vui lòng đăng nhập lại!"}]}).encode("utf-8")
    try:
        clean_body = body.strip("\x00").strip()
        req_data = json.loads(clean_body)
        channel = req_data.get("channel", "general")
        return json.dumps({"messages": channels.get(channel, [])}).encode("utf-8")
    except Exception:
         return json.dumps({"messages": []}).encode("utf-8")

def create_peerapp(ip, port):
    app.prepare_address(ip, port)
    app.run()