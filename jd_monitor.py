#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time
import re
import logging
import os
import random
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from configparser import ConfigParser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jd_monitor.log"),
        logging.StreamHandler()
    ]
)

class JDMonitor:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.load_config()
        self.session = requests.Session()
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            self.create_default_config()
            
        config = ConfigParser()
        config.read(self.config_file, encoding='utf-8')
        
        self.jd_url = config.get('JD', 'product_url')
        self.check_interval = config.getint('Monitor', 'check_interval')
        self.notify_minutes_before = config.getint('Monitor', 'notify_minutes_before')
        self.wxpusher_token = config.get('WxPusher', 'token')
        self.wxpusher_uids = json.loads(config.get('WxPusher', 'uids'))
        
        # 解析商品ID
        self.product_id = self.extract_product_id(self.jd_url)
        logging.info(f"监控商品ID: {self.product_id}")
        
    def create_default_config(self):
        """创建默认配置文件"""
        config = ConfigParser()
        
        config['JD'] = {
            'product_url': 'https://3.cn/2eg-GYHr'
        }
        
        config['Monitor'] = {
            'check_interval': '60',  # 检查间隔，单位秒
            'notify_minutes_before': '5'  # 提前通知时间，单位分钟
        }
        
        config['WxPusher'] = {
            'token': '请在这里填入你的WxPusher的Token',
            'uids': '[]'  # 接收通知的用户ID列表，JSON格式
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            config.write(f)
            
        logging.info(f"已创建默认配置文件: {self.config_file}，请修改配置后重新运行程序")
        
    def extract_product_id(self, url):
        """从京东链接中提取商品ID"""
        # 处理短链接
        if '3.cn' in url or 'item.jd.com' not in url:
            try:
                r = requests.get(url, allow_redirects=False)
                if 'Location' in r.headers:
                    url = r.headers['Location']
            except Exception as e:
                logging.error(f"解析短链接失败: {e}")
        
        # 尝试从URL中提取商品ID
        patterns = [
            r'item\.jd\.com\/(\d+)\.html',  # 标准商品页面
            r'product\/(\d+)\.html',         # 有些商品页面格式
            r'\?id=(\d+)'                    # URL参数中的ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # 如果上面都没匹配到，尝试解析查询参数
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # 检查常见的ID参数名
        for param in ['id', 'productId', 'product_id', 'sku', 'skuId']:
            if param in query_params:
                return query_params[param][0]
                
        logging.error(f"无法从URL中提取商品ID: {url}")
        return None
    
    def check_product_status(self):
        """检查商品状态"""
        if not self.product_id:
            logging.error("商品ID无效，无法检查商品状态")
            return False, None, None
            
        try:
            # 使用京东API检查商品状态
            api_url = f"https://item-soa.jd.com/getWareBusiness?skuId={self.product_id}"
            response = self.session.get(api_url)
            data = response.json()
            
            # 添加随机延迟，避免被检测为机器人
            time.sleep(random.uniform(1, 3))
            
            # 检查商品状态
            stock_state = data.get('stockInfo', {}).get('stockState', 0)
            product_name = data.get('wareInfo', {}).get('wname', '未知商品')
            price = data.get('price', {}).get('p', '未知价格')
            
            # 商品是否可购买 (33 - 有货, 34 - 无货, 36 - 预售, 40 - 可配送)
            is_available = stock_state in [33, 40]
            
            # 获取预约或抢购信息
            yuyue_info = data.get('yuyueInfo', {})
            if yuyue_info:
                yuyue_start_time = yuyue_info.get('startTime', 0) / 1000 if 'startTime' in yuyue_info else 0
                if yuyue_start_time > 0:
                    start_time = datetime.fromtimestamp(yuyue_start_time)
                    return is_available, product_name, start_time
            
            return is_available, product_name, None
            
        except Exception as e:
            logging.error(f"检查商品状态时出错: {e}")
            return False, None, None
    
    def send_wxpusher_notification(self, title, content):
        """发送WxPusher通知"""
        if not self.wxpusher_token or not self.wxpusher_uids:
            logging.error("WxPusher配置不完整，无法发送通知")
            return False
            
        try:
            url = "https://wxpusher.zjiecode.com/api/send/message"
            data = {
                "appToken": self.wxpusher_token,
                "content": content,
                "summary": title,  # 消息摘要，显示在微信通知上
                "contentType": 1,  # 内容类型 1-文本 2-HTML
                "uids": self.wxpusher_uids,
                "url": f"https://item.jd.com/{self.product_id}.html"  # 点击消息跳转的链接
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get('success'):
                logging.info(f"WxPusher通知发送成功: {title}")
                return True
            else:
                logging.error(f"WxPusher通知发送失败: {result}")
                return False
                
        except Exception as e:
            logging.error(f"发送WxPusher通知时出错: {e}")
            return False
    
    def run(self):
        """运行监控程序"""
        logging.info(f"开始监控京东商品: {self.jd_url}")
        logging.info(f"检查间隔: {self.check_interval}秒, 提前通知时间: {self.notify_minutes_before}分钟")
        
        notification_sent = False
        last_status = False
        
        while True:
            try:
                is_available, product_name, start_time = self.check_product_status()
                
                current_time = datetime.now()
                status_changed = is_available != last_status
                last_status = is_available
                
                if product_name:
                    logging.info(f"商品: {product_name} - {'可购买' if is_available else '不可购买'}")
                
                # 如果有开售时间，检查是否需要提前通知
                if start_time and not notification_sent:
                    time_diff = start_time - current_time
                    minutes_to_start = time_diff.total_seconds() / 60
                    
                    # 如果距离开售时间小于等于提前通知时间，发送通知
                    if 0 < minutes_to_start <= self.notify_minutes_before:
                        title = f"⏰ 京东商品即将开售提醒"
                        content = f"您监控的商品【{product_name}】将在{minutes_to_start:.1f}分钟后开始销售！\n\n开售时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n立即前往: https://item.jd.com/{self.product_id}.html"
                        
                        self.send_wxpusher_notification(title, content)
                        notification_sent = True
                        logging.info(f"已发送商品即将开售提醒，开售时间: {start_time}")
                
                # 如果商品状态变为可购买，发送通知
                if is_available and status_changed:
                    title = f"🎉 京东商品已上架可购买"
                    content = f"您监控的商品【{product_name}】已经上架可以购买了！\n\n立即前往: https://item.jd.com/{self.product_id}.html"
                    
                    self.send_wxpusher_notification(title, content)
                    logging.info(f"商品已上架可购买，已发送通知")
                
                # 等待下一次检查
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logging.info("程序已手动停止")
                break
                
            except Exception as e:
                logging.error(f"监控过程中出错: {e}")
                # 出错后等待一段时间再继续
                time.sleep(max(30, self.check_interval))

if __name__ == "__main__":
    monitor = JDMonitor()
    monitor.run()