import os
import glob
import pandas as pd

def filter_fund_data(
    file_path: str,
    target_funds: list,
    target_end_dates: list,
    target_report_types: list,
) -> pd.DataFrame:
    """【核心组件】负责单个 CSV 文件的精准筛选，类型自动对齐与防御"""
    try:
        # 1. 基础转换字典
        base_dtype = {
            "MasterFundCode": str,
            "ReportTypeID": str,
            "EndDate": str,
        }

        # 🤝【核心兼容逻辑】只读取第一行表头，动态判断是否追加 Symbol 列
        preview_df = pd.read_csv(file_path, nrows=0)
        if "Symbol" in preview_df.columns:
            base_dtype["Symbol"] = str  # 如果是股票明细文件，动态加入股票代码的强转，消灭警告

        # 2. 读取完整 CSV，加入 on_bad_lines='skip' 拯救因格式损坏而濒临跳过的文件
        df = pd.read_csv(
            file_path,
            dtype=base_dtype,
            on_bad_lines="skip",  # 遇到某一行列数不对（比如多出第13列）时自动跳过该行，不废掉整个文件
        )

        # 统一将入参转换成清洗后的字符串列表
        funds_str = [str(x).strip().zfill(6) for x in target_funds]
        dates_str = [str(x).strip() for x in target_end_dates]
        types_str = [str(x).strip() for x in target_report_types]

        # 多条件联合筛选
        condition = (
            df["MasterFundCode"].isin(funds_str)
            & df["EndDate"].isin(dates_str)
            & df["ReportTypeID"].isin(types_str)
        )

        return df[condition]

    except Exception as e:
        file_name = os.path.basename(file_path)
        print(
            f"  ❌ 报告主公，读取文件 [{file_name}] 时遇到绊脚石: {e}，已自动跳过。"
        )
        return pd.DataFrame()  # 出错时返回空表，确保主程序不崩溃




def batch_filter_and_save(
    input_folder: str,
    output_folder: str,
    output_filename: str,
    target_funds: list,
    target_end_dates: list,
    target_report_types: list,
):
    """【调度引擎】负责扫描文件夹、调用单文件筛选函数、合并并保存数据，并智能稽核缺失 Key"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"📁 发现目标目录不存在，已自动创建：{output_folder}")

    search_path = os.path.join(input_folder, "*.csv")
    csv_files = glob.glob(search_path)

    if not csv_files:
        print(f"⚠️ 警告：在路径 {input_folder} 下没有找到任何 CSV 文件！")
        return pd.DataFrame(), []

    print(f"🚀 发现 {len(csv_files)} 个文件，开始调用 `filter_fund_data` 进行解耦过滤...")

    all_filtered_dfs = []

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        filtered_df = filter_fund_data(
            file_path=file_path,
            target_funds=target_funds,
            target_end_dates=target_end_dates,
            target_report_types=target_report_types,
        )

        if not filtered_df.empty:
            all_filtered_dfs.append(filtered_df)
            print(f"  ✅ 文件 [{file_name}] 筛选成功，留存 {len(filtered_df)} 条数据。")
        else:
            print(f"  ⚪ 文件 [{file_name}] 扫描完毕，无匹配。")

    # 聚合战利品
    if all_filtered_dfs:
        final_df = pd.concat(all_filtered_dfs, ignore_index=True)
        final_output_path = os.path.join(output_folder, output_filename)
        
        # 导出为 CSV
        final_df.to_csv(final_output_path, index=False, encoding="utf-8-sig")
        print(f"\n🎉 报告主公！解耦批处理完成。总共聚合了 {len(final_df)} 条精华数据。")
        print(f"💾 最终文件已妥善保存至：{final_output_path}")
    else:
        final_df = pd.DataFrame()
        print("\n❌ 报告主公，所有文件翻遍了都没找到匹配数据，未生成文件。")

    # 🌟 核心升级：根据公募基金披露常识，建立“日期 $\rightarrow$ 合法报告类型”的智能映射
    expected_combinations = []
    for f in target_funds:
        for d in target_end_dates:
            # 根据季末月份自动锁定合法的报告类型编码
            if d.endswith("-03-31"):
                valid_types = ["1"]          # 一季报
            elif d.endswith("-06-30"):
                valid_types = ["2", "5"]     # 二季报 / 半年度
            elif d.endswith("-09-30"):
                valid_types = ["3"]          # 三季报
            elif d.endswith("-12-31"):
                valid_types = ["4", "6"]     # 四季报 / 年度
            else:
                valid_types = [str(t) for t in target_report_types]

            # 只有当该报告类型在用户传入的 target_report_types 范围内时才纳入预期比对
            for t in valid_types:
                if t in [str(x) for x in target_report_types]:
                    expected_combinations.append((str(f).zfill(6), str(d).strip(), str(t).strip()))

    if not final_df.empty:
        actual_combinations = set(
            zip(
                final_df["MasterFundCode"].astype(str).str.zfill(6),
                final_df["EndDate"].astype(str).str.strip(),
                final_df["ReportTypeID"].astype(str).str.strip()
            )
        )
    else:
        actual_combinations = set()

    missing_keys = [
        {"fund_code": f, "end_date": d, "report_type_id": t, "composite_key": f"{f}_{d}_R{t}"}
        for (f, d, t) in expected_combinations
        if (f, d, t) not in actual_combinations
    ]

    # 打印精简、规范的缺失清单
    if missing_keys:
        print(f"\n⚠️ [数据稽核警告] 在 CSMAR 原始文件中共有 {len(missing_keys)} 个合规定期报告组合未检索到数据：")
        print(f"{'复合 Key (Composite Key)':<30} | {'基金代码':<10} | {'报告期':<12} | {'报告类型ID':<10}")
        print("-" * 72)
        for item in missing_keys:
            print(f"{item['composite_key']:<30} | {item['fund_code']:<10} | {item['end_date']:<12} | {item['report_type_id']:<10}")
        print("-" * 72)
    else:
        print("\n✅ [数据稽核] 太棒了！所有合规报告期的预期组合均在原始文件中完美命中，无一遗漏。")

    return final_df, missing_keys

