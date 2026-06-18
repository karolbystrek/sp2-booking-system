import subprocess
import time
import sys
import os

services = [
    {"name": "API Gateway", "dir": "api_gateway", "port": 8000},
    {"name": "Identity Service", "dir": "identity_service", "port": 8001},
    {"name": "Schedule Service", "dir": "schedule_service", "port": 8002},
    {"name": "Reservations Service", "dir": "reservations_service", "port": 8003},
    {"name": "Availability Service", "dir": "availability_service", "port": 8004},
    {"name": "Notifications Service", "dir": "notifications_service", "port": 8005},
    {"name": "Event Broker", "dir": "event_broker", "port": 8006},
]

processes = []

def run_db_init():
    print("Initializing databases...")
    try:
        subprocess.run([sys.executable, "-m", "identity_service.init_db"], cwd=".", check=True)
        print("Identity DB initialized.")
    except Exception as e:
        print(f"Failed to initialize Identity DB: {e}")

if __name__ == "__main__":
    if "init" in sys.argv:
        run_db_init()
        
    print("Starting services...")
    for svc in services:
        print(f"Starting {svc['name']} on port {svc['port']}...")
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", f"{svc['dir']}.main:app", "--host", "0.0.0.0", "--port", str(svc['port'])],
            cwd="."
        )
        processes.append(process)

    try:
        print("All services started. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping all services...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
        print("All services stopped.")
