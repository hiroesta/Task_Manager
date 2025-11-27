# config.py
import os
from pathlib import Path
from openai import OpenAI

# 使用するモデル名
MODEL_NAME = "gpt-4.1-mini"

# 会議中での自分の呼ばれ方
USER_ALIASES = ["永井", "永井くん"]

# 出力ルートフォルダ
OUTPUT_ROOT = Path("output")

# OpenAI クライアント
# 環境変数 OPENAI_API_KEY に APIキーを設定しておくこと
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
