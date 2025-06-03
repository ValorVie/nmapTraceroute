#!/usr/bin/env python3
"""
基本功能測試
"""
import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.hop_data import HopData
from models.scan_result import ScanResult
from utils.validators import is_valid_ip, is_valid_domain, validate_port_list
from utils.nmap_executor import NmapExecutor
from core.traceroute_scanner import TracerouteScanner


class TestHopData(unittest.TestCase):
    """測試 HopData 類別"""
    
    def test_hop_data_creation(self):
        """測試跳點資料建立"""
        hop = HopData(
            hop_number=1,
            ip_address="192.168.1.1",
            hostname="gateway.local",
            rtt_ms=1.234
        )
        
        self.assertEqual(hop.hop_number, 1)
        self.assertEqual(hop.ip_address, "192.168.1.1")
        self.assertEqual(hop.hostname, "gateway.local")
        self.assertEqual(hop.rtt_ms, 1.234)
        self.assertEqual(hop.status, "success")
    
    def test_hop_data_validation(self):
        """測試跳點資料驗證"""
        # 測試無效的跳點編號
        with self.assertRaises(ValueError):
            HopData(hop_number=0, ip_address="192.168.1.1")
        
        # 測試空的 IP 地址
        with self.assertRaises(ValueError):
            HopData(hop_number=1, ip_address="")
    
    def test_hop_data_to_dict(self):
        """測試轉換為字典"""
        hop = HopData(
            hop_number=1,
            ip_address="192.168.1.1",
            hostname="gateway.local",
            rtt_ms=1.234
        )
        
        result = hop.to_dict()
        expected = {
            "hop_number": 1,
            "ip_address": "192.168.1.1",
            "hostname": "gateway.local",
            "rtt_ms": 1.234,
            "status": "success"
        }
        
        self.assertEqual(result, expected)


class TestScanResult(unittest.TestCase):
    """測試 ScanResult 類別"""
    
    def test_scan_result_creation(self):
        """測試掃描結果建立"""
        result = ScanResult(
            target="example.com",
            port=80,
            protocol="tcp"
        )
        
        self.assertEqual(result.target, "example.com")
        self.assertEqual(result.port, 80)
        self.assertEqual(result.protocol, "tcp")
        self.assertEqual(len(result.hops), 0)
        self.assertFalse(result.target_reached)
    
    def test_add_hop(self):
        """測試添加跳點"""
        result = ScanResult("example.com", 80, "tcp")
        
        hop1 = HopData(1, "192.168.1.1", "gateway.local", 1.234)
        hop2 = HopData(2, "10.0.0.1", "isp.example.com", 12.567)
        
        result.add_hop(hop1)
        result.add_hop(hop2)
        
        self.assertEqual(len(result.hops), 2)
        self.assertEqual(result.total_hops, 2)
    
    def test_statistics(self):
        """測試統計資訊"""
        result = ScanResult("example.com", 80, "tcp")
        
        hop1 = HopData(1, "192.168.1.1", "gateway.local", 1.234)
        hop2 = HopData(2, "10.0.0.1", "isp.example.com", 12.567)
        hop3 = HopData(3, "*", status="timeout")
        
        result.add_hop(hop1)
        result.add_hop(hop2)
        result.add_hop(hop3)
        
        stats = result.get_statistics()
        
        self.assertEqual(stats['total_hops'], 3)
        self.assertEqual(stats['successful_hops'], 2)
        self.assertEqual(stats['timeout_hops'], 1)
        self.assertAlmostEqual(stats['avg_rtt'], (1.234 + 12.567) / 2, places=3)


