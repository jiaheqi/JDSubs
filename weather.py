import requests
import logging
from datetime import datetime
import time
from configparser import ConfigParser
import json

class WeatherMonitor:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        config = ConfigParser()
        config.read(self.config_file, encoding='utf-8')

        self.api_key = config.get('Weather', 'api_key')
        self.city_id = config.get('Weather', 'city_id')
        self.push_time = config.get('Weather', 'push_time')
        self.wxpusher_token = config.get('WxPusher', 'token')
        self.wxpusher_uids = json.loads(config.get('WxPusher', 'uids'))

    def get_weather_forecast(self):
        """获取明天的天气预报"""
        try:
            # 高德天气API接口
            url = "https://restapi.amap.com/v3/weather/weatherInfo"
            params = {
                'city': self.city_id,
                'key': self.api_key,
                'extensions': 'all'  # 获取预报天气
            }
            response = requests.get(url, params=params)
            data = response.json()

            if data['status'] == '1' and data['forecasts']:
                # 获取明天的天气数据（索引0是今天，1是明天）
                forecasts = data['forecasts'][0]['casts'][1]
                return {
                    'date': forecasts['date'],
                    'temp_max': forecasts['daytemp'],
                    'temp_min': forecasts['nighttemp'],
                    'weather': forecasts['dayweather'],
                    'weather_night': forecasts['nightweather'],
                    'humidity': forecasts.get('humidity', '未知'),  # 高德API可能没有湿度数据
                    'precip': '0',  # 高德API没有直接提供降水量
                    'wind_dir': forecasts['daywind'] + '风',
                    'wind_scale': forecasts['daypower']
                }
            else:
                logging.error(f"获取天气数据失败: {data['code']}, {data.get('message', '')}")
                return None

        except Exception as e:
            logging.error(f"获取天气数据时出错: {e}")
            return None

    def format_weather_message(self, weather_data):
        """格式化天气消息"""
        if not weather_data:
            return None

        # 根据天气状况选择对应的emoji
        weather_emoji = {
            '晴': '☀️',
            '多云': '⛅️',
            '阴': '☁️',
            '雨': '🌧️',
            '雪': '❄️'
        }

        # 获取天气对应的emoji，如果没有匹配则使用默认emoji
        day_emoji = next((v for k, v in weather_emoji.items() if k in weather_data['weather']), '🌈')
        night_emoji = next((v for k, v in weather_emoji.items() if k in weather_data['weather_night']), '🌙')

        message = f"🌅 明日天气预报 {weather_data['date']}\n\n"
        message += f"白天: {day_emoji} {weather_data['weather']}\n"
        message += f"夜间: {night_emoji} {weather_data['weather_night']}\n\n"
        message += f"🌡️ 温度: {weather_data['temp_min']}°C ~ {weather_data['temp_max']}°C\n"
        message += f"💧 降水量: {weather_data['precip']}mm\n"
        message += f"💨 {weather_data['wind_dir']} {weather_data['wind_scale']}级\n"
        message += f"💦 相对湿度: {weather_data['humidity']}%\n\n"

        # 添加温馨提示
        tips = []
        try:
            temp_max = float(weather_data['temp_max'])
            temp_min = float(weather_data['temp_min'])
            if temp_max >= 30:
                tips.append('☀️ 温度较高，注意防暑降温')
            if temp_min <= 10:
                tips.append('❄️ 温度较低，注意保暖')
        except (ValueError, TypeError):
            logging.warning(f"温度数据格式异常: max={weather_data['temp_max']}, min={weather_data['temp_min']}")

        try:
            if float(weather_data['precip']) > 0:
                tips.append('☔️ 有降水，记得带伞')
        except (ValueError, TypeError):
            logging.warning(f"降水量数据格式异常: {weather_data['precip']}")

        try:
            # 处理风力等级可能包含范围的情况（如'1-3'）
            wind_scale = weather_data['wind_scale']
            if '-' in wind_scale:
                max_wind = int(wind_scale.split('-')[1])
            else:
                max_wind = int(wind_scale)
            if max_wind >= 4:
                tips.append('🌪️ 风力较大，注意防风')
        except (ValueError, TypeError, IndexError):
            logging.warning(f"风力等级数据格式异常: {weather_data['wind_scale']}")


        if tips:
            message += "温馨提示:\n" + "\n".join(tips)

        return message

    def send_wxpusher_notification(self, content):
        """发送WxPusher通知"""
        if not self.wxpusher_token or not self.wxpusher_uids:
            logging.error("WxPusher配置不完整，无法发送通知")
            return False

        try:
            url = "https://wxpusher.zjiecode.com/api/send/message"
            data = {
                "appToken": self.wxpusher_token,
                "content": content,
                "summary": "今日天气预报",
                "contentType": 1,
                "uids": self.wxpusher_uids
            }

            response = requests.post(url, json=data)
            result = response.json()

            if result.get('success'):
                logging.info("天气预报推送成功")
                return True
            else:
                logging.error(f"天气预报推送失败: {result}")
                return False

        except Exception as e:
            logging.error(f"发送天气预报通知时出错: {e}")
            return False

    def run(self):
        """运行天气监控程序"""
        logging.info("启动天气预报推送服务")
        
        while True:
            try:
                current_time = datetime.now()
                target_time = datetime.strptime(self.push_time, '%H:%M').time()
                
                # 如果当前时间等于目标推送时间
                if current_time.hour == target_time.hour and current_time.minute == target_time.minute:
                    # 获取并推送天气信息
                    weather_data = self.get_weather_forecast()
                    if weather_data:
                        message = self.format_weather_message(weather_data)
                        if message:
                            self.send_wxpusher_notification(message)
                    
                    # 等待一分钟，避免重复推送
                    time.sleep(60)
                else:
                    # 每分钟检查一次
                    time.sleep(60)

            except Exception as e:
                logging.error(f"天气预报服务运行出错: {e}")
                time.sleep(60)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('weather.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    weather_monitor = WeatherMonitor()
    weather_monitor.run()