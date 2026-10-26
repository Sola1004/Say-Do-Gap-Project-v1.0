# /Users/solaartemis/Hypocrisies/Say-Do-Gap-Project/main.py
import json
import os
import time
from pathlib import Path
import pandas as pd
from google import genai
from google.genai import types

# 引入全局配置
from config import settings
from left_branch.FundIndustryAnalyzer import FundIndustryAnalyzer
from left_branch.map_key_to_report_filename import map_key_to_report_filename
from left_branch.filter import batch_filter_and_save  # 🌟 引入解耦后的过滤函数
from right_branch.agent1_feature import Agent1Feature
from core_engine.comparator import COMPARATOR

def call_gemini_with_rotation(client, contents, config, max_retries_per_model=2):
    """
    智能多模型轮换与重试调用函数：
    - 优先使用 settings.DEFAULT_MODEL
    - 若遇到 503 过载，进行指数退避重试
    - 若遇到配额耗尽（RESOURCE_EXHAUSTED / 429 / exhausted），自动切换到下一个备用模型
    """
    # 构造模型尝试队列：以 DEFAULT_MODEL 打头，后面跟上 FALLBACK_MODELS 中不重复的模型
    models_to_try = [settings.DEFAULT_MODEL]
    if hasattr(settings, "FALLBACK_MODELS"):
        for m in settings.FALLBACK_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

    for model_idx, current_model in enumerate(models_to_try):
        delay = 3
        for attempt in range(max_retries_per_model):
            try:
                # print(f"🤖 正在尝试调用模型: [{current_model}] (尝试 {attempt + 1}/{max_retries_per_model})")
                response = client.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=config
                )
                return response
            except Exception as e:
                err_str = str(e)
                # 1. 触发 503 过载限流：同模型内重试
                if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                    if attempt < max_retries_per_model - 1:
                        print(f"⚠️ [{current_model}] 触发 503 过载，等待 {delay} 秒后重试...")
                        time.sleep(delay)
                        delay *= 2
                        continue
                
                # 2. 触发配额耗尽 / 额度超限 (Quota Exhausted / 429)：直接切换到下一个模型
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "exhausted" in err_str.lower():
                    print(f"🛑 [{current_model}] 触发配额耗尽 (Exhausted/429)。")
                    break  # 跳出当前模型的重试循环，进入外层切换下一个模型
                
                # 其他未知错误如果是最后一次尝试，则向上抛出
                if attempt == max_retries_per_model - 1 and model_idx == len(models_to_try) - 1:
                    raise e
                else:
                    print(f"⚠️ [{current_model}] 调用出错: {err_str}，准备切换/重试...")
                    break

        if model_idx < len(models_to_try) - 1:
            next_model = models_to_try[model_idx + 1]
            print(f"🔄 正在无缝切换至备用模型: [{next_model}]...")
            time.sleep(2)

    raise RuntimeError("❌ 致命错误：所有备用模型的调用额度均已耗尽或请求失败！")



def run_say_do_pipeline(
    target_funds: list,
    target_end_dates: list,
    target_report_types: list,
    input_folder: str = settings.IND_DIR,
    output_folder: str = settings.PROCESSED_DIR,
    output_filename: str = settings.FILTERD_INDUSTRY_FILENAME ,
    text_dir: str = settings.TEXT_DIR,
    details_json_folder: str = settings.DETAILS_JSON_DIR,
    output_panel_csv: str = settings.OUTPUT_PANEL_CSV,
    target_keys: list = None,
    skip_existing: bool = True,  # 🌟 新增参数：True 表示跳过已处理过的 Key，False 表示强制重新跑批覆盖
):
  print("==================================================")
  print(f"🚀 启动 Say-Do Gap 全链路自动化对齐流水线 (跳过已存在模式: {skip_existing})...")
  print("==================================================")



  # 1. 初始化客户端
  client = genai.Client()

  # 2. 自动化确保输出目录存在
  os.makedirs(details_json_folder, exist_ok=True)
  os.makedirs(output_folder, exist_ok=True)
  os.makedirs(os.path.dirname(output_panel_csv), exist_ok=True)

  # 3. 调用 filter 模块扫描并清洗原始持仓数据（接收返回的大表与智能稽核缺失列表）
  print(f"\n[左侧分支] 正在调用 filter 模块扫描并清洗原始持仓数据...")
  df_holding, missing_keys = batch_filter_and_save(
      input_folder=input_folder,
      output_folder=output_folder,
      output_filename=output_filename,
      target_funds=target_funds,
      target_end_dates=target_end_dates,
      target_report_types=target_report_types,
  )

  #   把精准的 missing_keys 存起来
  audit_json_path = os.path.join(output_folder, "missing_keys_audit.json")
  with open(audit_json_path, "w", encoding="utf-8") as f:
    json.dump(missing_keys, f, ensure_ascii=False, indent=4)
  print(f"📋 审计稽核清单已独立归档至：{audit_json_path}") 

  if df_holding is None or df_holding.empty:
    print("[错误] 过滤后得到的持仓数据为空，流水线终止。")
    return
  

