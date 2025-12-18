# 客服系统 - 关键词匹配模块

## 功能说明

本模块实现了基于关键词匹配的智能客服回复系统（方案三），能够根据用户问题自动匹配知识库中的答案。

## 文件结构

```
backend/customer_service/
├── __init__.py              # 模块初始化
├── knowledge_base.py        # 知识库（FAQ问答数据）
├── keyword_matcher.py       # 关键词匹配器
└── README.md                # 本文件
```

## 使用方法

### 1. 基本使用

```python
from backend.customer_service.keyword_matcher import get_matcher

# 获取匹配器实例（单例模式）
matcher = get_matcher()

# 生成回复
question = "手机能不能用变声器？"
reply = matcher.generate_reply(question)
print(reply)
```

### 2. 在GUI中使用

已在 `gui/main_window.py` 中集成，用户发送消息时会自动调用关键词匹配生成回复。

## 知识库结构

知识库定义在 `knowledge_base.py` 中，每个条目包含：

- `keywords`: 关键词列表（用于匹配）
- `answer`: 答案文本
- `priority`: 优先级（数字越小优先级越高）

## 匹配逻辑

1. **文本标准化**：将用户问题转为小写，移除标点符号
2. **关键词匹配**：检查问题中是否包含知识库中的关键词
3. **分数计算**：根据匹配的关键词数量和优先级计算匹配分数
4. **答案选择**：选择分数最高的答案，如果分数太低则使用默认回复
5. **语气词添加**：随机添加语气词（30%概率），让回复更自然

## 添加新问题

编辑 `knowledge_base.py`，在 `KNOWLEDGE_BASE` 字典中添加新条目：

```python
"新问题主题": {
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "answer": "答案内容...",
    "priority": 2  # 优先级，数字越小越优先
}
```

## 测试示例

```python
# 测试不同问题
test_questions = [
    "手机能不能用？",
    "变声参数怎么设置？",
    "虚拟声卡怎么安装？",
    "VIP多少钱？",
    "软件怎么用？",
    "没有声音怎么办？",
    "你好"  # 未匹配问题
]

matcher = get_matcher()
for q in test_questions:
    reply = matcher.generate_reply(q)
    print(f"Q: {q}")
    print(f"A: {reply}\n")
```

## 后续扩展

- 可以添加更多知识库条目
- 可以优化匹配算法（如使用TF-IDF、余弦相似度等）
- 可以接入AI API作为兜底（方案四）
- 可以记录未匹配问题，用于优化知识库

## 注意事项

- 关键词匹配是大小写不敏感的
- 匹配分数低于0.1时会使用默认回复
- 语气词添加是随机的，每次回复可能略有不同

