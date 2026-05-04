import argparse
from apps.peer_app import create_peerapp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Peer', description='Start a Peer node')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=2026) # Peer mặc định chạy cổng 2026
    args = parser.parse_args()
    
    print(f"Khởi động Peer Node tại {args.server_ip}:{args.server_port}...")
    create_peerapp(args.server_ip, args.server_port)