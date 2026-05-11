import json
from daemon.asynaprous import AsynapRous

app = AsynapRous() 
active_peers = {} 

@app.route('/submit-info', methods=['POST'])
async def submit_info(headers="guest", body=""):
    try:
        peer_data = json.loads(body)
        username = peer_data.get("username")
        
        if not username:
            return json.dumps({"status": "error"}).encode("utf-8")
            
        active_peers[username] = {
            "ip": peer_data.get("ip"),
            "port": peer_data.get("port")
        }
        print(f"[Tracker] Peer báo danh: {username} tại {peer_data['ip']}:{peer_data['port']}")
        return json.dumps({"status": "success"}).encode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)}).encode("utf-8")

@app.route('/get-list', methods=['GET'])
async def get_list(headers="guest", body=""):
    return json.dumps({"peers": active_peers}).encode("utf-8")

def create_trackerapp(ip, port):
    app.prepare_address(ip, port)
    app.run()