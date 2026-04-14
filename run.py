import subprocess
import time
import os
import sys
import requests

print("🚀 Starting AI Document Q&A System...")

venv_python = os.path.join("venv", "Scripts", "python.exe")

if not os.path.exists(venv_python):
    print("❌ Virtual environment not found.")
    sys.exit(1)

try:
    print("🧠 Starting Backend...")
    backend = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "backend:app", "--reload"],
        shell=True
    )

    # Wait until backend is actually ready
    print("⏳ Waiting for backend to be ready...")

    backend_ready = False
    for _ in range(30):  # wait up to 30 seconds
        try:
            res = requests.get("http://127.0.0.1:8000/docs")
            if res.status_code == 200:
                backend_ready = True
                print("✅ Backend is ready")
                break
        except:
            pass
        time.sleep(1)

    if not backend_ready:
        print("❌ Backend failed to start.")
        backend.terminate()
        sys.exit(1)

    print("🎨 Starting Frontend...")
    frontend = subprocess.Popen(
        [venv_python, "-m", "streamlit", "run", "app.py"],
        shell=True
    )

    print("✅ System started!")
    print("🌐 Open: http://localhost:8501")

    backend.wait()
    frontend.wait()

except KeyboardInterrupt:
    print("\n🛑 Shutting down...")
    backend.terminate()
    frontend.terminate()