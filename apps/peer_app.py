import json
import asyncio
from daemon.asynaprous import AsynapRous

app = AsynapRous()

# --- DATABASE 4 TÀI KHOẢN ---
USERS_DB = {
    "duy": "duy",
    "qui": "qui",
    "an": "an",
    "van": "van"
}

# --- DATABASE TẠM TRÊN RAM ---
logged_in_users = []
p2p_messages = {} 

TRACKER_HOST = "127.0.0.1" 
TRACKER_PORT = 9005


@app.route('/login', methods=['POST'])
async def login(headers="guest", body="anonymous"):
    try:
        data = json.loads(body)
        username = data.get("username", "").strip()
        password = data.get("password", username).strip() 
        
        if username in USERS_DB and USERS_DB[username] == password:
            # KIỂM TRA BẢO MẬT: 1 Cổng = 1 Node = 1 Người Dùng
            # Nếu danh sách đã có người, và người đó KHÔNG PHẢI là user đang cố đăng nhập (trường hợp F5 tải lại trang)
            if len(logged_in_users) > 0 and username not in logged_in_users:
                return json.dumps({
                    "status": "error", 
                    "message": f"Cổng này đang được sử dụng bởi '{logged_in_users[0]}'. Vui lòng chạy một cổng khác!"
                }).encode("utf-8")

            if username not in logged_in_users:
                logged_in_users.append(username)
            return json.dumps({"status": "success", "username": username}).encode("utf-8")
            
        return json.dumps({"status": "error", "message": "Sai tài khoản hoặc mật khẩu!"}).encode("utf-8")
    except Exception:
        return json.dumps({"status": "error"}).encode("utf-8")


@app.route('/logout', methods=['POST'])
async def logout_api(headers="guest", body="anonymous"):
    """API giải phóng cổng khi người dùng bấm Thoát"""
    try:
        data = json.loads(body)
        username = data.get("username", "")
        # Xóa user khỏi danh sách để nhường cổng cho người khác
        if username in logged_in_users:
            logged_in_users.remove(username)
        return json.dumps({"status": "success"}).encode("utf-8")
    except Exception:
        return json.dumps({"status": "error"}).encode("utf-8")



@app.route('/get-session-info', methods=['GET'])
async def get_session_info(headers="guest", body="anonymous"):
    if logged_in_users:
        return json.dumps({"status": "success", "username": logged_in_users[-1]}).encode("utf-8")
    return json.dumps({"status": "unauthorized"}).encode("utf-8")

# ==========================================
# GIAO TIẾP VỚI TRACKER 
# ==========================================
@app.route('/local-register', methods=['POST'])
async def local_register(headers="guest", body=""):
    try:
        req_data = json.loads(body)
        my_username = req_data.get("username", logged_in_users[-1] if logged_in_users else "unknown")
        
        tracker_reader, tracker_writer = await asyncio.open_connection(TRACKER_HOST, TRACKER_PORT)
        my_info = {
            "username": my_username,
            "ip": app.ip if app.ip != '0.0.0.0' else '127.0.0.1', 
            "port": app.port
        }
        body_bytes = json.dumps(my_info).encode('utf-8')
        
        req_tracker = (
            f"POST /submit-info HTTP/1.1\r\n"
            f"Host: {TRACKER_HOST}:{TRACKER_PORT}\r\n"
            f"Content-Length: {len(body_bytes)}\r\n\r\n"
        ).encode('utf-8') + body_bytes
        
        tracker_writer.write(req_tracker)
        await tracker_writer.drain()
        tracker_writer.close()
        
        return json.dumps({"status": "success"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)}).encode("utf-8")

@app.route('/get-peers', methods=['GET'])
async def get_peers_api(headers="guest", body=""):
    try:
        tracker_reader, tracker_writer = await asyncio.open_connection(TRACKER_HOST, TRACKER_PORT)
        req_tracker = f"GET /get-list HTTP/1.1\r\nHost: {TRACKER_HOST}:{TRACKER_PORT}\r\n\r\n"
        tracker_writer.write(req_tracker.encode('utf-8'))
        await tracker_writer.drain()
        
        tracker_res_bytes = await tracker_reader.read()
        tracker_writer.close()
        
        tracker_res_str = tracker_res_bytes.decode('utf-8', errors='ignore')
        res_body_str = tracker_res_str.split("\r\n\r\n", 1)[1] if "\r\n\r\n" in tracker_res_str else "{}"
        
        return res_body_str.encode('utf-8') 
    except Exception:
        return json.dumps({"peers": {}}).encode("utf-8")

# ==========================================
# GIAO TIẾP P2P (TRỰC TIẾP GIỮA CÁC MÁY)
# ==========================================



