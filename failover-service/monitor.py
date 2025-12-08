import socket
import time
import os
import sys
from datetime import datetime

# Configuration
MONITOR_CONFIG = {
    "db_town_primary": "/triggers/promote_town",
    "db_character_primary": "/triggers/promote_character"
}

RETRY_COUNT = 3
CHECK_INTERVAL = 5  # seconds

def is_reachable(host, port=5432):
    """Simple TCP Check to see if the database port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"[ERROR] Error checking {host}: {e}")
        return False

def trigger_failover(host, trigger_path):
    if os.path.exists(trigger_path) or os.path.exists(trigger_path + ".done"):
        return

    print(f"[CRITICAL] {host} is DOWN. Initiating Failover...")
    try:
        with open(trigger_path, 'w') as f:
            f.write(f"Promoted at {datetime.now()}")
        print(f"[SUCCESS] Created trigger file: {trigger_path}")
    except Exception as e:
        print(f"[ERROR] Failed to create trigger file: {e}")

def monitor_loop():
    print(f"[{datetime.now()}] Starting Failover Monitor...", flush=True)

    # Track consecutive failure counts
    failures = {host: 0 for host in MONITOR_CONFIG}

    while True:
        for host, trigger_path in MONITOR_CONFIG.items():
            if is_reachable(host):
                # If Primary is UP, reset failure count
                if failures[host] > 0:
                    print(f"[INFO] {host} is back online.", flush=True)
                failures[host] = 0

                # Cleanup: If the trigger file exists but Primary is back, remove it
                # so the system is ready for the next failure.
                if os.path.exists(trigger_path):
                    try:
                        os.remove(trigger_path)
                        print(f"[INFO] Cleared stale trigger for {host}", flush=True)
                    except OSError:
                        pass
            else:
                # If Primary is DOWN, increment count
                failures[host] += 1
                print(f"[WARN] {host} unreachable ({failures[host]}/{RETRY_COUNT})", flush=True)

                if failures[host] >= RETRY_COUNT:
                    trigger_failover(host, trigger_path)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Ensure the directory for triggers exists
    os.makedirs("/triggers", exist_ok=True)
    monitor_loop()