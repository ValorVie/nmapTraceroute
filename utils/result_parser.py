"""
nmap 輸出結果解析器
"""
import re
from typing import List, Optional, Tuple
from loguru import logger
from models.hop_data import HopData
from models.scan_result import ScanResult


class ResultParser:
    """nmap traceroute 結果解析器"""
    
    def __init__(self):
        """初始化解析器"""
        # Traceroute 行的正則表達式模式
        self.traceroute_pattern = re.compile(
            r'TRACEROUTE.*?\n(.*?)(?=\n\n|\nNmap|\Z)', 
            re.DOTALL | re.MULTILINE
        )
        
        # 跳點行的正則表達式模式
        # 匹配格式如: "1   1.23 ms gateway.local (192.168.1.1)"
        self.hop_pattern = re.compile(
            r'^\s*(\d+)\s+(.+?)$',
            re.MULTILINE
        )
        
        # IP 地址和延遲時間的模式
        self.ip_rtt_pattern = re.compile(
            r'(\d+(?:\.\d+)?)\s*ms.*?(\d+\.\d+\.\d+\.\d+|\*)'
        )
        
        # 主機名稱模式
        self.hostname_pattern = re.compile(
            r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        )
    
    def parse_nmap_output(
        self, 
        output: str, 
        target: str, 
        port: int, 
        protocol: str
    ) -> ScanResult:
        """
        解析 nmap 輸出
        
        Args:
            output: nmap 的標準輸出
            target: 目標主機
            port: 目標端口
            protocol: 使用的協定
        
        Returns:
            ScanResult 物件
        """
        logger.info(f"開始解析 nmap 輸出，目標: {target}:{port}")
        
        result = ScanResult(
            target=target,
            port=port,
            protocol=protocol
        )
        
        try:
            # 尋找 traceroute 部分
            traceroute_match = self.traceroute_pattern.search(output)
            
            if not traceroute_match:
                logger.warning("在 nmap 輸出中找不到 traceroute 資訊")
                # 嘗試其他解析方法
                hops = self._parse_alternative_format(output)
            else:
                traceroute_text = traceroute_match.group(1)
                logger.debug(f"找到 traceroute 部分: {traceroute_text[:200]}...")
                hops = self._parse_traceroute_hops(traceroute_text)
            
            # 添加跳點到結果
            for hop in hops:
                result.add_hop(hop)
            
            logger.info(f"成功解析 {len(hops)} 個跳點")
            
        except Exception as e:
            logger.error(f"解析 nmap 輸出時發生錯誤: {str(e)}")
            logger.debug(f"原始輸出: {output}")
        
        return result
    
    def _parse_traceroute_hops(self, traceroute_text: str) -> List[HopData]:
        """
        解析 traceroute 跳點
        
        Args:
            traceroute_text: traceroute 部分的文字
        
        Returns:
            HopData 列表
        """
        hops = []
        lines = traceroute_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('TRACEROUTE'):
                continue
            
            hop = self._parse_hop_line(line)
            if hop:
                hops.append(hop)
        
        # 填補缺失的跳點
        if hops:
            filled_hops = self._fill_missing_hops(hops)
            return filled_hops
        
        return hops
    
    def _fill_missing_hops(self, hops: List[HopData]) -> List[HopData]:
        """
        填補缺失的跳點
        
        Args:
            hops: 原始跳點列表
        
        Returns:
            填補後的跳點列表
        """
        if not hops:
            return hops
        
        # 建立完整的跳點列表
        filled_hops = []
        max_hop = max(hop.hop_number for hop in hops)
        
        # 建立跳點編號到跳點物件的映射
        hop_map = {hop.hop_number: hop for hop in hops}
        
        # 填補從 1 到最大跳點號的所有跳點
        for i in range(1, max_hop + 1):
            if i in hop_map:
                filled_hops.append(hop_map[i])
            else:
                # 建立缺失的跳點
                filled_hops.append(HopData(
                    hop_number=i,
                    ip_address="*",
                    hostname="No response",
                    status="timeout"
                ))
        
        return filled_hops
    
    def _parse_hop_line(self, line: str) -> Optional[HopData]:
        """
        解析單一跳點行
        
        Args:
            line: 跳點行文字
        
        Returns:
            HopData 物件或 None
        """
        try:
            # 提取跳點編號
            hop_match = re.match(r'^\s*(\d+)\s+(.+)$', line)
            if not hop_match:
                return None
            
            hop_number = int(hop_match.group(1))
            hop_info = hop_match.group(2).strip()
            
            # 如果是 * 表示超時
            if hop_info == '*' or 'timeout' in hop_info.lower():
                return HopData(
                    hop_number=hop_number,
                    ip_address="*",
                    status="timeout"
                )
            
            # 處理 nmap 的特殊格式，如 "... 5" 表示跳點 4 和 5 無回應
            if hop_info.startswith('...'):
                # 解析範圍，如 "... 5" 表示從當前跳點到 5 都無回應
                try:
                    end_hop = int(hop_info.replace('...', '').strip())
                    return HopData(
                        hop_number=hop_number,
                        ip_address="*",
                        hostname=f"No response (hops {hop_number}-{end_hop})",
                        status="timeout"
                    )
                except ValueError:
                    return HopData(
                        hop_number=hop_number,
                        ip_address="*",
                        hostname="No response",
                        status="timeout"
                    )
            
            # 解析 IP 地址和延遲時間
            ip_address, rtt_ms, hostname = self._extract_hop_details(hop_info)
            
            if not ip_address:
                # 如果沒有找到 IP 地址，可能是無回應的跳點
                logger.debug(f"跳點 {hop_number} 無 IP 地址，標記為無回應: {line}")
                return HopData(
                    hop_number=hop_number,
                    ip_address="*",
                    hostname="No response",
                    status="timeout"
                )
            
            return HopData(
                hop_number=hop_number,
                ip_address=ip_address,
                hostname=hostname,
                rtt_ms=rtt_ms,
                status="success" if rtt_ms is not None else "unknown"
            )
            
        except Exception as e:
            logger.warning(f"解析跳點行失敗: {line}, 錯誤: {str(e)}")
            return None
    
    def _extract_hop_details(self, hop_info: str) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """
        從跳點資訊中提取詳細資料
        
        Args:
            hop_info: 跳點資訊字串
        
        Returns:
            (ip_address, rtt_ms, hostname)
        """
        ip_address = None
        rtt_ms = None
        hostname = None
        
        # 查找 IP 地址
        ip_matches = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', hop_info)
        if ip_matches:
            ip_address = ip_matches[0]
        
        # 查找延遲時間
        rtt_matches = re.findall(r'(\d+(?:\.\d+)?)\s*ms', hop_info)
        if rtt_matches:
            try:
                rtt_ms = float(rtt_matches[0])
            except ValueError:
                pass
        
        # 查找主機名稱
        # 移除 IP 地址和時間資訊後查找剩餘的主機名稱
        cleaned_info = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '', hop_info)
        cleaned_info = re.sub(r'\d+(?:\.\d+)?\s*ms', '', cleaned_info)
        cleaned_info = cleaned_info.strip(' ()')
        
        hostname_matches = re.findall(r'([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', cleaned_info)
        if hostname_matches:
            hostname = hostname_matches[0]
        
        return ip_address, rtt_ms, hostname
    
    def _parse_alternative_format(self, output: str) -> List[HopData]:
        """
        使用備用格式解析（當標準格式解析失敗時）
        
        Args:
            output: nmap 完整輸出
        
        Returns:
            HopData 列表
        """
        logger.info("嘗試使用備用格式解析")
        hops = []
        
        # 尋找包含 "HOP RTT" 或類似模式的行
        lines = output.split('\n')
        in_traceroute = False
        
        for line in lines:
            line = line.strip()
            
            # 檢查是否進入 traceroute 區段
            if 'TRACEROUTE' in line.upper() or 'HOP RTT' in line.upper():
                in_traceroute = True
                continue
            
            # 檢查是否離開 traceroute 區段
            if in_traceroute and (line.startswith('Nmap') or line == ''):
                if not line:
                    continue
                else:
                    break
            
            # 解析跳點行
            if in_traceroute and line and not line.startswith('#'):
                hop = self._parse_hop_line(line)
                if hop:
                    hops.append(hop)
        
        return hops