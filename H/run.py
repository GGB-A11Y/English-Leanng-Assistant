"""后端一键启动入口:在 PyCharm 中右键本文件 → 运行,或在终端执行 `python run.py`。

等价于在 H 目录执行:
    uvicorn app.main:app --host 127.0.0.1 --port 8000
"""
import os
import sys

# 无论从哪里运行,都固定以本文件所在目录(H)为基准
H_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(H_DIR)
sys.path.insert(0, H_DIR)
import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
