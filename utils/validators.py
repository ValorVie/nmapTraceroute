"""
輸入驗證函數
"""
import re
import socket
from typing import List, Union
from pathlib import Path


def is_valid_ip(ip_address: str) -> bool:
    """
    驗證 IP 地址是否有效
    
    Args:
        ip_address: IP 地址字串
    
    Returns:
        是否為有效的 IP 地址
    """
    try:
        socket.inet_aton(ip_address)
        return True
    except socket.error:
        return False


def is_valid_domain(domain: str) -> bool:
    """
    驗證域名是否有效
    
    Args:
        domain: 域名字串
    
    Returns:
        是否為有效的域名
    """
    # 基本域名格式檢查
    domain_pattern = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    )
    
    if not domain_pattern.match(domain):
        return False
    
    # 檢查長度
    if len(domain) > 253:
        return False
    
    return True


def is_valid_target(target: str) -> bool:
    """
    驗證目標主機是否有效（IP 或域名）
    
    Args:
        target: 目標主機
    
    Returns:
        是否為有效的目標
    """
    return is_valid_ip(target) or is_valid_domain(target)


def is_valid_port(port: Union[int, str]) -> bool:
    """
    驗證端口號是否有效
    
    Args:
        port: 端口號
    
    Returns:
        是否為有效的端口號
    """
    try:
        port_num = int(port)
        return 1 <= port_num <= 65535
    except (ValueError, TypeError):
        return False


def validate_port_list(ports: Union[str, List[int]]) -> List[int]:
    """
    驗證並解析端口列表
    
    Args:
        ports: 端口字串或列表
    
    Returns:
        有效的端口列表
    
    Raises:
        ValueError: 當端口格式無效時
    """
    if isinstance(ports, list):
        # 如果已經是列表，驗證每個端口
        for port in ports:
            if not is_valid_port(port):
                raise ValueError(f"無效的端口號: {port}")
        return ports
    
    # 如果是字串，解析端口
    if isinstance(ports, str):
        result = []
        
        for port_part in ports.split(','):
            port_part = port_part.strip()
            
            if '-' in port_part:
                # 端口範圍
                try:
                    start, end = port_part.split('-', 1)
                    start_port = int(start.strip())
                    end_port = int(end.strip())
                    
                    if not is_valid_port(start_port) or not is_valid_port(end_port):
                        raise ValueError(f"端口範圍包含無效端口: {port_part}")
                    
                    if start_port > end_port:
                        raise ValueError(f"端口範圍無效: {port_part}")
                    
                    result.extend(range(start_port, end_port + 1))
                    
                except ValueError as e:
                    if "invalid literal" in str(e):
                        raise ValueError(f"端口範圍格式錯誤: {port_part}")
                    else:
                        raise
            else:
                # 單一端口
                try:
                    port = int(port_part)
                    if not is_valid_port(port):
                        raise ValueError(f"無效的端口號: {port}")
                    result.append(port)
                except ValueError:
                    raise ValueError(f"端口格式錯誤: {port_part}")
        
        return sorted(list(set(result)))  # 去重並排序
    
    raise ValueError("端口參數必須是字串或整數列表")


def is_valid_protocol(protocol: str) -> bool:
    """
    驗證協定是否有效
    
    Args:
        protocol: 協定名稱
    
    Returns:
        是否為有效的協定
    """
    return protocol.lower() in ['tcp', 'udp']


def validate_file_path(file_path: Union[str, Path], must_exist: bool = True) -> Path:
    """
    驗證檔案路徑
    
    Args:
        file_path: 檔案路徑
        must_exist: 檔案是否必須存在
    
    Returns:
        驗證後的 Path 物件
    
    Raises:
        ValueError: 當路徑無效時
    """
    path = Path(file_path)
    
    if must_exist:
        if not path.exists():
            raise ValueError(f"檔案不存在: {file_path}")
        
        if not path.is_file():
            raise ValueError(f"路徑不是檔案: {file_path}")
    
    return path


def validate_output_directory(dir_path: Union[str, Path]) -> Path:
    """
    驗證輸出目錄
    
    Args:
        dir_path: 目錄路徑
    
    Returns:
        驗證後的 Path 物件
    """
    path = Path(dir_path)
    
    # 嘗試建立目錄
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        raise ValueError(f"無法建立目錄，權限不足: {dir_path}")
    except Exception as e:
        raise ValueError(f"無法建立目錄: {dir_path}, 錯誤: {str(e)}")
    
    return path


def sanitize_filename(filename: str) -> str:
    """
    清理檔案名稱，移除不安全的字符
    
    Args:
        filename: 原始檔案名稱
    
    Returns:
        清理後的檔案名稱
    """
    # 移除或替換不安全的字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # 移除連續的底線
    filename = re.sub(r'_{2,}', '_', filename)
    
    # 移除開頭和結尾的底線
    filename = filename.strip('_')
    
    # 確保檔名不為空
    if not filename:
        filename = "output"
    
    return filename


def validate_timeout(timeout: Union[int, str]) -> int:
    """
    驗證超時時間
    
    Args:
        timeout: 超時時間
    
    Returns:
        驗證後的超時時間
    
    Raises:
        ValueError: 當超時時間無效時
    """
    try:
        timeout_int = int(timeout)
        if timeout_int < 5:
            raise ValueError("超時時間不能少於 5 秒")
        if timeout_int > 300:
            raise ValueError("超時時間不能超過 300 秒")
        return timeout_int
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("超時時間必須是數字")
        else:
            raise


def validate_max_hops(max_hops: Union[int, str]) -> int:
    """
    驗證最大跳點數
    
    Args:
        max_hops: 最大跳點數
    
    Returns:
        驗證後的最大跳點數
    
    Raises:
        ValueError: 當跳點數無效時
    """
    try:
        hops_int = int(max_hops)
        if hops_int < 1:
            raise ValueError("最大跳點數不能少於 1")
        if hops_int > 255:
            raise ValueError("最大跳點數不能超過 255")
        return hops_int
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("最大跳點數必須是數字")
        else:
            raise