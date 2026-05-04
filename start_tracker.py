import argparse
from apps.tracker_app import create_trackerapp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Tracker', description='Start the Tracker process')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=9000) # Tracker luôn chạy ở 9000
    args = parser.parse_args()
    
    print(f"Khởi động Centralized Tracker tại {args.server_ip}:{args.server_port}...")
    create_trackerapp(args.server_ip, args.server_port)