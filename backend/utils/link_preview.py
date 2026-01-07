"""
链接预览模块
获取链接的元数据（标题、描述、图片等）
"""
import re
import logging
from typing import Dict, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def is_valid_url(url: str) -> bool:
    """检查URL是否有效"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def fetch_link_preview(url: str, timeout: int = 5) -> Dict[str, any]:
    """
    获取链接预览信息
    
    Args:
        url: 链接URL
        timeout: 请求超时时间（秒）
    
    Returns:
        {
            "url": 原始URL,
            "title": 页面标题,
            "description": 页面描述,
            "image": 预览图片URL,
            "site_name": 网站名称,
            "success": 是否成功
        }
    """
    if not is_valid_url(url):
        return {
            "url": url,
            "title": None,
            "description": None,
            "image": None,
            "site_name": None,
            "success": False
        }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 提取标题
        title = None
        # 优先使用 og:title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title.get("content").strip()
        # 其次使用 title 标签
        if not title:
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()
        
        # 提取描述
        description = None
        # 优先使用 og:description
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            description = og_desc.get("content").strip()
        # 其次使用 description meta
        if not description:
            desc_meta = soup.find("meta", attrs={"name": "description"})
            if desc_meta and desc_meta.get("content"):
                description = desc_meta.get("content").strip()
        
        # 提取图片
        image = None
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            image_url = og_image.get("content").strip()
            # 如果是相对路径，转换为绝对路径
            if image_url.startswith("//"):
                image_url = f"{urlparse(url).scheme}:{image_url}"
            elif image_url.startswith("/"):
                parsed = urlparse(url)
                image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
            image = image_url
        
        # 提取网站名称
        site_name = None
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            site_name = og_site.get("content").strip()
        if not site_name:
            parsed = urlparse(url)
            site_name = parsed.netloc
        
        return {
            "url": url,
            "title": title or "无标题",
            "description": description or "",
            "image": image,
            "site_name": site_name or urlparse(url).netloc,
            "success": True
        }
        
    except requests.exceptions.Timeout:
        logger.warning(f"获取链接预览超时: {url}")
        return {
            "url": url,
            "title": None,
            "description": None,
            "image": None,
            "site_name": urlparse(url).netloc,
            "success": False
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"获取链接预览失败: {url}, 错误: {e}")
        return {
            "url": url,
            "title": None,
            "description": None,
            "image": None,
            "site_name": urlparse(url).netloc,
            "success": False
        }
    except Exception as e:
        logger.error(f"解析链接预览时出错: {url}, 错误: {e}", exc_info=True)
        return {
            "url": url,
            "title": None,
            "description": None,
            "image": None,
            "site_name": urlparse(url).netloc,
            "success": False
        }


def get_simple_preview(url: str) -> Dict[str, str]:
    """
    获取简单的链接预览（仅基于URL，不请求页面）
    用于快速预览或请求失败时的降级方案
    """
    try:
        parsed = urlparse(url)
        site_name = parsed.netloc or parsed.path
        if site_name.startswith("www."):
            site_name = site_name[4:]
        
        return {
            "url": url,
            "title": site_name,
            "description": "",
            "image": None,
            "site_name": site_name,
            "success": True
        }
    except Exception:
        return {
            "url": url,
            "title": "链接",
            "description": "",
            "image": None,
            "site_name": "",
            "success": False
        }

