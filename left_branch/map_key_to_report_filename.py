import glob
import os


def map_key_to_report_filename(
    fund_code: str, end_date: str, report_type_id: int, text_dir: str
) -> str:
  """根据基金代码、截止日期和 ReportTypeID，

  精准映射并寻找右侧文件夹中对应的文本文件名（支持 HY/FY/Q1/Q2 规则）。
  """
  year = end_date.split("-")[0]

  # 1. 建立 ReportTypeID 到文本后缀的确定性映射表
  # 1-Q1, 2-Q2, 3-Q3, 4-Q4, 5-HY(半年度), 6-FY(年度)
  type_to_suffix = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4", 5: "HY", 6: "FY"}

  suffix = type_to_suffix.get(report_type_id, "Q2")  # 默认兜底

  # 2. 构造文件名匹配模式 (例如: 004890_2026HY_*.txt)
  pattern = os.path.join(text_dir, f"{fund_code}_{year}{suffix}_*.txt")
  matched_files = glob.glob(pattern)

  # 特殊兼容处理：如果 12-31 的 ReportTypeID 是 4（四季报），有的文件可能叫 FY 或者是 Q4
  if not matched_files and report_type_id == 4:
    alt_pattern = os.path.join(text_dir, f"{fund_code}_{year}FY_*.txt")
    matched_files = glob.glob(alt_pattern)

  if matched_files:
    return matched_files[0]  # 返回找到的第一个匹配文本文件绝对路径
  else:
    return None  # 未找到对应文本