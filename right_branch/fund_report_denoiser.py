# -*- coding: utf-8 -*-
"""
基金季报文本脱水去噪核心类（支持批量与拦截词统计）
"""
import os
import re
import sys

# 确保主程序能正确跨目录引入 config 和 data
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import settings
from data.external.financial_stopwords import FINANCIAL_STOPWORDS
from data.external.protected_connectors import PROTECTED_CONNECTORS
from data.external.nonsense_patterns import NONSENSE_PATTERNS
from data.external.hard_action_keywords import HARD_ACTION_KEYWORDS

class FundReportDenoiser:
    """
    基金季报文本去噪预处理器
    通过纯Python策略字典库，高效剔除章节中的宏观套话，识别言行缺口核心干货
    """
    def __init__(self):
        # 运行时直接从编译好的 Py 集合中扣除保护词
        self.effective_stopwords = FINANCIAL_STOPWORDS - PROTECTED_CONNECTORS

    def _split_sentences(self, text):
        """传统标点正则精准断句"""
        sentence_endings = re.compile(r'([。？！；\n\r]+)')
        parts = sentence_endings.split(text)
        sentences = []
        for i in range(0, len(parts)-1, 2):
            sentence = parts[i].strip() + parts[i+1].strip()
            if parts[i].strip():
                sentences.append(sentence)
        if len(parts) % 2 == 1 and parts[-1].strip():
            sentences.append(parts[-1].strip())
        return sentences

    def denoise(self, text):
        """
        执行文本脱水过滤流水线
        返回：(清洗后的文本字符串, 被去掉的停用词集合)
        """
        raw_sentences = self._split_sentences(text)
        cleaned_sentences = []
        removed_words = set()

        for sentence in raw_sentences:
            has_digit = any(char.isdigit() for char in sentence) or "%" in sentence
            has_hard_action = any(kw in sentence for kw in HARD_ACTION_KEYWORDS)

            # 1. 最高优先级保护：包含核心操作词且带数据，无条件直接留存
            if has_hard_action and has_digit:
                cleaned_sentences.append(sentence)
                continue

            # 2. 内置高频套话正则式拦截
            if any(pattern.search(sentence) for pattern in NONSENSE_PATTERNS):
                # 记录因正则被过滤的句子中的已知停用词
                for word in self.effective_stopwords:
                    if word in sentence:
                        removed_words.add(word)
                continue

            # 3. 停用词密度动态拦截
            hit_words = [word for word in self.effective_stopwords if word in sentence]
            if len(hit_words) >= settings.MATCH_THRESHOLD and not has_hard_action:
                for w in hit_words:
                    removed_words.add(w)
                continue

            # 4. 数据盲区长句拦截
            if len(sentence) > settings.LONG_SENTENCE_LIMIT and not has_digit:
                for word in self.effective_stopwords:
                    if word in sentence:
                        removed_words.add(word)
                continue

            cleaned_sentences.append(sentence)

        return "".join(cleaned_sentences), removed_words


def process_folder(folder_path, folder_name, denoiser):
    """遍历处理指定的子文件夹"""
    print(f"\n==================== 开始处理文件夹: {folder_name} ====================")
    if not os.path.exists(folder_path):
        print(f"❌ 错误：找不到路径 {folder_path}")
        return

    # 获取文件夹下所有txt文件
    all_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    # 限制处理前 n=10 个文件
    files_to_process = all_files[:settings.BATCH_N]

    if not files_to_process:
        print("ℹ️ 该文件夹下没有符合条件的 .txt 文件。")
        return

    for idx, file_name in enumerate(files_to_process, 1):
        file_path = os.path.join(folder_path, file_name)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
            
        clean_text, removed_words = denoiser.denoise(raw_text)
        
        print(f"\n📄 [{folder_name} - {idx}/{len(files_to_process)}] 文件名: {file_name}")
        print(f"🗑️ [去掉的词语]: {', '.join(removed_words) if removed_words else '暂无特征套话词'}")
        print("✨ [清洗后的纯净文本]:")
        print(clean_text if clean_text.strip() else "[该文件已被完全脱水，未发现核心操作干货。]")
        print("-" * 50)


# ==================== 生产运行入口 ====================
if __name__ == "__main__":
    # 实例化去噪处理器
    report_denoiser = FundReportDenoiser()
    
    # 依次批量处理 oper_text 和 view_text
    process_folder(settings.OPER_TEXT_DIR, "oper_text", report_denoiser)
    process_folder(settings.VIEW_TEXT_DIR, "view_text", report_denoiser)
