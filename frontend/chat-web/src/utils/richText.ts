/**
 * 富文本消息处理工具
 * 支持 Markdown 格式、@提及功能、链接预览
 */

// @提及模式：@用户名 或 @客服
const MENTION_PATTERN = /@([\u4e00-\u9fa5A-Za-z0-9_]+)/g;
// URL 模式：识别 http/https/ftp/www 开头的链接
const URL_PATTERN = /(?:https?:\/\/|ftp:\/\/|www\.)[^\s<>{}|"'`]+/gi;

export interface MentionInfo {
  type: 'user' | 'service';
  name: string;
}

export interface RichTextResult {
  html: string;
  isRich: boolean;
  urls: string[];
  mentions: MentionInfo[];
}

/**
 * 转义 HTML 特殊字符
 */
function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
}

/**
 * 应用 Markdown 格式转换
 */
function applyMarkdown(text: string): string {
  let escaped = escapeHtml(text);

  // 代码块（多行）
  escaped = escaped.replace(/```([\s\S]*?)```/g, (match, code) => {
    return `<pre style="background-color:#f3f4f6;padding:8px;border-radius:4px;overflow-x:auto;"><code>${code}</code></pre>`;
  });

  // 行内代码
  escaped = escaped.replace(/`([^`]+)`/g, (match, code) => {
    return `<code style="background-color:#f3f4f6;padding:2px 4px;border-radius:3px;font-family:monospace;">${code}</code>`;
  });

  // 标题（# 到 ######）
  for (let i = 1; i <= 6; i++) {
    const regex = new RegExp(`^${'#'.repeat(i)}\\s+(.+)$`, 'gm');
    escaped = escaped.replace(regex, (match, title) => {
      const fontSize = 18 - i * 2;
      return `<h${i} style="margin:8px 0;font-size:${fontSize}px;font-weight:bold;">${title}</h${i}>`;
    });
  }

  // 引用
  escaped = escaped.replace(/^>\s+(.+)$/gm, (match, quote) => {
    return `<blockquote style="border-left:3px solid #d1d5db;padding-left:12px;margin:8px 0;color:#6b7280;">${quote}</blockquote>`;
  });

  // 无序列表
  escaped = escaped.replace(/^[-*]\s+(.+)$/gm, (match, item) => {
    return `<li style="margin:4px 0;">${item}</li>`;
  });
  // 将连续的 <li> 包裹在 <ul> 中
  escaped = escaped.replace(/(<li[^>]*>.*?<\/li>(?:\s*<li[^>]*>.*?<\/li>)*)/g, (match) => {
    return `<ul style="margin:8px 0;padding-left:20px;">${match}</ul>`;
  });

  // 有序列表
  escaped = escaped.replace(/^\d+\.\s+(.+)$/gm, (match, item) => {
    return `<li style="margin:4px 0;">${item}</li>`;
  });
  // 将连续的 <li> 包裹在 <ol> 中
  escaped = escaped.replace(/(<li[^>]*>.*?<\/li>(?:\s*<li[^>]*>.*?<\/li>)*)/g, (match) => {
    return `<ol style="margin:8px 0;padding-left:20px;">${match}</ol>`;
  });

  // 加粗 **text** 或 __text__
  escaped = escaped.replace(/\*\*([^*]+)\*\*|__([^_]+)__/g, (match, g1, g2) => {
    return `<strong>${g1 || g2}</strong>`;
  });

  // 斜体 *text* 或 _text_（但不在加粗中）
  escaped = escaped.replace(/(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)/g, (match, g1, g2) => {
    return `<em>${g1 || g2}</em>`;
  });

  // Markdown 链接 [text](url)
  escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, url) => {
    const href = /^https?:\/\//i.test(url) ? url : `http://${url}`;
    return `<a href="${href}" target="_blank" rel="noopener noreferrer" style="color:#2563eb;text-decoration:none;">${label}</a>`;
  });

  // 换行
  escaped = escaped.replace(/\n/g, '<br/>');

  return escaped;
}