# 5. 生成持仓事实矩阵
  analyzer = FundIndustryAnalyzer(df_holding)
  json_fact_dict = analyzer.export_to_json_fact(top_n=5)
  print(f"\n[左侧分支] 成功生成持仓事实矩阵，共计提取到 {len(json_fact_dict)} 个有效观测样本")

  success_count = 0
  skip_count = 0
  failure_count = 0
  
  # 优先读取已有的 panel csv（支持断点续跑和增量追加写入）
  existing_records = []
  if os.path.exists(output_panel_csv):
      try:
          df_old = pd.read_csv(output_panel_csv)
          existing_records = df_old.to_dict(orient="records")
      except Exception:
          pass
  
  panel_dict = {row["composite_key"]: row for row in existing_records}

  # 6. 遍历观测点进行大模型对齐分析
  failed_keys = []
  for composite_key, fact_data in json_fact_dict.items():
    if target_keys is not None and composite_key not in target_keys:
        continue

    # 🌟 增量跳过判断：如果开启了 skip_existing 且缓存文件已存在，直接跳过
    detail_json_path = os.path.join(details_json_folder, f"{composite_key}.json")
    if skip_existing and composite_key in panel_dict and os.path.exists(detail_json_path):
        print(f"\n⏩ [跳过已有] 检测到 Key [{composite_key}] 已存在缓存结果，自动跳过。")
        skip_count += 1
        continue

    fund_code = fact_data["fund_code"]
    end_date = fact_data["end_date"]
    report_type_id = fact_data["report_type_id"]

    print(f"\n--------------------------------------------------")
    print(f"📌 当前处理观测点: [Key: {composite_key}]")

    # 1. 查找文本文件路径
    matched_file_path = map_key_to_report_filename(
        fund_code=fund_code,
        end_date=end_date,
        report_type_id=report_type_id,
        text_dir=text_dir,
    )

    # 2. 细分判定：是“报告压根没有（文件缺失）”还是“文本存在但未披露”
    is_report_missing = False
    is_text_un_disclosed = False
    report_text = ""

    if not matched_file_path or not os.path.exists(matched_file_path):
        is_report_missing = True
    else:
        with open(matched_file_path, "r", encoding="utf-8") as f:
            report_text = f.read().strip()
        
        if not report_text or "未披露" in report_text or "该章节未披露" in report_text or "本报告期无" in report_text:
            is_text_un_disclosed = True

    try:
      # 3. 分支处理：报告完全缺失
      if is_report_missing:
          print(f"❌ [数据缺失] 未找到对应的文本文件，判定为报告完全缺失。")
          json_say_result = {
              "report_content_nature": "report_missing",
              "overall_sentiment": "数据缺失",
              "industry_views": [],
              "key_factors": ["原始文件缺失", "无法评估"],
              "confidence_score": 0.0
          }
          comparison_result = {
              "consistency_score": 0.0,
              "gap_type": "报告缺失",
              "diagnostic_summary": f"经系统核查，该基金在报告期 {end_date} 对应的文本文件未找到或未收录。",
              "challenge_question": "由于底层文本完全缺失，管理人是否存在信披延迟、未按时公开披露或数据同步断裂的问题？"
          }
      
      # 4. 分支处理：报告存在，但内容未披露/空白
      elif is_text_un_disclosed:
          print(f"⚠️ [合规风控提示] 文本存在但内容未披露/空白，触发合规异常记录。")
          json_say_result = {
              "report_content_nature": "not_disclosed",
              "overall_sentiment": "合规异常",
              "industry_views": [],
              "key_factors": ["信息披露缺失", "合规风险"],
              "confidence_score": 1.0
          }
          comparison_result = {
              "consistency_score": 0.0,
              "gap_type": "信息披露违规",
              "diagnostic_summary": f"经系统核查，该基金在报告期 {end_date} 的运作分析章节存在未披露或空白情形。",
              "challenge_question": "既然定期报告已发布，但运作分析章节却选择空置或未披露，管理人是在刻意回避业绩归因，还是有规避合规质询的嫌疑？"
          }
      
      # 5. 正常走大模型 Agent 1 和 Agent 4 分析逻辑
      else:
          # Agent 1 提取 Say (带多模型轮换与 NoneType 防护)
          prompt = Agent1Feature.get_prompt(report_text)
          response = call_gemini_with_rotation(
              client=client,
              contents=prompt,
              config=types.GenerateContentConfig(
                  system_instruction=Agent1Feature.SYSTEM_INSTRUCTION,
                  response_mime_type="application/json",
                  response_schema=Agent1Feature.ANALYSIS_SCHEMA,
              ),
          )
          if not response or not response.text:
              raise ValueError("Gemini API 返回的文本内容为空 (None)")
          json_say_result = json.loads(response.text)

          # Agent 4 对比 (带多模型轮换与灵魂质询)
          compare_prompt = COMPARATOR.get_prompt(
              fund_code=fund_code,
              end_date=end_date,
              report_type=f"R{report_type_id}",
              json_say=json_say_result,
              json_fact=fact_data,
          )
          compare_response = call_gemini_with_rotation(
              client=client,
              contents=compare_prompt,
              config=types.GenerateContentConfig(
                  system_instruction=COMPARATOR.SYSTEM_INSTRUCTION,
                  response_mime_type="application/json",
                  response_schema=COMPARATOR.COMPARISON_SCHEMA,
              ),
          )
          if not compare_response or not compare_response.text:
              raise ValueError("Agent 4 对比分析返回的文本内容为空 (None)")
          comparison_result = json.loads(compare_response.text)

      # 归档中间态 JSON
      detail_record = {
          "composite_key": composite_key,
          "left_do_fact": fact_data,
          "right_say_json": json_say_result,
          "comparison_result": comparison_result,
      }
      with open(
          os.path.join(details_json_folder, f"{composite_key}.json"),
          "w",
          encoding="utf-8",
      ) as jf:
        json.dump(detail_record, jf, ensure_ascii=False, indent=4)

      panel_row = {
          "composite_key": composite_key,
          "MasterFundCode": fund_code,
          "EndDate": end_date,
          "ReportTypeID": report_type_id,
          "report_content_nature": json_say_result.get("report_content_nature", "not_disclosed"),
          "overall_sentiment": json_say_result.get("overall_sentiment", "合规异常"),
          "consistency_score": comparison_result.get("consistency_score", 0.0),
          "gap_type": comparison_result.get("gap_type", "信息披露违规"),
          "diagnostic_summary": comparison_result.get("diagnostic_summary", ""),
          "challenge_question": comparison_result.get("challenge_question", ""),
      }
      panel_dict[composite_key] = panel_row
      success_count += 1
      print(f"✅ [处理成功并已归档]")

    except Exception as e:
      print(f"❌ [报错]: {e}")
      failure_count += 1
      failed_keys.append(composite_key)
    

  # 7. 最终汇总导出
  print("\n" + "=" * 50)
  if panel_dict:
    df_panel = pd.DataFrame(list(panel_dict.values()))
    df_panel.to_csv(output_panel_csv, index=False, encoding="utf-8-sig")
    print(f"🎉 跑批完成！成功处理 {success_count} 个样本，失败 {failure_count} 个。")
    print(f"📁 中间详情 JSON 保存在: {details_json_folder}")
    print(f"📈 最终 Panel Data 大表已更新至: {output_panel_csv}")
    # 📊 跑批结束后的汇总打印区域

    # 🌟 如果有失败的，直接在终端明明白白打印出来！
    if failed_keys:
        print(f"\n❌ 以下 {len(failed_keys)} 个失败的观测点 Key (Composite Key)，请复制定向排查：")
        print("-" * 50)
        for fk in failed_keys:
            print(fk)
        print("-" * 50)
        
        # 顺便独立保存成一个 JSON，方便后续直接传给代码定向重跑
        failed_json_path = os.path.join(output_folder, "failed_keys_audit.json")
        with open(failed_json_path, "w", encoding="utf-8") as f:
            json.dump(failed_keys, f, ensure_ascii=False, indent=4)
        print(f"📋 失败清单已自动保存至: {failed_json_path}")

  else:
    print("⚠️ 未生成有效面板数据。")
  print("=" * 50)


if __name__ == "__main__":
    # 定义你的监控矩阵参数
    my_funds = [
        # "008099",  # 林英睿
        # "004856",  # 建材指数
        # "004890",  # 宫正
        "000457",  # 李博
        # "011340",  # 王晗
        # "010245",  # 陈樱子
        # "005267",  # 谭丽
        # "006435",  # 杨锐文
        # "260101",  # 杨锐文
        # "260108",  # 刘彦春
        # "006345",  # 刘彦春
        # "162606",  # 刘彦春
    ]
    my_dates = ["2025-12-31", "2026-03-31", "2026-06-30"]
    my_types = ["1", "2", "5", "6"]

    # 启动全链路流水线（支持指定 target_keys 增量补跑，全量跑则传 target_keys=None）


    run_say_do_pipeline(
        target_funds=my_funds,
        target_end_dates=my_dates,
        target_report_types=my_types,
        skip_existing=False ,  # 💡 设为 True 则只跑没跑过的新 Key（增量跳过）；设为 False 则全部重新跑批覆盖！
        target_keys=None  # 例如 ["006435_2026-06-30_R5", "260101_2026-03-31_R1"]

    )