@app.route('/frontend-send', methods=['POST'])
async def frontend_send(headers="guest", body=""):
    try:
        data = json.loads(body)
        target_info = data.get("target") 
        target_username = data.get("target_username")
        # FIX TÊN: Lấy chính xác tên người gửi do Frontend truyền vào
        my_username = data.get("sender", logged_in_users[-1] if logged_in_users else "unknown")
        text = data.get("message")
        
        if target_username not in p2p_messages:
            p2p_messages[target_username] = []
        p2p_messages[target_username].append({"from": "me", "text": text})

        peer_reader, peer_writer = await asyncio.open_connection(target_info['ip'], target_info['port'])
        payload = json.dumps({"sender_username": my_username, "text": text}).encode('utf-8')
        
        req_p2p = (
            f"POST /p2p-receive HTTP/1.1\r\n"
            f"Content-Length: {len(payload)}\r\n\r\n"
        ).encode('utf-8') + payload
        
        peer_writer.write(req_p2p)
        await peer_writer.drain()
        peer_writer.close()
        
        return json.dumps({"status": "success"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"status": "failed", "error": str(e)}).encode("utf-8")

# Thêm vào phần database tạm trên RAM
group_messages = [] # Lưu tin nhắn của kênh chung #Chung



@app.route('/frontend-broadcast', methods=['POST'])
async def frontend_broadcast(headers="guest", body=""):
    try:
        data = json.loads(body)
        text = data.get("message")
        all_peers = data.get("peers", {}) 
        # FIX TÊN: Lấy chính xác tên do Frontend truyền vào
        my_username = data.get("sender", logged_in_users[-1] if logged_in_users else "unknown")

        # FIX DOUBLE TIN NHẮN: Kiểm tra trùng trước khi lưu
        msg_obj = {"from": my_username, "text": text, "is_group": True}
        if msg_obj not in group_messages:
            group_messages.append(msg_obj)

        for uname, info in all_peers.items():
            if uname == my_username: continue 
            
            try:
                peer_reader, peer_writer = await asyncio.open_connection(info['ip'], info['port'])
                payload = json.dumps({
                    "sender_username": my_username, 
                    "text": text,
                    "is_group": True 
                }).encode('utf-8')
                
                req_p2p = (
                    f"POST /p2p-receive HTTP/1.1\r\n"
                    f"Content-Length: {len(payload)}\r\n\r\n"
                ).encode('utf-8') + payload
                
                peer_writer.write(req_p2p)
                await peer_writer.drain()
                peer_writer.close()
            except:
                continue 

        return json.dumps({"status": "success"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}).encode("utf-8")


@app.route('/p2p-receive', methods=['POST'])
async def p2p_receive(headers="guest", body=""):
    try:
        data = json.loads(body.strip('\x00').strip())
        sender = data.get("sender_username")
        text = data.get("text")
        is_group = data.get("is_group", False)
        
        if is_group:
            # FIX DOUBLE TIN NHẮN: Chặn lưu trùng khi các tab tự gửi cho nhau
            msg_obj = {"from": sender, "text": text, "is_group": True}
            if msg_obj not in group_messages:
                group_messages.append(msg_obj)
        else:
            if sender not in p2p_messages: p2p_messages[sender] = []
            p2p_messages[sender].append({"from": sender, "text": text})
        
        return json.dumps({"status": "ok"}).encode("utf-8")
    except Exception:
        return json.dumps({"status": "error"}).encode("utf-8")


# Thêm API lấy lịch sử chat nhóm
@app.route('/get-group-history', methods=['GET'])
async def get_group_history(headers="guest", body=""):
    return json.dumps({"status": "success", "messages": group_messages}).encode("utf-8")
    
@app.route('/get-all-messages', methods=['GET'])
async def get_all_messages(headers="guest", body="anonymous"):
    try:
        # Kiểm tra xem có user nào đang đăng nhập không
        if not logged_in_users:
            return json.dumps({"status": "error"}).encode("utf-8")
        
        # Trả về cấu trúc gồm cả tin nhắn P2P và tin nhắn Group
        return json.dumps({
            "status": "success", 
            "p2p": p2p_messages, 
            "group": group_messages
        }).encode("utf-8")
    except Exception:
        return json.dumps({"status": "error"}).encode("utf-8")
    

@app.route('/get-chat-history', methods=['POST'])
async def get_chat_history(headers="guest", body=""):
    try:
        data = json.loads(body)
        target_username = data.get("target_username")
        history = p2p_messages.get(target_username, [])
        return json.dumps({"status": "success", "messages": history}).encode("utf-8")
    except Exception:
        return json.dumps({"status": "error"}).encode("utf-8")

def create_peerapp(ip, port):
    app.prepare_address(ip, port)
    app.run()