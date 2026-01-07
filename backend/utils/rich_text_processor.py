"""
富文本消息处理模块
支持 Markdown 格式、@提及功能、链接预览
"""
import re
from typing import List, Tuple, Dict, Optional
from urllib.parse import urlparse


# @提及模式：@用户名 或 @客服
MENTION_PATTERN = re.compile(r"@([\u4e00-\u9fa5A-Za-z0-9_]+)")
# URL 模式：识别 http/https/ftp/www 开头的链接
URL_PATTERN = re.compile(
    r"(?P<url>(?:https?://|ftp://|www\.)[^\s<>{}|\"']+)", 
    re.IGNORECASE
)


def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符"""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _apply_markdown(text: str) -> str:
    """
    应用 Markdown 格式转换：
    - **加粗**
    - *斜体*
    - `行内代码`
    - ```代码块```
    - [链接文本](https://example.com)
    - # 标题
    - > 引用
    - - 列表项
    """
    escaped = _escape_html(text)
    
    # 代码块（多行）
    def _code_block_repl(m: re.Match) -> str:
        code = m.group(1)
        return f'<pre style="background-color:#f3f4f6;padding:8px;border-radius:4px;overflow-x:auto;"><code>{code}</code></pre>'
    
    escaped = re.sub(
        r"```([\s\S]*?)```",
        _code_block_repl,
        escaped
    )
    
    # 行内代码
    escaped = re.sub(
        r"`([^`]+)`",
        lambda m: f'<code style="background-color:#f3f4f6;padding:2px 4px;border-radius:3px;font-family:monospace;">{m.group(1)}</code>',
        escaped
    )
    
    # 标题（# 到 ######）
    for i in range(1, 7):
        escaped = re.sub(
            rf"^{'#' * i}\s+(.+)$",
            lambda m, level=i: f"<h{level} style='margin:8px 0;font-size:{18-level*2}px;font-weight:bold;'>{m.group(1)}</h{level}>",
            escaped,
            flags=re.MULTILINE
        )
    
    # 引用
    escaped = re.sub(
        r"^>\s+(.+)$",
        lambda m: f'<blockquote style="border-left:3px solid #d1d5db;padding-left:12px;margin:8px 0;color:#6b7280;">{m.group(1)}</blockquote>',
        escaped,
        flags=re.MULTILINE
    )
    
    # 无序列表
    escaped = re.sub(
        r"^[-*]\s+(.+)$",
        lambda m: f'<li style="margin:4px 0;">{m.group(1)}</li>',
        escaped,
        flags=re.MULTILINE
    )
    # 将连续的 <li> 包裹在 <ul> 中
    escaped = re.sub(
        r"(<li[^>]*>.*?</li>(?:\s*<li[^>]*>.*?</li>)*)",
        lambda m: f'<ul style="margin:8px 0;padding-left:20px;">{m.group(1)}</ul>',
        escaped
    )
    
    # 有序列表
    escaped = re.sub(
        r"^\d+\.\s+(.+)$",
        lambda m: f'<li style="margin:4px 0;">{m.group(1)}</li>',
        escaped,
        flags=re.MULTILINE
    )
    # 将连续的 <li> 包裹在 <ol> 中
    escaped = re.sub(
        r"(<li[^>]*>.*?</li>(?:\s*<li[^>]*>.*?</li>)*)",
        lambda m: f'<ol style="margin:8px 0;padding-left:20px;">{m.group(1)}</ol>',
        escaped
    )
    
    # 加粗 **text** 或 __text__
    escaped = re.sub(
        r"\*\*([^*]+)\*\*|__([^_]+)__",
        lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>",
        escaped
    )
    
    # 斜体 *text* 或 _text_（但不在加粗中）
    escaped = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)",
        lambda m: f"<em>{m.group(1) or m.group(2)}</em>",
        escaped
    )
    
    # Markdown 链接 [text](url)
    def _md_link_repl(m: re.Match) -> str:
        label = m.group(1)
        url = m.group(2)
        href = url if re.match(r"^https?://", url, re.IGNORECASE) else f"http://{url}"
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer" style="color:#2563eb;text-decoration:none;">{label}</a>'
    
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        _md_link_repl,
        escaped
    )
    
    # 换行
    escaped = escaped.replace("\n", "<br/>")
    
    return escaped


def _apply_mentions(html: str, user_id: Optional[int] = None) -> Tuple[str, List[Dict[str, str]]]:
    """
    高亮 @提及 内容，并提取提及的用户信息。
    
    返回: (处理后的HTML, 提及列表)
    提及列表格式: [{"type": "user"|"service", "name": "用户名"}]
    """
    mentions: List[Dict[str, str]] = []
    
    def repl(m: re.Match) -> str:
        mention_name = m.group(1)
        # 判断是@客服还是@用户（简单规则：包含"客服"、"客服"、"service"等关键词为客服）
        mention_type = "service" if any(keyword in mention_name.lower() for keyword in ["客服", "service", "support", "agent"]) else "user"
        
        mentions.append({
            "type": mention_type,
            "name": mention_name
        })
        
        return (
            f'<span style="color:#7c3aed;font-weight:600;'
            f'background-color:rgba(124,58,237,0.1);padding:2px 6px;'
            f'border-radius:4px;cursor:pointer;" '
            f'class="mention" data-mention-type="{mention_type}" data-mention-name="{mention_name}">'
            f'@{mention_name}</span>'
        )
    
    new_html = MENTION_PATTERN.sub(repl, html)
    return new_html, mentions


def _apply_auto_link(html: str) -> Tuple[str, List[str]]:
    """
    将纯文本 URL 转换为 <a> 标签，并返回所有识别到的 URL。
    已经在 Markdown 链接中的 URL 不再重复处理。
    """
    urls: List[str] = []
    
    def repl(m: re.Match) -> str:
        url = m.group("url")
        # 避免处理已经在 a 标签中的 url
        # 简单检查：如果当前匹配位置前后有 </a> 或 <a，则跳过
        start_pos = m.start()
        end_pos = m.end()
        before_text = html[max(0, start_pos-10):start_pos]
        after_text = html[end_pos:min(len(html), end_pos+10)]
        
        if "</a>" in before_text or "<a" in before_text:
            return url  # 已经在链接中，不处理
        
        href = url
        if not re.match(r"^https?://", href, re.IGNORECASE):
            href = f"http://{href}"
        
        urls.append(href)
        return (
            f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#2563eb;text-decoration:none;">{url}</a>'
        )
    
    new_html = URL_PATTERN.sub(repl, html)
    return new_html, urls


def process_rich_text(
    content: str, 
    user_id: Optional[int] = None
) -> Dict[str, any]:
    """
    处理富文本消息，返回处理后的内容和元数据。
    
    Args:
        content: 原始消息内容
        user_id: 当前用户ID（可选，用于@提及处理）
    
    Returns:
        {
            "html": 处理后的HTML内容,
            "is_rich": 是否为富文本,
            "urls": 识别到的URL列表,
            "mentions": 提及列表 [{"type": "user"|"service", "name": "用户名"}]
        }
    """
    if not content:
        return {
            "html": "",
            "is_rich": False,
            "urls": [],
            "mentions": []
        }
    
    # 快速检测：若既无 markdown 符号、无 @、又无 URL 特征，则直接返回
    has_markdown = any(symbol in content for symbol in ["**", "*", "`", "#", ">", "-", "["])
    has_url = any(keyword in content.lower() for keyword in ["http", "www.", "ftp://"])
    has_mention = "@" in content
    
    if not (has_markdown or has_url or has_mention):
        return {
            "html": content,
            "is_rich": False,
            "urls": [],
            "mentions": []
        }
    
    # 应用 Markdown
    html = _apply_markdown(content)
    
    # 应用 @提及（在链接之前，避免链接中的@被处理）
    html, mentions = _apply_mentions(html, user_id)
    
    # 应用自动链接（最后处理，避免破坏已有的格式）
    html, urls = _apply_auto_link(html)
    
    return {
        "html": html,
        "is_rich": True,
        "urls": urls,
        "mentions": mentions
    }


def extract_urls_from_text(text: str) -> List[str]:
    """从文本中提取所有URL"""
    urls = []
    for match in URL_PATTERN.finditer(text):
        url = match.group("url")
        if not re.match(r"^https?://", url, re.IGNORECASE):
            url = f"http://{url}"
        urls.append(url)
    return urls


def extract_mentions_from_text(text: str) -> List[Dict[str, str]]:
    """从文本中提取所有@提及"""
    mentions = []
    for match in MENTION_PATTERN.finditer(text):
        mention_name = match.group(1)
        mention_type = "service" if any(keyword in mention_name.lower() for keyword in ["客服", "service", "support", "agent"]) else "user"
        mentions.append({
            "type": mention_type,
            "name": mention_name
        })
    return mentions

