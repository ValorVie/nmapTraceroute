# Python + nmap Traceroute 工具

一個使用 Python 和 nmap 建立的 Traceroute 工具，支援 TCP/UDP 協定選擇，能輸出 CSV 檔案和美觀的表格圖表。

## 功能特色

- 🚀 **靈活的協定支援**: 支援 TCP 和 UDP 協定的 traceroute
- 🎯 **多端口掃描**: 可同時掃描多個端口
- 📊 **多種輸出格式**: 支援終端顯示、CSV 檔案、HTML 報告
- 📈 **美觀的表格圖表**: 使用 Rich 庫生成美觀的表格
- 🔄 **批量掃描**: 支援從檔案讀取多個目標進行批量掃描
- ⏰ **即時監測**: 持續監控網路狀態，即時顯示路由變化
- 📈 **統計分析**: 提供成功率、回應時間等詳細統計
- ⚡ **高效能**: 模組化設計，易於擴展和維護

## 安裝需求

### 系統需求
- Python 3.12+
- nmap (已安裝並在 PATH 中)

### 安裝 nmap
```bash
# Windows
# 從 https://nmap.org/download.html 下載安裝

# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install nmap

# macOS
brew install nmap
```

### 安裝 Python 依賴
```bash
# 使用 uv 安裝專案依賴 (推薦)
uv add rich click pandas tabulate pydantic loguru

# 或者使用 uv sync
uv sync

# 傳統方式 (如果不使用 uv)
pip install -r requirements.txt
```

## 快速開始

### 命令列使用

```bash
# 基本使用 - 掃描單一目標
uv run python main.py -t 8.8.8.8 -p 443 --protocol tcp

# 掃描多個端口
uv run python main.py -t example.com -p 80,443,22 --show-chart

# 批量掃描
uv run python main.py -f targets.txt --output-csv results.csv

# UDP 掃描
uv run python main.py -t 8.8.8.8 -p 53 --protocol udp

# 儲存 HTML 報告
uv run python main.py -t github.com -p 443 --save-html --show-chart

# 即時監測模式
uv run python main.py -t 8.8.8.8 -p 53 --monitor --interval 10 --max_history 100

# 測試 nmap 安裝
uv run python main.py --test-nmap
```

### 程式化使用

```python
from core.traceroute_scanner import TracerouteScanner
from output.csv_writer import CSVWriter
from output.table_chart import TableChart

# 建立掃描器
scanner = TracerouteScanner(
    protocol="tcp",
    max_hops=30,
    timeout=30
)

# 掃描目標
result = scanner.scan_target("example.com", 443)

# 顯示結果
print(result)

# 儲存 CSV
csv_writer = CSVWriter()
csv_writer.write_scan_result(result)

# 顯示表格
table_chart = TableChart()
table_chart.display_scan_result(result)
```

## 命令列選項

```
Usage: uv run python main.py [OPTIONS]

Options:
  -t, --target TEXT          目標主機 (IP 或域名)
  -f, --targets-file PATH    批量掃描目標檔案
  -p, --ports TEXT           端口 (單一或範圍，如: 80,443 或 1-1000)
  --protocol [tcp|udp]       使用的協定 (預設: tcp)
  --max-hops INTEGER         最大跳點數 (預設: 30)
  --timeout INTEGER          超時時間秒數 (預設: 30)
  --output-csv PATH          輸出 CSV 檔案路徑
  --output-dir PATH          輸出目錄
  --show-chart              顯示表格圖表
  --save-html               儲存 HTML 報告
  --monitor                 啟用即時監測模式
  --interval INTEGER        監測間隔秒數 (預設: 5)
  --max-history INTEGER     最大歷史記錄數 (預設: 100)
  --verbose                 詳細輸出模式
  --quiet                   安靜模式 (只輸出結果)
  --test-nmap               測試 nmap 安裝
  --help                    顯示說明
```

## 專案結構

