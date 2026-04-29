import sys
import os
import importlib.util
import json
import urllib.request

from daemon import AsynapRous

app = AsynapRous()

# Biến toàn cục lưu trữ trạng thái mạng
active_peers = []   
channels = {
    "general": [],  
    "hcmut": []     
}

@app.route('/login', methods=['POST'])
async def login(headers="guest", body="anonymous"):
    return json.dumps({"status": "success", "message": "Đăng nhập thành công"}).encode("utf-8")

@app.route('/submit-info', methods=['POST'])
async def submit_info(headers, body):
    try:
        peer = json.loads(body)
        if peer not in active_peers:
            active_peers.append(peer)
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
        print(f"[P2P] Nhận tin: {msg.get('text')}")
        return json.dumps({"status": "received"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)}).encode("utf-8")

@app.route('/broadcast-peer', methods=['POST'])
async def broadcast_peer(headers, body):
    try:
        clean_body = body.strip("\x00").strip()
        msg = json.loads(clean_body)
        channel = msg.get("channel", "general")
        
        if channel not in channels:
            channels[channel] = []
        channels[channel].append(msg) 
        
        for peer in active_peers:
            target_url = f"http://{peer['ip']}:{peer['port']}/send-peer"
            try:
                req = urllib.request.Request(target_url, data=clean_body.encode('utf-8'), 
                                             headers={'Content-Type': 'application/json'}, method='POST')
                urllib.request.urlopen(req, timeout=2) 
            except Exception:
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