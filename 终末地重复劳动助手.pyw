import os
import sys
import subprocess

# 获取当前脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
# 切换到程序目录
os.chdir(script_dir)
# 运行主程序
subprocess.run([sys.executable, "main.py"])