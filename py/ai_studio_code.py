# -*- coding: utf-8 -*-
import re
import urllib.parse
import requests

class Spider:
    def __init__(self):
        self.name = '玩物社区'
        self.host = 'https://wanwuu.com/'
        self.default_pic = 'https://via.placeholder.com/400x225?text=Video'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S901U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': self.host,
        }
        self.classes = []
        # 修正分类字符串，确保格式正确
        category_str = "国产SM$guochan-sm#日韩SM$rihan-sm#欧美SM$oumei-sm#直播回放$zhibo-huifang#SM小说$novels/new#玩物社区$posts/all"
        for item in category_str.split('#'):
            if '$' in item:
                name, path = item.split('$')
                self.classes.append({"type_name": name, "type_id": path})

    # 框架接口
    def getDependence(self): return []
    def init(self, extend=""): pass
    def isVideoFormat(self, url): return False
    def manualVideoCheck(self): pass
    def getName(self): return self.name
    def homeContent(self, filter): return {"class": self.classes}
    def homeVideoContent(self): return self.categoryContent("guochan-sm", "1", False, {})

    # --- 核心修复：列表解析 ---
    def _parse_videos(self, html):
        """提取视频列表，修复图片不显示问题"""
        videos = []
        
        # 使用 split 分割 class="video-item"，这种方式比正则匹配 div 闭合更稳定
        # 避免因为网站 div 嵌套层级改变导致正则匹配失败
        blocks = html.split('class="video-item"')
        
        # 从第1个元素开始遍历（第0个是头部废料）
        for i in range(1, len(blocks)):
            block = blocks[i]
            
            # 1. 提取链接
            # 查找 href="..." 或 href='...'
            href_match = re.search(r'href=["\']([^"\']+)["\']', block)
            if not href_match:
                continue
            href = href_match.group(1)
            
            # 简单的过滤，确保是视频链接
            if '/videos/' not in href and '/novels/' not in href and '/posts/' not in href:
                continue

            # 2. 提取图片 (增强兼容性)
            pic = ""
            # 很多网站会用 data-src, data-original 等作为懒加载属性
            # 这里的正则兼容了 双引号 " 和 单引号 '
            img_patterns = [
                r'data-src=["\']([^"\']+)["\']',
                r'data-original=["\']([^"\']+)["\']',
                r'data-lazy-src=["\']([^"\']+)["\']',
                r'src=["\']([^"\']+)["\']',
                r'url\((["\']?)([^"\')]+)\1\)' # 匹配 background-image: url(...)
            ]
            
            for p in img_patterns:
                m = re.search(p, block)
                if m:
                    # 获取捕获组中最后一个非空的内容 (针对 url() 的情况)
                    candidate = m.group(len(m.groups()))
                    # 排除无效图片（如加载图标、空白图）
                    if candidate and 'blob:' not in candidate and 'loading' not in candidate and 'placeholder' not in candidate:
                        pic = candidate
                        break
            
            # 3. 提取标题
            title = ""
            # 尝试 title 属性，alt 属性，或者 A 标签内的文本
            t_match = re.search(r'title=["\']([^"\']+)["\']', block)
            if not t_match:
                t_match = re.search(r'alt=["\']([^"\']+)["\']', block)
            if not t_match:
                t_match = re.search(r'<a[^>]+>(.*?)</a>', block)
            
            if t_match:
                title = self.clean_title(t_match.group(1))
            
            if not title:
                continue # 没有标题通常是无效块

            # 4. 提取时长/备注
            remark = ""
            r_match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)', block)
            if r_match:
                remark = r_match.group(1)

            videos.append({
                "vod_id": self._abs(href),
                "vod_name": title,
                "vod_pic": self._abs(pic) if pic else self.default_pic,
                "vod_remarks": remark
            })
        
        return videos

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
            if tid in ("novels/new", "posts/all"):
                url = f"{self.host}{tid}/page/{pg}/" if pg > 1 else f"{self.host}{tid}/"
            else:
                url = f"{self.host}videos/{tid}/page/{pg}/" if pg > 1 else f"{self.host}videos/{tid}/"
            
            r = requests.get(url, headers=self.headers, timeout=10)
            r.encoding = 'utf-8'
            videos = self._parse_videos(r.text)
            return self._page(videos, pg)
        except Exception as e:
            print(f"分类失败: {e}")
            return self._page([], pg)

    def searchContent(self, key, quick, pg='1'):
        try:
            pg = int(pg)
            wd = urllib.parse.quote(key)
            url = f"{self.host}videos/search/{wd}/page/{pg}/" if pg > 1 else f"{self.host}videos/search/{wd}/"
            
            r = requests.get(url, headers=self.headers, timeout=10)
            r.encoding = 'utf-8'
            videos = self._parse_videos(r.text)
            return self._page(videos, pg)
        except Exception as e:
            print(f"搜索失败: {e}")
            return self._page([], pg)

    def detailContent(self, array):
        vid = array[0] if array[0].startswith('http') else self._abs(array[0])
        try:
            r = requests.get(vid, headers=self.headers, timeout=10)
            r.encoding = 'utf-8'
            html = r.text

            title = ""
            title_match = re.search(r'<title>(.*?)</title>', html, re.I)
            if title_match:
                title = re.split(r'[-—_]', title_match.group(1))[0].strip()
            
            pic = ""
            # 详情页图片匹配增强
            for pic_pattern in [
                r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"',
                r'poster=["\']([^"\']+)["\']',
                r'data-poster=["\']([^"\']+)["\']'
            ]:
                pic_match = re.search(pic_pattern, html, re.I)
                if pic_match and 'blob:' not in pic_match.group(1):
                    pic = pic_match.group(1)
                    break
            
            # 使用嗅探模式
            play_url = f"video://{vid}"
            
            vod = {
                "vod_id": vid,
                "vod_name": self.clean_title(title) if title else "视频",
                "vod_pic": self._abs(pic) if pic else self.default_pic,
                "vod_content": title,
                "vod_play_from": self.name,
                "vod_play_url": f"在线播放${play_url}"
            }
            return {"list": [vod]}
        except Exception as e:
            print(f"详情失败: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0, 
            "playUrl": "", 
            "url": id, 
            "header": self.headers
        }

    def _abs(self, url):
        if not url: return ""
        if url.startswith('blob:'): return self.default_pic
        if url.startswith('//'): return 'https:' + url
        if url.startswith('http'): return url
        return urllib.parse.urljoin(self.host, url)

    def _page(self, videos, pg):
        return {
            "list": videos, 
            "page": int(pg), 
            "pagecount": 9999, 
            "limit": 30, 
            "total": 999999
        }

    def clean_title(self, title):
        if not title: return ""
        title = re.sub(r'<[^>]+>', '', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip()

    config = {"player": {}, "filter": {}}
    header = property(lambda self: self.headers)
    
    def localProxy(self, param):
        return []