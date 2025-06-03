"""
表格式圖表生成器
"""
from pathlib import Path
from typing import List, Union
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from loguru import logger

from models.scan_result import ScanResult


class TableChart:
    """表格式圖表生成器"""
    
    def __init__(self, output_dir: Union[str, Path] = "output_data/charts"):
        """
        初始化表格圖表生成器
        
        Args:
            output_dir: 輸出目錄
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.console = Console(record=True, width=120)
        logger.info(f"表格圖表生成器初始化，輸出目錄: {self.output_dir}")
    
    def display_scan_result(self, result: ScanResult, show_stats: bool = True) -> None:
        """
        在終端顯示掃描結果表格
        
        Args:
            result: 掃描結果
            show_stats: 是否顯示統計資訊
        """
        self.console.clear()
        
        # 建立標題
        title = f"Traceroute to {result.target}:{result.port} ({result.protocol.upper()})"
        self.console.print(Panel(title, style="bold blue"))
        
        # 建立跳點表格
        table = Table(
            title=f"Scan Time: {result.scan_time.strftime('%Y-%m-%d %H:%M:%S')}",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Hop", justify="center", style="cyan", width=5)
        table.add_column("IP Address", style="green", width=15)
        table.add_column("Hostname", style="yellow", width=30)
        table.add_column("RTT (ms)", justify="right", style="red", width=12)
        table.add_column("Status", justify="center", style="blue", width=10)
        
        # 添加跳點資料
        for hop in result.hops:
            # 設定狀態顏色
            if hop.status == "success":
                status_style = "green"
            elif hop.status == "timeout":
                status_style = "red"
            else:
                status_style = "yellow"
            
            # 格式化 RTT
            rtt_str = f"{hop.rtt_ms:.3f}" if hop.rtt_ms is not None else "*"
            
            table.add_row(
                str(hop.hop_number),
                hop.ip_address,
                hop.hostname or "-",
                rtt_str,
                Text(hop.status, style=status_style)
            )
        
        self.console.print(table)
        
        # 顯示統計資訊
        if show_stats:
            self._display_statistics(result)
    
    def _display_statistics(self, result: ScanResult) -> None:
        """
        顯示統計資訊
        
        Args:
            result: 掃描結果
        """
        stats = result.get_statistics()
        
        # 建立統計表格
        stats_table = Table(
            title="Statistics",
            box=box.SIMPLE,
            show_header=False,
            width=50
        )
        
        stats_table.add_column("Metric", style="bold cyan", width=20)
        stats_table.add_column("Value", style="white", width=20)
        
        # 添加統計資料
        stats_table.add_row("Total Hops", str(stats['total_hops']))
        stats_table.add_row(
            "Target Reached", 
            Text("Yes", style="green") if stats['target_reached'] else Text("No", style="red")
        )
        stats_table.add_row("Successful Hops", str(stats['successful_hops']))
        stats_table.add_row("Timeout Hops", str(stats['timeout_hops']))
        
        if stats['avg_rtt'] is not None:
            stats_table.add_row("Average RTT", f"{stats['avg_rtt']:.3f} ms")
            stats_table.add_row("Min RTT", f"{stats['min_rtt']:.3f} ms")
            stats_table.add_row("Max RTT", f"{stats['max_rtt']:.3f} ms")
        
        if result.scan_duration:
            stats_table.add_row("Scan Duration", f"{result.scan_duration:.2f} s")
        
        self.console.print("\n")
        self.console.print(stats_table)
    
    def save_html_report(
        self, 
        result: ScanResult, 
        filename: str = None
    ) -> Path:
        """
        將表格儲存為 HTML 報告
        
        Args:
            result: 掃描結果
            filename: 檔案名稱（可選）
        
        Returns:
            HTML 檔案路徑
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traceroute_{result.target}_{timestamp}.html"
        
        if not filename.endswith('.html'):
            filename += '.html'
        
        file_path = self.output_dir / filename
        
        try:
            # 清除之前的記錄
            self.console = Console(record=True, width=120)
            
            # 生成表格
            self.display_scan_result(result, show_stats=True)
            
            # 儲存為 HTML
            html_content = self.console.export_html(inline_styles=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"成功儲存 HTML 報告: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"儲存 HTML 報告失敗: {str(e)}")
            raise
    
    def display_batch_summary(self, results: List[ScanResult]) -> None:
        """
        顯示批量掃描摘要
        
        Args:
            results: 掃描結果列表
        """
        self.console.clear()
        
        # 標題
        title = f"Batch Traceroute Summary ({len(results)} targets)"
        self.console.print(Panel(title, style="bold blue"))
        
        # 建立摘要表格
        table = Table(
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Target", style="cyan", width=20)
        table.add_column("Port", justify="center", style="blue", width=8)
        table.add_column("Protocol", justify="center", style="green", width=10)
        table.add_column("Hops", justify="center", style="yellow", width=8)
        table.add_column("Reached", justify="center", style="red", width=10)
        table.add_column("Avg RTT", justify="right", style="magenta", width=12)
        table.add_column("Duration", justify="right", style="white", width=12)
        
        # 統計資料
        total_scans = len(results)
        successful_scans = 0
        total_hops = 0
        
        # 添加結果資料
        for result in results:
            stats = result.get_statistics()
            
            if stats['target_reached']:
                successful_scans += 1
            
            total_hops += stats['total_hops']
            
            # 格式化資料
            avg_rtt_str = f"{stats['avg_rtt']:.3f} ms" if stats['avg_rtt'] is not None else "-"
            duration_str = f"{result.scan_duration:.2f} s" if result.scan_duration else "-"
            reached_text = Text("Yes", style="green") if stats['target_reached'] else Text("No", style="red")
            
            table.add_row(
                result.target,
                str(result.port),
                result.protocol.upper(),
                str(stats['total_hops']),
                reached_text,
                avg_rtt_str,
                duration_str
            )
        
        self.console.print(table)
        
        # 顯示整體統計
        self._display_batch_statistics(total_scans, successful_scans, total_hops)
    
    def _display_batch_statistics(
        self, 
        total_scans: int, 
        successful_scans: int, 
        total_hops: int
    ) -> None:
        """
        顯示批量掃描統計
        
        Args:
            total_scans: 總掃描數
            successful_scans: 成功掃描數
            total_hops: 總跳點數
        """
        stats_table = Table(
            title="Batch Statistics",
            box=box.SIMPLE,
            show_header=False,
            width=40
        )
        
        stats_table.add_column("Metric", style="bold cyan", width=20)
        stats_table.add_column("Value", style="white", width=15)
        
        success_rate = (successful_scans / total_scans * 100) if total_scans > 0 else 0
        avg_hops = (total_hops / total_scans) if total_scans > 0 else 0
        
        stats_table.add_row("Total Scans", str(total_scans))
        stats_table.add_row("Successful", str(successful_scans))
        stats_table.add_row("Success Rate", f"{success_rate:.1f}%")
        stats_table.add_row("Average Hops", f"{avg_hops:.1f}")
        
        self.console.print("\n")
        self.console.print(stats_table)
    
    def save_batch_html_report(
        self, 
        results: List[ScanResult], 
        filename: str = None
    ) -> Path:
        """
        儲存批量掃描的 HTML 報告
        
        Args:
            results: 掃描結果列表
            filename: 檔案名稱（可選）
        
        Returns:
            HTML 檔案路徑
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traceroute_batch_{timestamp}.html"
        
        if not filename.endswith('.html'):
            filename += '.html'
        
        file_path = self.output_dir / filename
        
        try:
            # 清除之前的記錄
            self.console = Console(record=True, width=120)
            
            # 生成批量摘要
            self.display_batch_summary(results)
            
            # 儲存為 HTML
            html_content = self.console.export_html(inline_styles=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"成功儲存批量 HTML 報告: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"儲存批量 HTML 報告失敗: {str(e)}")
            raise