# -*- coding: utf-8 -*-
# by 
import json
import sys
import re
from pyquery import PyQuery as pq

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):

    def init(self, extend=""):
        self.host = "http://goodav17.com"
        self.mag_host = "https://18mag.net"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; 23113RKC6C Build/AQ3A.240912.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/140.0.7339.207 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }

    def getName(self):
        return "GGJAV"

    def isVideoFormat(self, url):
        return url.lower().endswith('.m3u8') or url.startswith('magnet:?')

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "最新": "/new",
            "分类": "/categories",
            "女优": "/actresses"
        }
        classes = []
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        result['class'] = classes
        return result

    def homeVideoContent(self):
        return {'list': self.get_video_list(self.host)}

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        vdata = []

        if tid == '/categories':
            data = self.getpq("/")
            seen = set()
            for a in data('a').items():
                href = a.attr('href')
                if href and '/type/' in href:
                    parts = [p for p in href.strip('/').split('/') if p]
                    try:
                        idx = parts.index('type')
                        if idx + 1 < len(parts):
                            name = parts[idx+1]
                            cat_id = f"/type/{name}"
                            decoded_name = self.unquote_str(name)
                            if cat_id not in seen and decoded_name:
                                seen.add(cat_id)
                                vdata.append({
                                    'vod_id': cat_id,
                                    'vod_name': decoded_name,
                                    'vod_tag': 'folder',
                                    'style': {'ratio': 1.1, 'type': 'rect'}
                                })
                    except:
                        continue

        elif tid == '/actresses':
            data = self.getpq("/")
            seen = set()
            for a in data('a').items():
                href = a.attr('href')
                text = a.text()
                if href and '/actor/' in href:
                    parts = [p for p in href.strip('/').split('/') if p]
                    try:
                        idx = parts.index('actor')
                        if idx + 1 < len(parts):
                            name = parts[idx+1]
                            act_id = f"/actor/{name}"
                            decoded_name = self.unquote_str(name)
                            if act_id not in seen and decoded_name:
                                seen.add(act_id)
                                vdata.append({
                                    'vod_id': act_id,
                                    'vod_name': decoded_name or text,
                                    'vod_tag': 'folder',
                                    'style': {'ratio': 1, 'type': 'oval'}
                                })
                    except:
                        continue

        else:
            if tid == '/new':
                url = f"{self.host}/?page={pg}"
            else:
                clean_tid = tid.rstrip('/')
                url = f"{self.host}{clean_tid}/{pg}/"
            vdata = self.get_video_list(url)

        result['list'] = vdata
        return result

    def detailContent(self, ids):
        url = ids[0] if ids[0].startswith('http') else f"{self.host}{ids[0]}"
        data = self.getpq(url)

        if not data or not data('title').text():
             return {'list': [{'vod_name': '加载失败', 'vod_play_from': 'Error', 'vod_play_url': 'Error$#'}]}

        title = data('title').text()
        if ' - 正妹AV' in title:
            title = title.split(' - 正妹AV')[0]

        content = data('meta[name="description"]').attr('content') or ""
        if ' - 正妹AV' in content:
            content = content.split(' - 正妹AV')[0]
        if ',,' in content:
             content = content.split(',,')[0]

        mag_search_url = ""
        for a in data('a').items():
            href = a.attr('href')
            if href and '18mag.net' in href:
                mag_search_url = href
                break

        iframe_src = ""
        for iframe in data('iframe').items():
            src = iframe.attr('src') or ""
            if 'embed' in src or 'ggjav' in src:
                iframe_src = src
                break

        if not iframe_src:
            html = str(data)
            match = re.search(r'src=["\'](https?://[^"\']*(?:ggjav|embed)[^"\']*)["\']', html)
            if match:
                iframe_src = match.group(1)

        play_url_ggjav = f"Play${iframe_src}" if iframe_src else "Error$无法获取播放地址"
        play_url_mag = f"MagnetSearch${mag_search_url}" if mag_search_url else "无磁力$#"

        vod = {
            'vod_name': title,
            'vod_play_from': 'GGJAV$$$磁力链接',
            'vod_play_url': f"{play_url_ggjav}$$${play_url_mag}",
            'vod_content': content,
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = f"{self.host}/search/{key}/{pg}/"
        return {'list': self.get_video_list(url), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        safe_headers = self.headers.copy()
        safe_headers['Cookie'] = ''

        if flag == '磁力链接' or flag == 'Magnet' or 'MagnetSearch$' in id:
            try:
                search_url = id.split('$', 1)[1] if '$' in id else id
                if not search_url.startswith('http'):
                    return {'parse': 0, 'url': id, 'error': '无效搜索链接', 'header': safe_headers}

                mag_headers = {'User-Agent': self.headers['User-Agent']}
                s_resp = self.fetch(search_url, headers=mag_headers)
                s_html = s_resp.text if hasattr(s_resp, 'text') else str(s_resp)

                detail_matches = re.findall(r'href=["\'](/![^"\']+)["\']', s_html)

                if detail_matches:
                    detail_link = detail_matches[0]
                    d_url = f"{self.mag_host}{detail_link}"

                    d_resp = self.fetch(d_url, headers=mag_headers)
                    d_html = d_resp.text if hasattr(d_resp, 'text') else str(d_resp)

                    mag_match = re.search(r'(magnet:\?xt=urn:btih:[^\s"\'<>]+)', d_html)

                    if mag_match:
                        full_magnet = mag_match.group(1)

                        xt = re.search(r'(xt=urn:btih:[a-zA-Z0-9]+)', full_magnet)
                        dn = re.search(r'(dn=[^&]+)', full_magnet)
                        xl = re.search(r'(xl=[0-9]+)', full_magnet)

                        parts = []
                        if xt: parts.append(xt.group(1))
                        if dn: parts.append(dn.group(1))
                        if xl: parts.append(xl.group(1))

                        if parts:
                            clean_magnet = 'magnet:?' + '&'.join(parts)
                        else:
                            clean_magnet = full_magnet.split('&tr=')[0]

                        push_url = 'push://' + clean_magnet

                        return {
                            'parse': 0,
                            'url': push_url,
                            'header': safe_headers
                        }
                    else:
                        return {'parse': 0, 'url': id, 'error': '详情页无磁力', 'header': safe_headers}
                else:
                    return {'parse': 0, 'url': id, 'error': '未找到详情页链接', 'header': safe_headers}

            except Exception as e:
                print(f"Magnet Error: {e}")
                return {'parse': 0, 'url': id, 'error': '磁力异常', 'header': safe_headers}

        try:
            play_url = id.split('$', 1)[1] if '$' in id else id

            ggjav_headers = safe_headers.copy()
            ggjav_headers['Referer'] = self.host

            response = self.fetch(play_url, headers=ggjav_headers)
            content = response.text if hasattr(response, 'text') else str(response)
            match = re.search(r'(https?://[^"\']+\.m3u8)', content)

            if match:
                return {'parse': 0, 'url': match.group(1), 'header': ggjav_headers}
            else:
                return {'parse': 0, 'url': play_url, 'error': 'M3U8 not found', 'header': ggjav_headers}
        except Exception as e:
            return {'parse': 0, 'url': id, 'header': safe_headers}

    def get_video_list(self, url):
        data = self.getpq(url)
        vlist = []
        for item in data('.movie').items():
            link = item('a').attr('href')
            if not link or 'html' not in link:
                continue

            vid_id = link.replace(self.host, '')
            img = item('.movie_image img')
            pic = img.attr('large_image') or img.attr('src') or img.attr('data-original')

            title = img.attr('alt') or item.text()
            if ' - 正妹AV' in title:
                title = title.split(' - 正妹AV')[0]
            if ',' in title and len(title) > 30:
                match = re.search(r'[A-Za-z]+-\d+', title)
                if match:
                    start = match.start()
                    title = title[start:]

            vlist.append({'vod_id': vid_id, 'vod_name': title, 'vod_pic': pic, 'vod_tag': '', 'style': {'ratio': 1.33, 'type': 'rect'}})
        return vlist

    def unquote_str(self, s):
        try:
            from urllib.parse import unquote
            return unquote(s)
        except:
            return s

    def getpq(self, path=''):
        url = path if path.startswith('http') else f'{self.host}{path}'
        try:
            response = self.fetch(url, headers=self.headers)
            content = response.text if hasattr(response, 'text') else str(response)
            return pq(content)
        except Exception as e:
            return pq("<html></html>")
