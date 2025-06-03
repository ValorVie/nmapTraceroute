"""
nmap 命令執行器
"""
import subprocess
import shutil
import platform
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger
from config.default_settings import WINDOWS_NMAP_PATHS


class NmapExecutor:
    """nmap 命令執行器"""
    
    def __init__(self, timeout: int = 30):
        """
        初始化執行器
        
        Args:
            timeout: 命令執行超時時間（秒）
        """
        self.timeout = timeout
        self.nmap_path = None
        self._validate_nmap_installation()
    
    def _validate_nmap_installation(self) -> bool:
        """檢查 nmap 是否已安裝"""
        nmap_path = self._find_nmap_executable()
        if not nmap_path:
            raise RuntimeError(
                "nmap 未安裝或不在 PATH 中。請先安裝 nmap：\n"
                "Windows: 從 https://nmap.org/download.html 下載安裝\n"
                "Linux: sudo apt-get install nmap\n"
                "macOS: brew install nmap"
            )
        self.nmap_path = nmap_path
        return True
    
    def _find_nmap_executable(self) -> Optional[str]:
        """尋找 nmap 執行檔"""
        # 首先檢查 PATH 中是否有 nmap
        nmap_path = shutil.which("nmap")
        if nmap_path:
            return nmap_path
        
        # 如果是 Windows，檢查常見的安裝路徑
        if platform.system() == "Windows":
            for path in WINDOWS_NMAP_PATHS:
                if Path(path).exists():
                    return path
        
        return None
    
    def build_command(
        self, 
        target: str, 
        ports: List[int], 
        protocol: str = "tcp",
        max_hops: int = 30,
        verbose: bool = True
    ) -> List[str]:
        """
        建構 nmap 命令
        
        Args:
            target: 目標主機
            ports: 端口列表
            protocol: 協定 (tcp/udp)
            max_hops: 最大跳點數
            verbose: 是否啟用詳細輸出
        
        Returns:
            nmap 命令列表
        """
        cmd = [self.nmap_path or "nmap"]
        
        # 端口參數
        if len(ports) == 1:
            cmd.extend(["-p", str(ports[0])])
        else:
            cmd.extend(["-p", ",".join(map(str, ports))])
        
        # 協定參數
        if protocol.lower() == "udp":
            cmd.append("-sU")
        else:
            cmd.append("-sT")  # TCP connect scan
        
        # Traceroute 參數
        cmd.append("--traceroute")
        
        # 最大跳點數
        cmd.extend(["--max-retries", "1"])
        cmd.extend(["--host-timeout", f"{self.timeout}s"])
        
        # 詳細輸出
        if verbose:
            cmd.append("-vv")
        
        # 避免 DNS 解析延遲（可選）
        cmd.append("-n")
        
        # 目標
        cmd.append(target)
        
        logger.info(f"建構的 nmap 命令: {' '.join(cmd)}")
        return cmd
    
    def execute_scan(self, command: List[str]) -> Tuple[str, str, int]:
        """
        執行 nmap 掃描
        
        Args:
            command: nmap 命令列表
        
        Returns:
            (stdout, stderr, return_code)
        """
        try:
            logger.info(f"執行 nmap 命令: {' '.join(command)}")
            
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='replace'  # 處理編碼問題
            )
            
            logger.info(f"nmap 執行完成，返回碼: {process.returncode}")
            
            if process.returncode != 0:
                logger.warning(f"nmap 執行警告，stderr: {process.stderr}")
            
            return process.stdout, process.stderr, process.returncode
            
        except subprocess.TimeoutExpired:
            error_msg = f"nmap 命令執行超時 ({self.timeout} 秒)"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except subprocess.SubprocessError as e:
            error_msg = f"執行 nmap 命令失敗: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except Exception as e:
            error_msg = f"執行 nmap 時發生未預期錯誤: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def test_nmap_version(self) -> str:
        """
        測試 nmap 版本
        
        Returns:
            nmap 版本資訊
        """
        try:
            result = subprocess.run(
                [self.nmap_path or "nmap", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                version_info = result.stdout.strip()
                logger.info(f"nmap 版本: {version_info}")
                return version_info
            else:
                raise RuntimeError("無法取得 nmap 版本資訊")
                
        except Exception as e:
            raise RuntimeError(f"測試 nmap 版本失敗: {str(e)}")