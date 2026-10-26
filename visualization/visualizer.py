import os
import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from IPython.display import display, HTML
import plotly.express as px
import json


current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core_engine.panel_processor import SayDoPanelDataProcessor
# from core_engine.data_processor import SayDoDashboardDataProcessor
from left_branch.FundIndustryAnalyzer import FundIndustryAnalyzer

class SayDoDashboardRenderer:
    def __init__(self):
        self.project_root = project_root
        self.report_type_map = {
                    'R6': '年报',
                    'R4': '季报',
                    'R2': '季报',
                    'R5': '中报',
                    'R1': '季报',
                    'R3': '季报',
                }
        # self.report_type_map = {
        #     'R6': '年报(FY)',
        #     'R4': '四季报(Q4)',
        #     'R2': '二季报(Q2)',
        #     'R5': '中报(HY)',
        #     'R1': '一季报(Q1)',
        #     'R3': '三季报(Q3)',
        #     'FY': '年报(FY)'
        # }

        self._apply_global_fonts()

    def _render_data_audit_summary(self, final_df: pd.DataFrame):
        """📊 数据审计与缺失值监控：持仓端精简、异常端精准挂载经理姓名"""
        if final_df.empty:
            return

        total_samples = len(final_df)
        
        # 1. 状态分类统计
        missing_reports = final_df[final_df['report_content_nature'] == 'report_missing']
        un_disclosed = final_df[final_df['report_content_nature'] == 'not_disclosed']
        normal_samples = total_samples - len(missing_reports) - len(un_disclosed)
        coverage_rate = round((normal_samples / total_samples) * 100, 2) if total_samples > 0 else 0.0

        # 🌟 建立 composite_key -> 基金经理 的精准映射
        manager_mapping = {}
        for _, r in final_df.iterrows():
            ck = str(r.get('composite_key', '')).strip()
            m_name = str(r.get('基金经理', '')).strip()
            if ck and m_name and m_name != 'nan':
                manager_mapping[ck] = m_name
                f_code = str(r.get('基金代码', '')).strip().zfill(6)
                if f_code:
                    manager_mapping[f_code] = m_name

        # 面板总观测样本 keys
        all_panel_keys = final_df['composite_key'].dropna().tolist() if 'composite_key' in final_df.columns else []

        # 2. 读取持仓端 missing_keys_audit.json
        missing_keys_path = os.path.join(self.project_root, "data", "processed", "missing_keys_audit.json")
        missing_keys_list = []
        if os.path.exists(missing_keys_path):
            try:
                with open(missing_keys_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        if isinstance(item, dict):
                            missing_keys_list.append(item.get('composite_key', str(item)))
                        else:
                            missing_keys_list.append(str(item))
            except Exception as e:
                print(f"⚠️ 读取持仓审计文件出错: {e}")

        # 3. 渲染列表函数
        def build_list_html(keys, include_manager=False):
            if not keys:
                return "<div style='padding: 8px; color: #94a3b8; font-size: 12px; text-align: center;'>暂无记录</div>"
            html = "<div style='max-height: 200px; overflow-y: auto; text-align: left;'>"
            for k in keys:
                mgr_tag = ""
                if include_manager:
                    k_str = str(k).strip()
                    mgr_name = manager_mapping.get(k_str, "")
                    if not mgr_name and len(k_str) >= 6:
                        mgr_name = manager_mapping.get(k_str[:6], "")
                    
                    if mgr_name and mgr_name != 'nan':
                        mgr_tag = f" <span style='color: #2563eb; font-weight: 600;'>[{mgr_name}]</span>"
                    else:
                        mgr_tag = " <span style='color: #64748b; font-weight: 400;'>[未知经理]</span>"

                html += f"""
                <div style='font-family: monospace; font-size: 11.5px; color: #111827; padding: 5px 6px; border-bottom: 1px solid #f1f5f9; line-height: 1.4;'>
                    <div>{k}</div>
                    {f"<div>{mgr_tag}</div>" if include_manager else ""}
                </div>
                """
            html += "</div>"
            return html

        panel_keys_html = build_list_html(all_panel_keys, include_manager=False)
        holding_keys_html = build_list_html(missing_keys_list, include_manager=False)  # 🌟 持仓端不显示经理，保持纯净
        
        missing_reports_keys = missing_reports['composite_key'].dropna().tolist() if 'composite_key' in missing_reports.columns else []
        report_keys_html = build_list_html(missing_reports_keys, include_manager=True)

        un_disclosed_keys = un_disclosed['composite_key'].dropna().tolist() if 'composite_key' in un_disclosed.columns else []
        un_disclosed_keys_html = build_list_html(un_disclosed_keys, include_manager=True)

        # 4. 纯黑极简排版布局
        summary_html = f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-top: 5px solid #111827; border-radius: 8px; padding: 22px 26px; margin-top: 32px; margin-bottom: 36px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
                <div>
                    <h2 style="margin: 0; font-size: 20px; font-weight: 800; color: #111827;">📊 投研底层数据合规与持仓/文本样本完整度审计面板</h2>
                    <p style="margin: 6px 0 0 0; font-size: 13.5px; color: #475569; font-weight: 600;">实时监测全链路流水线中的面板总样本、持仓端缺口、报告文件缺失与运作章节未披露异常</p>
                </div>
                <span style="background-color: #f8fafc; color: #111827; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: 700; border: 1px solid #cbd5e1;">文本有效包含率: {coverage_rate}%</span>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px;">
                
                <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden;">
                    <div style="padding: 14px; text-align: center; background: #f8fafc; border-bottom: 1px solid #cbd5e1;">
                        <div style="font-size: 12px; color: #475569; font-weight: 700;">面板总观测样本</div>
                        <div style="font-size: 20px; font-weight: 800; color: #111827; margin-top: 4px;">{total_samples}</div>
                    </div>
                    <div style="padding: 8px; background: #ffffff;">
                        {panel_keys_html}
                    </div>
                </div>

                <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden;">
                    <div style="padding: 14px; text-align: center; background: #f8fafc; border-bottom: 1px solid #cbd5e1;">
                        <div style="font-size: 12px; color: #475569; font-weight: 700;">持仓端缺失 (Missing Keys)</div>
                        <div style="font-size: 20px; font-weight: 800; color: #111827; margin-top: 4px;">{len(missing_keys_list)}</div>
                    </div>
                    <div style="padding: 8px; background: #ffffff;">
                        {holding_keys_html}
                    </div>
                </div>

                <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden;">
                    <div style="padding: 14px; text-align: center; background: #f8fafc; border-bottom: 1px solid #cbd5e1;">
                        <div style="font-size: 12px; color: #475569; font-weight: 700;">报告文件缺失/未收录</div>
                        <div style="font-size: 20px; font-weight: 800; color: #111827; margin-top: 4px;">{len(missing_reports)}</div>
                    </div>
                    <div style="padding: 8px; background: #ffffff;">
                        {report_keys_html}
                    </div>
                </div>

                <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden;">
                    <div style="padding: 14px; text-align: center; background: #f8fafc; border-bottom: 1px solid #cbd5e1;">
                        <div style="font-size: 12px; color: #475569; font-weight: 700;">【投资运作】章节未披露</div>
                        <div style="font-size: 20px; font-weight: 800; color: #111827; margin-top: 4px;">{len(un_disclosed)}</div>
                    </div>
                    <div style="padding: 8px; background: #ffffff;">
                        {un_disclosed_keys_html}
                    </div>
                </div>

            </div>
        </div>
        """
        display(HTML(summary_html))


    def _apply_global_fonts(self):
        """🌟 核心优化：针对大屏显示强制加大字号、增加行距，解决阅读费劲的痛点"""
        # 1. Plotly 图表专属全局配置（强制把默认字号从 10-12px 拉大到 14-15px）
        self.plotly_layout_defaults = dict(
            font=dict(
                family="Microsoft YaHei, PingFang SC, sans-serif",
                size=14,  # 图表内所有文字放大到 14px
                color="#1e293b"
            ),
            title=dict(
                font=dict(size=16, color="#0f172a"),  # 图表标题进一步加粗加大
                x=0.02
            )
        )
        
        # 2. 网页/长卷文本与表格的 CSS 样式注入（可直接应用在 HTML 渲染中）
        self.custom_css = """
        <style>
            /* 整体正文和表格字号显著放大，大屏观看极度舒适 */
            body, .dash-text, p {
                font-size: 16px !important;
                line-height: 1.8 !important;
                color: #0f172a !important;
            }
            /* 表格文字与间距加宽 */
            table.dataframe, .render-table th, .render-table td {
                font-size: 15px !important;
                padding: 12px 14px !important;
            }
            /* 🌟 灵魂质询区域：升级为高级专业金融风（深蓝色系） */
            .challenge-box {
                font-size: 16.5px !important;            /* 保证大屏看得清 */
                line-height: 1.9 !important;             /* 行间距拉开，绝不拥挤 */
                color: #1e3a8a !important;               /* 深海军蓝正文，沉稳克制 */
                background-color: #f8fafc !important;    /* 极其干净的浅蓝灰底色 */
                padding: 18px !important;                /* 留白充足，告别局促 */
                border-left: 5px solid #1d4ed8 !important; /* 厚重的专业深蓝左边框，压迫感十足 */
                border-radius: 6px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }
            /* 核心指标数字加粗加大 */
            .metric-value {
                font-size: 21px !important;
                font-weight: 700 !important;
            }
        </style>
        """

    def _get_global_master_color_map(self, group_df: pd.DataFrame) -> dict:
        """🌟 核心：统一从多列中提取所有重仓行业、调仓行业及特殊项目，生成全局强一致的颜色映射"""
        import plotly.express as px
        
        # 1. 自动收集所有“第i重仓行业”和“第i调仓行业”中的行业名称
        all_industries = set()
        for i in range(1, 6):
            col_heavy = f'第{i}重仓行业'
            col_turn = f'第{i}调仓行业'
            if col_heavy in group_df.columns:
                all_industries.update(group_df[col_heavy].dropna().unique().tolist())
            if col_turn in group_df.columns:
                all_industries.update(group_df[col_turn].dropna().unique().tolist())
                
        # 2. 核心锚定与特殊项目颜色强行绑定（确保 others 和 现金 颜色上下绝对一致）
        color_map = {
            'others': '#94a3b8',
            'Others / 其他': '#94a3b8',
            'others占比': '#94a3b8',
            'others调仓权重': '#94a3b8',
            '现金及其他资产': '#a855f7',
            '现金调仓权重': '#a855f7',
            '现金及其他资产占比': '#a855f7',
            # 常用重点行业锚定
            '制造业': '#3b82f6',       # 经典蓝
            '采矿业': '#ef4444',       # 红色
            '金融业': '#10b981',       # 绿色
            '金融': '#10b981',
            '能源': '#f97316',         # 橙色
            '房地产业': '#84cc16',     # 黄绿色
            '房地产': '#84cc16',
            '工业': '#06b6d4',         # 青色
            '科技': '#6366f1',         # 靛青色
            '信息技术': '#6366f1',
            '医疗保健': '#ec4899',     # 粉色
            '公用事业': '#14b8a6',     # 墨绿色
        }
        
        # 3. 对其余动态提取到的行业，用高质感调色盘自动分配
        palette = px.colors.qualitative.Prism + px.colors.qualitative.Safe + px.colors.qualitative.Pastel
        palette_idx = 0
        for ind in sorted(list(all_industries)):
            if ind not in color_map and ind not in ['', 'nan', None]:
                color_map[ind] = palette[palette_idx % len(palette)]
                palette_idx += 1
                
        return color_map

    def _render_leaderboard(self, df_all_funds: pd.DataFrame):
        """🔥 渲染 Say-Do Gap 全市场基金经理“打脸”与虚假承诺排行榜（置于看板首页）"""
        if df_all_funds.empty:
            return

        # 按平均一致性得分升序排序（得分越低，说明长期言行不一、打脸越严重，排在最前）
        df_sorted = df_all_funds.sort_values(by='AvgConsistencyScore', ascending=True).head(10)

        rows_html = ""
        for idx, (_, row) in enumerate(df_sorted.iterrows(), 1):
            fund_code = str(row.get('MasterFundCode', '')).zfill(6)
            manager = row.get('ManagerName', '未知经理')
            score = round(float(row.get('AvgConsistencyScore', 0.0)), 4)
            gap_type = row.get('DominantGap', '风格漂移/言行不一')
            worst_p = row.get('WorstPeriod', '最新报告期')
            quote = row.get('ChallengeQuote', '暂无详细打脸语录。')

            # 前三名赋予醒目的警示红/橙色徽章
            rank_badge_bg = "#ef4444" if idx == 1 else ("#f97316" if idx == 2 else ("#f59e0b" if idx == 3 else "#64748b"))
            
            rows_html += f"""
            <tr style='border-bottom: 1px solid #e2e8f0; transition: background 0.2s;'>
                <td style='padding: 14px 16px; text-align: center; font-weight: 800;'>
                    <span style='background: {rank_badge_bg}; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 13px;'>TOP {idx}</span>
                </td>
                <td style='padding: 14px 16px; font-weight: 700; color: #111827;'>
                    {fund_code} <span style='color: #1d4ed8; font-weight: 600; font-size: 13px;'>[{manager}]</span>
                </td>
                <td style='padding: 14px 16px; text-align: center; font-family: monospace; font-weight: 800; color: #dc2626; font-size: 16px;'>
                    {score}
                </td>
                <td style='padding: 14px 16px; text-align: center;'>
                    <span style='background: #fef2f2; color: #dc2626; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 700; border: 1px solid #fecaca;'>{gap_type}</span>
                </td>
                <td style='padding: 14px 16px; color: #111827; font-size: 13.5px; line-height: 1.5;'>
                    <div style='font-weight: 700; margin-bottom: 3px; color: #475569;'>📅 崩塌期：{worst_p}</div>
                    <div style='font-weight: 700; color: #111827;'>“{quote}”</div>
                </td>
            </tr>
            """

        leaderboard_html = f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-top: 5px solid #dc2626; border-radius: 8px; padding: 22px 26px; margin-top: 32px; margin-bottom: 36px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
                <div>
                    <h2 style="margin: 0; font-size: 20px; font-weight: 800, color: #111827; color: #111827;">🔥 Say-Do Gap 全市场基金经理“打脸”与虚假承诺红黑榜</h2>
                    <p style="margin: 6px 0 0 0; font-size: 13.5px; color: #475569; font-weight: 600;">基于大模型语义交叉比对与全仓动态追踪，无情揭露言行不一、宏观八股与实操背离最严重的基金产品</p>
                </div>
                <span style="background-color: #fef2f2; color: #dc2626; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: 700; border: 1px solid #fecaca;">高危漂移黑榜</span>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; overflow: hidden;">
                <thead>
                    <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1;">
                        <th style="padding: 14px 16px; width: 80px; text-align: center; color: #111827; font-size: 14px; font-weight: 800;">排名</th>
                        <th style="padding: 14px 16px; width: 180px; color: #111827; font-size: 14px; font-weight: 800;">基金代码 / 经理</th>
                        <th style="padding: 14px 16px; width: 130px; text-align: center; color: #111827; font-size: 14px; font-weight: 800;">平均一致性得分</th>
                        <th style="padding: 14px 16px; width: 170px; text-align: center; color: #111827; font-size: 14px; font-weight: 800;">主导偏差类型</th>
                        <th style="padding: 14px 16px; color: #111827; font-size: 14px; font-weight: 800;">核心打脸复盘与质询直击</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """
        display(HTML(leaderboard_html))

    def _get_report_sort_weight(self, comp_key: str) -> int:
        """同日期报告排序权重：二季报/四季报优先，中报/年报居后"""
        comp_str = str(comp_key)
        if '_R2' in comp_str or '_R4' in comp_str:
            return 1
        elif '_R5' in comp_str or 'FY' in comp_str or '_R6' in comp_str:
            return 2
        return 3

    def _format_periods(self, group_df: pd.DataFrame) -> list:
        """生成带精炼报告类型的标签列表，确保同日报告不重名"""
        periods = []
        for _, r in group_df.iterrows():
            date_str = str(r['报告期_str'])
            comp_key = str(r.get('composite_key', ''))
            suffix = comp_key.split('_')[-1] if '_' in comp_key else 'R1'
            
            label_desc = self.report_type_map.get(suffix, suffix)
            same_day_count = len(group_df[group_df['报告期_str'] == date_str])
            
            if same_day_count > 1:
                periods.append(f"{date_str} [{label_desc}]")
            else:
                periods.append(date_str)
        return periods

    
    def _render_fund_card(self, fund_code: str, manager_name: str, group: pd.DataFrame, avg_score: float, dominant_gap: str, latest_stock: float):
        """1. 渲染顶部母卡片：精简头部，移除冗余的最新股仓"""
        html = f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-left: 5px solid #1d4ed8; border-radius: 8px; padding: 18px 24px; margin-top: 32px; margin-bottom: 14px; box-shadow: 0 3px 6px rgba(0,0,0,0.04); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-size: 18px; font-weight: 700; color: #111827; margin-right: 14px;">基金代码: <span style="color: #111827;">{fund_code}</span></span>
                    <span style="font-size: 15px; color: #1d4ed8; font-weight: 600; margin-right: 16px;">[{manager_name}]</span>
                    <div style="display: inline-flex; gap: 10px; align-items: center;">
                        <span style="background: #fef2f2; padding: 4px 10px; border-radius: 4px; font-size: 13px; font-weight: 700;">
                            <span style="color: #111827;">平均一致性得分:</span> <span style="color: #dc2626;">{avg_score}</span>
                        </span>
                        <span style="background: #eff6ff; padding: 4px 10px; border-radius: 4px; font-size: 13px; font-weight: 600;">
                            <span style="color: #111827;">总体偏差倾向:</span> <span style="color: #1d4ed8;">{dominant_gap}</span>
                        </span>
                    </div>
                </div>
                <span style="background-color: #f1f5f9; color: #111827; padding: 5px 12px; border-radius: 4px; font-size: 13px; font-weight: 600;">观测跨度: {len(group)} 个报告期</span>
            </div>
        </div>
        """
        display(HTML(html))


    def _render_structured_table(self, group: pd.DataFrame, periods: list):
        """2. 渲染结构化指标对比表：正黑加粗、每句独立段落、段首缩进两个中文字符"""
        sentiments, scores, gap_types, stocks, top3s, hhis, challenges_html = [], [], [], [], [], [], []

        for _, row in group.iterrows():
            sentiments.append(row.get('总体情绪', '中性'))
            scores.append(str(round(float(row.get('一致性得分', 0.0)), 4)))
            gap_types.append(row.get('偏差类型', '正常/初始期'))
            
            stocks.append(f"{round(float(row.get('真实总股仓NAV占比', 0.0)), 2)}%")
            top3s.append(f"{round(float(row.get('Top3行业集中度', 0.0)), 2)}%")
            hhis.append(str(round(float(row.get('HHI分散度指数', 0.0)), 3)))

            # 🌟 核心优化：正黑色、加粗、独立段落、段首缩进 2em（两个中文字符）
            raw_challenge = str(row.get('challenge_question', '初始基准期，暂无质询建议。'))
            if "初始基准期" in raw_challenge or len(raw_challenge) < 15:
                formatted_challenge = f"<div style='font-size: 15px; color: #111827; font-weight: 700; line-height: 1.7; text-indent: 2em;'>{raw_challenge}</div>"
            else:
                import re
                raw_sentences = [s.strip() for s in re.split(r'([。？；!！])', raw_challenge) if s.strip()]
                
                sentences = []
                temp_s = ""
                for item in raw_sentences:
                    temp_s += item
                    if item in ['。', '？', '；', '!', '！']:
                        sentences.append(temp_s.strip())
                        temp_s = ""
                if temp_s:
                    sentences.append(temp_s.strip())

                if not sentences:
                    sentences = [raw_challenge]

                # 逐句输出为独立段落，增加 text-indent: 2em 实现段首缩进两格
                points_html = ""
                for sent in sentences:
                    points_html += f"<div style='margin-bottom: 8px; text-indent: 2em;'>{sent}</div>"
                
                formatted_challenge = f"<div style='font-size: 14.5px; color: #111827; font-weight: 700; line-height: 1.75; text-align: left;'>{points_html}</div>"

            challenges_html.append(formatted_challenge)

        th_cells = "<th style='padding: 14px 16px; width: 130px; background: #f8fafc; border-bottom: 2px solid #cbd5e1; color: #111827; font-size: 15px; font-weight: 800;'>指标维度</th>"
        for p in periods:
            th_cells += f"<th style='padding: 14px 16px; width: 280px; background: #f8fafc; border-bottom: 2px solid #cbd5e1; color: #111827; text-align: center; font-size: 15px; font-weight: 800;'>📅 {p}</th>"

        def make_row_html(label, val_list, val_style="color: #111827; font-weight: 700;"):
            tr = f"<td style='padding: 14px 16px; font-weight: 800; color: #111827; background: #f8fafc; font-size: 15px;'>{label}</td>"
            for v in val_list:
                tr += f"<td style='padding: 14px 16px; text-align: center; font-size: 15px; {val_style}'>{v}</td>"
            return f"<tr style='border-bottom: 1px solid #e2e8f0;'>{tr}</tr>"

        table_html = f"""
        <table style="width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <thead><tr>{th_cells}</tr></thead>
            <tbody>
                {make_row_html("总体情绪", sentiments)}
                {make_row_html("一致性得分", scores, "color: #dc2626; font-weight: 800; font-family: monospace; font-size: 16px;")}
                {make_row_html("偏差类型", [f"<span style='background: #f1f5f9; color: #111827; padding: 4px 10px; border-radius: 4px; font-size: 13px; font-weight: 700; border: 1px solid #cbd5e1;'>{gt}</span>" for gt in gap_types])}
                {make_row_html("真实股仓占比", stocks, "font-weight: 700; color: #111827; font-size: 15px;")}
                {make_row_html("Top3行业集中度", top3s, "font-weight: 700; color: #111827; font-size: 15px;")}
                {make_row_html("HHI分散度指数", hhis, "font-family: monospace; font-weight: 700; font-size: 15px;")}
                <tr style='border-bottom: 1px solid #e2e8f0;'>
                    <td style='padding: 14px 16px; font-weight: 800; color: #111827; background: #f8fafc; vertical-align: top; font-size: 15px;'>灵魂质询建议</td>
                    {"".join([f"<td style='padding: 14px 16px; vertical-align: top; background: #ffffff;'>{ch}</td>" for ch in challenges_html])}
                </tr>
            </tbody>
        </table>
        """
        display(HTML(table_html))



    def _render_consistency_score_chart(self, fund_code: str, group: pd.DataFrame, periods: list):
        """一致性得分演变折线图：主视图保持整洁，悬停提示中完美展示完整的偏差类型与动态细节"""
        score_records = []
        
        for idx, (_, row) in enumerate(group.iterrows()):
            period_label = periods[idx] if idx < len(periods) else str(row.get('报告期_str', ''))
            
            score = float(row.get('一致性得分', 0.0) or 0.0)
            gap_type = str(row.get('偏差类型', '正常/初始期'))
            sentiment = str(row.get('总体情绪', '中性'))
            
            score_records.append({
                '报告期标签': period_label,
                '一致性得分': score,
                '偏差类型': gap_type,
                '总体情绪': sentiment
            })

        if not score_records:
            return

        df_score = pd.DataFrame(score_records)

        x_vals = df_score['报告期标签'].tolist()
        y_vals = df_score['一致性得分'].tolist()
        
        # 🌟 精心排版悬停提示：将偏差类型与总体情绪清晰地内嵌在 Hover 浮窗中
        custom_hover = [
            f"<b>报告期</b>: {r['报告期标签']}<br>"
            f"<b>一致性得分</b>: {r['一致性得分']:.2f}<br>"
            f"<b>偏差类型 (Say-Do Gap)</b>: <span style='color:#d97706;'>{r['偏差类型']}</span><br>"
            f"<b>总体情绪</b>: {r['总体情绪']}" 
            for r in score_records
        ]

        fig_score = go.Figure()
        fig_score.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines+markers+text',
            name='一致性得分',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8, color='#1d4ed8'),
            text=[f"{v:.2f}" for v in y_vals],
            textposition="top center",
            customdata=custom_hover,
            hovertemplate="%{customdata}<extra></extra>"
        ))

        fig_score.update_layout(
            height=260,
            template="plotly_white",
            title=dict(text=f"[{fund_code}] 言行一致性得分演变趋势（0~1 独立信誉评分）", font=dict(size=14, color="#1e293b")),
            xaxis=dict(title="报告期 (信披类型)", type='category'),
            yaxis=dict(title="得分", range=[-0.05, 1.05]),
            margin=dict(l=15, r=15, t=35, b=15)
        )
        fig_score.show()

            
    def _render_mid_turnover_chart(self, fund_code: str, group: pd.DataFrame, periods: list, global_color_map: dict):
        """2. 中部动态调仓双向堆积图：直接接入带后缀的 periods 作为时间轴标签"""
        turnover_records = []
        
        # 使用 enumerate 通过行顺序精准对齐传进来的 periods 列表
        for i, (_, row) in enumerate(group.iterrows()):
            # 优先从 periods 中取带后缀的标签，防止越界则回退
            period_label = periods[i] if i < len(periods) else str(row.get('报告期_str', '未知日期'))
            
            # 过滤掉初始期（没有上一期做差，不产生调仓动作）
            if '2025-12-31' in period_label or '初始期' in period_label:
                continue
            
            # 搜集第1~5调仓行业及占比
            for j in range(1, 6):
                ind_name = row.get(f'第{j}调仓行业')
                ind_val = row.get(f'第{j}调仓占比')
                if pd.notna(ind_name) and pd.notna(ind_val):
                    try:
                        val = float(str(ind_val).replace('%', '').strip())
                    except Exception:
                        continue
                    if val != 0:
                        turnover_records.append({'报告期': period_label, '行业': str(ind_name).strip(), '调仓占比': val})
            
            # 补充 others 调仓和现金调仓
            oth_turn = row.get('others调仓权重', 0.0)
            if pd.notna(oth_turn) and float(oth_turn) != 0:
                turnover_records.append({'报告期': period_label, '行业': 'Others / 其他', '调仓占比': float(oth_turn)})
                
            cash_turn = row.get('现金调仓权重', 0.0)
            if pd.notna(cash_turn) and float(cash_turn) != 0:
                turnover_records.append({'报告期': period_label, '行业': '现金类资产', '调仓占比': float(cash_turn)})

        if not turnover_records:
            return

        df_t = pd.DataFrame(turnover_records)
        df_t['调仓占比'] = pd.to_numeric(df_t['调仓占比'], errors='coerce').fillna(0.0)
        
        # 保持 periods 的原有先后顺序作为分类轴顺序
        valid_periods = [p for p in periods if not ('2025-12-31' in p or '初始期' in p)]
        df_t['报告期'] = pd.Categorical(df_t['报告期'], categories=valid_periods, ordered=True)
        
        df_pivot = df_t.pivot_table(index='报告期', columns='行业', values='调仓占比', aggfunc='sum', fill_value=0.0)
        df_pivot = df_pivot.sort_index()

        fig_mid = go.Figure()
        for col in df_pivot.columns:
            y_vals = [float(v) for v in df_pivot[col].values]
            x_vals = [str(v) for v in df_pivot.index.values]
            custom_text = [f"{val:+.2f}%" for val in y_vals]

            bar_color = global_color_map.get(str(col), global_color_map.get('others', '#94a3b8'))

            fig_mid.add_trace(go.Bar(
                x=x_vals,
                y=y_vals,
                name=str(col),
                width=0.1,
                marker=dict(color=bar_color),
                customdata=custom_text,
                hovertemplate="<b>%{data.name}</b>: %{customdata}<extra></extra>"
            ))

        fig_mid.update_layout(
            barmode='relative',
            height=320,
            template="plotly_white",
            title=dict(text=f"[{fund_code}] 动态调仓双向堆积演变（纯买卖动作追踪）", font=dict(size=14, color="#1e293b")),
            xaxis=dict(title="报告期", type='category'),
            yaxis=dict(title="调仓变动占比 (%)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=15, r=15, t=35, b=15)
        )
        fig_mid.show()


    def _render_bottom_stack_chart(self, fund_code: str, group: pd.DataFrame, periods: list, global_color_map: dict):
        """4. 渲染底部行业全仓配置堆叠演变趋势图：接入全局统一行业颜色映射"""
        stack_records = []
        
        # 尝试直接加载底层持仓大表，获取该基金的全生命周期持仓明细
        holding_csv_path = os.path.join(self.project_root, "data", "processed", "combined_fund_industry_class.csv")
        if os.path.exists(holding_csv_path):
            df_holding = pd.read_csv(holding_csv_path)
            analyzer = FundIndustryAnalyzer(df_holding)
            master_matrix = analyzer.calc_master_panel_matrix()
            
            if not master_matrix.empty:
                master_matrix['MasterFundCode'] = master_matrix['MasterFundCode'].astype(str).str.zfill(6)
                master_matrix['EndDate'] = master_matrix['EndDate'].astype(str).str.strip()
                fund_master = master_matrix[master_matrix['MasterFundCode'] == str(fund_code).zfill(6)]
                
                for _, m_row in fund_master.iterrows():
                    e_date = str(m_row['EndDate']).strip()
                    
                    # 收集前5大重仓行业及占比
                    for i in range(1, 6):
                        ind_name = m_row.get(f'第{i}重仓行业')
                        ind_val = m_row.get(f'第{i}重仓占比')
                        if pd.notna(ind_name) and pd.notna(ind_val):
                            try:
                                val = float(str(ind_val).replace('%', '').strip())
                            except Exception:
                                continue
                            if 0 < val <= 100:
                                stack_records.append({'报告期': e_date, '行业': str(ind_name).strip(), '占比': val})

                    others_val = m_row.get('Others占比', 0.0)
                    if pd.notna(others_val):
                        try:
                            val_oth = float(str(others_val).replace('%', '').strip())
                        except Exception:
                            val_oth = 0.0
                        if 0 < val_oth <= 100:
                            stack_records.append({'报告期': e_date, '行业': 'Others / 其他', '占比': val_oth})

                    cash_val = m_row.get('现金及其他资产占比', 0.0)
                    if pd.notna(cash_val):
                        try:
                            val_cash = float(str(cash_val).replace('%', '').strip())
                        except Exception:
                            val_cash = 0.0
                        if 0 < val_cash <= 100:
                            stack_records.append({'报告期': e_date, '行业': '现金类资产', '占比': val_cash})

        if stack_records:
            df_stack = pd.DataFrame(stack_records)
            df_stack['占比'] = pd.to_numeric(df_stack['占比'], errors='coerce').fillna(0.0)
            
            # 使用 pivot 确保同一报告期内的各个行业明细独立平铺，不盲目 sum 累加
            df_pivot = df_stack.pivot_table(index='报告期', columns='行业', values='占比', aggfunc='first', fill_value=0.0)
            df_pivot = df_pivot.astype(float)

            df_pivot = df_pivot.sort_index()

            mean_weights = df_pivot.mean().sort_values(ascending=False)
            df_pivot = df_pivot[mean_weights.index]

            fig_bottom = go.Figure()
            for col in df_pivot.columns:
                y_vals_b = [float(v) for v in df_pivot[col].values]
                x_vals_b = [str(v) for v in df_pivot.index.values]  # 纯日期字符串，不带任何后缀
                custom_text_b = [f"{val:.2f}%" for val in y_vals_b]

                # 🌟 核心修改：通过相同的全局颜色字典获取颜色，确保与中部调仓图完美对应
                bar_color_b = global_color_map.get(str(col), global_color_map.get('others', '#94a3b8'))

                fig_bottom.add_trace(go.Bar(
                    x=x_vals_b,
                    y=y_vals_b,
                    name=str(col),
                    width=0.12,
                    marker=dict(color=bar_color_b),
                    customdata=custom_text_b,
                    hovertemplate="<b>%{data.name}</b>: %{customdata}<extra></extra>"
                ))

            fig_bottom.update_layout(
                barmode='stack',
                height=340,
                template="plotly_white",
                title=dict(text=f"[{fund_code}] 行业全仓配置堆叠演变趋势（全周期追踪）", font=dict(size=14, color="#1e293b")),
                xaxis=dict(title="报告期", type='category'),
                yaxis=dict(title="仓位占比 (%)", range=[0, 105]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=15, r=15, t=35, b=15)
            )
            fig_bottom.show()

    
    def render_all(self):
        """总入口函数：首屏轰出打脸黑榜，随后逐个渲染基金高级双轴多维投研长卷"""
        print("⚡️ 正在加载并对齐底层多路投研异构数据...")
        
        holding_csv_path = os.path.join(self.project_root, "data", "processed", "combined_fund_industry_class.csv")
        if not os.path.exists(holding_csv_path):
            print(f"[错误] 未找到持仓底层大表: {holding_csv_path}")
            return
            
        df_holding = pd.read_csv(holding_csv_path)
        analyzer = FundIndustryAnalyzer(df_holding)
        master_matrix = analyzer.calc_master_panel_matrix()

        panel_processor = SayDoPanelDataProcessor(
            panel_csv_path=os.path.join(self.project_root, "data", "processed", "say_do_gap_panel_data.csv"),
            text_dir=os.path.join(self.project_root, "data", "raw", "quarterly_reports", "oper_text"),
            master_matrix_df=master_matrix
        )
        final_df = panel_processor.build_final_display_table()
        
        if final_df.empty:
            print("[可视化提示] 最终合成宽表为空，暂无数据可供渲染。")
            return
        

        df_flat = final_df.reset_index()
        df_flat['报告期_str'] = pd.to_datetime(df_flat['报告期']).dt.strftime('%Y-%m-%d')
        
        df_flat['__sort_weight'] = df_flat['composite_key'].apply(self._get_report_sort_weight)
        fund_avg_scores = df_flat.groupby(['基金代码', '基金经理'])['一致性得分'].transform(lambda x: pd.to_numeric(x, errors='coerce').mean())
        df_flat['__avg_consistency_score'] = fund_avg_scores
        
        df_flat = df_flat.sort_values(
            by=['__avg_consistency_score', '基金代码', '报告期_str', '__sort_weight'], 
            ascending=[True, True, True, True]
        )
        self._render_data_audit_summary(df_flat)


        # 🌟 1. 核心聚合：在进入循环前，直接从 df_flat 提炼出全市场的“打脸排行榜”汇总数据
        leaderboard_rows = []
        for (f_code, m_name), sub_g in df_flat.groupby(['基金代码', '基金经理'], sort=False):
            avg_sc = pd.to_numeric(sub_g['一致性得分'], errors='coerce').mean()
            # 挑出得分最低（最惨崩塌期）的那一行
            worst_row = sub_g.loc[sub_g['一致性得分'].astype(float).idxmin()] if not sub_g.empty else sub_g.iloc[0]
            
            leaderboard_rows.append({
                'MasterFundCode': f_code,
                'ManagerName': m_name,
                'AvgConsistencyScore': avg_sc,
                'DominantGap': worst_row.get('偏差类型', '风格漂移/言行不一'),
                'WorstPeriod': str(worst_row.get('报告期_str', '')).split()[0],
                'ChallengeQuote': str(worst_row.get('challenge_question', '暂无详细打脸语录。'))[:75] + "..."
            })
        
        df_leaderboard = pd.DataFrame(leaderboard_rows)
        
        # 🌟 2. 轰出看板首屏：渲染高危漂移黑榜
        print("🔥 正在生成全市场 Say-Do Gap 打脸红黑榜...")
        self._render_leaderboard(df_leaderboard)

        grouped = list(df_flat.groupby(['基金代码', '基金经理'], sort=False))
        print(f"🎨 正在渲染高级双轴多维投研长卷，共计覆盖 {len(grouped)} 个基金全生命周期视图...\n")

        # 预先规范化 master_matrix 方便后续精准捞取首期
        if not master_matrix.empty:
            master_matrix['MasterFundCode'] = master_matrix['MasterFundCode'].astype(str).str.zfill(6)
            master_matrix['EndDate'] = master_matrix['EndDate'].astype(str).str.strip()

        for (fund_code, manager_name), group in grouped:
            group = group.sort_values(by=['报告期_str', '__sort_weight'])
            latest_row = group.iloc[-1]
            global_color_map = self._get_global_master_color_map(group)

            avg_score = round(group['一致性得分'].astype(float).mean(), 4) if '一致性得分' in group.columns else 0.0
            gap_types_series = group['偏差类型'].dropna()
            dominant_gap = gap_types_series.mode()[0] if not gap_types_series.empty else "正常/初始期"
            latest_stock = round(float(latest_row.get('真实总股仓NAV占比', 0.0)), 2)

            periods = self._format_periods(group)

            # 1 & 2 & 3. 渲染顶部卡片、结构化表格、一致性得分、中部调仓图
            self._render_fund_card(fund_code, manager_name, group, avg_score, dominant_gap, latest_stock)
            self._render_structured_table(group, periods)
            self._render_consistency_score_chart(fund_code, group, periods)
            self._render_mid_turnover_chart(fund_code, group, periods, global_color_map)

            # 4. 底部全仓图专用：安全克隆一个 group 副本，并从 master_matrix 把 1231 补进这个副本里供画图使用
            bottom_group = group.copy()
            if not master_matrix.empty:
                f_code_str = str(fund_code).zfill(6)
                fund_initials = master_matrix[(master_matrix['MasterFundCode'] == f_code_str) & (master_matrix['EndDate'] == '2025-12-31')]
                
                if not fund_initials.empty:
                    init_row = fund_initials.iloc[0].to_dict()
                    extra_row = {
                        '报告期_str': '2025-12-31',
                        '真实总股仓NAV占比': init_row.get('真实总股仓NAV占比', 0.0),
                        'Others占比': init_row.get('Others占比', 0.0),
                        '现金及其他资产占比': init_row.get('现金及其他资产占比', 0.0)
                    }
                    for i in range(1, 6):
                        extra_row[f'第{i}重仓行业'] = init_row.get(f'第{i}重仓行业')
                        extra_row[f'第{i}重仓占比'] = init_row.get(f'第{i}重仓占比')
                    
                    bottom_group = pd.concat([pd.DataFrame([extra_row]), bottom_group], ignore_index=True)
                    bottom_group = bottom_group.sort_values(by=['报告期_str'])
                    
                    bottom_periods = []
                    for _, r in bottom_group.iterrows():
                        d_str = str(r['报告期_str'])
                        if d_str == '2025-12-31':
                            bottom_periods.append('2025-12-31 [初始期]')
                        else:
                            orig_match = group[group['报告期_str'] == d_str]
                            if not orig_match.empty:
                                idx_orig = group.index.get_loc(orig_match.index[0])
                                bottom_periods.append(periods[idx_orig])
                            else:
                                bottom_periods.append(d_str)
                else:
                    bottom_periods = periods
            else:
                bottom_periods = periods

            self._render_bottom_stack_chart(fund_code, bottom_group, bottom_periods, global_color_map)



if __name__ == "__main__":
    renderer = SayDoDashboardRenderer()
    renderer.render_all()
    