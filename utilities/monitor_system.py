#!/usr/bin/env python3
"""
Real-time system monitoring for RedshiftManager
Monitor logs, processes, and system status
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Add project path
sys.path.append(str(Path(__file__).parent))


def print_header():
    """Print monitoring header"""
    print("=" * 80)
    print("🔍 RedshiftManager - Real-Time System Monitor")
    print("=" * 80)
    print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 80)


def check_processes():
    """Check if services are running"""
    print("\n🔧 Process Status:")

    # Check Streamlit
    try:
        with open("streamlit.pid", "r") as f:
            streamlit_pid = f.read().strip()

        result = subprocess.run(
            ["ps", "-p", streamlit_pid], capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ Streamlit: Running (PID: {streamlit_pid})")
        else:
            print("❌ Streamlit: Not running")
    except FileNotFoundError:
        print("❌ Streamlit: PID file not found")

    # Check FastAPI
    try:
        with open("api.pid", "r") as f:
            api_pid = f.read().strip()

        result = subprocess.run(["ps", "-p", api_pid], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ FastAPI: Running (PID: {api_pid})")
        else:
            print("❌ FastAPI: Not running")
    except FileNotFoundError:
        print("❌ FastAPI: PID file not found")


def check_endpoints():
    """Check if endpoints are responding"""
    print("\n🌐 Endpoint Status:")

    # Check Streamlit
    try:
        response = requests.get("http://localhost:8501", timeout=3)
        print(f"✅ Streamlit UI: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Streamlit UI: Connection failed")

    # Check FastAPI health
    try:
        response = requests.get("http://localhost:8000/health", timeout=3)
        if response.status_code == 200:
            print(f"✅ FastAPI Health: {response.status_code}")
        else:
            print(f"⚠️ FastAPI Health: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ FastAPI Health: Connection failed")

    # Check FastAPI docs
    try:
        response = requests.get("http://localhost:8000/docs", timeout=3)
        print(f"✅ FastAPI Docs: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ FastAPI Docs: Connection failed")


def monitor_logs():
    """Monitor log files"""
    print("\n📋 Recent Log Activity:")

    log_files = [
        "logs/main_20250728.log",
        "logs/errors_20250728.log",
        "streamlit_output.log",
        "api_output.log",
    ]

    for log_file in log_files:
        if Path(log_file).exists():
            # Get last 3 lines
            try:
                result = subprocess.run(
                    ["tail", "-3", log_file], capture_output=True, text=True
                )
                if result.stdout.strip():
                    print(f"\n📄 {log_file}:")
                    for line in result.stdout.strip().split("\n"):
                        if line.strip():
                            print(f"  {line}")
                else:
                    print(f"\n📄 {log_file}: (empty)")
            except Exception as e:
                print(f"\n📄 {log_file}: Error reading - {e}")
        else:
            print(f"\n📄 {log_file}: Not found")


def check_system_resources():
    """Check system resources"""
    print("\n💻 System Resources:")

    try:
        # CPU usage
        result = subprocess.run(["top", "-bn1"], capture_output=True, text=True)
        cpu_line = [line for line in result.stdout.split("\n") if "Cpu(s)" in line]
        if cpu_line:
            print(f"🔥 {cpu_line[0].strip()}")

        # Memory usage
        result = subprocess.run(["free", "-h"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            print(f"💾 {lines[1]}")

        # Disk usage
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            print(f"💿 {lines[1]}")

    except Exception as e:
        print(f"❌ Resource check failed: {e}")


def monitor_live_logs():
    """Monitor logs in real-time"""
    print("\n📺 Live Log Monitoring (last 10 seconds):")
    print("Press Ctrl+C to stop...")

    try:
        # Monitor main log file
        main_log = "logs/main_20250728.log"
        if Path(main_log).exists():
            subprocess.run(["tail", "-f", main_log], timeout=10)
    except subprocess.TimeoutExpired:
        print("\n⏱️ Live monitoring timeout (10 seconds)")
    except KeyboardInterrupt:
        print("\n⏹️ Live monitoring stopped")


def main():
    """Main monitoring function"""
    print_header()

    while True:
        try:
            check_processes()
            check_endpoints()
            check_system_resources()
            monitor_logs()

            print("\n" + "=" * 80)
            print("🔄 Next check in 30 seconds... (Ctrl+C to stop)")
            print("=" * 80)

            time.sleep(30)

            # Clear screen for next iteration
            os.system("clear" if os.name == "posix" else "cls")
            print_header()

        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"\n❌ Error in monitoring: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
