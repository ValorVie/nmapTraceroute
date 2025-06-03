"""
命令列參數解析器
"""
import click
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger


def validate_ports(ctx, param, value) -> List[int]:
    """
    驗證端口參數
    
    Args:
        ctx: Click 上下文
        param: 參數物件
        value: 端口字串
    
    Returns:
        端口列表
    """
    if not value:
        return [80]  # 預設端口
    
    ports = []
    try:
        # 處理逗號分隔的端口
        for port_part in value.split(','):
            port_part = port_part.strip()
            
            # 處理端口範圍 (例如: 80-85)
            if '-' in port_part:
                start, end = port_part.split('-', 1)
                start_port = int(start.strip())
                end_port = int(end.strip())
                
                if start_port > end_port:
                    raise click.BadParameter(f"端口範圍無效: {port_part}")
                
                if end_port - start_port > 100:
                    raise click.BadParameter(f"端口範圍過大 (最多100個): {port_part}")
                
                ports.extend(range(start_port, end_port + 1))
            else:
                # 單一端口
                port = int(port_part)
                ports.append(port)
        
        # 驗證端口範圍
        for port in ports:
            if not (1 <= port <= 65535):
                raise click.BadParameter(f"端口號必須在 1-65535 範圍內: {port}")
        
        return sorted(list(set(ports)))  # 去重並排序
        
    except ValueError as e:
        raise click.BadParameter(f"端口格式錯誤: {value}")


def validate_protocol(ctx, param, value) -> str:
    """
    驗證協定參數
    
    Args:
        ctx: Click 上下文
        param: 參數物件
        value: 協定字串
    
    Returns:
        驗證後的協定
    """
    if value.lower() not in ['tcp', 'udp']:
        raise click.BadParameter("協定必須是 'tcp' 或 'udp'")
    return value.lower()


def validate_target_file(ctx, param, value) -> Optional[Path]:
    """
    驗證目標檔案
    
    Args:
        ctx: Click 上下文
        param: 參數物件
        value: 檔案路徑
    
    Returns:
        驗證後的檔案路徑
    """
    if value is None:
        return None
    
    file_path = Path(value)
    if not file_path.exists():
        raise click.BadParameter(f"目標檔案不存在: {value}")
    
    if not file_path.is_file():
        raise click.BadParameter(f"路徑不是檔案: {value}")
    
    return file_path


def validate_output_path(ctx, param, value) -> Optional[Path]:
    """
    驗證輸出路徑
    
    Args:
        ctx: Click 上下文
        param: 參數物件
        value: 輸出路徑
    
    Returns:
        驗證後的輸出路徑
    """
    if value is None:
        return None
    
    output_path = Path(value)
    
    # 確保父目錄存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    return output_path


@click.command()
@click.option(
    '-t', '--target',
    type=str,
    help='目標主機 (IP 或域名)'
)
@click.option(
    '-f', '--targets-file',
    type=click.Path(exists=True),
    callback=validate_target_file,
    help='批量掃描目標檔案'
)
@click.option(
    '-p', '--ports',
    type=str,
    default='80',
    callback=validate_ports,
    help='端口 (單一或範圍，如: 80,443 或 1-1000)'
)
@click.option(
    '--protocol',
    type=click.Choice(['tcp', 'udp'], case_sensitive=False),
    default='tcp',
    callback=validate_protocol,
    help='使用的協定 (預設: tcp)'
)
@click.option(
    '--max-hops',
    type=click.IntRange(1, 255),
    default=30,
    help='最大跳點數 (預設: 30)'
)
@click.option(
    '--timeout',
    type=click.IntRange(5, 300),
    default=30,
    help='超時時間秒數 (預設: 30)'
)
@click.option(
    '--output-csv',
    type=click.Path(),
    callback=validate_output_path,
    help='輸出 CSV 檔案路徑'
)
@click.option(
    '--output-dir',
    type=click.Path(),
    help='輸出目錄'
)
@click.option(
    '--show-chart',
    is_flag=True,
    help='顯示表格圖表'
)
@click.option(
    '--save-html',
    is_flag=True,
    help='儲存 HTML 報告'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='詳細輸出模式'
)
@click.option(
    '--quiet',
    is_flag=True,
    help='安靜模式 (只輸出結果)'
)
@click.option(
    '--test-nmap',
    is_flag=True,
    help='測試 nmap 安裝'
)
@click.option(
    '--monitor',
    is_flag=True,
    help='啟用即時監測模式'
)
@click.option(
    '--interval',
    type=click.IntRange(1, 3600),
    default=5,
    help='監測間隔秒數 (預設: 5)'
)
@click.option(
    '--max-history',
    type=click.IntRange(10, 10000),
    default=100,
    help='最大歷史記錄數 (預設: 100)'
)
def cli_main(
    target: Optional[str],
    targets_file: Optional[Path],
    ports: List[int],
    protocol: str,
    max_hops: int,
    timeout: int,
    output_csv: Optional[Path],
    output_dir: Optional[str],
    show_chart: bool,
    save_html: bool,
    verbose: bool,
    quiet: bool,
    test_nmap: bool,
    monitor: bool,
    interval: int,
    max_history: int
):
    """
    Python + nmap Traceroute 工具
    
    範例:
        uv run python main.py -t 211.75.74.41 -p 443 --protocol tcp
        uv run python main.py -f targets.txt --output-csv results.csv --show-chart
        uv run python main.py -t 8.8.8.8 -p 53 --monitor --interval 10
        uv run python main.py --test-nmap
    """
    # 驗證參數
    if test_nmap:
        _test_nmap_installation()
        return None  # 測試完成後直接退出
    
    if not target and not targets_file:
        raise click.UsageError("必須指定目標主機 (-t) 或目標檔案 (-f)")
    
    if target and targets_file:
        raise click.UsageError("不能同時指定目標主機和目標檔案")
    
    # 返回解析後的參數
    return {
        'target': target,
        'targets_file': targets_file,
        'ports': ports,
        'protocol': protocol,
        'max_hops': max_hops,
        'timeout': timeout,
        'output_csv': output_csv,
        'output_dir': output_dir,
        'show_chart': show_chart,
        'save_html': save_html,
        'verbose': verbose,
        'quiet': quiet,
        'monitor': monitor,
        'interval': interval,
        'max_history': max_history
    }


def _test_nmap_installation():
    """測試 nmap 安裝"""
    try:
        from core.traceroute_scanner import TracerouteScanner
        
        scanner = TracerouteScanner()
        if scanner.test_nmap():
            click.echo(click.style("✓ nmap 測試成功！", fg='green'))
            return True
        else:
            click.echo(click.style("✗ nmap 測試失敗！", fg='red'))
            return False
    except Exception as e:
        click.echo(click.style(f"✗ nmap 測試失敗: {str(e)}", fg='red'))
        return False


def parse_arguments():
    """
    解析命令列參數的便利函數
    
    Returns:
        解析後的參數字典
    """
    try:
        return cli_main.main(standalone_mode=False)
    except click.ClickException as e:
        e.show()
        return None
    except Exception as e:
        click.echo(click.style(f"參數解析錯誤: {str(e)}", fg='red'), err=True)
        return None


if __name__ == '__main__':
    # 直接執行時使用標準 Click 行為
    cli_main()