/**
 * 应用 @提及 高亮
 */
function applyMentions(html: string): { html: string; mentions: MentionInfo[] } {
  const mentions: MentionInfo[] = [];
  const mentionKeywords = ['客服', 'service', 'support', 'agent'];

  const newHtml = html.replace(MENTION_PATTERN, (match, name) => {
    const mentionType: 'user' | 'service' = mentionKeywords.some(
      (keyword) => name.toLowerCase().includes(keyword)
    )
      ? 'service'
      : 'user';

    mentions.push({
      type: mentionType,
      name: name,
    });

    return `<span style="color:#7c3aed;font-weight:600;background-color:rgba(124,58,237,0.1);padding:2px 6px;border-radius:4px;cursor:pointer;" class="mention" data-mention-type="${mentionType}" data-mention-name="${name}">@${name}</span>`;
  });

  return { html: newHtml, mentions };
}

/**
 * 应用自动链接转换
 */
function applyAutoLink(html: string): { html: string; urls: string[] } {
  const urls: string[] = [];

  const newHtml = html.replace(URL_PATTERN, (match) => {
    // 避免处理已经在 a 标签中的 url
    const beforeText = html.substring(Math.max(0, html.indexOf(match) - 10), html.indexOf(match));
    if (beforeText.includes('</a>') || beforeText.includes('<a')) {
      return match;
    }

    const href = /^https?:\/\//i.test(match) ? match : `http://${match}`;
    urls.push(href);
    return `<a href="${href}" target="_blank" rel="noopener noreferrer" style="color:#2563eb;text-decoration:none;">${match}</a>`;
  });

  return { html: newHtml, urls };
}

/**
 * 处理富文本消息
 */
export function processRichText(content: string): RichTextResult {
  if (!content) {
    return {
      html: '',
      isRich: false,
      urls: [],
      mentions: [],
    };
  }

  // 快速检测：若既无 markdown 符号、无 @、又无 URL 特征，则直接返回
  const hasMarkdown = /[*`#>\[\-]/.test(content);
  const hasUrl = /https?:\/\/|www\.|ftp:\/\//i.test(content);
  const hasMention = content.includes('@');

  if (!hasMarkdown && !hasUrl && !hasMention) {
    return {
      html: content,
      isRich: false,
      urls: [],
      mentions: [],
    };
  }

  // 应用 Markdown
  let html = applyMarkdown(content);

  // 应用 @提及（在链接之前，避免链接中的@被处理）
  const { html: htmlWithMentions, mentions } = applyMentions(html);
  html = htmlWithMentions;

  // 应用自动链接（最后处理，避免破坏已有的格式）
  const { html: finalHtml, urls } = applyAutoLink(html);

  return {
    html: finalHtml,
    isRich: true,
    urls,
    mentions,
  };
}

/**
 * 从文本中提取所有URL
 */
export function extractUrlsFromText(text: string): string[] {
  const urls: string[] = [];
  const matches = text.matchAll(URL_PATTERN);
  for (const match of matches) {
    const url = match[0];
    const href = /^https?:\/\//i.test(url) ? url : `http://${url}`;
    urls.push(href);
  }
  return urls;
}

/**
 * 从文本中提取所有@提及
 */
export function extractMentionsFromText(text: string): MentionInfo[] {
  const mentions: MentionInfo[] = [];
  const mentionKeywords = ['客服', 'service', 'support', 'agent'];
  const matches = text.matchAll(MENTION_PATTERN);
  for (const match of matches) {
    const name = match[1];
    const mentionType: 'user' | 'service' = mentionKeywords.some(
      (keyword) => name.toLowerCase().includes(keyword)
    )
      ? 'service'
      : 'user';
    mentions.push({
      type: mentionType,
      name: name,
    });
  }
  return mentions;
}

