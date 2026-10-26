import os
import glob
import pandas as pd
import os
import sys
import glob
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 这样就能完美导入了！
from left_branch.FundIndustryAnalyzer import FundIndustryAnalyzer

class SayDoPanelDataProcessor:
    """
    Say-Do 评判面板与持仓特征大表的融合处理器：
    负责提取基金经理姓名、关联 master_matrix、构建 [基金经理, 基金代码, EndDate] 复合索引。
    """
    def __init__(
        self,
        panel_csv_path: str = "data/processed/say_do_gap_panel_data.csv",
        text_dir: str = "data/raw/quarterly_reports/oper_text",
        master_matrix_df: pd.DataFrame = None
    ):
        self.panel_csv_path = panel_csv_path
        self.text_dir = text_dir
        self.master_matrix_df = master_matrix_df

    def _extract_manager_name(self, fund_code: str) -> str:
        """
        通过基金代码去 oper_text 目录下匹配对应的 txt 文件名，
        例如: 000457_2025FY_李博.txt -> 提取出 "李博"
        """
        if not os.path.exists(self.text_dir):
            return str(fund_code)
        
        # 匹配以该基金代码开头的任意报告期文本
        pattern = os.path.join(self.text_dir, f"{str(fund_code).zfill(6)}_*_*.txt")
        matched_files = glob.glob(pattern)
        
        if matched_files:
            # 取第一个匹配的文件名进行解析
            file_name = os.path.basename(matched_files[0])
            name_part = file_name.replace(".txt", "")
            parts = name_part.split("_")
            if len(parts) >= 3:
                return parts[-1]  # 获取最后一段作为基金经理姓名
                
        return str(fund_code) # 找不到则兜底返回基金代码

    def build_final_display_table(self) -> pd.DataFrame:
        """
        核心处理方法（已加固：以 master_matrix 全量持仓为左底座，完美保留 1231 初始期）：
        1. 以 df_master（底层全景事实大表，含 1231）为主表。
        2. 左连接 say_do_gap_panel_data.csv 获得大模型评判结果。
        3. 对缺失大模型得分的首期自动填充默认初始态。
        4. 设置复合索引：[基金经理, 基金代码, 报告期]
        """
        # 1. 如果有 master_matrix，以它作为绝对底座
        if self.master_matrix_df is not None and not self.master_matrix_df.empty:
            df_master = self.master_matrix_df.copy()
            df_master["MasterFundCode"] = df_master["MasterFundCode"].astype(str).str.zfill(6)
            df_master["EndDate"] = df_master["EndDate"].astype(str).str.strip()

            # 动态注入基金经理姓名
            print("🔍 正在从文本路径提取基金经理姓名...")
            df_master["基金经理"] = df_master["MasterFundCode"].apply(self._extract_manager_name)

            # 2. 读取言行不一评判面板数据
            df_panel = pd.DataFrame()
            if os.path.exists(self.panel_csv_path):
                df_panel = pd.read_csv(self.panel_csv_path)
                df_panel["MasterFundCode"] = df_panel["MasterFundCode"].astype(str).str.zfill(6)
                df_panel["EndDate"] = df_panel["EndDate"].astype(str).str.strip()

            # 3. 🌟 核心修正：以持仓大表 df_master 为主表（Left Join），确保 1231 初始期绝对不丢失！
            if not df_panel.empty:
                df_merged = pd.merge(
                    df_master, 
                    df_panel, 
                    on=["MasterFundCode", "EndDate"], 
                    how="left"
                )
            else:
                df_merged = df_master.copy()
        else:
            if os.path.exists(self.panel_csv_path):
                df_merged = pd.read_csv(self.panel_csv_path)
                df_merged["MasterFundCode"] = df_merged["MasterFundCode"].astype(str).str.zfill(6)
                df_merged["EndDate"] = df_merged["EndDate"].astype(str).str.strip()
            else:
                print(f"[错误] 未找到 Panel 评判大表: {self.panel_csv_path}")
                return pd.DataFrame()

        # 4. 对像 1231 这样没有大模型评判记录的首期，进行安全的默认值填充
        df_merged["overall_sentiment"] = df_merged.get("overall_sentiment", pd.Series()).fillna("中性(初始期)")
        df_merged["consistency_score"] = pd.to_numeric(df_merged.get("consistency_score", pd.Series()), errors="coerce").fillna(0.0)
        df_merged["gap_type"] = df_merged.get("gap_type", pd.Series()).fillna("初始基准期")
        df_merged["diagnostic_summary"] = df_merged.get("diagnostic_summary", pd.Series()).fillna("初始基准期，暂无摘要")
        df_merged["challenge_question"] = df_merged.get("challenge_question", pd.Series()).fillna("初始基准期，无上一期可作言行对比，仅展示底层持仓事实。")

        # 5. 重命名和规范化列名以方便展示
        df_merged = df_merged.rename(columns={
            "MasterFundCode": "基金代码",
            "EndDate": "报告期",
            "overall_sentiment": "总体情绪",
            "consistency_score": "一致性得分",
            "gap_type": "偏差类型",
            "diagnostic_summary": "诊断摘要"
        })

        # 6. 确保“报告期”字段存在（防止后续 visualizer 报错找不到 '报告期'）
        if "报告期" not in df_merged.columns and "EndDate" in df_merged.columns:
            df_merged["报告期"] = df_merged["EndDate"]

        # 7. 设置多级复合索引 [基金经理, 基金代码, 报告期]
        if {"基金经理", "基金代码", "报告期"}.issubset(df_merged.columns):
            df_merged = df_merged.set_index(["基金经理", "基金代码", "报告期"])

        return df_merged

    def build_final_display_table(self) -> pd.DataFrame:
        """
        核心处理方法：
        1. 读取 say_do_gap_panel_data.csv
        2. 动态注入“基金经理”列
        3. 与 master_matrix 按照 [MasterFundCode, EndDate] 进行横向合并
        4. 设置复合索引：[基金经理, 基金代码, EndDate]
        """
        if not os.path.exists(self.panel_csv_path):
            print(f"[错误] 未找到 Panel 评判大表: {self.panel_csv_path}")
            return pd.DataFrame()

        # 1. 读取言行不一评判面板数据
        df_panel = pd.read_csv(self.panel_csv_path)
        df_panel["MasterFundCode"] = df_panel["MasterFundCode"].astype(str).str.zfill(6)
        df_panel["EndDate"] = df_panel["EndDate"].astype(str).str.strip()

        # 2. 提取并映射基金经理姓名
        print("🔍 正在从文本路径提取基金经理姓名...")
        df_panel["基金经理"] = df_panel["MasterFundCode"].apply(self._extract_manager_name)

        # 3. 如果传入了 master_matrix，则按 [MasterFundCode, EndDate] 联表合并
        if self.master_matrix_df is not None and not self.master_matrix_df.empty:
            df_master = self.master_matrix_df.copy()
            df_master["MasterFundCode"] = df_master["MasterFundCode"].astype(str).str.zfill(6)
            df_master["EndDate"] = df_master["EndDate"].astype(str).str.strip()

            # 左连接融合（保留所有 panel 评判记录）
            df_merged = df_panel.merge(
                df_master, 
                on=["MasterFundCode", "EndDate"], 
                how="left"
            )
        else:
            df_merged = df_panel.copy()

        # 4. 重命名和规范化列名以方便展示
        df_merged = df_merged.rename(columns={
            "MasterFundCode": "基金代码",
            "EndDate": "报告期",
            "overall_sentiment": "总体情绪",
            "consistency_score": "一致性得分",
            "gap_type": "偏差类型",
            "diagnostic_summary": "诊断摘要"
        })

        # 5. 设置多级复合索引 [基金经理, 基金代码, 报告期]
        if {"基金经理", "基金代码", "报告期"}.issubset(df_merged.columns):
            df_merged = df_merged.set_index(["基金经理", "基金代码", "报告期"])

        return df_merged


