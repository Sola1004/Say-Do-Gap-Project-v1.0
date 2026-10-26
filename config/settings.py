# -*- coding: utf-8 -*-
"""
项目全局系统配置
"""

# Say-Do-Gap-Project/config/settings.py
import os
import sys
import glob
import json
from pathlib import Path
from typing import List, Dict, Any

# 第三方科学计算与数据处理
import pandas as pd
import numpy as np

# 可视化与 IPython 交互
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from IPython.display import display, HTML

# 官方 Google GenAI SDK（用于语义对齐与大模型审计）
from google import genai
from google.genai import types

GEMINI_API_KEY ='Your_API_KEY'
#export GEMINI_API_KEY='Your_API_KEY'

# 1. 自动计算项目根目录（从 config 文件夹往上一级即为根目录）
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

# 2. 自动注册到环境变量 sys.path 中
if project_root not in sys.path:
  sys.path.insert(0, project_root)  # 用 insert(0, ...) 确保优先级最高

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据相关路径
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DATA_PATH = os.path.join(
    DATA_DIR, "processed", "combined_fund_industry_class.csv"
)
TEXT_DIR = os.path.join(DATA_DIR, "raw", "quarterly_reports", "oper_text")
IND_DIR = str(Path(__file__).resolve().parent.parent / "data" / "raw" / "quantitative_market" / "按行业分类的股票投资组合文件")

# 中间态与输出路径
INTERMEDIATE_DIR = os.path.join(DATA_DIR, "intermediate")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "data", "processed")
DETAILS_JSON_DIR = os.path.join(INTERMEDIATE_DIR, "alignment_details")
OUTPUT_PANEL_CSV = os.path.join(
    DATA_DIR, "processed", "say_do_gap_panel_data.csv"
)
FILTERD_INDUSTRY_FILENAME = "combined_fund_industry_class.csv"

# 默认主模型（选用最新的轻量高效主力模型）
DEFAULT_MODEL = "models/gemini-2.5-flash"

# 多模型自动轮换降级池（按优先级从高到低排列，专用于文本/结构化 JSON 解析）
FALLBACK_MODELS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
    "models/gemini-3.7-flash",
    "models/gemini-3.6-flash",
    "models/gemini-3.5-flash",
    "models/gemini-3.8-flash",
    "models/gemini-3.1-pro-preview",
]


