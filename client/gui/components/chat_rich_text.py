import re
from typing import List, Tuple, Dict, Optional


MENTION_PATTERN = re.compile(r"@([\u4e00-\u9fa5A-Za-z0-9_]+)")
URL_PATTERN = re.compile(
    r"(?P<url>(?:https?://|ftp://|www\.)[^\s<>{}|\"']+)", re.IGNORECASE
)


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _apply_basic_markdown(text: str) -> str:
    """
    增强的 Markdown 解析：
    - **加粗** 或 __加粗__
    - *斜体* 或 _斜体_
    - `行内代码`
    - ```代码块```
    - # 标题（1-6级）
    - > 引用
    - - 无序列表
    - 1. 有序列表
    - [链接文本](https://example.com)
    并将换行替换为 <br/>。
    """
    escaped = _escape_html(text)
    
    # 代码块（多行）
    def _code_block_repl(m: re.Match) -> str:
        code = m.group(1)
        return f'<pre style="background-color:#1e293b;padding:12px;border-radius:8px;overflow-x:auto;border:1px solid #334155;margin:8px 0;"><code style="color:#e2e8f0;font-family:\'Consolas\',\'Monaco\',\'Courier New\',monospace;font-size:0.9em;line-height:1.6;">{code}</code></pre>'
    
    escaped = re.sub(
        r"```([\s\S]*?)```",
        _code_block_repl,
        escaped
    )
    
    # 行内代码
    escaped = re.sub(
        r"`([^`]+)`",
        lambda m: f'<code style="background-color:#f1f5f9;padding:3px 6px;border-radius:4px;font-family:\'Consolas\',\'Monaco\',\'Courier New\',monospace;font-size:0.9em;color:#e11d48;border:1px solid #e2e8f0;">{m.group(1)}</code>',
        escaped
    )
    
    # 标题（# 到 ######）
    for i in range(1, 7):
        escaped = re.sub(
            rf"^{'#' * i}\s+(.+)$",
            lambda m, level=i: f"<h{level} style='margin:12px 0 8px 0;font-size:{20-level*2}px;font-weight:700;color:#0f172a;line-height:1.3;'>{m.group(1)}</h{level}>",
            escaped,
            flags=re.MULTILINE
        )
    
    # 引用
    escaped = re.sub(
        r"^>\s+(.+)$",
        lambda m: f'<blockquote style="border-left:4px solid #3b82f6;padding:8px 12px;margin:8px 0;background-color:#f8fafc;border-radius:0 6px 6px 0;color:#475569;font-style:italic;">{m.group(1)}</blockquote>',
        escaped,
        flags=re.MULTILINE
    )
    
    # 无序列表
    escaped = re.sub(
        r"^[-*]\s+(.+)$",
        lambda m: f'<li style="margin:6px 0;line-height:1.6;">{m.group(1)}</li>',
        escaped,
        flags=re.MULTILINE
    )
    # 将连续的 <li> 包裹在 <ul> 中
    escaped = re.sub(
        r"(<li[^>]*>.*?</li>(?:\s*<li[^>]*>.*?</li>)*)",
        lambda m: f'<ul style="margin:10px 0;padding-left:24px;list-style-type:disc;">{m.group(1)}</ul>',
        escaped
    )
    
    # 有序列表
    escaped = re.sub(
        r"^\d+\.\s+(.+)$",
        lambda m: f'<li style="margin:6px 0;line-height:1.6;">{m.group(1)}</li>',
        escaped,
        flags=re.MULTILINE
    )
    # 将连续的 <li> 包裹在 <ol> 中
    escaped = re.sub(
        r"(<li[^>]*>.*?</li>(?:\s*<li[^>]*>.*?</li>)*)",
        lambda m: f'<ol style="margin:10px 0;padding-left:24px;list-style-type:decimal;">{m.group(1)}</ol>',
        escaped
    )

    # 加粗 **text** 或 __text__
    escaped = re.sub(
        r"\*\*([^*]+)\*\*|__([^_]+)__",
        lambda m: f'<strong style="font-weight:700;color:#0f172a;">{m.group(1) or m.group(2)}</strong>',
        escaped,
    )

    # 斜体 *text* 或 _text_（但不在加粗中）
    escaped = re.sub(
        r"(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)",
        lambda m: f'<em style="font-style:italic;color:#475569;">{m.group(1) or m.group(2)}</em>',
        escaped,
    )

    # Markdown 链接 [text](url)
    def _md_link_repl(m: re.Match) -> str:
        label = m.group(1)
        url = m.group(2)
        href = url if re.match(r"^https?://", url, re.IGNORECASE) else f"http://{url}"
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer" style="color:#2563eb;text-decoration:none;font-weight:500;border-bottom:1px solid rgba(37,99,235,0.3);transition:all 0.2s ease;">{label}</a>'

    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        _md_link_repl,
        escaped,
    )

    # 换行
    escaped = escaped.replace("\n", "<br/>")
    return escaped


