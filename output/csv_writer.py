"""
CSV 檔案輸出功能
"""
import csv
from pathlib import Path
from typing import List, Union
from datetime import datetime
from loguru import logger

from models.scan_result import ScanResult


class CSVWriter:
    """CSV 檔案輸出器"""
    
    def __init__(self, output_dir: Union[str, Path] = "output_data/csv"):
        """
        初始化 CSV 輸出器
        
        Args:
            output_dir: 輸出目錄
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CSV 輸出器初始化，輸出目錄: {self.output_dir}")
    
    def write_scan_result(
        self, 
        result: ScanResult, 
        filename: str = None
    ) -> Path:
        """
        將單一掃描結果寫入 CSV 檔案
        
        Args:
            result: 掃描結果
            filename: 檔案名稱（可選）
        
        Returns:
            CSV 檔案路徑
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traceroute_{result.target}_{timestamp}.csv"
        
        # 確保檔名以 .csv 結尾
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        file_path = self.output_dir / filename
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 寫入標題資訊
                writer.writerow(['# Traceroute Results'])
                writer.writerow(['# Target:', result.target])
                writer.writerow(['# Port:', result.port])
                writer.writerow(['# Protocol:', result.protocol.upper()])
                writer.writerow(['# Scan Time:', result.scan_time.strftime('%Y-%m-%d %H:%M:%S')])
                
                if result.scan_duration:
                    writer.writerow(['# Scan Duration (s):', f"{result.scan_duration:.2f}"])
                
                # 統計資訊
                stats = result.get_statistics()
                writer.writerow(['# Statistics:'])
                writer.writerow(['# Total Hops:', stats['total_hops']])
                writer.writerow(['# Target Reached:', 'Yes' if stats['target_reached'] else 'No'])
                writer.writerow(['# Successful Hops:', stats['successful_hops']])
                writer.writerow(['# Timeout Hops:', stats['timeout_hops']])
                
                if stats['avg_rtt'] is not None:
                    writer.writerow(['# Average RTT (ms):', f"{stats['avg_rtt']:.3f}"])
                    writer.writerow(['# Min RTT (ms):', f"{stats['min_rtt']:.3f}"])
                    writer.writerow(['# Max RTT (ms):', f"{stats['max_rtt']:.3f}"])
                
                writer.writerow([])  # 空行分隔
                
                # 寫入欄位標題
                writer.writerow([
                    'Hop Number',
                    'IP Address', 
                    'Hostname',
                    'RTT (ms)',
                    'Status'
                ])
                
                # 寫入跳點資料
                for hop in result.hops:
                    writer.writerow([
                        hop.hop_number,
                        hop.ip_address,
                        hop.hostname or '',
                        f"{hop.rtt_ms:.3f}" if hop.rtt_ms is not None else '',
                        hop.status
                    ])
            
            logger.info(f"成功寫入 CSV 檔案: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"寫入 CSV 檔案失敗: {str(e)}")
            raise
    
    def write_multiple_results(
        self, 
        results: List[ScanResult], 
        filename: str = None
    ) -> Path:
        """
        將多個掃描結果寫入單一 CSV 檔案
        
        Args:
            results: 掃描結果列表
            filename: 檔案名稱（可選）
        
        Returns:
            CSV 檔案路徑
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traceroute_batch_{timestamp}.csv"
        
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        file_path = self.output_dir / filename
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 寫入檔案標題
                writer.writerow(['# Batch Traceroute Results'])
                writer.writerow(['# Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow(['# Total Scans:', len(results)])
                writer.writerow([])
                
                # 寫入欄位標題
                writer.writerow([
                    'Target',
                    'Port',
                    'Protocol',
                    'Scan Time',
                    'Hop Number',
                    'IP Address',
                    'Hostname',
                    'RTT (ms)',
                    'Status',
                    'Total Hops',
                    'Target Reached',
                    'Scan Duration (s)'
                ])
                
                # 寫入所有結果的跳點資料
                for result in results:
                    stats = result.get_statistics()
                    scan_time_str = result.scan_time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    if result.hops:
                        for hop in result.hops:
                            writer.writerow([
                                result.target,
                                result.port,
                                result.protocol.upper(),
                                scan_time_str,
                                hop.hop_number,
                                hop.ip_address,
                                hop.hostname or '',
                                f"{hop.rtt_ms:.3f}" if hop.rtt_ms is not None else '',
                                hop.status,
                                stats['total_hops'],
                                'Yes' if stats['target_reached'] else 'No',
                                f"{result.scan_duration:.2f}" if result.scan_duration else ''
                            ])
                    else:
                        # 如果沒有跳點資料，至少記錄目標資訊
                        writer.writerow([
                            result.target,
                            result.port,
                            result.protocol.upper(),
                            scan_time_str,
                            '',
                            '',
                            '',
                            '',
                            'No Data',
                            0,
                            'No',
                            f"{result.scan_duration:.2f}" if result.scan_duration else ''
                        ])
            
            logger.info(f"成功寫入批量 CSV 檔案: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"寫入批量 CSV 檔案失敗: {str(e)}")
            raise
    
    def write_summary_csv(self, results: List[ScanResult], filename: str = None) -> Path:
        """
        寫入摘要 CSV 檔案（只包含統計資訊）
        
        Args:
            results: 掃描結果列表
            filename: 檔案名稱（可選）
        
        Returns:
            CSV 檔案路徑
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traceroute_summary_{timestamp}.csv"
        
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        file_path = self.output_dir / filename
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                
                # 寫入標題
                writer.writerow(['# Traceroute Summary'])
                writer.writerow(['# Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([])
                
                # 寫入欄位標題
                writer.writerow([
                    'Target',
                    'Port', 
                    'Protocol',
                    'Scan Time',
                    'Total Hops',
                    'Target Reached',
                    'Successful Hops',
                    'Timeout Hops',
                    'Avg RTT (ms)',
                    'Min RTT (ms)',
                    'Max RTT (ms)',
                    'Scan Duration (s)'
                ])
                
                # 寫入摘要資料
                for result in results:
                    stats = result.get_statistics()
                    writer.writerow([
                        result.target,
                        result.port,
                        result.protocol.upper(),
                        result.scan_time.strftime('%Y-%m-%d %H:%M:%S'),
                        stats['total_hops'],
                        'Yes' if stats['target_reached'] else 'No',
                        stats['successful_hops'],
                        stats['timeout_hops'],
                        f"{stats['avg_rtt']:.3f}" if stats['avg_rtt'] is not None else '',
                        f"{stats['min_rtt']:.3f}" if stats['min_rtt'] is not None else '',
                        f"{stats['max_rtt']:.3f}" if stats['max_rtt'] is not None else '',
                        f"{result.scan_duration:.2f}" if result.scan_duration else ''
                    ])
            
            logger.info(f"成功寫入摘要 CSV 檔案: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"寫入摘要 CSV 檔案失敗: {str(e)}")
            raise