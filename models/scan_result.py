"""
掃描結果資料結構定義
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from .hop_data import HopData


@dataclass
class ScanResult:
    """完整的 Traceroute 掃描結果"""
    target: str
    port: int
    protocol: str
    hops: List[HopData] = field(default_factory=list)
    scan_time: datetime = field(default_factory=datetime.now)
    target_reached: bool = False
    total_hops: int = 0
    scan_duration: Optional[float] = None  # 掃描耗時（秒）
    
    def __post_init__(self):
        """計算統計資訊"""
        self.total_hops = len(self.hops)
        
        # 檢查是否到達目標
        if self.hops:
            last_hop = self.hops[-1]
            # 如果最後一跳的 IP 就是目標，或者狀態為 success，則認為到達目標
            self.target_reached = (
                last_hop.ip_address == self.target or 
                last_hop.status == "success"
            )
    
    def add_hop(self, hop: HopData):
        """添加跳點"""
        self.hops.append(hop)
        self.total_hops = len(self.hops)
    
    def get_statistics(self) -> dict:
        """取得統計資訊"""
        valid_rtts = [hop.rtt_ms for hop in self.hops if hop.rtt_ms is not None]
        
        stats = {
            "total_hops": self.total_hops,
            "target_reached": self.target_reached,
            "successful_hops": len([h for h in self.hops if h.status == "success"]),
            "timeout_hops": len([h for h in self.hops if h.status == "timeout"]),
        }
        
        if valid_rtts:
            stats.update({
                "avg_rtt": sum(valid_rtts) / len(valid_rtts),
                "min_rtt": min(valid_rtts),
                "max_rtt": max(valid_rtts),
            })
        else:
            stats.update({
                "avg_rtt": None,
                "min_rtt": None,
                "max_rtt": None,
            })
        
        return stats
    
    def to_dict(self) -> dict:
        """轉換為字典格式"""
        return {
            "target": self.target,
            "port": self.port,
            "protocol": self.protocol,
            "scan_time": self.scan_time.isoformat(),
            "scan_duration": self.scan_duration,
            "hops": [hop.to_dict() for hop in self.hops],
            "statistics": self.get_statistics()
        }
    
    def __str__(self) -> str:
        """字串表示"""
        lines = [
            f"Traceroute to {self.target}:{self.port} ({self.protocol.upper()})",
            f"Scan time: {self.scan_time.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        for hop in self.hops:
            lines.append(str(hop))
        
        stats = self.get_statistics()
        lines.extend([
            "",
            "Statistics:",
            f"  Total hops: {stats['total_hops']}",
            f"  Target reached: {'Yes' if stats['target_reached'] else 'No'}",
            f"  Successful hops: {stats['successful_hops']}",
        ])
        
        if stats['avg_rtt'] is not None:
            lines.extend([
                f"  Average RTT: {stats['avg_rtt']:.3f} ms",
                f"  Min RTT: {stats['min_rtt']:.3f} ms",
                f"  Max RTT: {stats['max_rtt']:.3f} ms",
            ])
        
        return "\n".join(lines)