# Agent 2: 综合比对引擎
from google.genai import types


class COMPARATOR:
  SYSTEM_INSTRUCTION = (
      "你是一个精通中国公募基金行为金融学、投资风格漂移与言行一致性（Say-Do Gap）研究的资深量化风控专家。"
      "你的任务是综合分析基金经理在定期报告中的主观言论（Say）与期末底层客观持仓及调仓变动（Do），"
      "进行全方位的偏离度交叉验证，并以极其犀利、一针见血且富有深度的口吻，向基金经理抛出直击灵魂的质询与挑战。"
  )

  @staticmethod
  def get_prompt(
      fund_code: str, end_date: str, report_type: str, json_say: dict, json_fact: dict
  ) -> str:
    import json

    say_str = json.dumps(json_say, ensure_ascii=False, indent=2)
    fact_str = json.dumps(json_fact, ensure_ascii=False, indent=2)

    return f"""
请对以下基金在特定报告期的“言（Say）”与“动（Do）”进行深度交叉比对、偏离度诊断，并输出**充满批判性与深度质询的投研挑战**。

【基金基本信息】：
- 基金代码: 
{fund_code}
- 报告期: 
{end_date} (报告类型: {report_type})

【右侧主观言论 (Say - 文本大模型提取结果)】：
{say_str}

【左侧客观事实 (Do - 数据库调仓矩阵提取结果)】：
{fact_str}

【核心比对风控与语义辨析规则（极其重要）】：
1. **区分“战术行动”与“业绩归因”**：
   - 若 Say 中包含的是对过去市场表现、指数走势、宏观或原材料价格波动的**客观复盘与业绩归因**（例如：“本期指数上涨主要受某某材料价格上涨影响”），且 Do 中表现为被动持仓或微幅变动：这属于正常的客观陈述，不构成主观调仓承诺，绝不能因此判定为言行不一或风格漂移。此时评分应较高（0.85-1.0）。
   - 只有当 Say 中明确包含**主观战术意图、看好某特定方向并声称要增加配置**，而 Do 中实际仓位却背道而驰时，方可判定为“风格漂移/言行不一”并大幅扣分。
2. **识别指数/被动型产品的属性**：
   - 若该基金属于被动指数型或复制型产品，其“Say”中的行业提及通常多为指数客观表现说明。比对时应侧重于评估其合规运作与指数跟踪的吻合度，避免用主动权益基金的“主动调仓”标准去刻意扣分。

【你的分析与输出任务】：
请从以下几个维度进行严谨的量化归因，并严格按指定的 JSON 格式输出：
1. **Consistency Score (一致性评分)**：0 到 1 之间的浮点数。
2. **Gap Type (偏离类型)**：
- "高度一致"：言行基本吻合，或属于合规的客观复盘与被动跟随
- "嘴硬体正直/暗中布局"：嘴上没怎么大肆宣扬，但实际调仓动作极大
- "风格漂移/言行不一"：嘴上说看好某方向或制定了主动战术，实际大幅减仓背离
- "被动跟随/市场震荡应对"：主要受市场或指数规则被动影响
3. **Industry Cross Analysis (行业层面 Say-Do 对比)**：逐一比对经理在 Say 里提及的行业立场与 Do 里的实际权重变动，结合“业绩归因 vs 战术意图”原则进行比对。
4. **Diagnostic Summary (偏离诊断总结)**：一针见血地总结该基金本期的 Say-Do 偏离特质。
5. **Challenge Question (犀利质询建议)**：站在机构投资者的尽调（DDQ）立场，向该基金经理提出一个**极其犀利、一针见血、不留情面**的质询问题。逼问其言论与动作之间的逻辑漏洞、潜在风格漂移风险或信披合规隐患（例如：“既然你在报告中大谈特谈某某板块的宏观逻辑，但持仓却纹丝不动，这究竟是纯粹的‘事后诸葛亮式’业绩归因，还是你的战术执行力存在严重滞后？”）。
"""

  # 结构化输出 Schema，确保大模型返回规范的 JSON
  COMPARISON_SCHEMA = types.Schema(
      type=types.Type.OBJECT,
      required=[
          "fund_code",
          "end_date",
          "consistency_score",
          "gap_type",
          "industry_comparisons",
          "diagnostic_summary",
          "challenge_question",
      ],
      properties={
          "fund_code": types.Schema(type=types.Type.STRING),
          "end_date": types.Schema(type=types.Type.STRING),
          "consistency_score": types.Schema(type=types.Type.NUMBER),
          "gap_type": types.Schema(
              type=types.Type.STRING,
              description=(
                  "高度一致 / 嘴硬体正直/暗中布局 / 风格漂移/言行不一 /"
                  " 被动跟随"
              ),
          ),
          "industry_comparisons": types.Schema(
              type=types.Type.ARRAY,
              items=types.Schema(
                  type=types.Type.OBJECT,
                  required=[
                      "industry",
                      "say_stance",
                      "actual_action",
                      "is_consistent",
                      "comment",
                  ],
                  properties={
                      "industry": types.Schema(type=types.Type.STRING),
                      "say_stance": types.Schema(
                          type=types.Type.STRING,
                          description="看好 / 看空 / 中性 / 未重点提及",
                      ),
                      "actual_action": types.Schema(
                          type=types.Type.STRING,
                          description="加仓 / 减仓 / 持平 / 被动微调",
                      ),
                      "is_consistent": types.Schema(type=types.Type.BOOLEAN),
                      "comment": types.Schema(
                          type=types.Type.STRING, description="比对说明"
                      ),
                  },
              ),
          ),
          "diagnostic_summary": types.Schema(type=types.Type.STRING),
        #   "challenge_question": types.Schema(
        #     #   type=types.Schema.STRING if hasattr(types, "Schema") else str,
        #       type=str,
        #       description="站在机构尽调立场，针对该期言行背离或归因漏洞提出的犀利、一针见血的质询建议"
        #   ),
          "challenge_question": types.Schema(
                                type=types.Type.STRING,
                                description="对基金经理的灵魂质询，追问其为何存在业绩归因偏离或信披缺失"
                            )
      },
  )