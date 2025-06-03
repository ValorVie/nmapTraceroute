"""
即時監測器
提供持續監控網路狀態的功能
"""
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from collections import deque
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
from loguru import logger

from core.traceroute_scanner import TracerouteScanner
from models.scan_result import ScanResult
from output.csv_writer import CSVWriter


@dataclass
class MonitorStats:
    """監測統計資料"""
    total_scans: int = 0
    successful_scans: int = 0
    failed_scans: int = 0
    avg_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    last_scan_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        return (self.successful_scans / self.total_scans * 100) if self.total_scans > 0 else 0.0


class RealtimeMonitor:
    """即時監測器"""
    
    def __init__(
        self,
        target: str,
        port: int = 80,
        protocol: str = "tcp",
        interval: int = 5,
        max_history: int = 100,
        timeout: int = 30
    ):
        """
        初始化即時監測器
        
        Args:
            target: 目標主機
            port: 目標端口
            protocol: 協定 (tcp/udp)
            interval: 掃描間隔（秒）
            max_history: 最大歷史記錄數
            timeout: 掃描超時時間
        """
        self.target = target
        self.port = port
        self.protocol = protocol
        self.interval = interval
        self.max_history = max_history
        self.timeout = timeout
        
        # 初始化組件
        self.scanner = TracerouteScanner(
            protocol=protocol,
            timeout=timeout,
            verbose=False
        )
        self.console = Console()
        
        # 監測狀態
        self.is_running = False
        self.monitor_thread = None
        self.history = deque(maxlen=max_history)
        self.stats = MonitorStats()
        self.current_result = None
        self.scanning_in_progress = False  # 防止重疊掃描
        self.stopping = False  # 防止重複停止
        
        # 回調函數
        self.on_scan_complete: Optional[Callable[[ScanResult], None]] = None
        self.on_status_change: Optional[Callable[[bool], None]] = None
        
        logger.info(f"即時監測器初始化完成，目標: {target}:{port}")
    
    def start_monitoring(self, display_live: bool = True):
        """
        開始監測
        
        Args:
            display_live: 是否顯示即時介面
        """
        if self.is_running:
            logger.warning("監測已在運行中")
            return
        
        self.is_running = True
        self.stopping = False  # 重置停止標記
        self.stats = MonitorStats()  # 重置統計
        
        logger.info(f"開始監測 {self.target}:{self.port}，間隔: {self.interval}秒")
        
        # 啟動監測執行緒
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self.monitor_thread.start()
        
        # 如果需要顯示即時介面
        if display_live:
            try:
                self._display_live_interface()
            except KeyboardInterrupt:
                self.stop_monitoring()
                self._show_exit_options()
    
    def stop_monitoring(self):
        """停止監測"""
        if not self.stopping:
            self.stopping = True
            self.is_running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            
            logger.info("監測已停止")
    
    def _monitor_loop(self):
        """監測主迴圈"""
        while self.is_running and not self.stopping:
            try:
                # 檢查是否有掃描在進行中
                if self.scanning_in_progress:
                    logger.warning("上次掃描尚未完成，跳過本次掃描")
                    time.sleep(self.interval)
                    continue
                
                # 設置掃描標記
                self.scanning_in_progress = True
                
                # 執行掃描
                start_time = time.time()
                result = self.scanner.scan_target(self.target, self.port)
                scan_duration = time.time() - start_time
                
                # 更新統計
                self._update_stats(result, scan_duration)
                
                # 加入歷史記錄
                self.history.append(result)
                self.current_result = result
                
                # 觸發回調
                if self.on_scan_complete:
                    self.on_scan_complete(result)
                
                # 清除掃描標記
                self.scanning_in_progress = False
                
                # 計算實際等待時間（間隔 - 掃描時間）
                actual_wait = max(0, self.interval - scan_duration)
                if actual_wait > 0:
                    time.sleep(actual_wait)
                else:
                    logger.warning(f"掃描時間 ({scan_duration:.1f}s) 超過設定間隔 ({self.interval}s)")
                
            except Exception as e:
                logger.error(f"監測迴圈錯誤: {str(e)}")
                self.stats.failed_scans += 1
                self.scanning_in_progress = False
                time.sleep(self.interval)
    
    def _update_stats(self, result: ScanResult, scan_duration: float):
        """更新統計資料"""
        self.stats.total_scans += 1
        self.stats.last_scan_time = datetime.now()
        
        # 檢查是否成功
        scan_stats = result.get_statistics()
        if scan_stats['target_reached']:
            self.stats.successful_scans += 1
            
            # 更新回應時間統計
            if scan_stats['avg_rtt'] is not None:
                avg_rtt = scan_stats['avg_rtt']
                self.stats.min_response_time = min(self.stats.min_response_time, avg_rtt)
                self.stats.max_response_time = max(self.stats.max_response_time, avg_rtt)
                
                # 計算總體平均回應時間
                total_successful = self.stats.successful_scans
                current_avg = self.stats.avg_response_time
                self.stats.avg_response_time = ((current_avg * (total_successful - 1)) + avg_rtt) / total_successful
        else:
            self.stats.failed_scans += 1
    
    def _display_live_interface(self):
        """顯示即時監測介面"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=8)
        )
        
        layout["main"].split_row(
            Layout(name="current", ratio=2),
            Layout(name="stats", ratio=1)
        )
        
        with Live(layout, refresh_per_second=1, screen=True) as live:
            try:
                while self.is_running and not self.stopping:
                    # 更新介面
                    layout["header"].update(self._create_header_panel())
                    layout["current"].update(self._create_current_result_panel())
                    layout["stats"].update(self._create_stats_panel())
                    layout["footer"].update(self._create_controls_panel())
                    
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                if not self.stopping:
                    self.stopping = True
                    self.console.print("\n⏹️  正在停止監測，請稍候...")
                    self.stop_monitoring()
                    self._show_exit_options()
                else:
                    # 第二次 Ctrl+C，強制退出
                    self.console.print("\n🚨 強制退出監測")
                    self.stop_monitoring()
                    sys.exit(0)
    
    def _create_header_panel(self) -> Panel:
        """建立標題面板"""
        title = f"即時監測 - {self.target}:{self.port} ({self.protocol.upper()})"
        status = "🟢 運行中" if self.is_running else "🔴 已停止"
        
        header_text = f"{title} | {status}"
        if self.stats.last_scan_time:
            header_text += f" | 最後掃描: {self.stats.last_scan_time.strftime('%H:%M:%S')}"
        
        return Panel(header_text, style="bold blue")
    
    def _create_current_result_panel(self) -> Panel:
        """建立當前結果面板"""
        if not self.current_result:
            return Panel("等待第一次掃描結果...", title="當前狀態")
        
        # 建立跳點表格
        table = Table(box=box.SIMPLE)
        table.add_column("跳點", justify="center", style="cyan", width=6)
        table.add_column("IP 位址", style="green", width=16)
        table.add_column("回應時間", justify="right", style="yellow", width=12)
        table.add_column("狀態", justify="center", width=10)
        
        for hop in self.current_result.hops:
            status_style = "green" if hop.status == "success" else "red"
            rtt_str = f"{hop.rtt_ms:.1f}ms" if hop.rtt_ms is not None else "*"
            
            table.add_row(
                str(hop.hop_number),
                hop.ip_address,
                rtt_str,
                Text(hop.status, style=status_style)
            )
        
        scan_stats = self.current_result.get_statistics()
        status = "✅ 可達" if scan_stats['target_reached'] else "❌ 不可達"
        
        return Panel(table, title=f"路由追蹤結果 ({status})")
    
    def _create_stats_panel(self) -> Panel:
        """建立統計面板"""
        stats_table = Table(box=box.SIMPLE, show_header=False)
        stats_table.add_column("項目", style="bold cyan")
        stats_table.add_column("數值", style="white")
        
        stats_table.add_row("總掃描次數", str(self.stats.total_scans))
        stats_table.add_row("成功次數", str(self.stats.successful_scans))
        stats_table.add_row("失敗次數", str(self.stats.failed_scans))
        stats_table.add_row("成功率", f"{self.stats.success_rate:.1f}%")
        
        if self.stats.successful_scans > 0:
            stats_table.add_row("平均回應", f"{self.stats.avg_response_time:.1f}ms")
            stats_table.add_row("最小回應", f"{self.stats.min_response_time:.1f}ms")
            stats_table.add_row("最大回應", f"{self.stats.max_response_time:.1f}ms")
        
        return Panel(stats_table, title="統計資訊")
    
    def _create_controls_panel(self) -> Panel:
        """建立控制面板"""
        controls = [
            "🎛️  控制選項:",
            "",
            "Ctrl+C - 停止監測並顯示選項",
            "Ctrl+C 兩次 - 強制退出程式",
            "在監測結束後，您可以選擇:",
            "• 儲存 CSV 報告",
            "• 儲存 HTML 報告",
            "• 查看詳細統計",
            "",
            f"📊 監測間隔: {self.interval}秒 | 歷史記錄: {len(self.history)}/{self.max_history}",
            f"⚠️  建議間隔 ≥ 10秒 (nmap 掃描約需 5-8秒)",
            f"🔄 掃描狀態: {'進行中' if self.scanning_in_progress else '等待中'}"
        ]
        
        return Panel("\n".join(controls), title="說明")
    
    def _show_exit_options(self):
        """顯示退出選項"""
        self.console.clear()
        
        # 顯示最終統計
        self.console.print("\n" + "="*60)
        self.console.print("📊 監測完成統計報告", style="bold blue")
        self.console.print("="*60)
        
        self.console.print(f"目標: {self.target}:{self.port}")
        self.console.print(f"監測時間: {len(self.history) * self.interval / 60:.1f} 分鐘")
        self.console.print(f"總掃描: {self.stats.total_scans} 次")
        self.console.print(f"成功率: {self.stats.success_rate:.1f}%")
        
        if self.stats.successful_scans > 0:
            self.console.print(f"平均回應時間: {self.stats.avg_response_time:.1f}ms")
        
        # 提供選項
        self.console.print("\n📁 儲存選項:")
        
        while True:
            self.console.print("\n請選擇操作:")
            self.console.print("1. 儲存 CSV 報告")
            self.console.print("2. 儲存 HTML 報告")
            self.console.print("3. 查看詳細歷史")
            self.console.print("4. 結束程式")
            
            choice = input("\n請輸入選擇 (1-4): ").strip()
            
            if choice == "1":
                self._save_csv_report()
            elif choice == "2":
                self._save_html_report()
            elif choice == "3":
                self._show_detailed_history()
            elif choice == "4":
                self.console.print("👋 再見！")
                break
            else:
                self.console.print("❌ 無效選擇，請重新輸入")
    
    def _save_csv_report(self):
        """儲存 CSV 報告"""
        if not self.history:
            self.console.print("❌ 沒有資料可以儲存")
            return
        
        try:
            csv_writer = CSVWriter()
            results = list(self.history)
            
            filename = f"monitor_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_file = csv_writer.write_multiple_results(results, filename)
            
            self.console.print(f"✅ CSV 報告已儲存: {csv_file}")
            
        except Exception as e:
            self.console.print(f"❌ 儲存 CSV 失敗: {str(e)}")
    
    def _save_html_report(self):
        """儲存 HTML 報告"""
        if not self.history:
            self.console.print("❌ 沒有資料可以儲存")
            return
        
        try:
            from output.table_chart import TableChart
            
            table_chart = TableChart()
            results = list(self.history)
            
            filename = f"monitor_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            html_file = table_chart.save_batch_html_report(results, filename)
            
            self.console.print(f"✅ HTML 報告已儲存: {html_file}")
            
        except Exception as e:
            self.console.print(f"❌ 儲存 HTML 失敗: {str(e)}")
    
    def _show_detailed_history(self):
        """顯示詳細歷史"""
        if not self.history:
            self.console.print("❌ 沒有歷史資料")
            return
        
        self.console.print(f"\n📈 詳細歷史記錄 (最近 {len(self.history)} 次掃描):")
        
        table = Table()
        table.add_column("時間", style="cyan")
        table.add_column("狀態", justify="center")
        table.add_column("跳點數", justify="center", style="yellow")
        table.add_column("平均回應", justify="right", style="green")
        table.add_column("目標可達", justify="center")
        
        for result in self.history:
            stats = result.get_statistics()
            status = "✅" if stats['target_reached'] else "❌"
            avg_rtt = f"{stats['avg_rtt']:.1f}ms" if stats['avg_rtt'] is not None else "-"
            reachable = "是" if stats['target_reached'] else "否"
            
            table.add_row(
                result.scan_time.strftime("%H:%M:%S"),
                status,
                str(stats['total_hops']),
                avg_rtt,
                reachable
            )
        
        self.console.print(table)
        input("\n按 Enter 返回選單...")
    
    def get_current_stats(self) -> MonitorStats:
        """取得當前統計資料"""
        return self.stats
    
    def get_history(self) -> List[ScanResult]:
        """取得歷史記錄"""
        return list(self.history)