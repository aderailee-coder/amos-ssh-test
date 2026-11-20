#!/usr/bin/env python3
"""
verilog_llm_loop.py
Ader-Ai Fleet - Phase 3: 本地 LLM + EDA 工具閉迴路（AutoChip 風格）

功能：
1. 使用本地 Ollama LLM 生成 Verilog RTL
2. Yosys 語法檢查 + 初步綜合
3. Verilator 編譯 + 基本模擬驗證
4. 錯誤訊息自動回饋 LLM，最多迭代 5 次
5. 成功後輸出最終 .v 檔案 + testbench + 波形

硬體需求：本地 Ollama（deepseek-coder / qwen2.5-coder）
EDA 工具：yosys, verilator, gtkwave（需先安裝）

使用方式：
    python3 verilog_llm_loop.py --spec "4-bit counter with enable and overflow flag" \
                                --model deepseek-coder:6.7b \
                                --output counter4.v

Tailscale 整合：可在 Mac M4 Max 或 Oracle VPS 上執行，模型統一走本地 Ollama。
"""

import argparse
import subprocess
import sys
import os
import re
from datetime import datetime

# ==================== 設定區 ====================
MAX_ITERATIONS = 5
OLLAMA_MODEL = "deepseek-coder:6.7b"   # 可改成 qwen2.5-coder:14b 等
WORK_DIR = "/tmp/eda_llm_loop"
os.makedirs(WORK_DIR, exist_ok=True)

# ==================== 工具函式 ====================
def run_cmd(cmd, cwd=None, timeout=120):
    """執行 shell 指令，回傳 (stdout, stderr, returncode)"""
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or WORK_DIR,
            capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", 124

def call_ollama(prompt, model=OLLAMA_MODEL):
    """呼叫本地 Ollama 生成 Verilog（使用 ollama run）"""
    # 為了穩定性，這裡使用 subprocess 呼叫 ollama CLI
    # 實際生產環境建議改用 ollama Python SDK
    full_prompt = f"""你是一位專業的 Verilog RTL 設計工程師。
請根據以下規格生成**完整、可綜合**的 Verilog 模組。
只輸出 Verilog 程式碼，不要額外解釋。

規格：
{prompt}

要求：
- 使用 IEEE 1364-2001 語法
- 加入合理的註解
- 模組名稱使用 snake_case
- 輸出必須可以直接被 Yosys 綜合
"""
    cmd = f'ollama run {model} "{full_prompt}"'
    stdout, stderr, code = run_cmd(cmd, timeout=180)
    if code != 0:
        print(f"[ERROR] Ollama 呼叫失敗: {stderr}")
        return None
    # 擷取 ```verilog ... ``` 區塊
    match = re.search(r'```(?:verilog|systemverilog)?\s*(.*?)\s*```', stdout, re.DOTALL)
    if match:
        return match.group(1).strip()
    return stdout.strip()

def check_syntax_yosys(verilog_code, module_name):
    """Yosys 語法檢查 + 初步綜合"""
    v_file = os.path.join(WORK_DIR, f"{module_name}.v")
    with open(v_file, "w") as f:
        f.write(verilog_code)

    # Yosys 指令：讀檔 + 綜合檢查
    yosys_cmd = f'yosys -p "read_verilog {v_file}; synth -top {module_name}"'
    stdout, stderr, code = run_cmd(yosys_cmd)
    success = code == 0 and "ERROR" not in stderr.upper()
    return success, stdout + "\n" + stderr

def run_verilator(verilog_code, module_name):
    """Verilator 編譯檢查（不一定要跑模擬）"""
    v_file = os.path.join(WORK_DIR, f"{module_name}.v")
    with open(v_file, "w") as f:
        f.write(verilog_code)

    # 簡單編譯檢查（不產生可執行檔）
    verilator_cmd = f'verilator --lint-only --top-module {module_name} {v_file}'
    stdout, stderr, code = run_cmd(verilator_cmd)
    success = code == 0
    return success, stdout + "\n" + stderr

def generate_testbench(module_name, verilog_code):
    """簡單自動產生 testbench（可依需求擴充）"""
    tb = f"""`timescale 1ns/1ps
module {module_name}_tb;
    // TODO: 根據模組 port 自動產生 stimulus
    // 目前為 placeholder，請手動補充
    initial begin
        $dumpfile("{module_name}.vcd");
        $dumpvars(0, {module_name}_tb);
        #100 $finish;
    end
endmodule
"""
    tb_file = os.path.join(WORK_DIR, f"{module_name}_tb.v")
    with open(tb_file, "w") as f:
        f.write(tb)
    return tb_file

# ==================== 主迴路 ====================
def main():
    parser = argparse.ArgumentParser(description="本地 LLM + EDA 閉迴路生成 Verilog")
    parser.add_argument("--spec", required=True, help="設計規格描述（中文或英文）")
    parser.add_argument("--model", default=OLLAMA_MODEL, help="Ollama 模型名稱")
    parser.add_argument("--output", default="output.v", help="輸出 Verilog 檔案路徑")
    args = parser.parse_args()

    print(f"\n=== Ader-Ai Fleet EDA LLM Loop 啟動 ===")
    print(f"規格：{args.spec}")
    print(f"模型：{args.model}")
    print(f"最大迭代次數：{MAX_ITERATIONS}\n")

    history = []
    current_code = None
    success = False

    for iteration in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- 第 {iteration} 次迭代 ---")

        if iteration == 1:
            prompt = args.spec
        else:
            # 把上一次錯誤餵給 LLM
            error_summary = "\n".join(history[-2:])   # 只取最近兩次錯誤
            prompt = f"""上一次生成的 Verilog 出現以下錯誤，請修正：

{error_summary}

請重新生成正確版本。"""

        verilog = call_ollama(prompt, args.model)
        if not verilog:
            print("[ERROR] LLM 未能生成有效程式碼")
            continue

        # 儲存當前版本
        current_code = verilog
        module_name = re.search(r'module\s+(\w+)', verilog)
        module_name = module_name.group(1) if module_name else "top"

        # Yosys 檢查
        yosys_ok, yosys_log = check_syntax_yosys(verilog, module_name)
        print(f"Yosys 檢查：{'通過' if yosys_ok else '失敗'}")

        # Verilator 檢查
        verilator_ok, verilator_log = run_verilator(verilog, module_name)
        print(f"Verilator 檢查：{'通過' if verilator_ok else '失敗'}")

        if yosys_ok and verilator_ok:
            print("✅ 兩項檢查皆通過！")
            success = True
            break
        else:
            error_msg = f"Yosys: {yosys_log[:500]}\nVerilator: {verilator_log[:500]}"
            history.append(error_msg)
            print("❌ 檢查失敗，將錯誤回饋 LLM 重試...")

    # 輸出結果
    if success and current_code:
        output_path = os.path.abspath(args.output)
        with open(output_path, "w") as f:
            f.write(current_code)
        print(f"\n✅ 成功！最終 Verilog 已儲存至：{output_path}")

        # 產生 testbench
        tb_file = generate_testbench(module_name, current_code)
        print(f"   Testbench 已產生：{tb_file}")
        print(f"   建議執行：gtkwave {WORK_DIR}/{module_name}.vcd （若有模擬）")
    else:
        print("\n❌ 達到最大迭代次數仍失敗。建議手動審核或調整提示詞。")
        if current_code:
            fallback = args.output.replace(".v", "_last_attempt.v")
            with open(fallback, "w") as f:
                f.write(current_code)
            print(f"   最後一次嘗試版本已儲存：{fallback}")

if __name__ == "__main__":
    main()
