"""
預設設定和配置
"""
from pathlib import Path


# 基本設定
DEFAULT_PROTOCOL = "udp"
DEFAULT_PORT = 33434
DEFAULT_MAX_HOPS = 30
DEFAULT_TIMEOUT = 30

# 輸出設定
DEFAULT_OUTPUT_DIR = "output_data"
DEFAULT_CSV_DIR = "output_data/csv"
DEFAULT_CHARTS_DIR = "output_data/charts"
DEFAULT_LOGS_DIR = "output_data/logs"

# nmap 設定
NMAP_RETRY_COUNT = 1
NMAP_HOST_TIMEOUT = "30s"
NMAP_MAX_PORTS = 100  # 單次掃描最大端口數

# Windows 上的 nmap 路徑
WINDOWS_NMAP_PATHS = [
    r"C:\Program Files (x86)\Nmap\nmap.exe",
    r"C:\Program Files\Nmap\nmap.exe",
    r"C:\Tools\Nmap\nmap.exe",
]

# 日誌設定
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
LOG_ROTATION = "10 MB"
LOG_RETENTION = "7 days"

# CSV 輸出格式
CSV_ENCODING = "utf-8"
CSV_DELIMITER = ","

# HTML 輸出設定
HTML_WIDTH = 120
HTML_INLINE_STYLES = True

# 驗證範圍
MIN_PORT = 1
MAX_PORT = 65535
MIN_HOPS = 1
MAX_HOPS = 255
MIN_TIMEOUT = 5
MAX_TIMEOUT = 300

# 支援的協定
SUPPORTED_PROTOCOLS = ["tcp", "udp"]

# 預設端口映射
COMMON_PORTS = {
    "http": 80,
    "https": 443,
    "ssh": 22,
    "ftp": 21,
    "telnet": 23,
    "smtp": 25,
    "dns": 53,
    "pop3": 110,
    "imap": 143,
    "snmp": 161,
    "ldap": 389,
    "smb": 445,
}

# 錯誤訊息
ERROR_MESSAGES = {
    "nmap_not_found": "nmap 未安裝或不在 PATH 中",
    "invalid_target": "無效的目標主機",
    "invalid_port": "無效的端口號",
    "invalid_protocol": "無效的協定",
    "file_not_found": "檔案不存在",
    "permission_denied": "權限不足",
    "timeout": "操作超時",
    "network_unreachable": "網路無法到達",
}

# 成功訊息
SUCCESS_MESSAGES = {
    "scan_completed": "掃描完成",
    "file_saved": "檔案儲存成功",
    "nmap_test_passed": "nmap 測試通過",
}


def get_output_paths():
    """
    取得輸出路徑設定
    
    Returns:
        包含所有輸出路徑的字典
    """
    base_dir = Path(DEFAULT_OUTPUT_DIR)
    
    return {
        "base": base_dir,
        "csv": base_dir / "csv",
        "charts": base_dir / "charts", 
        "logs": base_dir / "logs",
    }


def ensure_output_directories():
    """確保所有輸出目錄存在"""
    paths = get_output_paths()
    
    for name, path in paths.items():
        path.mkdir(parents=True, exist_ok=True)


def get_nmap_common_options():
    """
    取得常用的 nmap 選項
    
    Returns:
        nmap 選項字典
    """
    return {
        "max_retries": NMAP_RETRY_COUNT,
        "host_timeout": NMAP_HOST_TIMEOUT,
        "no_dns": True,  # 使用 -n 選項避免 DNS 解析
        "privileged": False,  # 是否需要特權模式
    }


def validate_port(port):
    """
    驗證端口號
    
    Args:
        port: 端口號
    
    Returns:
        是否有效
    """
    try:
        port_num = int(port)
        return MIN_PORT <= port_num <= MAX_PORT
    except (ValueError, TypeError):
        return False


def validate_protocol(protocol):
    """
    驗證協定
    
    Args:
        protocol: 協定名稱
    
    Returns:
        是否有效
    """
    return protocol.lower() in SUPPORTED_PROTOCOLS


def get_port_by_service(service_name):
    """
    根據服務名稱取得端口號
    
    Args:
        service_name: 服務名稱
    
    Returns:
        端口號或 None
    """
    return COMMON_PORTS.get(service_name.lower())


# 在模組載入時確保輸出目錄存在
ensure_output_directories()