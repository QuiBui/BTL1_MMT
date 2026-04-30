#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# AsynapRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
app.sampleapp
~~~~~~~~~~~~~~~~~

"""


import sys
import os
import importlib.util
import json
import urllib.request
import asyncio

from daemon import AsynapRous

app = AsynapRous()

# Biến toàn cục lưu trữ trạng thái mạng
active_peers = [
    {"ip": "127.0.0.1", "port": 2026},
    {"ip": "127.0.0.1", "port": 2027}
]
channels = {
    "general": [],  
    "hcmut": []     
}

# Thêm danh sách này ở đầu file, chỗ khai báo active_peers
logged_in_users = []

@app.route('/login', methods=['POST'])
async def login(headers="guest", body="anonymous"):
    try:
        data = json.loads(body)
        username = data.get("username", "")
        password = data.get("password", "")
        
        if password == "123456":
            # KIỂM TRA TRÙNG TÊN 
            if username in logged_in_users:
                return json.dumps({"status": "error", "message": "Tên này đã có người sử dụng!"}).encode("utf-8")
            
            # Nếu chưa ai dùng thì cho phép đăng nhập và lưu tên lại
            logged_in_users.append(username)
            return json.dumps({"status": "success", "message": "Đăng nhập thành công"}).encode("utf-8")
        else:
            return json.dumps({"status": "error", "message": "Sai mật khẩu!"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"status": "error", "message": "Request không hợp lệ"}).encode("utf-8")
    


@app.route('/submit-info', methods=['POST'])
async def submit_info(headers, body):
    try:
        peer = json.loads(body)
        if peer not in active_peers:
            active_peers.append(peer)
            print(f"[Tracker] Peer mới tham gia: {peer['ip']}:{peer['port']}")
        return json.dumps({"status": "success"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)}).encode("utf-8")

@app.route('/get-list', methods=['GET'])
async def get_list(headers, body):
    return json.dumps({"peers": active_peers, "channels": list(channels.keys())}).encode("utf-8")

@app.route('/add-list', methods=['POST'])
async def add_list(headers, body):
    try:
        new_peers = json.loads(body).get("peers", [])
        for p in new_peers:
            if p not in active_peers:
                active_peers.append(p)
        return json.dumps({"status": "updated", "total_peers": len(active_peers)}).encode("utf-8")
    except Exception as e:
         return json.dumps({"error": str(e)}).encode("utf-8")

@app.route('/connect-peer', methods=['POST'])
async def connect_peer(headers, body):
    return json.dumps({"status": "ready"}).encode("utf-8")

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
    try:
        clean_body = body.strip("\x00").strip()
        msg = json.loads(clean_body)
        channel = msg.get("channel", "general")
        
        # Lưu vào kênh của chính mình trước
        if channel not in channels:
            channels[channel] = []
        channels[channel].append(msg) 
        
        print(f"[P2P] Đang broadcast tin nhắn của {msg.get('sender')} cho {len(active_peers)} peers...")
        
        # Gửi đến tất cả các peer đang online (Non-blocking)
        for peer in active_peers:
            is_self_ip = peer['ip'] in [app.ip, '127.0.0.1', 'localhost', '0.0.0.0']
            if is_self_ip and int(peer['port']) == int(app.port):
                continue
            target_url = f"http://{peer['ip']}:{peer['port']}/send-peer"
            try:
                req = urllib.request.Request(
                    target_url, 
                    data=clean_body.encode('utf-8'), 
                    headers={'Content-Type': 'application/json'}, 
                    method='POST'
                )
                # Dùng asyncio.to_thread để không làm block Event Loop
                await asyncio.to_thread(urllib.request.urlopen, req, timeout=2) 
            except Exception as e:
                print(f"[P2P Warning] Không thể gửi đến {target_url}: {e}")
                pass 
                
        return json.dumps({"status": "broadcasted"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)}).encode("utf-8")

@app.route('/get-messages', methods=['POST'])
async def get_messages(headers, body):
    try:
        clean_body = body.strip("\x00").strip()
        req_data = json.loads(clean_body)
        channel = req_data.get("channel", "general")
        return json.dumps({"messages": channels.get(channel, [])}).encode("utf-8")
    except Exception:
         return json.dumps({"messages": []}).encode("utf-8")

def create_sampleapp(ip, port):
    app.prepare_address(ip, port)
    app.run()