```
nmapTraceroute/
├── main.py                          # 主程式入口
├── pyproject.toml                   # 專案配置
├── README.md                        # 專案說明
├── PROJECT_ARCHITECTURE.md         # 架構文件
│
├── config/
│   └── default_settings.py         # 預設參數配置
│
├── core/
│   ├── traceroute_scanner.py        # 主要掃描器類別
│   └── realtime_monitor.py          # 即時監測器
│
├── cli/
│   └── argument_parser.py           # 命令列參數處理
│
├── utils/
│   ├── nmap_executor.py             # nmap 命令執行器
│   ├── result_parser.py             # nmap 輸出解析器
│   └── validators.py                # 輸入驗證
│
├── models/
│   ├── hop_data.py                  # 單一跳點資料結構
│   └── scan_result.py               # 完整掃描結果結構
│
├── output/
│   ├── csv_writer.py                # CSV 檔案輸出
│   └── table_chart.py               # 表格式圖表生成
│
├── tests/                           # 測試檔案
├── examples/                        # 使用範例
├── docs/                           # 說明文件
└── output_data/                    # 輸出檔案目錄
    ├── csv/                        # CSV 檔案
    ├── charts/                     # 圖表檔案
    └── logs/                       # 日誌檔案
```

## 使用範例

### 1. 基本 Traceroute

```bash
# 範例: 追蹤到 Google DNS 的路徑
uv run python main.py -t 8.8.8.8 -p 53 --protocol tcp --show-chart
```

輸出：
```
┌─────┬─────────────────┬──────────────────────────────┬─────────────┬──────────┐
│ Hop │ IP Address      │ Hostname                     │ RTT (ms)    │ Status   │
├─────┼─────────────────┼──────────────────────────────┼─────────────┼──────────┤
│  1  │ 192.168.1.1     │ gateway.local                │ 1.234       │ success  │
│  2  │ 10.0.0.1        │ isp-gateway.example.com      │ 12.567      │ success  │
│  3  │ 203.69.123.45   │ router.telecom.tw            │ 25.891      │ success  │
│ ... │ ...             │ ...                          │ ...         │ ...      │
│ 12  │ 8.8.8.8         │ dns.google                   │ 45.123      │ success  │
└─────┴─────────────────┴──────────────────────────────┴─────────────┴──────────┘

Statistics:
- Total Hops: 12
- Target Reached: Yes
- Average RTT: 28.45 ms
- Max RTT: 67.89 ms
```

### 2. 批量掃描

建立目標檔案 `targets.txt`:
```
8.8.8.8
1.1.1.1
208.67.222.222
github.com
```

執行批量掃描:
```bash
uv run python main.py -f targets.txt -p 443 --output-csv batch_results.csv --show-chart
```

### 3. UDP Traceroute

```bash
# UDP 掃描 DNS 服務
uv run python main.py -t 8.8.8.8 -p 53 --protocol udp --timeout 60
```

### 4. 多端口掃描

```bash
# 掃描常見服務端口
uv run python main.py -t example.com -p 22,80,443 --save-html
```

### 5. 即時監測模式

```bash
# 基本即時監測
uv run python main.py -t 8.8.8.8 -p 53 --monitor

# 自訂監測間隔和歷史記錄數
uv run python main.py -t github.com -p 443 --monitor --interval 30 --max-history 200

# 靜默監測模式
uv run python main.py -t 1.1.1.1 -p 53 --monitor --quiet --interval 10
```

即時監測功能特色：
- 🔄 持續監控網路連線狀態
- 📊 即時顯示路由路徑變化
- 📈 統計成功率和回應時間
- 💾 支援結束後儲存詳細報告
- ⌨️ 互動式控制選項
- ⚠️ 自動防止掃描重疊
- 🕒 建議監測間隔 ≥ 10秒

**監測間隔建議：**
- 最小間隔：5 秒
- 建議間隔：10-30 秒
- 長期監測：60 秒或更長
- nmap 掃描通常需要 5-8 秒完成

**報告功能：**
- 📊 **增強版 CSV 報告**：包含監測摘要、統計分析、詳細記錄和跳點分析
- 📈 **互動式 HTML 報告**：含圖表、趨勢分析、跳點穩定性分析
- 🔍 **詳細統計**：成功率、回應時間分布、跳點行為分析
- 📋 **即時顯示**：監測過程中即時更新統計和狀態

## 輸出格式

### CSV 輸出

