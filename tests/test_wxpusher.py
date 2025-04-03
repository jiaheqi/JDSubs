#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import json
from unittest.mock import patch, MagicMock
from configparser import ConfigParser
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from jd_monitor_lite import JDMonitor

class TestWxPusherNotification(unittest.TestCase):
    def setUp(self):
        # 创建测试配置文件
        self.test_config = 'test_config.ini'
        config = ConfigParser()
        config['JD'] = {'product_url': 'https://item.jd.com/123456.html'}
        config['Monitor'] = {
            'check_interval': '60',
            'notify_minutes_before': '5'
        }
        config['WxPusher'] = {
            'token': 'test_token',
            'uids': '["test_uid1", "test_uid2"]'
        }
        with open(self.test_config, 'w', encoding='utf-8') as f:
            config.write(f)
            
        self.monitor = JDMonitor(config_file=self.test_config)
    
    def tearDown(self):
        # 清理测试配置文件
        if os.path.exists(self.test_config):
            os.remove(self.test_config)
    
    @patch('urllib.request.urlopen')
    def test_successful_notification(self, mock_urlopen):
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'success': True,
            'msg': 'success',
            'data': {'messageId': '123'}
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        result = self.monitor.send_wxpusher_notification(
            "测试标题",
            "测试内容"
        )
        self.assertTrue(result)
    
    @patch('urllib.request.urlopen')
    def test_failed_notification(self, mock_urlopen):
        # 模拟失败响应
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'success': False,
            'msg': 'invalid token',
            'data': None
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        result = self.monitor.send_wxpusher_notification(
            "测试标题",
            "测试内容"
        )
        self.assertFalse(result)
    
    def test_invalid_config(self):
        # 测试配置不完整的情况
        self.monitor.wxpusher_token = ''
        result = self.monitor.send_wxpusher_notification(
            "测试标题",
            "测试内容"
        )
        self.assertFalse(result)
        
        self.monitor.wxpusher_token = 'test_token'
        self.monitor.wxpusher_uids = []
        result = self.monitor.send_wxpusher_notification(
            "测试标题",
            "测试内容"
        )
        self.assertFalse(result)
    
    @patch('urllib.request.urlopen')
    def test_network_error(self, mock_urlopen):
        # 模拟网络错误
        mock_urlopen.side_effect = Exception('Network error')
        
        result = self.monitor.send_wxpusher_notification(
            "测试标题",
            "测试内容"
        )
        self.assertFalse(result)
    
    @patch('urllib.request.urlopen')
    def test_json_decode_error(self, mock_urlopen):
        # 模拟JSON解析错误
        mock_response = MagicMock()
        mock_response.read.return_value = b'Invalid JSON'
        mock_urlopen.return_value = mock_response
        
        result = self.monitor.send_wxpusher_notification(
            "测试标题",
            "测试内容"
        )
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()