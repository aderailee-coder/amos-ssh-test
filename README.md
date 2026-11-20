# Ader-Ai Fleet - Phase 3: 本地 LLM + EDA 閉迴路

**verilog_llm_loop.py**  
使用本地 Ollama LLM + Yosys + Verilator 自動生成、驗證、迭代修復 Verilog RTL。

## 快速啟動（Oracle VPS / Mac M4 Max）

### 1. 安裝相依工具
```bash
# Ubuntu / Debian（VPS）
sudo apt update
sudo apt install -y yosys verilator gtkwave

# macOS（MacBook Pro M4 Max）
brew install yosys verilator gtkwave
```

### 2. 確認 Ollama 模型已就緒
```bash
ollama list
# 推薦：
#   deepseek-coder:6.7b
#   qwen2.5-coder:14b
#   rtllcoder/deepseek-v1.1（若有）
```

### 3. 執行範例
```bash
cd ~/projects/eda-llm
python3 verilog_llm_loop.py \
    --spec "設計一個 4-bit up/down counter，具 enable 與 overflow flag" \
    --model deepseek-coder:6.7b \
    --output my_counter.v
```

### 4. 成功輸出
- `my_counter.v`：最終通過 Yosys + Verilator 檢查的 RTL
- 同目錄產生 testbench 與波形檔（.vcd）

## Tailscale 跨機協作建議
- 在 Mac M4 Max 上跑大型模型（33B）
- 在 Oracle VPS 上跑輕量模型 + EDA 工具
- 兩台機器皆可直接執行此腳本，模型走本地 Ollama

## 下一步擴充建議
- 加入更完整的 testbench 自動生成（依 port 產生 stimulus）
- 整合 OpenROAD（實體設計）
- 建立 cron job 定期掃描內部 repo 產生優化建議

「雲端大腦 + 本地鐵拳 = 財富自由加速器」