import json
from daemon import AsynapRous

app = AsynapRous()
active_peers = [] # Chỉ Tracker mới giữ biến này

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
    return json.dumps({"peers": active_peers}).encode("utf-8")

def create_trackerapp(ip, port):
    app.prepare_address(ip, port)
    app.run()