# -*- coding: utf-8 -*-
import os
import sys
import time
import psutil

# Kích hoạt bảng mã UTF-8 cho Windows console
if sys.platform == "win32":
    os.system("chcp 65001 > nul")

def get_gpu_info():
    """Lấy thông tin GPU NVIDIA thông qua nvidia-smi nếu khả dụng"""
    try:
        import subprocess
        # Gọi nvidia-smi để lấy phần trăm sử dụng GPU và VRAM
        res = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,nounits,noheader"],
            universal_newlines=True
        )
        gpu_util, mem_used, mem_total = res.strip().split(",")
        return {
            "gpu_util": float(gpu_util.strip()),
            "vram_used": float(mem_used.strip()) / 1024.0,  # sang GB
            "vram_total": float(mem_total.strip()) / 1024.0,
            "available": True
        }
    except Exception:
        return {"available": False}

def find_deep_fake_process():
    """Tìm tiến trình CHAY_HE_THONG.py đang chạy"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info['cmdline']
            if cmd and any("CHAY_HE_THONG.py" in arg for arg in cmd):
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None

def main():
    try:
        while True:
            os.system("cls" if sys.platform == "win32" else "clear")
            print("=====================================================================")
            print("       BẢNG THEO DÕI HIỆU NĂNG HỆ THỐNG DEEP FAKE TIME-SERIES")
            print("=====================================================================")
            
            # 1. Trạng thái ứng dụng
            proc = find_deep_fake_process()
            if proc:
                print(f" [*] Trạng thái ứng dụng :   \033[92mĐANG HOẠT ĐỘNG (PID: {proc.pid})\033[0m")
                try:
                    cpu_percent = proc.cpu_percent(interval=0.1)
                    mem_info = proc.memory_info()
                    print(f"     └─ CPU tiêu thụ     :   {cpu_percent:.1f}%")
                    print(f"     └─ RAM tiêu thụ     :   {mem_info.rss / (1024*1024):.1f} MB")
                except Exception:
                    pass
            else:
                print(" [*] Trạng thái ứng dụng :   \033[91mĐANG DỪNG\033[0m")
            
            print("-" * 69)
            print(" TÀI NGUYÊN HỆ THỐNG CHUNG:")
            
            # 2. CPU chung
            cpu_usage = psutil.cpu_percent(interval=0.5)
            cpu_color = "\033[91m" if cpu_usage > 85 else ("\033[93m" if cpu_usage > 50 else "\033[92m")
            print(f" [CPU] Tổng số nhân     :   {psutil.cpu_count(logical=True)} Threads")
            print(f" [CPU] Mức sử dụng      :   {cpu_color}{cpu_usage:.1f}%\033[0m")
            
            # Thanh tiến trình CPU
            bar_len = 30
            filled_len = int(bar_len * cpu_usage / 100)
            bar = "█" * filled_len + "░" * (bar_len - filled_len)
            print(f"       [{bar}]")
            
            # 3. RAM chung
            ram = psutil.virtual_memory()
            ram_used_gb = ram.used / (1024**3)
            ram_total_gb = ram.total / (1024**3)
            ram_color = "\033[91m" if ram.percent > 85 else ("\033[93m" if ram.percent > 50 else "\033[92m")
            print(f" [RAM] Mức sử dụng      :   {ram_color}{ram_used_gb:.2f} GB / {ram_total_gb:.2f} GB ({ram.percent}%)\033[0m")
            
            ram_filled = int(bar_len * ram.percent / 100)
            ram_bar = "█" * ram_filled + "░" * (bar_len - ram_filled)
            print(f"       [{ram_bar}]")
            
            # 4. GPU & VRAM NVIDIA
            gpu = get_gpu_info()
            if gpu["available"]:
                gpu_color = "\033[91m" if gpu["gpu_util"] > 85 else ("\033[93m" if gpu["gpu_util"] > 50 else "\033[92m")
                print(f" [GPU] Mức sử dụng GPU  :   {gpu_color}{gpu['gpu_util']:.1f}%\033[0m")
                gpu_filled = int(bar_len * gpu["gpu_util"] / 100)
                gpu_bar = "█" * gpu_filled + "░" * (bar_len - gpu_filled)
                print(f"       [{gpu_bar}]")
                
                vram_percent = (gpu["vram_used"] / gpu["vram_total"]) * 100
                vram_color = "\033[91m" if vram_percent > 85 else ("\033[93m" if vram_percent > 50 else "\033[92m")
                print(f" [GPU] Dung lượng VRAM  :   {vram_color}{gpu['vram_used']:.2f} GB / {gpu['vram_total']:.2f} GB ({vram_percent:.1f}%)\033[0m")
            else:
                print(" [GPU] NVIDIA CUDA      :   \033[93mKhông phát hiện được GPU thông qua nvidia-smi\033[0m")
                
            print("=====================================================================")
            print(" Nhấn Ctrl+C để thoát theo dõi.")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n[*] Đã đóng chương trình giám sát.")

if __name__ == "__main__":
    main()
