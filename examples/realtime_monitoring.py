#!/usr/bin/env python3
"""
即時監測功能使用範例
"""
import sys
import os
import time

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.realtime_monitor import RealtimeMonitor


def example_basic_monitoring():
    """基本即時監測範例"""
    print("=== 基本即時監測範例 ===")
    
    # 建立監測器
    monitor = RealtimeMonitor(
        target="8.8.8.8",  # Google DNS
        port=53,
        protocol="tcp",
        interval=5,  # 每 5 秒掃描一次
        max_history=50
    )
    
    try:
        print(f"開始監測 {monitor.target}:{monitor.port}")
        print("按 Ctrl+C 停止監測")
        
        # 開始監測（不顯示即時介面，僅在控制台輸出）
        monitor.start_monitoring(display_live=False)
        
        # 讓程式運行一段時間
        time.sleep(30)
        
        # 停止監測
        monitor.stop_monitoring()
        
        # 顯示統計
        stats = monitor.get_current_stats()
        print(f"\n監測完成統計:")
        print(f"總掃描次數: {stats.total_scans}")
        print(f"成功次數: {stats.successful_scans}")
        print(f"成功率: {stats.success_rate:.1f}%")
        
        if stats.successful_scans > 0:
            print(f"平均回應時間: {stats.avg_response_time:.1f}ms")
        
    except KeyboardInterrupt:
        print("\n監測被用戶中斷")
        monitor.stop_monitoring()


def example_with_callbacks():
    """使用回調函數的監測範例"""
    print("\n=== 回調函數監測範例 ===")
    
    scan_count = 0
    
    def on_scan_complete(result):
        """掃描完成回調"""
        nonlocal scan_count
        scan_count += 1
        
        stats = result.get_statistics()
        status = "✅" if stats['target_reached'] else "❌"
        
        print(f"掃描 #{scan_count}: {status} {result.target}:{result.port} "
              f"({stats['total_hops']} 跳點)")
    
    def on_status_change(is_reachable):
        """狀態變化回調"""
        status = "可達" if is_reachable else "不可達"
        print(f"🔄 狀態變化: 目標現在{status}")
    
    # 建立監測器
    monitor = RealtimeMonitor(
        target="github.com",
        port=443,
        protocol="tcp",
        interval=10
    )
    
    # 設定回調函數
    monitor.on_scan_complete = on_scan_complete
    monitor.on_status_change = on_status_change
    
    try:
        print(f"開始監測 {monitor.target}:{monitor.port} (使用回調)")
        print("按 Ctrl+C 停止監測")
        
        monitor.start_monitoring(display_live=False)
        time.sleep(60)  # 運行 1 分鐘
        
    except KeyboardInterrupt:
        print("\n監測被用戶中斷")
    finally:
        monitor.stop_monitoring()


def example_programmatic_monitoring():
    """程式化監測範例（不使用即時介面）"""
    print("\n=== 程式化監測範例 ===")
    
    monitor = RealtimeMonitor(
        target="1.1.1.1",  # Cloudflare DNS
        port=53,
        protocol="udp",
        interval=3,
        max_history=20
    )
    
    print(f"開始背景監測 {monitor.target}:{monitor.port}")
    
    # 啟動監測（背景模式）
    monitor.start_monitoring(display_live=False)
    
    try:
        # 模擬其他工作
        for i in range(10):
            time.sleep(5)
            
            # 每 5 秒檢查一次狀態
            stats = monitor.get_current_stats()
            print(f"[{i+1}/10] 掃描進度: {stats.total_scans} 次, "
                  f"成功率: {stats.success_rate:.1f}%")
            
            # 檢查歷史記錄
            history = monitor.get_history()
            if history:
                latest = history[-1]
                latest_stats = latest.get_statistics()
                print(f"         最新結果: {'✅' if latest_stats['target_reached'] else '❌'} "
                      f"{latest_stats['total_hops']} 跳點")
    
    finally:
        monitor.stop_monitoring()
        
        # 最終統計
        final_stats = monitor.get_current_stats()
        print(f"\n最終統計:")
        print(f"監測時間: {len(monitor.get_history()) * monitor.interval / 60:.1f} 分鐘")
        print(f"總掃描: {final_stats.total_scans} 次")
        print(f"成功率: {final_stats.success_rate:.1f}%")


def example_multiple_targets():
    """多目標監測範例"""
    print("\n=== 多目標監測範例 ===")
    
    targets = [
        ("8.8.8.8", 53, "tcp"),      # Google DNS
        ("1.1.1.1", 53, "tcp"),      # Cloudflare DNS  
        ("208.67.222.222", 53, "tcp") # OpenDNS
    ]
    
    monitors = []
    
    for target, port, protocol in targets:
        monitor = RealtimeMonitor(
            target=target,
            port=port,
            protocol=protocol,
            interval=8,
            max_history=10
        )
        monitors.append(monitor)
        
        # 啟動監測
        monitor.start_monitoring(display_live=False)
        print(f"已啟動監測: {target}:{port}")
    
    try:
        print("\n所有監測器已啟動，運行 60 秒...")
        time.sleep(60)
        
    finally:
        # 停止所有監測器並顯示結果
        print("\n停止所有監測器...")
        for i, monitor in enumerate(monitors):
            monitor.stop_monitoring()
            
            stats = monitor.get_current_stats()
            target_info = targets[i]
            print(f"{target_info[0]}:{target_info[1]} - "
                  f"成功率: {stats.success_rate:.1f}% "
                  f"({stats.successful_scans}/{stats.total_scans})")


def main():
    """主函數"""
    print("即時監測功能範例")
    print("=" * 50)
    
    examples = [
        ("基本監測", example_basic_monitoring),
        ("回調函數", example_with_callbacks),
        ("程式化監測", example_programmatic_monitoring),
        ("多目標監測", example_multiple_targets),
    ]
    
    for name, example_func in examples:
        try:
            print(f"\n🚀 執行範例: {name}")
            example_func()
            print(f"✅ 範例 '{name}' 完成")
            
        except KeyboardInterrupt:
            print(f"\n⏹️  範例 '{name}' 被中斷")
            break
        except Exception as e:
            print(f"❌ 範例 '{name}' 失敗: {str(e)}")
        
        # 稍作暫停
        time.sleep(2)
    
    print("\n🎉 所有範例執行完成！")


if __name__ == "__main__":
    main()