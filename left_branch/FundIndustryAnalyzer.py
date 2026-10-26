import pandas as pd
import numpy as np
from typing import List, Dict, Any

class FundIndustryAnalyzer:
    """
    全市场解耦矩阵化——基金全仓行业持仓分析类
    自动打破 P0207/P0208/P0209 隔离，实现境内外互补拼图资产的真正全仓矩阵聚合。
    """
    def __init__(self, df: pd.DataFrame):
        """
        全量加载并执行强类型清洗
        """
        temp_df = df.copy()
        
        # 1. 强转类型，防止前导零丢失与空格干扰
        temp_df["MasterFundCode"] = temp_df["MasterFundCode"].astype(str).str.zfill(6)
        temp_df["EndDate"] = temp_df["EndDate"].astype(str).str.strip()
        
        # 2. 核心清洗：彻底剔除所有系统自带的“合计”行（因为我们要跨系统自己算真正的全仓合计）
        self.clean_df = temp_df[temp_df["IndustryName"] != "合计"].copy()
        
        # 3. 数值类型矩阵化对齐
        self.clean_df["FairValue"] = pd.to_numeric(self.clean_df["FairValue"], errors='coerce').fillna(0.0)
        self.clean_df["FairValueToNAV"] = pd.to_numeric(self.clean_df["FairValueToNAV"], errors='coerce').fillna(0.0)

    def calc_all_metrics_vectorized(self) -> pd.DataFrame:
        """
        打破系统分类边界的【全仓纯矩阵向量化计算】
        """
        df = self.clean_df.copy()
        if df.empty:
            return pd.DataFrame()

        group_keys = ["MasterFundCode", "EndDate", "ReportTypeID"]

        # 1. 计算全仓 HHI 分散度指数
        df["Total_Stock_Value"] = df.groupby(group_keys)["FairValue"].transform("sum")
        df["Stock_Weight"] = np.where(df["Total_Stock_Value"] > 0, df["FairValue"] / df["Total_Stock_Value"], 0.0)
        df["Weight_Sq"] = df["Stock_Weight"] ** 2
        hhi_df = df.groupby(group_keys)["Weight_Sq"].sum().reset_index(name="HHI分散度指数")

        # 2. 计算行业集中度与真实总股仓
        df["Rank"] = df.groupby(group_keys)["FairValueToNAV"].rank(method="first", ascending=False)
        
        df["Value_Top3"] = np.where(df["Rank"] <= 3, df["FairValueToNAV"], 0.0)
        df["Value_Top5"] = np.where(df["Rank"] <= 5, df["FairValueToNAV"], 0.0)
        
        conc_df = df.groupby(group_keys).agg(
            Top3行业集中度=("Value_Top3", "sum"),
            Top5行业集中度=("Value_Top5", "sum"),
            真实总股仓NAV占比=("FairValueToNAV", "sum")
        ).reset_index()

        # 3. 提取第一重仓行业
        top1_df = df[df["Rank"] == 1][group_keys + ["IndustryName", "FairValueToNAV"]].copy()
        top1_df = top1_df.rename(columns={"IndustryName": "第一重仓行业", "FairValueToNAV": "第一重仓占比"})

        summary_df = top1_df.merge(conc_df, on=group_keys, how="left")
        summary_df = summary_df.merge(hhi_df, on=group_keys, how="left")

        return summary_df.sort_values(by=group_keys).reset_index(drop=True)

    def calc_industry_turnover_detail(self, top_change_n: int = None) -> pd.DataFrame:
        """
        全矩阵向量化计算：独立输出行业调仓环比变动明细大表
        """
        df = self.clean_df.copy()
        if df.empty:
            return pd.DataFrame()

        df["Type_Priority"] = np.where(df["ReportTypeID"] == 5, 2, np.where(df["ReportTypeID"] == 2, 1, 0))
        df["Max_Priority"] = df.groupby(["MasterFundCode", "EndDate"])["Type_Priority"].transform("max")
        df = df[df["Type_Priority"] == df["Max_Priority"]].copy()
        
        group_keys = ["MasterFundCode", "EndDate", "ReportTypeID"]

        timeline = df[group_keys].drop_duplicates().sort_values(by=["MasterFundCode", "EndDate"]).copy()
        timeline["Time_Seq"] = timeline.groupby("MasterFundCode").cumcount() + 1
        df = df.merge(timeline[group_keys + ["Time_Seq"]], on=group_keys, how="left")

        df_curr = df[group_keys + ["IndustryCode", "IndustryName", "FairValueToNAV", "Time_Seq"]].copy()
        df_curr = df_curr.rename(columns={"FairValueToNAV": "Curr_Weight_NAV"})
        
        df_prev = df[["MasterFundCode", "IndustryName", "FairValueToNAV", "Time_Seq"]].copy()
        df_prev["Time_Seq"] = df_prev["Time_Seq"] + 1  
        df_prev = df_prev.rename(columns={"FairValueToNAV": "Prev_Weight_NAV"})

        df_diff = df_curr.merge(df_prev, on=["MasterFundCode", "IndustryName", "Time_Seq"], how="outer")
        df_diff = df_diff.sort_values(by=["MasterFundCode", "Time_Seq"])
        
        df_diff["MasterFundCode"] = df_diff["MasterFundCode"].ffill().bfill()
        df_diff["EndDate"] = df_diff.groupby(["MasterFundCode", "Time_Seq"])["EndDate"].transform(lambda x: x.ffill().bfill())
        df_diff["ReportTypeID"] = df_diff.groupby(["MasterFundCode", "Time_Seq"])["ReportTypeID"].transform(lambda x: x.ffill().bfill())
        
        df_diff["Curr_Weight_NAV"] = df_diff["Curr_Weight_NAV"].fillna(0.0)
        df_diff["Prev_Weight_NAV"] = df_diff["Prev_Weight_NAV"].fillna(0.0)
        
        df_diff["Weight_Change_Pct"] = df_diff["Curr_Weight_NAV"] - df_diff["Prev_Weight_NAV"]
        df_diff["Abs_Change"] = df_diff["Weight_Change_Pct"].abs()

        df_diff["Is_First_Period"] = df_diff.groupby("MasterFundCode")["Time_Seq"].transform("min") == df_diff["Time_Seq"]
        df_diff = df_diff[~df_diff["Is_First_Period"]].copy()

        df_diff["Change_Rank"] = df_diff.groupby(group_keys)["Abs_Change"].rank(method="first", ascending=False)

        if top_change_n is not None:
            df_diff = df_diff[df_diff["Change_Rank"] <= top_change_n].copy()

        output_cols = [
            "MasterFundCode", "EndDate", "ReportTypeID", 
            "IndustryCode", "IndustryName", 
            "Prev_Weight_NAV", "Curr_Weight_NAV", "Weight_Change_Pct", "Change_Rank"
        ]
        
        df_diff["ReportTypeID"] = df_diff["ReportTypeID"].astype("Int64")
        df_diff["Change_Rank"] = df_diff["Change_Rank"].astype("Int64")
        
        result_df = df_diff.dropna(subset=["EndDate"])[output_cols].copy()
        return result_df.sort_values(by=["MasterFundCode", "EndDate", "Change_Rank"]).reset_index(drop=True)

    def calc_master_panel_matrix(self) -> pd.DataFrame:
        """
        🌟 升级版全景大宽表（绝对完备与防错版）：
        完美兼容基金初期（First Period）及各种缺失情形，同时计算：
        1. 第1-5重仓及集中度、HHI分散度
        2. Others 长尾调仓净变动（带正负号代数和）
        3. 现金调仓权重（大类现金资产环比变动额）
        4. 强力防错：以 base_summary 为主轴，确保所有复合 Key 矩阵在对齐时绝不丢失初始期（如 2025-12-31）
        """
        df = self.clean_df.copy()
        if df.empty:
            return pd.DataFrame()

        # 1. 报告期优先级清洗（中报优先）
        df["Type_Priority"] = np.where(df["ReportTypeID"] == 5, 2, np.where(df["ReportTypeID"] == 2, 1, 0))
        df["Max_Priority"] = df.groupby(["MasterFundCode", "EndDate"])["Type_Priority"].transform("max")
        df = df[df["Type_Priority"] == df["Max_Priority"]].copy()

        group_keys = ["MasterFundCode", "EndDate"]

        # 2. 计算基础静态指标 (HHI, 真实总股仓, 集中度)
        df["Total_Stock_Value"] = df.groupby(group_keys + ["ReportTypeID"])["FairValue"].transform("sum")
        df["Stock_Weight"] = np.where(df["Total_Stock_Value"] > 0, df["FairValue"] / df["Total_Stock_Value"], 0.0)
        df["Weight_Sq"] = df["Stock_Weight"] ** 2
        hhi_df = df.groupby(group_keys)["Weight_Sq"].sum().reset_index(name="HHI分散度指数")

        df["Rank"] = df.groupby(group_keys + ["ReportTypeID"])["FairValueToNAV"].rank(method="first", ascending=False)
        
        df["Value_Top3"] = np.where(df["Rank"] <= 3, df["FairValueToNAV"], 0.0)
        df["Value_Top5"] = np.where(df["Rank"] <= 5, df["FairValueToNAV"], 0.0)
        
        conc_df = df.groupby(group_keys).agg(
            Top3行业集中度=("Value_Top3", "sum"),
            Top5行业集中度=("Value_Top5", "sum"),
            真实总股仓NAV占比=("FairValueToNAV", "sum")
        ).reset_index()

        # 3. 提取 Top 1 ~ 5 重仓行业及占比
        top_n_frames = []
        for i in range(1, 6):
            t_df = df[df["Rank"] == i][group_keys + ["IndustryName", "FairValueToNAV"]].copy()
            t_df = t_df.rename(columns={
                "IndustryName": f"第{i}重仓行业", 
                "FairValueToNAV": f"第{i}重仓占比"
            })
            t_df = t_df.drop_duplicates(subset=group_keys)
            top_n_frames.append(t_df)

        base_summary = conc_df.merge(hhi_df, on=group_keys, how="left")
        for t_df in top_n_frames:
            base_summary = base_summary.merge(t_df, on=group_keys, how="left")

        # 4. 计算 Others 占比与现金占比
        top5_cols = [f"第{i}重仓占比" for i in range(1, 6)]
        for col in top5_cols:
            if col not in base_summary.columns:
                base_summary[col] = 0.0
        
        top5_sum = base_summary[top5_cols].fillna(0).sum(axis=1)
        base_summary["Others占比"] = (base_summary["真实总股仓NAV占比"] - top5_sum).clip(lower=0.0)
        base_summary["现金及其他资产占比"] = (100.0 - base_summary["真实总股仓NAV占比"]).clip(lower=0.0)

        # 5. 提取动态调仓前 5 行业、Others 净变动 及 现金调仓权重（以 base_summary 为基准循环，绝不漏期）
        df_diff_all = self._get_raw_turnover_diff_df() 
        turnover_pivoted_records = []

        # 预先计算现金序列的差分
        cash_series_df = base_summary[group_keys + ["现金及其他资产占比"]].copy()
        cash_series_df = cash_series_df.sort_values(by=["MasterFundCode", "EndDate"])
        cash_series_df["Prev_Cash"] = cash_series_df.groupby("MasterFundCode")["现金及其他资产占比"].shift(1)
        cash_series_df["现金调仓权重"] = (cash_series_df["现金及其他资产占比"] - cash_series_df["Prev_Cash"]).fillna(0.0)
        cash_dict = cash_series_df.set_index(["MasterFundCode", "EndDate"])["现金调仓权重"].to_dict()

        for _, b_row in base_summary.iterrows():
            f_code = b_row["MasterFundCode"]
            e_date = b_row["EndDate"]
            record = {
                "MasterFundCode": f_code, 
                "EndDate": e_date,
                "others调仓权重": 0.0,
                "现金调仓权重": round(cash_dict.get((f_code, e_date), 0.0), 4)
            }
            
            for idx in range(1, 6):
                record[f"第{idx}调仓行业"] = None
                record[f"第{idx}调仓占比"] = None

            if not df_diff_all.empty:
                match_group = df_diff_all[
                    (df_diff_all["MasterFundCode"] == f_code) & 
                    (df_diff_all["EndDate"] == e_date)
                ]
                if not match_group.empty:
                    is_first = match_group["Is_First_Period"].any() if "Is_First_Period" in match_group.columns else False
                    if not is_first:
                        valid_group = match_group[~match_group["Is_First_Period"]].copy() if "Is_First_Period" in match_group.columns else match_group
                        sorted_group = valid_group.sort_values(by="Change_Rank")
                        for idx, (_, row) in enumerate(sorted_group.iterrows(), start=1):
                            if idx <= 5:
                                record[f"第{idx}调仓行业"] = row["IndustryName"]
                                record[f"第{idx}调仓占比"] = row["Weight_Change_Pct"]
                        
                        total_net_change = valid_group["Weight_Change_Pct"].sum()
                        top5_net_change = valid_group[valid_group["Change_Rank"] <= 5]["Weight_Change_Pct"].sum()
                        record["others调仓权重"] = round(total_net_change - top5_net_change, 4)

            turnover_pivoted_records.append(record)

        df_turnover_wide = pd.DataFrame(turnover_pivoted_records)

        # 6. 最终大合并：静态特征 + 动态调仓宽表
        if not df_turnover_wide.empty:
            final_master_df = base_summary.merge(df_turnover_wide, on=group_keys, how="left")
        else:
            final_master_df = base_summary

        return final_master_df.sort_values(by=group_keys).reset_index(drop=True)


    def _get_raw_turnover_diff_df(self) -> pd.DataFrame:
        """
        内部辅助方法：保留 Is_First_Period 标识的原始时序差分大表
        """
        df = self.clean_df.copy()
        if df.empty:
            return pd.DataFrame()

        df["Type_Priority"] = np.where(df["ReportTypeID"] == 5, 2, np.where(df["ReportTypeID"] == 2, 1, 0))
        df["Max_Priority"] = df.groupby(["MasterFundCode", "EndDate"])["Type_Priority"].transform("max")
        df = df[df["Type_Priority"] == df["Max_Priority"]].copy()
        
        group_keys = ["MasterFundCode", "EndDate", "ReportTypeID"]

        timeline = df[group_keys].drop_duplicates().sort_values(by=["MasterFundCode", "EndDate"]).copy()
        timeline["Time_Seq"] = timeline.groupby("MasterFundCode").cumcount() + 1
        df = df.merge(timeline[group_keys + ["Time_Seq"]], on=group_keys, how="left")

        df_curr = df[group_keys + ["IndustryCode", "IndustryName", "FairValueToNAV", "Time_Seq"]].copy()
        df_curr = df_curr.rename(columns={"FairValueToNAV": "Curr_Weight_NAV"})
        
        df_prev = df[["MasterFundCode", "IndustryName", "FairValueToNAV", "Time_Seq"]].copy()
        df_prev["Time_Seq"] = df_prev["Time_Seq"] + 1  
        df_prev = df_prev.rename(columns={"FairValueToNAV": "Prev_Weight_NAV"})

        df_diff = df_curr.merge(df_prev, on=["MasterFundCode", "IndustryName", "Time_Seq"], how="outer")
        df_diff = df_diff.sort_values(by=["MasterFundCode", "Time_Seq"])
        
        df_diff["MasterFundCode"] = df_diff["MasterFundCode"].ffill().bfill()
        df_diff["EndDate"] = df_diff.groupby(["MasterFundCode", "Time_Seq"])["EndDate"].transform(lambda x: x.ffill().bfill())
        df_diff["ReportTypeID"] = df_diff.groupby(["MasterFundCode", "Time_Seq"])["ReportTypeID"].transform(lambda x: x.ffill().bfill())
        
        df_diff["Curr_Weight_NAV"] = df_diff["Curr_Weight_NAV"].fillna(0.0)
        df_diff["Prev_Weight_NAV"] = df_diff["Prev_Weight_NAV"].fillna(0.0)
        
        df_diff["Weight_Change_Pct"] = df_diff["Curr_Weight_NAV"] - df_diff["Prev_Weight_NAV"]
        df_diff["Abs_Change"] = df_diff["Weight_Change_Pct"].abs()

        df_diff["Is_First_Period"] = df_diff.groupby("MasterFundCode")["Time_Seq"].transform("min") == df_diff["Time_Seq"]
        
        non_first_mask = ~df_diff["Is_First_Period"]
        if non_first_mask.any():
            df_diff.loc[non_first_mask, "Change_Rank"] = df_diff[non_first_mask].groupby(group_keys)["Abs_Change"].rank(method="first", ascending=False)
        
        return df_diff.dropna(subset=["EndDate"]).copy()


    def export_results(self, output_dir: str = "/Users/solaartemis/Hypocrisies/output/data", top_change_n: int = 5):
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        static_board = self.calc_all_metrics_vectorized()
        turnover_detail = self.calc_industry_turnover_detail(top_change_n=top_change_n)
        master_panel = self.calc_master_panel_matrix()
        
        file_name = "基金行业持仓及调仓全量矩阵看板.xlsx"
        full_excel_path = os.path.join(output_dir, file_name)
        
        with pd.ExcelWriter(full_excel_path, engine="openpyxl") as writer:
            static_board.to_excel(writer, sheet_name="全仓行业持仓静态看板", index=False)
            turnover_detail.to_excel(writer, sheet_name=f"时序调仓绝对值前{top_change_n}明细", index=False)
            if not master_panel.empty:
                master_panel.to_excel(writer, sheet_name="基金时序宽表大盘", index=False)
            
        print(f"🎉 导出成功！最新大盘宽表已沉淀至：\n🔗 {full_excel_path}\n")

    def export_to_json_fact(self, top_n: int = 5) -> dict:
        turnover_df = self.calc_industry_turnover_detail(top_change_n=top_n)
        if turnover_df.empty:
            return {}

        structured_data = {}
        group_keys = ["MasterFundCode", "EndDate", "ReportTypeID"]
        for (fund_code, end_date, report_type_id), group in turnover_df.groupby(group_keys):
            key = f"{fund_code}_{end_date}_R{report_type_id}"
            actions = []
            for _, row in group.iterrows():
                change_val = row["Weight_Change_Pct"]
                if change_val > 0.5:
                    action_type = "加仓"
                elif change_val < -0.5:
                    action_type = "减仓"
                else:
                    action_type = "持平"

                actions.append({
                    "industry": row["IndustryName"],
                    "action_type": action_type,
                    "weight_change_pct": round(float(change_val), 2),
                    "change_rank": int(row["Change_Rank"])
                })

            structured_data[key] = {
                "fund_code": str(fund_code),
                "end_date": str(end_date),
                "report_type_id": int(report_type_id),
                "actual_actions": actions,
                "fact_summary": f"在 {end_date} 报告期，调仓最大的是 {actions[0]['industry']}（变动 {actions[0]['weight_change_pct']}%）"
            }
        return structured_data