def _apply_mentions(html: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    高亮 @提及 内容，并提取提及的用户信息。
    
    返回: (处理后的HTML, 提及列表)
    提及列表格式: [{"type": "user"|"service", "name": "用户名"}]
    """
    mentions: List[Dict[str, str]] = []
    
    def repl(m: re.Match) -> str:
        mention_name = m.group(1)
        # 判断是@客服还是@用户（简单规则：包含"客服"、"service"等关键词为客服）
        mention_type = "service" if any(keyword in mention_name.lower() for keyword in ["客服", "service", "support", "agent"]) else "user"
        
        mentions.append({
            "type": mention_type,
            "name": mention_name
        })
        
        # 根据类型设置不同颜色
        if mention_type == "service":
            bg_color = "rgba(59,130,246,0.12)"
            text_color = "#2563eb"
            border_color = "rgba(59,130,246,0.2)"
        else:
            bg_color = "rgba(124,58,237,0.12)"
            text_color = "#7c3aed"
            border_color = "rgba(124,58,237,0.2)"
        
        return (
            f'<span style="color:{text_color};font-weight:600;'
            f'background-color:{bg_color};padding:3px 8px;'
            f'border-radius:6px;cursor:pointer;border:1px solid {border_color};'
            f'display:inline-block;transition:all 0.2s ease;" '
            f'class="mention" data-mention-type="{mention_type}" data-mention-name="{mention_name}">'
            f'@{mention_name}</span>'
        )

    new_html = MENTION_PATTERN.sub(repl, html)
    return new_html, mentions


def _apply_auto_link(html: str) -> Tuple[str, List[str]]:
    """
    将纯文本 URL 转换为 <a>，并返回所有识别到的 URL 供外部生成预览卡片。
    已经在 Markdown 链接中的 URL 不再重复处理（前面已转为 <a>）。
    """
    urls: List[str] = []

    def repl(m: re.Match) -> str:
        url = m.group("url")
        # 避免处理已经在 a 标签中的 url
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
            f'style="color:#2563eb;text-decoration:none;font-weight:500;border-bottom:1px solid rgba(37,99,235,0.3);transition:all 0.2s ease;">{url}</a>'
        )

    new_html = URL_PATTERN.sub(repl, html)
    return new_html, urls


def format_message_rich_text(content: str) -> Tuple[str, bool, List[str]]:
    """
    将原始纯文本消息转换为富文本 HTML。

    返回: (渲染内容, 是否为富文本, 需要预览的 URL 列表)
    - 对于不包含 Markdown/@/URL 的普通文本，保持原样并返回 is_rich=False；
    - 一旦检测到上述任一特性，则返回 HTML，并将 is_rich 设为 True。
    """
    if not content:
        return content, False, []

    # 快速检测：若既无 markdown 符号、无 @、又无 URL 特征，则直接返回
    has_markdown = any(symbol in content for symbol in ["**", "*", "`", "#", ">", "-", "["])
    has_url = any(keyword in content.lower() for keyword in ["http", "www.", "ftp://"])
    has_mention = "@" in content
    
    if not (has_markdown or has_url or has_mention):
        return content, False, []

    html = _apply_basic_markdown(content)
    html, mentions = _apply_mentions(html)
    html, urls = _apply_auto_link(html)
    return html, True, urls


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


