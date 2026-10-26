class Agent1Feature:
  # 类属性：系统指令
  SYSTEM_INSTRUCTION = (
      "你是一个精通行业分类、板块多空观点和量化因子的资深金融专家与合规风控专家。"
      "请严格按照要求的 JSON 结构输出分析结果，不仅要评估全局情绪，还要细分各赛道的具体多空立场。"
      "注意：必须防范幻觉，对于缺失、未披露或纯合规套话的文本，切勿强行编造行业观点，必须如实归类文本性质。"
  )

  # 类属性：结构化 JSON Schema
  ANALYSIS_SCHEMA = {
      "type": "OBJECT",
      "properties": {
          "report_content_nature": {
              "type": "STRING",
              "description": (
                  "文本的真实信息含量性质：'substantive'（干货满满，有明确行业/风格倾向）、"
                  "'platitudes'（假大空、套话、泛泛而谈，无实质观点）、"
                  "'not_disclosed'（未披露、章节缺失或客观空白）"
              ),
          },
          "overall_sentiment": {
              "type": "STRING",
              "description": "全文整体的宏观市场情绪：利好、震荡、利空 或 中性/未知",
          },
          "industry_views": {
              "type": "ARRAY",
              "description": (
                  "分行业/赛道的具体观点。若 report_content_nature 为"
                  " 'not_disclosed' 或 'platitudes'，此项应为空数组 []"
              ),
              "items": {
                  "type": "OBJECT",
                  "properties": {
                      "industry": {
                        "type": "STRING",
                        "description": (
                            "行业或板块名称，如：AI算力、军工电子、建筑材料等"
                        ),
                      },
                      "stance": {
                          "type": "STRING",
                          "description": (
                              "立场：看好、看空、中性 或 未提及"
                          ),
                      },
                      "reason": {
                          "type": "STRING",
                          "description": "简述该立场的文本依据，若无具体依据写“无”",
                      },
                  },
                  "required": ["industry", "stance", "reason"],
              },
          },
          "key_factors": {
              "type": "ARRAY",
              "items": {"type": "STRING"},
              "description": "量化视角下的核心驱动因子或事件标签",
          },
          "confidence_score": {
              "type": "NUMBER",
              "description": "分析置信度评分（0到1之间）",
          },
      },
      "required": [
          "report_content_nature",
          "overall_sentiment",
          "industry_views",
          "key_factors",
          "confidence_score",
      ],
  }

  @staticmethod
  def get_prompt(text_content: str) -> str:
    """静态方法：根据输入的文本动态生成 Prompt"""
    return f"""
请以资深金融量化研究员的视角，深度分析以下基金经理的运作分析文本。
提取出全文的宏观整体情绪、各个细分赛道的具体多空观点（看好/看空及理由），以及核心量化因子。

【核心语义辨析规则（极其重要）】：
在提取 `industry_views` 时，必须严格区分以下两种性质的表述，**切勿将“客观业绩归因”误判为“战术行动指南”**：
1. **战术行动指南（Tactical Action / 主观意图）**：
   - 特征：基金经理明确表达了对某行业/板块的主观投资偏好、未来建仓规划、战术看好或调仓逻辑（例如：“本期我们增加了对XX板块的配置”、“未来看好XX方向的超额收益”）。
   - 处理：**允许**提取具体的“看好/看空”立场。
2. **客观业绩归因与复盘（Retrospective Attribution / 事后解释）**：
   - 特征：基金经理仅在做**事后的市场复盘、指数表现解释或业绩成因归因**（例如：“本季度指数上涨主要受XX原材料价格上涨影响”、“本基金遵循指数复制原则运作”）。这属于客观陈述，**不包含主观买卖调仓的承诺**。
   - 处理：**不得**将其机械抽取为对该行业的主观“看好”立场（应将立场标为“中性”或不予采纳为战术意图），防止在后续动作比对中产生误判。

【风控规则】：
1. **内容性质判定（report_content_nature）**：
- 若文本包含具体的板块观察、战术思考、逻辑推演，判定为 "substantive"。
- 若文本通篇充斥“坚持长期价值投资、精选个股、严格风控”等毫无实质内容的合规套话、片汤话，判定为 "platitudes"。
- 若文本缺失、标注“该章节未披露”、“本报告期无”或极度简短，判定为 "not_disclosed"。
2. **防幻觉与静默原则**：
- 当判定为 "platitudes" 或 "not_disclosed" 时，`industry_views` 必须严格保持为空数组 `[]`，切勿强行编造或臆测行业倾向！
- 只有在 "substantive" 情况下，才允许依据上述辨析规则提取严谨的行业观点。

文本内容：
{text_content}
"""