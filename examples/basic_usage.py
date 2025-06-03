#!/usr/bin/env python3
"""
基本使用範例
展示如何使用 nmaptraceroute 工具的核心功能
"""
import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.traceroute_scanner import TracerouteScanner
from output.csv_writer import CSVWriter
from output.table_chart import TableChart


def example_single_target():
    """單一目標掃描範例"""
    print("=== 單一目標掃描範例 ===")
    
    # 建立掃描器
    scanner = TracerouteScanner(
        protocol="tcp",
        max_hops=20,
        timeout=30
    )
    
    # 掃描目標
    target = "8.8.8.8"  # Google DNS
    port = 53
    
    print(f"掃描目標: {target}:{port}")
    
    try:
        result = scanner.scan_target(target, port)
        
        # 顯示結果
        print(result)
        
        return result
        
    except Exception as e:
        print(f"掃描失敗: {str(e)}")
        return None


def example_multiple_ports():
    """多端口掃描範例"""
    print("\n=== 多端口掃描範例 ===")
    
    scanner = TracerouteScanner(protocol="tcp")
    
    target = "github.com"
    ports = [80, 443, 22]  # HTTP, HTTPS, SSH
    
    print(f"掃描目標: {target}, 端口: {ports}")
    
    results = []
    for port in ports:
        try:
            result = scanner.scan_target(target, port)
            results.append(result)
            
            stats = result.get_statistics()
            print(f"  端口 {port}: {stats['total_hops']} 跳點, "
                  f"到達目標: {'是' if stats['target_reached'] else '否'}")
            
        except Exception as e:
            print(f"  端口 {port}: 掃描失敗 - {str(e)}")
    
    return results


def example_csv_output():
    """CSV 輸出範例"""
    print("\n=== CSV 輸出範例 ===")
    
    # 執行掃描
    scanner = TracerouteScanner()
    result = scanner.scan_target("cloudflare.com", 443)
    
    # 建立 CSV 輸出器
    csv_writer = CSVWriter("examples/output")
    
    try:
        # 儲存 CSV 檔案
        csv_file = csv_writer.write_scan_result(result, "example_output.csv")
        print(f"CSV 檔案已儲存: {csv_file}")
        
        return csv_file
        
    except Exception as e:
        print(f"CSV 輸出失敗: {str(e)}")
        return None


def example_table_chart():
    """表格圖表範例"""
    print("\n=== 表格圖表範例 ===")
    
    # 執行掃描
    scanner = TracerouteScanner()
    result = scanner.scan_target("microsoft.com", 80)
    
    # 建立表格圖表生成器
    table_chart = TableChart("examples/output")
    
    try:
        # 顯示表格
        table_chart.display_scan_result(result)
        
        # 儲存 HTML 報告
        html_file = table_chart.save_html_report(result, "example_report.html")
        print(f"\nHTML 報告已儲存: {html_file}")
        
        return html_file
        
    except Exception as e:
        print(f"表格圖表生成失敗: {str(e)}")
        return None


def example_batch_scan():
    """批量掃描範例"""
    print("\n=== 批量掃描範例 ===")
    
    # 建立目標清單
    targets = [
        "8.8.8.8",      # Google DNS
        "1.1.1.1",      # Cloudflare DNS
        "208.67.222.222" # OpenDNS
    ]
    
    scanner = TracerouteScanner()
    
    try:
        # 批量掃描
        results = scanner.scan_multiple_targets(targets, ports=53)
        
        print(f"批量掃描完成，共 {len(results)} 個結果:")
        
        for i, result in enumerate(results, 1):
            stats = result.get_statistics()
            status = "✓" if stats['target_reached'] else "✗"
            print(f"{i}. {status} {result.target} - {stats['total_hops']} 跳點")
        
        # 儲存批量結果
        csv_writer = CSVWriter("examples/output")
        csv_file = csv_writer.write_multiple_results(results, "batch_results.csv")
        print(f"\n批量結果已儲存: {csv_file}")
        
        return results
        
    except Exception as e:
        print(f"批量掃描失敗: {str(e)}")
        return None


def example_udp_scan():
    """UDP 掃描範例"""
    print("\n=== UDP 掃描範例 ===")
    
    # 建立 UDP 掃描器
    scanner = TracerouteScanner(protocol="udp", timeout=60)
    
    target = "8.8.8.8"
    port = 53  # DNS over UDP
    
    print(f"UDP 掃描目標: {target}:{port}")
    
    try:
        result = scanner.scan_target(target, port)
        
        stats = result.get_statistics()
        print(f"結果: {stats['total_hops']} 跳點, "
              f"到達目標: {'是' if stats['target_reached'] else '否'}")
        
        return result
        
    except Exception as e:
        print(f"UDP 掃描失敗: {str(e)}")
        return None


def main():
    """主函數，執行所有範例"""
    print("Python + nmap Traceroute 工具 - 基本使用範例")
    print("=" * 50)
    
    # 檢查 nmap 是否可用
    try:
        scanner = TracerouteScanner()
        if not scanner.test_nmap():
            print("錯誤: nmap 不可用，請先安裝 nmap")
            return
    except Exception as e:
        print(f"錯誤: 無法初始化掃描器 - {str(e)}")
        return
    
    # 執行範例
    examples = [
        example_single_target,
        example_multiple_ports,
        example_csv_output,
        example_table_chart,
        example_batch_scan,
        example_udp_scan,
    ]
    
    for example_func in examples:
        try:
            example_func()
        except KeyboardInterrupt:
            print("\n使用者中斷執行")
            break
        except Exception as e:
            print(f"範例執行失敗: {str(e)}")
        
        print("\n" + "-" * 30)
    
    print("\n所有範例執行完成！")


if __name__ == "__main__":
    main()