

# 基金经理“言行不一”开源大看板 (Say-Do Gap with LLM)

> **"不是在听你的宏观大实话，而是在抓你调仓的小辫子。"**

本仓库是一个聚焦于公募基金经理“言行不一”（Say-Do Gap）的量化投研与大模型审计开源项目。项目通过自动化流水线，将基金定期报告中的定性文本（如宏观展望、策略阐述）与底层的量化持仓变动进行语义交叉对齐与动态打分，一键生成极具视觉冲击力的开源红黑榜与深度复盘长卷。

👉 **[[点击这里直接在线预览带完整图表的看板]](https://github.io)**

## 📌 数据来源与合规声明 (Data Sources & Compliance)

> * **持仓与市场底层**：资产配置、行业集中度及持仓变动来源于 CSMAR ——【按行业分类的股票投资组合文件】。
> * **文本与运作章节**：各报告期【公募基金定期报告】中【4.4 报告期内基金投资策略和运作分析】采集自天天基金网、巨潮网（后续可拓展至路演纪要等）。
> * **语义对齐与审计**：基于大模型（LLM）的多维意图提取、情感倾向分析与 Say-Do Gap 一致性动态打分。
> * *免责声明：本看板所有数据监测、打分结果与打脸复盘仅用于量化研究与学术审计，不构成任何投资建议。*
> 
> 

## 📂 数据准备 (Data Preparation)
本看板依赖行业持仓原始数据。由于文件较大，请按以下方式准备数据：
1. 在目录下找到 data/raw/quantitative_market/按行业分类的股票投资组合文件.zip
2. 解压该文件到当前目录：
   ```bash
   unzip 按行业分类的股票投资组合文件.zip -d data/raw/quantitative_market/

## 🚀 核心亮点 (Key Features)

* **纯黑极简工业风UI**：高颜值、现代化的投研长卷渲染，直观展示基金经理一致性得分与排名。
* **大模型多维审计**：利用大模型深入剖析文本承诺与实际调仓的背离程度，自动生成犀利的“核心打脸复盘与质询直击”。
* **全链路自动化流水线**：从多源数据清洗、持仓对齐到 LLM 语义打分与 HTML 看板一键渲染。



## 📂 项目结构 (Project Structure)

```text
Say-Do-Gap-Project/
├── .venv/                         # 虚拟环境目录
├── config/                        # 配置文件与全局设置
│   └── settings.py
├── core_engine/                   # 核心计算与校验引擎
│   ├── comparator.py
│   ├── panel_processor.py
│   └── validator.py
├── data/                          # 数据资产目录
│   ├── debug_intermediate/        # 调试中间文件
│   ├── external/                  # 外部参考数据
│   ├── intermediate/              # 中间处理数据
│   │   └── alignment_details/     # 对齐详情明细
│   ├── processed/                 # 清洗后规范化数据
│   └── raw/                       # 原始数据
│       ├── quantitative_market/   # 市场与持仓底层数据 (如 CSMAR)
│       └── quarterly_reports/     # 定期报告及运作分析文本 (天天基金网、巨潮网等)
├── left_branch/                   # 左侧投研链路（持仓与映射清洗）
│   ├── filter.py
│   ├── FundIndustryAnalyzer.py
│   └── map_key_to_report_filename.py
├── right_branch/                  # 右侧审计链路（大模型语义提取与降噪）
│   ├── agent1_feature.py
│   └── fund_report_denoiser.py
├── visualization/                 # 可视化与看板渲染模块
│   └── visualizer.py
├── main.py                        # 项目主运行入口
├── README.md                      # 项目说明与合规文档
├── requirements.txt               # 依赖包列表
├── Say_Do_Gap_Dashboard.ipynb     # 核心 Jupyter 调试与看板长卷 Notebook
├── saydogapV001_workflow.jpeg     # 工作流架构图
└── temp.py                        # 临时测试脚本

```



## 🛠️ 快速开始 (Quick Start)

1. **克隆仓库**
```bash
git clone https://github.com/你的用户名/Say-Do-Gap-Project.git
cd Say-Do-Gap-Project

```


2. **安装依赖**
```bash
pip install -r requirements.txt

```


3. **运行流水线与渲染看板**
在本地 Python 环境或 Notebook 中执行主渲染脚本，即可一键生成最新的基金经理“打脸”红黑榜。

---

## 📄 License & Contact

本项目采用 [MIT License](https://www.google.com/search?q=LICENSE) 开源协议。欢迎各位量化大佬、研究员和开发者共同 PR、提 Issue 交流！