CSV 檔案包含以下欄位：
- Hop Number: 跳點編號
- IP Address: IP 地址
- Hostname: 主機名稱
- RTT (ms): 回應時間
- Status: 狀態 (success/timeout/unreachable)

### HTML 報告

HTML 報告包含：
- 彩色表格顯示
- 統計資訊摘要
- 互動式圖表（如果啟用）

## 進階使用

### 自訂配置

```python
from core.traceroute_scanner import TracerouteScanner

# 自訂掃描參數
scanner = TracerouteScanner(
    protocol="tcp",
    max_hops=20,      # 最大跳點數
    timeout=60,       # 超時時間
    verbose=True      # 詳細輸出
)

# 批量掃描多個目標
targets = ["google.com", "github.com", "stackoverflow.com"]
results = scanner.scan_multiple_targets(targets, ports=[80, 443])

# 處理結果
for result in results:
    stats = result.get_statistics()
    print(f"{result.target}: {stats['total_hops']} hops, "
          f"reached: {stats['target_reached']}")
```

### 錯誤處理

```python
try:
    result = scanner.scan_target("unreachable.example.com", 80)
    if result.get_statistics()['target_reached']:
        print("目標可達")
    else:
        print("目標不可達")
except Exception as e:
    print(f"掃描失敗: {str(e)}")
```

## 疑難排解

### 常見問題

1. **nmap 找不到**
   ```
   錯誤: nmap 未安裝或不在 PATH 中
   ```
   解決: 安裝 nmap 並確保在系統 PATH 中

2. **權限不足**
   ```
   錯誤: 權限不足，無法執行原始套接字操作
   ```
   解決: 在 Linux/macOS 上使用 sudo 執行，或使用 TCP connect 掃描

3. **目標不可達**
   ```
   警告: 目標不可達或被防火牆封鎖
   ```
   解決: 檢查網路連線和防火牆設定

4. **即時監測問題**
   ```
   警告: 上次掃描尚未完成，跳過本次掃描
   ```
   解決: 增加監測間隔時間（建議 ≥ 10秒）

5. **Ctrl+C 後沒有顯示選項**
   ```
   監測被意外中斷
   ```
   解決: 確保在即時監測介面按 Ctrl+C，而非在背景模式

### 除錯模式

```bash
# 啟用詳細輸出
uv run python main.py -t example.com -p 80 --verbose

# 測試 nmap 功能
uv run python main.py --test-nmap
```

## 開發

### 執行測試

```bash
# 安裝開發依賴
uv add --dev pytest pytest-cov black isort mypy

# 執行測試
uv run pytest tests/

# 執行範例
uv run python examples/basic_usage.py

# 完整功能演示
uv run python demo_all_features.py
```

### 演示腳本

我們提供了一個完整的功能演示腳本 `demo_all_features.py`：

```bash
uv run python demo_all_features.py
```

演示內容包括：
- 🚀 基本 traceroute 掃描
- 📦 批量目標掃描
- ⏱️ 即時監測功能
- 📋 增強版報告生成

### 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/new-feature`)
3. 提交變更 (`git commit -am 'Add some feature'`)
4. 推送到分支 (`git push origin feature/new-feature`)
5. 建立 Pull Request

## 授權

此專案使用 MIT 授權條款，詳見 LICENSE 檔案。

## 更新日誌

### v0.2.0 (2025-06-03)
- ✨ 新增即時監測功能
- 📊 增強版 CSV 報告 (詳細統計、跳點分析)
- 📈 互動式 HTML 報告 (圖表、趨勢分析)
- 🔄 防止掃描重疊機制
- ⌨️ 改進 Ctrl+C 中斷處理
- 🎯 優化 nmap 命令參數
- 📋 添加跳點穩定性分析

### v0.1.0 (2025-06-03)
- 初始版本發布
- 支援 TCP/UDP traceroute
- CSV 和 HTML 輸出功能
- 批量掃描支援
- 美觀的表格顯示

## 相關連結

- [nmap 官方網站](https://nmap.org/)
- [專案架構文件](PROJECT_ARCHITECTURE.md)
- [使用範例](examples/)

---

如有問題或建議，歡迎提出 Issue 或 Pull Request！