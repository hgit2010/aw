# -*- coding: utf-8 -*-
import json
import re
import sys
from urllib.parse import quote
sys.path.append('..')
from base.spider import Spider
from pyquery import PyQuery as pq

class Spider(Spider):
    def getName(self):
        return "QS五月天"

    def init(self, extend=""):
        self.host = "https://qswyt4444.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'{self.host}/',
        }

    def homeContent(self, filter):
        result = {}
        # 完整 36 个分类
        classes = [{'type_id': f'/movie/block/{i}', 'type_name': n} for i, n in [
            (21,'淫荡少妇'),(22,'人妻诱惑'),(23,'大奶萝莉'),(24,'丝袜制服'),(25,'母狗调教'),
            (26,'白虎嫩逼'),(27,'性爱自拍'),(28,'洗澡偷拍'),(29,'厕所偷拍'),(30,'酒店偷拍'),
            (31,'监控破解'),(32,'街头抄底'),(33,'兄妹乱伦'),(34,'嫂子乱伦'),(35,'母子乱伦'),
            (36,'姐弟乱伦'),(37,'父女乱伦'),(38,'爱上小姨子'),(39,'高端外围'),(40,'金先生探花'),
            (41,'探花寻欢'),(42,'足浴嫖娼'),(43,'学生兼职'),(44,'约炮实录'),(45,'强奸'),
            (46,'群P'),(47,'偷情'),(48,'破处'),(49,'舔逼'),(50,'同志'),
            (51,'主播'),(52,'护士'),(53,'技师'),(54,'空姐'),(55,'老师'),(56,'嫩模')
        ]]
        result['class'] = classes
        return result

    def homeVideoContent(self):
        try:
            res = self.fetch(self.host, headers=self.headers)
            return {'list': self.parse_list(res.text)}
        except:
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        url = f'{self.host}{tid}?page={pg}'
        res = self.fetch(url, headers=self.headers)
        return {'list': self.parse_list(res.text), 'page': pg, 'pagecount': 999, 'limit': 20}

    def parse_list(self, html):
        videos = []
        pattern = r'\{"id":\d+,"name":\d+,"user_id":\d+,"type":\d+[^}]*\},"([a-f0-9]{16})","([^"]+?)",.*?"(https?://[^"]+?dcc-file[^"]+?\.(?:jpg|png|jpeg|webp)[^"]*?)"'
        
        matches = re.finditer(pattern, html)
        seen_ids = set()

        for m in matches:
            vid, name, pic = m.groups()
            if vid in seen_ids: continue
            
            # 时长提取
            scope = html[m.end():m.end()+500]
            rem = re.search(r'"(\d{1,2}:\d{2}(?::\d{2})?)"', scope)
            
            videos.append({
                'vod_id': f"{vid}###{name}###{pic}",
                'vod_name': name,
                'vod_pic': pic,
                'vod_remarks': rem.group(1) if rem else ""
            })
            seen_ids.add(vid)
        return videos

    def detailContent(self, array):
        parts = array[0].split('###')
        vid = parts[0]
        name = parts[1] if len(parts) > 1 else ""
        pic = parts[2] if len(parts) > 2 else ""

        url = f'{self.host}/movie/detail/{vid}'
        res = self.fetch(url, headers=self.headers)
        html = res.text

        vod_play_url_list = []
        lines = re.findall(r'"name":"(线路\d+)".*?"m3u8_url":"([^"]+?)"', html)
        for ln, path in lines:
            vod_play_url_list.append(f"{ln}${self.host}{path}")

        if not vod_play_url_list:
            m3u8s = re.findall(r'"(/api/m3u8/p/[a-f0-9]+\.m3u8)"', html)
            for i, p in enumerate(m3u8s):
                vod_play_url_list.append(f"线路{i+1}${self.host}{p}")

        return {"list": [{
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_play_from": "WytPlayer",
            "vod_play_url": "#".join(vod_play_url_list)
        }]}

    def searchContent(self, key, quick, pg="1"):
        url = f'{self.host}/search/{quote(key)}?page={pg}'
        res = self.fetch(url, headers=self.headers)
        return {"list": self.parse_list(res.text)}

    def playerContent(self, flag, id, vipFlags):
        return {'parse': 0, 'url': id, 'header': json.dumps(self.headers)}