class TestValidators(unittest.TestCase):
    """測試驗證函數"""
    
    def test_is_valid_ip(self):
        """測試 IP 地址驗證"""
        # 有效的 IP 地址
        self.assertTrue(is_valid_ip("192.168.1.1"))
        self.assertTrue(is_valid_ip("8.8.8.8"))
        self.assertTrue(is_valid_ip("127.0.0.1"))
        
        # 無效的 IP 地址
        self.assertFalse(is_valid_ip("256.1.1.1"))
        self.assertFalse(is_valid_ip("192.168.1"))
        self.assertFalse(is_valid_ip("not.an.ip"))
        self.assertFalse(is_valid_ip(""))
    
    def test_is_valid_domain(self):
        """測試域名驗證"""
        # 有效的域名
        self.assertTrue(is_valid_domain("example.com"))
        self.assertTrue(is_valid_domain("sub.example.com"))
        self.assertTrue(is_valid_domain("test-domain.org"))
        
        # 無效的域名
        self.assertFalse(is_valid_domain(""))
        self.assertFalse(is_valid_domain(".com"))
        self.assertFalse(is_valid_domain("domain."))
        self.assertFalse(is_valid_domain("domain..com"))
    
    def test_validate_port_list(self):
        """測試端口列表驗證"""
        # 單一端口
        self.assertEqual(validate_port_list("80"), [80])
        self.assertEqual(validate_port_list([80]), [80])
        
        # 多個端口
        self.assertEqual(validate_port_list("80,443,22"), [22, 80, 443])
        
        # 端口範圍
        self.assertEqual(validate_port_list("80-83"), [80, 81, 82, 83])
        
        # 混合格式
        self.assertEqual(validate_port_list("22,80-82,443"), [22, 80, 81, 82, 443])
        
        # 無效端口
        with self.assertRaises(ValueError):
            validate_port_list("0")
        
        with self.assertRaises(ValueError):
            validate_port_list("65536")
        
        with self.assertRaises(ValueError):
            validate_port_list("abc")


class TestNmapExecutor(unittest.TestCase):
    """測試 NmapExecutor 類別"""
    
    @patch('shutil.which')
    def test_nmap_installation_check(self, mock_which):
        """測試 nmap 安裝檢查"""
        # 模擬 nmap 已安裝
        mock_which.return_value = "/usr/bin/nmap"
        
        try:
            executor = NmapExecutor()
            self.assertTrue(True)  # 如果沒有拋出異常，測試通過
        except RuntimeError:
            self.fail("NmapExecutor 在 nmap 已安裝時不應拋出異常")
    
    @patch('shutil.which')
    def test_nmap_not_installed(self, mock_which):
        """測試 nmap 未安裝的情況"""
        # 模擬 nmap 未安裝
        mock_which.return_value = None
        
        with self.assertRaises(RuntimeError):
            NmapExecutor()
    
    def test_build_command(self):
        """測試建構 nmap 命令"""
        with patch('shutil.which', return_value="/usr/bin/nmap"):
            executor = NmapExecutor()
            
            command = executor.build_command(
                target="example.com",
                ports=[80],
                protocol="tcp",
                max_hops=30,
                verbose=True
            )
            
            self.assertIn("nmap", command)
            self.assertIn("-p", command)
            self.assertIn("80", command)
            self.assertIn("--traceroute", command)
            self.assertIn("example.com", command)


class TestTracerouteScanner(unittest.TestCase):
    """測試 TracerouteScanner 類別"""
    
    @patch('shutil.which')
    def test_scanner_initialization(self, mock_which):
        """測試掃描器初始化"""
        mock_which.return_value = "/usr/bin/nmap"
        
        scanner = TracerouteScanner(
            protocol="tcp",
            max_hops=20,
            timeout=30
        )
        
        self.assertEqual(scanner.protocol, "tcp")
        self.assertEqual(scanner.max_hops, 20)
        self.assertEqual(scanner.timeout, 30)
    
    @patch('shutil.which')
    def test_invalid_protocol(self, mock_which):
        """測試無效的協定"""
        mock_which.return_value = "/usr/bin/nmap"
        
        with self.assertRaises(ValueError):
            TracerouteScanner(protocol="invalid")


class TestIntegration(unittest.TestCase):
    """整合測試"""
    
    def test_full_workflow_mock(self):
        """測試完整的工作流程（使用模擬）"""
        # 這個測試使用模擬來測試完整的工作流程
        # 而不需要實際執行 nmap
        
        with patch('shutil.which', return_value="/usr/bin/nmap"):
            with patch('subprocess.run') as mock_run:
                # 模擬 nmap 輸出
                mock_output = """
TRACEROUTE (using port 80/tcp)
HOP RTT     ADDRESS
1   1.234 ms 192.168.1.1
2   12.567 ms 10.0.0.1
3   25.891 ms example.com (203.0.113.1)
"""
                mock_run.return_value = MagicMock(
                    stdout=mock_output,
                    stderr="",
                    returncode=0
                )
                
                scanner = TracerouteScanner()
                result = scanner.scan_target("example.com", 80)
                
                self.assertEqual(result.target, "example.com")
                self.assertEqual(result.port, 80)
                self.assertEqual(result.protocol, "tcp")


if __name__ == '__main__':
    # 執行測試
    unittest.main(verbosity=2)