#!/usr/bin/env python3
"""
Python + nmap Traceroute 工具
主程式入口點
"""
import sys
from pathlib import Path
from loguru import logger

from cli.argument_parser import parse_arguments
from core.traceroute_scanner import TracerouteScanner
from output.csv_writer import CSVWriter
from output.table_chart import TableChart


def main():
    """主程式入口"""
    try:
        # 解析命令列參數
        args = parse_arguments()
        if args is None:
            sys.exit(0)  # 正常退出（如 --test-nmap）
        
        # 建立掃描器
        scanner = TracerouteScanner(
            protocol=args['protocol'],
            max_hops=args['max_hops'],
            timeout=args['timeout'],
            verbose=args['verbose']
        )
        
        # 建立輸出器
        csv_writer = None
        table_chart = None
        
        if args['output_csv'] or args['output_dir']:
            output_dir = args['output_dir'] or "output_data/csv"
            csv_writer = CSVWriter(output_dir)
        
        if args['show_chart'] or args['save_html']:
            output_dir = args['output_dir'] or "output_data/charts"
            table_chart = TableChart(output_dir)
        
        # 檢查是否為即時監測模式
        if args['monitor']:
            # 即時監測模式
            if not args['target']:
                logger.error("即時監測模式需要指定單一目標 (-t)")
                sys.exit(1)
            
            if len(args['ports']) > 1:
                logger.warning("即時監測模式只支援單一端口，使用第一個端口")
            
            _handle_realtime_monitoring(args)
        
        # 執行掃描
        elif args['target']:
            # 單一目標掃描
            result = scanner.scan_target(
                target=args['target'],
                ports=args['ports'],
                protocol=args['protocol']
            )
            
            # 處理輸出
            _handle_single_result(
                result,
                args,
                csv_writer,
                table_chart
            )
            
        elif args['targets_file']:
            # 批量掃描
            results = scanner.scan_multiple_targets(
                targets=args['targets_file'],
                ports=args['ports'],
                protocol=args['protocol']
            )
            
            # 處理輸出
            _handle_batch_results(
                results,
                args,
                csv_writer,
                table_chart
            )
        
        logger.info("程式執行完成")
        
    except KeyboardInterrupt:
        logger.info("使用者中斷程式執行")
        sys.exit(130)
    except Exception as e:
        logger.error(f"程式執行失敗: {str(e)}")
        if not args or args.get('verbose'):
            import traceback
            logger.error(traceback.format_exc())
        sys.exit(1)


def _handle_single_result(result, args, csv_writer, table_chart):
    """
    處理單一掃描結果
    
    Args:
        result: 掃描結果
        args: 命令列參數
        csv_writer: CSV 輸出器
        table_chart: 表格圖表生成器
    """
    # 顯示結果到終端（除非是安靜模式）
    if not args['quiet']:
        print(str(result))
    
    # 儲存 CSV
    if csv_writer and args['output_csv']:
        csv_file = csv_writer.write_scan_result(
            result,
            filename=args['output_csv'].name if args['output_csv'] else None
        )
        if not args['quiet']:
            print(f"\n✓ CSV 檔案已儲存: {csv_file}")
    
    # 顯示表格圖表
    if table_chart and args['show_chart']:
        table_chart.display_scan_result(result)
    
    # 儲存 HTML 報告
    if table_chart and args['save_html']:
        html_file = table_chart.save_html_report(result)
        if not args['quiet']:
            print(f"✓ HTML 報告已儲存: {html_file}")


def _handle_batch_results(results, args, csv_writer, table_chart):
    """
    處理批量掃描結果
    
    Args:
        results: 掃描結果列表
        args: 命令列參數
        csv_writer: CSV 輸出器
        table_chart: 表格圖表生成器
    """
    if not results:
        logger.warning("沒有成功的掃描結果")
        return
    
    # 顯示摘要到終端（除非是安靜模式）
    if not args['quiet']:
        print(f"\n批量掃描完成，共 {len(results)} 個結果：")
        for i, result in enumerate(results, 1):
            stats = result.get_statistics()
            status = "✓" if stats['target_reached'] else "✗"
            print(f"{i:2d}. {status} {result.target}:{result.port} "
                  f"({stats['total_hops']} hops)")
    
    # 儲存 CSV
    if csv_writer:
        if args['output_csv']:
            # 儲存到指定檔案
            csv_file = csv_writer.write_multiple_results(
                results,
                filename=args['output_csv'].name if args['output_csv'] else None
            )
        else:
            # 儲存摘要和詳細資料
            csv_file = csv_writer.write_multiple_results(results)
            summary_file = csv_writer.write_summary_csv(results)
            
        if not args['quiet']:
            print(f"\n✓ 批量 CSV 檔案已儲存: {csv_file}")
            if 'summary_file' in locals():
                print(f"✓ 摘要 CSV 檔案已儲存: {summary_file}")
    
    # 顯示批量摘要表格
    if table_chart and args['show_chart']:
        table_chart.display_batch_summary(results)
    
    # 儲存批量 HTML 報告
    if table_chart and args['save_html']:
        html_file = table_chart.save_batch_html_report(results)
        if not args['quiet']:
            print(f"✓ 批量 HTML 報告已儲存: {html_file}")


def _handle_realtime_monitoring(args):
    """
    處理即時監測
    
    Args:
        args: 命令列參數
    """
    from core.realtime_monitor import RealtimeMonitor
    
    # 建立即時監測器
    monitor = RealtimeMonitor(
        target=args['target'],
        port=args['ports'][0],  # 使用第一個端口
        protocol=args['protocol'],
        interval=args['interval'],
        max_history=args['max_history'],
        timeout=args['timeout']
    )
    
    try:
        # 開始監測
        if not args['quiet']:
            print(f"🚀 開始即時監測 {args['target']}:{args['ports'][0]}")
            print(f"📊 監測間隔: {args['interval']}秒")
            print("按 Ctrl+C 停止監測\n")
        
        monitor.start_monitoring(display_live=not args['quiet'])
        
    except KeyboardInterrupt:
        print("\n⏹️  監測已停止")
    except Exception as e:
        logger.error(f"即時監測失敗: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