if __name__ == "__main__":
    df = pd.read_csv('/Users/solaartemis/Hypocrisies/Say-Do-Gap-Project/data/processed/combined_fund_industry_class.csv')
    analyzer = FundIndustryAnalyzer(df)
    
    master_matrix = analyzer.calc_master_panel_matrix()
    print("\n==================== 🌟 基金宏观与调仓全景大宽表 🌟 ====================")
    print(master_matrix.head().to_string(index=False))
    
    OUTPUT_DIR = '/Users/solaartemis/Hypocrisies/Say-Do-Gap-Project/data/processed'
    analyzer.export_results(output_dir=OUTPUT_DIR, top_change_n=5)


    
    # 纯矩阵流并行运算
    full_board = analyzer.calc_all_metrics_vectorized()
    
    print("\n==================== ⚡️ 真正全仓(境内+境外拼图)行业持仓看板大表 ⚡️ ====================")
    print(full_board.to_string(index=False))

    
    # 2. 一键获取所有基金、所有时间点的“全量行业”调仓明细表
    turnover_detail_all = analyzer.calc_industry_turnover_detail()
    turnover_top3 = analyzer.calc_industry_turnover_detail(top_change_n=5)
    print("\n==================== ⚡️ 自由筛选视角：调仓绝对值前 3 异动明细大表 ⚡️ ====================")
    print(turnover_top3.to_string(index=False))
    
    # --- 💡 自由筛选示例展示 ---
    print("\n==================== 🔍 衍生操作：直接用 pandas 过滤出‘大举加仓(>4%)’的行业记录 ====================")
    heavy_buying = turnover_detail_all[turnover_detail_all["Weight_Change_Pct"] > 4.0]
    print(heavy_buying.to_string(index=False))


    structured_data = analyzer.export_to_json_fact()
    print('structured_data:\n',structured_data)
