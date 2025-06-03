"""
主要的 Traceroute 掃描器
"""
import time
from typing import List, Optional, Union
from pathlib import Path
from loguru import logger

from utils.nmap_executor import NmapExecutor
from utils.result_parser import ResultParser
from models.scan_result import ScanResult


class TracerouteScanner:
    """主要的 Traceroute 掃描器"""
    
    def __init__(
        self, 
        protocol: str = "tcp", 
        max_hops: int = 30, 
        timeout: int = 30,
        verbose: bool = True
    ):
        """
        初始化掃描器
        
        Args:
            protocol: 使用的協定 (tcp/udp)
            max_hops: 最大跳點數
            timeout: 超時時間（秒）
            verbose: 是否啟用詳細輸出
        """
        self.protocol = protocol.lower()
        self.max_hops = max_hops
        self.timeout = timeout
        self.verbose = verbose
        
        # 驗證協定
        if self.protocol not in ["tcp", "udp"]:
            raise ValueError("協定必須是 'tcp' 或 'udp'")
        
        # 初始化執行器和解析器
        self.nmap_executor = NmapExecutor(timeout=timeout)
        self.result_parser = ResultParser()
        
        logger.info(f"TracerouteScanner 初始化完成，協定: {protocol}, 最大跳點: {max_hops}")
    
    def scan_target(
        self, 
        target: str, 
        ports: Union[int, List[int]], 
        protocol: Optional[str] = None
    ) -> ScanResult:
        """
        掃描指定目標和端口
        
        Args:
            target: 目標主機 (IP 或域名)
            ports: 端口號或端口列表
            protocol: 覆蓋預設協定
        
        Returns:
            ScanResult 物件
        """
        # 處理端口參數
        if isinstance(ports, int):
            port_list = [ports]
            primary_port = ports
        else:
            port_list = list(ports)
            primary_port = port_list[0] if port_list else 80
        
        # 使用指定協定或預設協定
        scan_protocol = protocol or self.protocol
        
        logger.info(f"開始掃描目標: {target}, 端口: {port_list}, 協定: {scan_protocol}")
        
        start_time = time.time()
        
        try:
            # 建構 nmap 命令
            command = self.nmap_executor.build_command(
                target=target,
                ports=port_list,
                protocol=scan_protocol,
                max_hops=self.max_hops,
                verbose=self.verbose
            )
            
            # 執行掃描
            stdout, stderr, return_code = self.nmap_executor.execute_scan(command)
            
            # 計算掃描時間
            scan_duration = time.time() - start_time
            
            # 解析結果
            result = self.result_parser.parse_nmap_output(
                output=stdout,
                target=target,
                port=primary_port,
                protocol=scan_protocol
            )
            
            # 設定掃描時間
            result.scan_duration = scan_duration
            
            # 記錄結果
            stats = result.get_statistics()
            logger.info(
                f"掃描完成，耗時: {scan_duration:.2f}s, "
                f"跳點數: {stats['total_hops']}, "
                f"到達目標: {stats['target_reached']}"
            )
            
            if return_code != 0:
                logger.warning(f"nmap 返回非零狀態碼: {return_code}")
                if stderr:
                    logger.warning(f"stderr: {stderr}")
            
            return result
            
        except Exception as e:
            logger.error(f"掃描目標 {target} 失敗: {str(e)}")
            # 返回空結果而不是拋出異常
            result = ScanResult(
                target=target,
                port=primary_port,
                protocol=scan_protocol
            )
            result.scan_duration = time.time() - start_time
            return result
    
    def scan_multiple_targets(
        self, 
        targets: Union[str, Path, List[str]], 
        ports: Union[int, List[int]] = 80,
        protocol: Optional[str] = None
    ) -> List[ScanResult]:
        """
        批量掃描多個目標
        
        Args:
            targets: 目標清單或包含目標的檔案路徑
            ports: 端口號或端口列表
            protocol: 覆蓋預設協定
        
        Returns:
            ScanResult 列表
        """
        # 處理目標參數
        if isinstance(targets, (str, Path)):
            # 如果是檔案路徑，讀取目標清單
            target_file = Path(targets)
            if target_file.exists():
                target_list = self._read_targets_from_file(target_file)
            else:
                # 如果不是檔案，當作單一目標處理
                target_list = [str(targets)]
        else:
            target_list = list(targets)
        
        logger.info(f"批量掃描 {len(target_list)} 個目標")
        
        results = []
        for i, target in enumerate(target_list, 1):
            target = target.strip()
            if not target or target.startswith('#'):
                continue
            
            logger.info(f"掃描進度: {i}/{len(target_list)} - {target}")
            
            try:
                result = self.scan_target(target, ports, protocol)
                results.append(result)
            except Exception as e:
                logger.error(f"掃描目標 {target} 時發生錯誤: {str(e)}")
                # 繼續掃描其他目標
                continue
        
        logger.info(f"批量掃描完成，成功掃描 {len(results)} 個目標")
        return results
    
    def _read_targets_from_file(self, file_path: Path) -> List[str]:
        """
        從檔案讀取目標清單
        
        Args:
            file_path: 目標檔案路徑
        
        Returns:
            目標清單
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                targets = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        targets.append(line)
                return targets
        except Exception as e:
            logger.error(f"讀取目標檔案失敗: {str(e)}")
            raise
    
    def test_nmap(self) -> bool:
        """
        測試 nmap 是否正常工作
        
        Returns:
            測試是否成功
        """
        try:
            version_info = self.nmap_executor.test_nmap_version()
            logger.info(f"nmap 測試成功: {version_info}")
            return True
        except Exception as e:
            logger.error(f"nmap 測試失敗: {str(e)}")
            return False