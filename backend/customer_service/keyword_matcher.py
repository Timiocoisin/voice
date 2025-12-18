# -*- coding: utf-8 -*-
"""
关键词匹配服务
实现基于关键词的智能匹配和回复生成
"""

import re
import random
from typing import Optional, Tuple
from .knowledge_base import KNOWLEDGE_BASE, GREETING_WORDS, ENDING_WORDS


class KeywordMatcher:
    """关键词匹配器"""

    # 更人性化的开头/结尾话术
    HUMAN_PREFIXES = [
        "我大概明白你的情况啦，我帮你整理下重点：",
        "这个问题很多小伙伴也问过，我给你简单说一下：",
        "我来帮你一步一步看下哈：",
        "收到～这边的建议是：",
    ]

    HUMAN_SUFFIXES = [
        "如果还有不清楚的地方，随时再问我就好～",
        "你可以先按这个方式试一下，有问题我再帮你一起排查～",
        "先按这个步骤来操作看看效果，如果不行再一起想其他办法哈。",
        "后续使用中有任何小问题，都可以直接在这里问我～",
    ]

    def __init__(self):
        self.knowledge_base = KNOWLEDGE_BASE
        # 构建关键词索引（小写，便于匹配）
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """构建关键词索引"""
        self.keyword_index = {}
        for topic, data in self.knowledge_base.items():
            if topic == "默认":
                continue
            for keyword in data["keywords"]:
                keyword_lower = keyword.lower()
                if keyword_lower not in self.keyword_index:
                    self.keyword_index[keyword_lower] = []
                self.keyword_index[keyword_lower].append({
                    "topic": topic,
                    "priority": data["priority"]
                })
    
    def _normalize_text(self, text: str) -> str:
        """文本标准化处理"""
        # 转小写
        text = text.lower()
        # 移除标点符号（保留中文和英文）
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        return text
    
    def _extract_keywords(self, text: str) -> list:
        """从文本中提取关键词"""
        normalized = self._normalize_text(text)
        # 分词（简单版本：按空格和常见分隔符）
        words = re.split(r'[\s,，。！？]+', normalized)
        # 过滤空字符串和单字符
        keywords = [w for w in words if len(w) > 1]
        return keywords
    
    def _calculate_match_score(self, question: str, topic_data: dict) -> float:
        """计算匹配分数"""
        question_lower = question.lower()
        keywords = topic_data["keywords"]
        
        # 计算匹配的关键词数量
        matched_count = 0
        for keyword in keywords:
            if keyword.lower() in question_lower:
                matched_count += 1
        
        if not keywords:
            return 0.0
        
        # 基础分数：匹配关键词比例
        base_score = matched_count / len(keywords)
        
        # 优先级权重（优先级越小，权重越高）
        priority_weight = 1.0 / topic_data["priority"]
        
        # 最终分数
        final_score = base_score * priority_weight
        
        return final_score
    
    def match(self, question: str) -> Tuple[str, float]:
        """
        匹配问题并返回答案
        
        Args:
            question: 用户问题
            
        Returns:
            (answer, score): 答案和匹配分数
        """
        if not question or not question.strip():
            return self.knowledge_base["默认"]["answer"], 0.0
        
        question = question.strip()
        best_topic = None
        best_score = 0.0
        
        # 遍历所有主题，计算匹配分数
        for topic, data in self.knowledge_base.items():
            if topic == "默认":
                continue
            
            score = self._calculate_match_score(question, data)
            if score > best_score:
                best_score = score
                best_topic = topic
        
        # 如果匹配分数太低，统一提示联系客服 QQ（带一点人情味）
        if best_score < 0.1:
            answer = "这个问题我这边暂时没有查到详细说明呢，建议您直接联系人工客服处理哈～ 联系方式：QQ：xxxxxxxxxxxxxxxxxxx"
        else:
            answer = self.knowledge_base[best_topic]["answer"]
        
        return answer, best_score
    
    def generate_reply(self, question: str, add_greeting: bool = True) -> str:
        """
        生成回复（带随机语气词）
        
        Args:
            question: 用户问题
            add_greeting: 是否添加随机语气词
            
        Returns:
            完整的回复文本
        """
        # 先处理打招呼这类简单问候，避免直接走“联系QQ”的兜底
        if question:
            q_norm = question.strip().lower()
            # 常见的问候语（中英文）
            greeting_keywords = ["你好", "在吗", "您好", "哈喽", "hello", "hi", "嗨"]
            if len(q_norm) <= 8 and any(g in q_norm for g in greeting_keywords):
                return "你好呀～我是《声音序章》的智能小助手，有什么想了解的可以直接告诉我哈~"

        answer, score = self.match(question)

        # 匹配到具体问题（score >= 0.1）时，做“人性化包装”
        if score >= 0.1:
            # 1）可选：在前面加一句自然的开头
            if random.random() < 0.6:  # 60% 概率加开头，避免每句都一样
                prefix = random.choice(self.HUMAN_PREFIXES)
                answer = f"{prefix}\n\n{answer}"

            # 2）可选：在后面加一句安抚/补充
            if random.random() < 0.6:
                suffix = random.choice(self.HUMAN_SUFFIXES)
                answer = f"{answer}\n\n{suffix}"

            # 3）原来的语气词逻辑（保持不变）
            if add_greeting:
                # 随机选择语气词（30%概率再加一层口语化）
                if random.random() < 0.3:
                    greeting = random.choice(GREETING_WORDS)
                    ending = random.choice(ENDING_WORDS)
                    if not answer.startswith(greeting):
                        answer = f"{greeting}，{answer}"
                    if not answer.endswith(ending) and not answer.endswith("~"):
                        answer = f"{answer}{ending}"
        
        return answer


# 单例模式
_matcher_instance = None

def get_matcher() -> KeywordMatcher:
    """获取关键词匹配器实例（单例）"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = KeywordMatcher()
    return _matcher_instance

