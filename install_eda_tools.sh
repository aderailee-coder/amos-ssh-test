#!/bin/bash
# Ader-Ai Fleet - Phase 3 安裝腳本
# 支援 Ubuntu（VPS）與 macOS（Mac M4）

set -e

echo "=== Ader-Ai Fleet EDA LLM 環境安裝 ==="

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "[VPS] 偵測到 Ubuntu/Debian"
    sudo apt update
    sudo apt install -y yosys verilator gtkwave python3 python3-pip
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "[Mac] 偵測到 macOS"
    if ! command -v brew &> /dev/null; then
        echo "請先安裝 Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    brew install yosys verilator gtkwave
else
    echo "不支援的作業系統"
    exit 1
fi

echo "✅ EDA 工具安裝完成"
echo "請確認 Ollama 模型已就緒：ollama list"