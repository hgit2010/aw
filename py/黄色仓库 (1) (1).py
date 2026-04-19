import re
import sys
import urllib.parse
import json
import requests
import urllib3
from pyquery import PyQuery as pq

# 禁用SSL证书警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        self.name = "黄色仓库"
        self.header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        }
        self.host = self.getDynamicHost()
        self.header['Referer'] = self.host 

    def getName(self):
        return self.name

    def getDynamicHost(self):
        """动态获取域名，失败则返回保底"""
        fallback = "http://6016ck.cc/" 
        target_url = "http://hscangku.com"
        
        # 临时header用于探测
        temp_header = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36"
        }

        try:
            # 1. 访问发布页
            res = requests.get(target_url, headers=temp_header, verify=False, timeout=5)
            # 2. 提取跳转参数
            match = re.search(r'strU="(.*?)"', res.text)
            if match:
                jump_url = f"{match.group(1)}{target_url}/&p=/"
                # 3. 获取Location (禁止自动跳转)
                res_jump = requests.get(jump_url, headers=temp_header, verify=False, allow_redirects=False, timeout=5)
                real_url = res_jump.headers.get('Location') or res_jump.headers.get('location')
                
                if real_url:
                    return real_url.rstrip('/')
        except:
            pass
        return fallback

    def init(self, extend):
        pass

    def homeContent(self, filter):
        # 【修改】删除了显示当前源的条目，界面更清爽
        classes = [
            {"type_name": "日韩AV", "type_id": "1"},
            {"type_name": "国产系列", "type_id": "2"}, 
            {"type_name": "欧美", "type_id": "3"},
            {"type_name": "成人动漫", "type_id": "4"},
            {"type_name": "日本有码", "type_id": "7"},
            {"type_name": "一本道高清无码", "type_id": "8"},
            {"type_name": "有码中文字幕", "type_id": "9"},
            {"type_name": "日本无码", "type_id": "10"},
            {"type_name": "国产视频", "type_id": "15"},
            {"type_name": "欧美高清", "type_id": "21"},
            {"type_name": "动漫剧情", "type_id": "22"}
        ]
        return {'class': classes}

    def homeVideoContent(self):
        url = f"{self.host}/"
        return self._parse_video_list(url)

    def categoryContent(self, tid, pg, filter, extend):
        if tid == 'new': return self.homeVideoContent()
        url = f"{self.host}/vodtype/{tid}-{pg}.html"
        data = self._parse_video_list(url)
        data['page'] = int(pg)
        data['pagecount'] = 9999
        data['limit'] = 90
        data['total'] = 999999
        return data

    def searchContent(self, key, quick, page='1'):
        url = f"{self.host}/vodsearch/-------------.html?wd={urllib.parse.quote(key)}"
        return self._parse_video_list(url)

    def _parse_video_list(self, url):
        """通用列表解析方法 (含广告过滤)"""
        try:
            rsp = self.fetch(url)
            root = pq(rsp.text)
            videos = []
            
            items = root('.stui-vodlist li')
            if not items: items = root('.ul-img li')

            for item in items.items():
                vid = item.find('a').attr('href')
                
                # 过滤逻辑: 必须以/vodplay/开头
                if not vid or not vid.startswith('/vodplay/'):
                    continue

                title = item.find('a').attr('title') or item.find('h4').text()
                img = item.find('a').attr('data-original') or item.find('.lazyload').attr('data-original')
                rem = item.find('.pic-text').text()

                if title:
                    videos.append({
                        "vod_id": vid,
                        "vod_name": title,
                        "vod_pic": self.getFullUrl(img),
                        "vod_remarks": rem
                    })
            return {'list': videos}
        except:
            return {'list': []}

    def detailContent(self, array):
        ids = array[0]
        try:
            url = self.getFullUrl(ids)
            rsp = self.fetch(url)
            root = pq(rsp.text)
            
            # 1. 提取标题
            raw_title = root('.stui-pannel__head .title').text()
            if not raw_title:
                raw_title = root('title').text().split(' - ')[0]
            
            # 2. 清洗标题：移除干扰词
            clean_title = raw_title.replace('目录', '').replace('为你推荐', '').strip()

            pic = root('.stui-vodlist__thumb').attr('data-original') or root('img').attr('src')
            script_text = root('script').text()

            # 3. 提取播放地址
            m3u8_url = self._extract_m3u8(script_text)
            
            play_url = ""
            if m3u8_url:
                play_url = f"线路1${m3u8_url}"
            else:
                iframe = root('iframe').attr('src')
                if iframe and 'm3u8' in iframe:
                    play_url = f"iframe线路${self.getFullUrl(iframe)}"
                else:
                    play_url = f"详情页线路${url}"

            vod = {
                "vod_id": ids,
                "vod_name": clean_title,
                "vod_pic": self.getFullUrl(pic),
                "vod_content": clean_title, # 简介同步清洗后的标题
                "vod_play_from": "黄色仓库",
                "vod_play_url": play_url
            }
            return {"list": [vod]}
        except:
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        try:
            # 1. 直连
            if '.m3u8' in id:
                return {"parse": 0, "playUrl": "", "url": id, "header": self.header}
            
            # 2. 详情页解析
            real_url = id.split("$")[1] if "$" in id else id
            real_url = self.getFullUrl(real_url)
            
            rsp = self.fetch(real_url)
            m3u8 = self._extract_m3u8(pq(rsp.text)('script').text())
            
            if m3u8:
                return {"parse": 0, "playUrl": "", "url": m3u8, "header": self.header}
        except:
            pass
        return {}

    def _extract_m3u8(self, text):
        """提取m3u8核心逻辑"""
        # 方式1: player_aaaa JSON
        match = re.search(r'player_aaaa\s*=\s*({.*?});', text, re.DOTALL)
        if match:
            try:
                js = json.loads(match.group(1).replace('\\/', '/'))
                url = js.get('url')
                if url and '.m3u8' in url:
                    return self.getFullUrl(url)
            except: pass
            
        # 方式2: 正则提取
        urls = re.findall(r'https?://[^\s"\'<>]+\.m3u8', text)
        if urls: return urls[0]
        
        # 方式3: 相对路径正则
        rel_urls = re.findall(r'"url"\s*:\s*"([^"]+\.m3u8[^"]*)"', text)
        if rel_urls: return self.getFullUrl(rel_urls[0])
            
        return None

    def getFullUrl(self, url):
        if not url: return ""
        if url.startswith("http"): return url
        if url.startswith("//"): return "https:" + url
        return self.host.rstrip('/') + url

    def fetch(self, url):
        return requests.get(url, headers=self.header, verify=False, timeout=10)

    def localProxy(self, param):
        return {}
