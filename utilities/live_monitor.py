#!/usr/bin/env python3
"""
Live monitoring script for RedshiftManager
Shows real-time logs and system status
"""

import os
import subprocess
import time
from datetime import datetime
from pathlib import Path


def show_header():
    """Show monitoring header"""
    print("\033[2J\033[H")  # Clear screen
    print("=" * 80)
    print(f"🚀 RedshiftManager Live Monitor - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)


def show_process_status():
    """Show running processes"""
    print("📊 Process Status:")
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        lines = result.stdout.split("\n")

        for line in lines:
            if "streamlit" in line and "grep" not in line:
                parts = line.split()
                if len(parts) > 10:
                    pid = parts[1]
                    cpu = parts[2]
                    mem = parts[3]
                    print(
                        f"  🟢 Streamlit UI (PID: {pid}) - CPU: {cpu}%, Memory: {mem}%"
                    )

            if "python.*api" in line and "grep" not in line:
                parts = line.split()
                if len(parts) > 10:
                    pid = parts[1]
                    cpu = parts[2]
                    mem = parts[3]
                    print(
                        f"  🟢 FastAPI Server (PID: {pid}) - CPU: {cpu}%, Memory: {mem}%"
                    )
    except Exception as e:
        print(f"  ❌ Error checking processes: {e}")


def show_service_urls():
    """Show service URLs"""
    print("\n🌐 Service URLs:")
    print("  📱 Streamlit UI: http://localhost:8501")
    print("  🔗 FastAPI Server: http://localhost:8000")
    print("  📚 API Docs: http://localhost:8000/docs")


def show_live_logs():
    """Show recent log entries"""
    print("\n📋 Recent Log Activity (last 10 entries):")
    print("-" * 80)

    log_files = [
        ("Main System", "logs/main_20250728.log"),
        ("Errors", "logs/errors_20250728.log"),
        ("Streamlit", "streamlit_output.log"),
        ("FastAPI", "api_output.log"),
    ]

    for name, log_file in log_files:
        if Path(log_file).exists():
            try:
                result = subprocess.run(
                    ["tail", "-5", log_file], capture_output=True, text=True
                )
                if result.stdout.strip():
                    print(f"\n📄 {name} ({log_file}):")
                    for line in result.stdout.strip().split("\n"):
                        if line.strip():
                            # Color code log levels
                            if "| ERROR" in line or "ERROR:" in line:
                                print(f"  🔴 {line}")
                            elif "| INFO" in line or "INFO:" in line:
                                print(f"  🟢 {line}")
                            elif "| WARNING" in line or "WARNING:" in line:
                                print(f"  🟡 {line}")
                            else:
                                print(f"  ⚪ {line}")
            except Exception as e:
                print(f"  ❌ Error reading {log_file}: {e}")


def show_system_resources():
    """Show system resource usage"""
    print("\n💻 System Resources:")
    try:
        # Memory usage
        result = subprocess.run(["free", "-h"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            print(f"  💾 Memory: {lines[1]}")

        # CPU usage (simplified)
        result = subprocess.run(["uptime"], capture_output=True, text=True)
        if result.stdout:
            print(f"  🔥 Load: {result.stdout.strip()}")

    except Exception as e:
        print(f"  ❌ Resource check failed: {e}")


def main():
    """Main monitoring loop"""
    try:
        while True:
            show_header()
            show_process_status()
            show_service_urls()
            show_system_resources()
            show_live_logs()

            print("\n" + "=" * 80)
            print("🔄 Refreshing in 10 seconds... (Ctrl+C to stop)")
            print("=" * 80)

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n\n🛑 Live monitoring stopped by user")
        print("✅ Services are still running in background")
        print("📋 PID files: streamlit.pid, api.pid")


if __name__ == "__main__":
    main()
