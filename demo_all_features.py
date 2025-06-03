#!/usr/bin/env python3
"""
完整功能演示腳本
"""
import sys
import time
from datetime import datetime

def demo_basic_scan():
    """演示基本掃描功能"""
    print("=" * 60)
    print("🚀 演示 1: 基本 traceroute 掃描")
    print("=" * 60)
    
    import subprocess
    
    cmd = [
        "uv", "run", "python", "main.py",
        "-t", "8.8.8.8",
        "-p", "53",
        "--protocol", "tcp",
        "--show-chart"
    ]
    
    print(f"執行命令: {' '.join(cmd)}")
    print("正在執行...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print("✅ 基本掃描完成")
        if result.returncode != 0:
            print(f"⚠️ 警告: 返回碼 {result.returncode}")
            print(f"錯誤輸出: {result.stderr}")
        
    except subprocess.TimeoutExpired:
        print("⏰ 掃描超時")
    except Exception as e:
        print(f"❌ 執行失敗: {e}")


def demo_batch_scan():
    """演示批量掃描功能"""
    print("\n" + "=" * 60)
    print("📦 演示 2: 批量掃描")
    print("=" * 60)
    
    import subprocess
    
    cmd = [
        "uv", "run", "python", "main.py",
        "-f", "examples/targets.txt",
        "--output-csv", f"batch_demo_{datetime.now().strftime('%H%M%S')}.csv",
        "--save-html"
    ]
    
    print(f"執行命令: {' '.join(cmd)}")
    print("正在執行批量掃描...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print("✅ 批量掃描完成")
        if result.returncode != 0:
            print(f"⚠️ 警告: 返回碼 {result.returncode}")
            print(f"錯誤輸出: {result.stderr}")
        
    except subprocess.TimeoutExpired:
        print("⏰ 批量掃描超時")
    except Exception as e:
        print(f"❌ 執行失敗: {e}")


def demo_realtime_monitoring():
    """演示即時監測功能"""
    print("\n" + "=" * 60)
    print("⏱️ 演示 3: 即時監測 (程式化)")
    print("=" * 60)
    
    try:
        from core.realtime_monitor import RealtimeMonitor
        
        # 建立監測器
        monitor = RealtimeMonitor(
            target="1.1.1.1",  # Cloudflare DNS
            port=53,
            protocol="tcp",
            interval=15,  # 15 秒間隔
            max_history=5   # 只保留 5 次記錄用於演示
        )
        
        print(f"目標: {monitor.target}:{monitor.port}")
        print(f"間隔: {monitor.interval} 秒")
        print("運行 5 次掃描...")
        print("-" * 40)
        
        # 啟動監測（背景模式）
        monitor.start_monitoring(display_live=False)
        
        # 讓它運行 5 次掃描
        for i in range(5):
            time.sleep(monitor.interval + 2)  # 多等 2 秒確保掃描完成
            
            stats = monitor.get_current_stats()
            print(f"掃描 {i+1}/5: 成功率 {stats.success_rate:.1f}% ({stats.successful_scans}/{stats.total_scans})")
        
        # 停止監測
        monitor.stop_monitoring()
        
        # 顯示最終統計
        final_stats = monitor.get_current_stats()
        print("\n📊 最終統計:")
        print(f"總掃描次數: {final_stats.total_scans}")
        print(f"成功次數: {final_stats.successful_scans}")
        print(f"成功率: {final_stats.success_rate:.1f}%")
        
        if final_stats.successful_scans > 0:
            print(f"平均回應時間: {final_stats.avg_response_time:.1f}ms")
        
        print("✅ 即時監測演示完成")
        
    except Exception as e:
        print(f"❌ 即時監測演示失敗: {e}")


def demo_enhanced_reports():
    """演示增強版報告功能"""
    print("\n" + "=" * 60)
    print("📋 演示 4: 增強版報告功能")
    print("=" * 60)
    
    try:
        from core.realtime_monitor import RealtimeMonitor
        
        # 建立監測器並運行短期監測
        monitor = RealtimeMonitor(
            target="8.8.8.8",
            port=53,
            protocol="tcp",
            interval=10,
            max_history=3
        )
        
        print("生成測試數據...")
        monitor.start_monitoring(display_live=False)
        
        # 運行 3 次掃描
        time.sleep(35)  # 約 3 次掃描的時間
        monitor.stop_monitoring()
        
        if monitor.get_current_stats().total_scans > 0:
            print("生成增強版 CSV 報告...")
            csv_file = monitor._create_enhanced_csv_report(f"demo_report_{datetime.now().strftime('%H%M%S')}.csv")
            print(f"✅ CSV 報告: {csv_file}")
            
            print("生成增強版 HTML 報告...")
            html_file = monitor._create_enhanced_html_report(f"demo_report_{datetime.now().strftime('%H%M%S')}.html")
            print(f"✅ HTML 報告: {html_file}")
            
            print("📈 報告包含:")
            print("  • 詳細統計摘要")
            print("  • 成功率趨勢圖表")
            print("  • 回應時間分析")
            print("  • 跳點穩定性分析")
            print("  • 完整掃描記錄")
            
        else:
            print("⚠️ 沒有產生足夠的測試數據")
        
    except Exception as e:
        print(f"❌ 報告演示失敗: {e}")


def main():
    """主演示函數"""
    print("🎯 nmapTraceroute 完整功能演示")
    print("=" * 60)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    demos = [
        ("基本掃描", demo_basic_scan),
        ("批量掃描", demo_batch_scan),
        ("即時監測", demo_realtime_monitoring),
        ("增強報告", demo_enhanced_reports),
    ]
    
    for name, demo_func in demos:
        try:
            demo_func()
        except KeyboardInterrupt:
            print(f"\n⏹️ 演示 '{name}' 被中斷")
            break
        except Exception as e:
            print(f"❌ 演示 '{name}' 失敗: {e}")
        
        # 等待一下再繼續
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print("🎉 演示完成！")
    print("=" * 60)
    print("您可以使用以下命令來體驗各項功能:")
    print()
    print("# 基本掃描")
    print("uv run python main.py -t 8.8.8.8 -p 53 --show-chart")
    print()
    print("# 即時監測 (按 Ctrl+C 停止)")
    print("uv run python main.py -t 8.8.8.8 -p 53 --monitor --interval 10")
    print()
    print("# 批量掃描")
    print("uv run python main.py -f examples/targets.txt --save-html")
    print()


if __name__ == "__main__":
    main()