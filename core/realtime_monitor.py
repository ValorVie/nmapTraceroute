"""
即時監測器
提供持續監控網路狀態的功能
"""
import time
import threading
import sys
import csv
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
            self._display_live_interface()
            # 注意：_display_live_interface 現在會處理 Ctrl+C 和顯示退出選項
    
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
        
        ctrl_c_count = 0
        
        try:
            with Live(layout, refresh_per_second=1, screen=True) as live:
                while self.is_running and not self.stopping:
                    try:
                        # 更新介面
                        layout["header"].update(self._create_header_panel())
                        layout["current"].update(self._create_current_result_panel())
                        layout["stats"].update(self._create_stats_panel())
                        layout["footer"].update(self._create_controls_panel())
                        
                        time.sleep(1)
                        
                    except KeyboardInterrupt:
                        ctrl_c_count += 1
                        if ctrl_c_count == 1:
                            # 第一次 Ctrl+C，優雅停止
                            if not self.stopping:
                                self.stopping = True
                                live.stop()  # 立即停止 Live 介面
                                break
                        else:
                            # 第二次 Ctrl+C，強制退出
                            self.console.print("\n🚨 強制退出監測")
                            self.stop_monitoring()
                            sys.exit(0)
                            
        except KeyboardInterrupt:
            # 處理在 Live 上下文外的 Ctrl+C
            ctrl_c_count += 1
            if ctrl_c_count == 1 and not self.stopping:
                self.stopping = True
            elif ctrl_c_count >= 2:
                self.console.print("\n🚨 強制退出監測")
                self.stop_monitoring()
                sys.exit(0)
        
        # 確保在退出 Live 介面後執行停止和選項顯示
        if self.stopping and not self.is_running == False:
            self.console.print("\n⏹️  正在停止監測，請稍候...")
            self.stop_monitoring()
        
        # 顯示退出選項（只有在第一次 Ctrl+C 時）
        if ctrl_c_count == 1:
            self._show_exit_options()
    
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
            "在監測結束後，您可以選擇:「儲存 CSV 報告」、「儲存 HTML 報告」、「查看詳細統計」",
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
            # 建立增強版的 CSV 報告
            filename = f"monitor_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            csv_file = self._create_enhanced_csv_report(filename)
            
            self.console.print(f"✅ 增強版 CSV 報告已儲存: {csv_file}")
            
        except Exception as e:
            self.console.print(f"❌ 儲存 CSV 失敗: {str(e)}")
    
    def _create_enhanced_csv_report(self, filename: str) -> str:
        """建立增強版的 CSV 報告"""
        import csv
        from pathlib import Path
        
        output_dir = Path("output_data/csv")
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / filename

        with open(csv_path, 'w', newline='', encoding='utf-8 with BOM') as f:
            writer = csv.writer(f)
            
            # 寫入監測摘要資訊
            writer.writerow(['=== 即時監測報告 ==='])
            writer.writerow(['目標', self.target])
            writer.writerow(['端口', self.port])
            writer.writerow(['協定', self.protocol.upper()])
            writer.writerow(['監測間隔', f'{self.interval} 秒'])
            writer.writerow(['監測時間', f'{len(self.history) * self.interval / 60:.1f} 分鐘'])
            writer.writerow(['生成時間', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow([])
            
            # 寫入統計摘要
            writer.writerow(['=== 統計摘要 ==='])
            writer.writerow(['項目', '數值'])
            writer.writerow(['總掃描次數', self.stats.total_scans])
            writer.writerow(['成功次數', self.stats.successful_scans])
            writer.writerow(['失敗次數', self.stats.failed_scans])
            writer.writerow(['成功率', f'{self.stats.success_rate:.1f}%'])
            
            if self.stats.successful_scans > 0:
                writer.writerow(['平均回應時間', f'{self.stats.avg_response_time:.3f} ms'])
                writer.writerow(['最小回應時間', f'{self.stats.min_response_time:.3f} ms'])
                writer.writerow(['最大回應時間', f'{self.stats.max_response_time:.3f} ms'])
            
            writer.writerow([])
            
            # 寫入詳細記錄標題
            writer.writerow(['=== 詳細掃描記錄 ==='])
            writer.writerow([
                '掃描時間', '目標', '端口', '協定', '跳點數', '目標可達',
                '成功跳點', '超時跳點', '平均RTT(ms)', '最小RTT(ms)', '最大RTT(ms)', '掃描耗時(s)'
            ])
            
            # 寫入每次掃描的詳細資料
            for result in self.history:
                stats = result.get_statistics()
                writer.writerow([
                    result.scan_time.strftime('%Y-%m-%d %H:%M:%S'),
                    result.target,
                    result.port,
                    result.protocol.upper(),
                    stats['total_hops'],
                    '是' if stats['target_reached'] else '否',
                    stats['successful_hops'],
                    stats['timeout_hops'],
                    f"{stats['avg_rtt']:.3f}" if stats['avg_rtt'] is not None else '',
                    f"{stats['min_rtt']:.3f}" if stats['min_rtt'] is not None else '',
                    f"{stats['max_rtt']:.3f}" if stats['max_rtt'] is not None else '',
                    f"{result.scan_duration:.2f}" if result.scan_duration else ''
                ])
        
            
            writer.writerow([])
            
            # 寫入每個跳點的 RTT 統計
            writer.writerow(['=== 跳點 RTT 統計分析 ==='])
            hop_stats = self._calculate_hop_rtt_statistics()
            
            if hop_stats:
                writer.writerow([
                    '跳點編號', '出現次數', '成功次數', '成功率(%)', 
                    '平均RTT(ms)', '最小RTT(ms)', '最大RTT(ms)', 
                    'RTT標準差(ms)', '唯一IP數量', '主要IP位址'
                ])
                
                for hop_num in sorted(hop_stats.keys()):
                    stats = hop_stats[hop_num]
                    writer.writerow([
                        hop_num,
                        stats['total_count'],
                        stats['success_count'],
                        f"{stats['success_rate']:.1f}",
                        f"{stats['avg_rtt']:.3f}" if stats['avg_rtt'] is not None else '',
                        f"{stats['min_rtt']:.3f}" if stats['min_rtt'] is not None else '',
                        f"{stats['max_rtt']:.3f}" if stats['max_rtt'] is not None else '',
                        f"{stats['rtt_std']:.3f}" if stats['rtt_std'] is not None else '',
                        stats['unique_ips'],
                        stats['primary_ip']
                    ])

            writer.writerow([])
            
            # 寫入所有跳點詳細資料
            writer.writerow(['=== 所有跳點詳細資料 ==='])
            writer.writerow([
                '掃描時間', '跳點編號', 'IP位址', '主機名', 'RTT(ms)', '狀態'            ])
            
            for result in self.history:
                scan_time_str = result.scan_time.strftime('%Y-%m-%d %H:%M:%S')
                for hop in result.hops:
                    writer.writerow([
                        scan_time_str,
                        hop.hop_number,
                        hop.ip_address,
                        hop.hostname or '',
                        f"{hop.rtt_ms:.3f}" if hop.rtt_ms is not None else '',
                        hop.status
                    ])

        return str(csv_path)
    
    def _save_html_report(self):
        """儲存 HTML 報告"""
        if not self.history:
            self.console.print("❌ 沒有資料可以儲存")
            return
        
        try:
            filename = f"monitor_{self.target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            html_file = self._create_enhanced_html_report(filename)
            
            self.console.print(f"✅ 增強版 HTML 報告已儲存: {html_file}")
            
        except Exception as e:
            self.console.print(f"❌ 儲存 HTML 失敗: {str(e)}")
    
    def _create_enhanced_html_report(self, filename: str) -> str:
        """建立增強版的 HTML 報告"""
        from pathlib import Path
        
        output_dir = Path("output_data/html")
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = output_dir / filename
        
        # 計算統計數據
        success_count = sum(1 for result in self.history if result.get_statistics()['target_reached'])
        success_rate = (success_count / len(self.history) * 100) if self.history else 0
        
        # 建立 HTML 內容
        html_content = self._generate_html_content(success_rate)
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(html_path)
    
    def _generate_html_content(self, success_rate: float) -> str:
        """生成完整的 HTML 內容"""
        return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>即時監測報告 - {self.target}:{self.port}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff; }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #6c757d; font-size: 0.9em; }}
        .chart-container {{ width: 100%; height: 400px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        .success {{ color: #28a745; }}
        .failure {{ color: #dc3545; }}
        .section {{ margin: 30px 0; }}
        .section-title {{ font-size: 1.5em; font-weight: bold; margin-bottom: 15px; color: #333; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 即時監測報告</h1>
            <p>目標: {self.target}:{self.port} ({self.protocol.upper()})</p>
            <p>監測時間: {len(self.history) * self.interval / 60:.1f} 分鐘 | 生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{self.stats.total_scans}</div>
                <div class="stat-label">總掃描次數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value success">{self.stats.successful_scans}</div>
                <div class="stat-label">成功次數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value failure">{self.stats.failed_scans}</div>
                <div class="stat-label">失敗次數</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{success_rate:.1f}%</div>
                <div class="stat-label">成功率</div>
            </div>
        </div>
        
        {self._generate_response_time_stats_html() if self.stats.successful_scans > 0 else ''}
        
        <div class="section">
            <div class="section-title">📈 成功率趨勢圖</div>
            <canvas id="successChart" class="chart-container"></canvas>
        </div>
        
        <div class="section">
            <div class="section-title">⏱️ 回應時間趨勢圖</div>
            <canvas id="rttChart" class="chart-container"></canvas>
        </div>
        
        <div class="section">
            <div class="section-title">📋 詳細掃描記錄</div>
            {self._generate_scan_history_table_html()}
        </div>
        
        <div class="section">
            <div class="section-title">🔍 跳點分析</div>
            {self._generate_hop_analysis_html()}
        </div>
    </div>
    
    <script>
        {self._generate_chart_javascript()}
    </script>
</body>
</html>"""
    
    def _generate_response_time_stats_html(self) -> str:
        """生成回應時間統計的 HTML"""
        return f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{self.stats.avg_response_time:.1f}ms</div>
                <div class="stat-label">平均回應時間</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{self.stats.min_response_time:.1f}ms</div>
                <div class="stat-label">最小回應時間</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{self.stats.max_response_time:.1f}ms</div>
                <div class="stat-label">最大回應時間</div>
            </div>
        </div>
        """
    
    def _generate_scan_history_table_html(self) -> str:
        """生成掃描歷史表格的 HTML"""
        table_rows = []
        for i, result in enumerate(self.history, 1):
            stats = result.get_statistics()
            status_class = "success" if stats['target_reached'] else "failure"
            status_text = "✅ 成功" if stats['target_reached'] else "❌ 失敗"
            
            avg_rtt = f"{stats['avg_rtt']:.1f}ms" if stats['avg_rtt'] is not None else "-"
            
            table_rows.append(f"""
                <tr>
                    <td>{i}</td>
                    <td>{result.scan_time.strftime('%H:%M:%S')}</td>
                    <td>{stats['total_hops']}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{stats['successful_hops']}</td>
                    <td>{stats['timeout_hops']}</td>
                    <td>{avg_rtt}</td>
                    <td>{result.scan_duration:.1f}s</td>
                </tr>
            """)
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>掃描時間</th>
                    <th>跳點數</th>
                    <th>狀態</th>
                    <th>成功跳點</th>
                    <th>超時跳點</th>
                    <th>平均RTT</th>
                    <th>掃描耗時</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        """
    
    def _generate_hop_analysis_html(self) -> str:
        """生成跳點分析的 HTML"""
        if not self.history:
            return "<p>沒有數據可供分析</p>"
        
        # 分析每個跳點的穩定性
        hop_stats = {}
        for result in self.history:
            for hop in result.hops:
                hop_num = hop.hop_number
                if hop_num not in hop_stats:
                    hop_stats[hop_num] = {'ips': set(), 'success': 0, 'total': 0, 'rtts': []}
                
                hop_stats[hop_num]['total'] += 1
                if hop.status == 'success':
                    hop_stats[hop_num]['success'] += 1
                    hop_stats[hop_num]['ips'].add(hop.ip_address)
                    if hop.rtt_ms is not None:
                        hop_stats[hop_num]['rtts'].append(hop.rtt_ms)
        
        analysis_rows = []
        for hop_num in sorted(hop_stats.keys()):
            stats = hop_stats[hop_num]
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            avg_rtt = sum(stats['rtts']) / len(stats['rtts']) if stats['rtts'] else 0
            unique_ips = len(stats['ips'])
            
            analysis_rows.append(f"""
                <tr>
                    <td>{hop_num}</td>
                    <td>{success_rate:.1f}%</td>
                    <td>{unique_ips}</td>
                    <td>{avg_rtt:.1f}ms</td>
                    <td>{stats['success']}/{stats['total']}</td>
                </tr>
            """)
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>跳點</th>
                    <th>成功率</th>
                    <th>唯一IP數</th>
                    <th>平均RTT</th>
                    <th>成功/總計</th>
                </tr>
            </thead>
            <tbody>
                {''.join(analysis_rows)}
            </tbody>
        </table>
        """
    
    def _generate_chart_javascript(self) -> str:
        """生成圖表的 JavaScript 代碼"""
        # 準備數據
        success_data = []
        rtt_data = []
        labels = []
        
        for result in self.history:
            labels.append(result.scan_time.strftime('%H:%M:%S'))
            stats = result.get_statistics()
            success_data.append(1 if stats['target_reached'] else 0)
            rtt_data.append(stats['avg_rtt'] if stats['avg_rtt'] is not None else 0)
        
        return f"""
        // 成功率圖表
        const successCtx = document.getElementById('successChart').getContext('2d');
        new Chart(successCtx, {{
            type: 'line',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: '成功 (1) / 失敗 (0)',
                    data: {success_data},
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 1
                    }}
                }}
            }}
        }});
        
        // 回應時間圖表
        const rttCtx = document.getElementById('rttChart').getContext('2d');
        new Chart(rttCtx, {{
            type: 'line',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: '平均回應時間 (ms)',
                    data: {rtt_data},
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
        """
    
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
    
    def _calculate_hop_rtt_statistics(self) -> dict:
        """計算每個跳點的 RTT 統計資料"""
        import statistics
        from collections import defaultdict, Counter
        
        hop_data = defaultdict(lambda: {
            'rtts': [],
            'ips': [],
            'success_count': 0,
            'total_count': 0
        })
        
        # 收集每個跳點的數據
        for result in self.history:
            for hop in result.hops:
                hop_num = hop.hop_number
                hop_data[hop_num]['total_count'] += 1
                
                if hop.status == 'success' and hop.rtt_ms is not None:
                    hop_data[hop_num]['success_count'] += 1
                    hop_data[hop_num]['rtts'].append(hop.rtt_ms)
                
                if hop.ip_address:
                    hop_data[hop_num]['ips'].append(hop.ip_address)
        
        # 計算統計數據
        hop_stats = {}
        for hop_num, data in hop_data.items():
            rtts = data['rtts']
            ips = data['ips']
            
            # 計算成功率
            success_rate = (data['success_count'] / data['total_count'] * 100) if data['total_count'] > 0 else 0
            
            # 計算 RTT 統計
            avg_rtt = statistics.mean(rtts) if rtts else None
            min_rtt = min(rtts) if rtts else None
            max_rtt = max(rtts) if rtts else None
            rtt_std = statistics.stdev(rtts) if len(rtts) > 1 else None
            
            # 找出最常出現的 IP 位址
            ip_counter = Counter(ips)
            primary_ip = ip_counter.most_common(1)[0][0] if ips else 'N/A'
            unique_ips = len(set(ips))
            
            hop_stats[hop_num] = {
                'total_count': data['total_count'],
                'success_count': data['success_count'],
                'success_rate': success_rate,
                'avg_rtt': avg_rtt,
                'min_rtt': min_rtt,
                'max_rtt': max_rtt,
                'rtt_std': rtt_std,
                'unique_ips': unique_ips,
                'primary_ip': primary_ip
            }
        
        return hop_stats