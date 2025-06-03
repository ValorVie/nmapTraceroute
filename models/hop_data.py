"""
跳點資料結構定義
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class HopData:
    """單一跳點的資料結構"""
    hop_number: int
    ip_address: str
    hostname: Optional[str] = None
    rtt_ms: Optional[float] = None
    status: str = "success"  # success, timeout, unreachable
    
    def __post_init__(self):
        """資料驗證"""
        if self.hop_number < 1:
            raise ValueError("跳點編號必須大於 0")
        
        if not self.ip_address:
            raise ValueError("IP 位址不能為空")
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            "hop_number": self.hop_number,
            "ip_address": self.ip_address,
            "hostname": self.hostname or "",
            "rtt_ms": self.rtt_ms if self.rtt_ms is not None else "",
            "status": self.status
        }
    
    def __str__(self) -> str:
        """字串表示"""
        hostname_str = f" ({self.hostname})" if self.hostname else ""
        rtt_str = f" {self.rtt_ms:.3f}ms" if self.rtt_ms is not None else " *"
        return f"{self.hop_number:2d}  {self.ip_address}{hostname_str}{rtt_str}"