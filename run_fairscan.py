import os
import sys
import socket
import subprocess
import time
import webbrowser

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True

def find_available_port(start_port: int, host: str = "127.0.0.1", max_attempts: int = 20) -> int:
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port, host):
            return port
    return start_port

def kill_process_on_port(port: int):
    """Gracefully terminate existing process on Windows using the port."""
    try:
        cmd = f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
        pids = [p.strip() for p in res.stdout.splitlines() if p.strip() and p.strip() != "0"]
        for pid in pids:
            try:
                subprocess.run(["powershell", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"], capture_output=True)
                print(f"  • Terminated leftover process (PID {pid}) on port {port}.")
            except Exception:
                pass
    except Exception:
        pass

def main():
    print("=========================================================")
    print("  FairScan — Dataset Fairness & Bias Audit Platform")
    print("=========================================================")

    root_dir = os.path.dirname(os.path.abspath(__file__))

    # Target Backend Port
    target_backend_port = 8000
    if is_port_in_use(target_backend_port):
        print(f"[!] Port {target_backend_port} is busy. Clearing previous session...")
        kill_process_on_port(target_backend_port)
        time.sleep(1)

    # If still in use, fallback to next open port
    backend_port = find_available_port(target_backend_port)
    if backend_port != target_backend_port:
        print(f"[*] Port {target_backend_port} reserved by OS. Using open port: {backend_port}")

    # 1. Start FastAPI Backend
    print(f"\n[1/2] Starting FastAPI analytical server on http://127.0.0.1:{backend_port} ...")
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(backend_port),
    ]
    backend_proc = subprocess.Popen(backend_cmd, cwd=root_dir)

    # 2. Start Vite Frontend
    print("[2/2] Starting React Vite frontend on http://localhost:5173 ...")
    frontend_dir = os.path.join(root_dir, "frontend")
    frontend_env = os.environ.copy()
    frontend_env["VITE_API_PORT"] = str(backend_port)
    frontend_proc = subprocess.Popen(["npm", "run", "dev"], cwd=frontend_dir, env=frontend_env, shell=True)

    print("\n✓ FairScan Services Online!")
    print(f"  • Web UI:      http://localhost:5173")
    print(f"  • Backend API: http://127.0.0.1:{backend_port}/docs")
    print("\nPress Ctrl+C to stop services.\n")

    try:
        time.sleep(2)
        webbrowser.open("http://localhost:5173")
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("FairScan stopped cleanly.")

if __name__ == "__main__":
    main()
