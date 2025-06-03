#!/usr/bin/env python3
"""
即時監測功能測試腳本
"""
import sys
import os
import time

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.realtime_monitor import RealtimeMonitor


def test_basic_monitoring():
    """測試基本即時監測功能"""
    print("開始測試即時監測功能...")
    
    # 建立監測器
    monitor = RealtimeMonitor(
        target="8.8.8.8",  # Google DNS
        port=53,
        protocol="tcp",
        interval=5,  # 15 秒間隔
        max_history=10
    )
    
    try:
        print(f"目標: {monitor.target}:{monitor.port}")
        print(f"間隔: {monitor.interval} 秒")
        print("按 Ctrl+C 停止監測並進入選單")
        print("-" * 50)
        
        # 開始監測
        monitor.start_monitoring(display_live=True)
        
    except KeyboardInterrupt:
        print("\n監測被中斷")
    except Exception as e:
        print(f"錯誤: {e}")
    finally:
        monitor.stop_monitoring()


if __name__ == "__main__":
    test_basic_monitoring()