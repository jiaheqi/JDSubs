from flask import Flask, render_template, jsonify, request
import subprocess
import psutil
import os
import configparser
import json
from datetime import datetime

app = Flask(__name__)

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

# 从环境变量获取配置
def get_env_config(key, default=None):
    return os.environ.get(key, default)

# 脚本配置
SCRIPTS = {
    'weather': {
        'name': '天气监控',
        'file': 'weather.py',
        'process': None,
        'log_file': 'weather.log'
    },
    'jd_monitor': {
        'name': '京东商品监控',
        'file': 'jd_monitor.py',
        'process': None,
        'log_file': 'jd_monitor.log'
    }
}

# 配置文件路径
CONFIG_FILE = 'config.ini'

def get_script_status(script_id):
    """获取脚本运行状态"""
    script = SCRIPTS.get(script_id)
    if not script:
        return None
    
    # 检查进程是否在运行
    if script['process'] and script['process'].poll() is None:
        return 'running'
    return 'stopped'

@app.route('/')
def index():
    # 获取配置数据
    config = configparser.ConfigParser()
    config_dict = {}
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE, encoding='utf-8')
        for section in config.sections():
            config_dict[section] = {}
            for key, value in config.items(section):
                config_dict[section][key] = value
    
    # 创建一个不包含process对象的scripts字典副本
    scripts_data = {}
    for script_id, script in SCRIPTS.items():
        scripts_data[script_id] = {
            'name': script['name'],
            'file': script['file'],
            'log_file': script['log_file']
        }
    
    return render_template('index.html', scripts=scripts_data, configData=config_dict)

@app.route('/api/logs/<script_id>')
def get_logs(script_id):
    script = SCRIPTS.get(script_id)
    if not script or 'log_file' not in script:
        return jsonify({'status': 'error', 'message': '日志不存在'})
    
    try:
        log_file = script['log_file']
        lines = request.args.get('lines', default=50, type=int)
        
        if not os.path.exists(log_file):
            return jsonify({'status': 'error', 'message': '日志文件不存在'})
        
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.readlines()
        
        # 获取最后N行
        log_content = log_content[-lines:] if lines > 0 else log_content
        
        return jsonify({
            'status': 'success', 
            'data': ''.join(log_content),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/config')
def get_config():
    try:
        if not os.path.exists(CONFIG_FILE):
            return jsonify({'status': 'error', 'message': '配置文件不存在'})
        
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding='utf-8')
        
        # 将配置转换为字典
        config_dict = {}
        for section in config.sections():
            config_dict[section] = {}
            for key, value in config.items(section):
                config_dict[section][key] = value
        
        return jsonify({'status': 'success', 'data': config_dict})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/config', methods=['POST'])
def update_config():
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': '请求格式错误，需要JSON格式'})
        
        config_data = request.json
        
        if not os.path.exists(CONFIG_FILE):
            return jsonify({'status': 'error', 'message': '配置文件不存在'})
        
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE, encoding='utf-8')
        
        # 更新配置
        for section, section_data in config_data.items():
            if section not in config:
                config.add_section(section)
            
            for key, value in section_data.items():
                config.set(section, key, str(value))
        
        # 保存配置
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            config.write(f)
        
        return jsonify({'status': 'success', 'message': '配置已更新'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/start/<script_id>')
def start_script(script_id):
    script = SCRIPTS.get(script_id)
    if not script:
        return jsonify({'status': 'error', 'message': '脚本不存在'})
    
    if get_script_status(script_id) == 'running':
        return jsonify({'status': 'error', 'message': '脚本已在运行'})
    
    try:
        script['process'] = subprocess.Popen(['python3', script['file']], 
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
        return jsonify({'status': 'success', 'message': f'{script["name"]}已启动'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/stop/<script_id>')
def stop_script(script_id):
    script = SCRIPTS.get(script_id)
    if not script:
        return jsonify({'status': 'error', 'message': '脚本不存在'})
    
    if get_script_status(script_id) != 'running':
        return jsonify({'status': 'error', 'message': '脚本未在运行'})
    
    try:
        process = psutil.Process(script['process'].pid)
        for child in process.children(recursive=True):
            child.terminate()
        process.terminate()
        script['process'] = None
        return jsonify({'status': 'success', 'message': f'{script["name"]}已停止'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/status/<script_id>')
def script_status(script_id):
    status = get_script_status(script_id)
    if status is None:
        return jsonify({'status': 'error', 'message': '脚本不存在'})
    return jsonify({'status': 'success', 'data': status})

@app.route('/wxpusher/callback', methods=['POST'])
def wxpusher_callback():
    try:
        data = request.json
        if data and 'data' in data and 'uid' in data['data']:
            uid = data['data']['uid']
            
            # 读取现有配置
            config = configparser.ConfigParser()
            config.read(CONFIG_FILE, encoding='utf-8')
            
            # 获取现有的uids列表
            current_uids = json.loads(config.get('WxPusher', 'uids'))
            
            # 如果uid不在列表中，添加它
            if uid not in current_uids:
                current_uids.append(uid)
                config.set('WxPusher', 'uids', json.dumps(current_uids))
                
                # 保存更新后的配置
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    config.write(f)
                    
            return jsonify({'status': 'success', 'message': 'UID已更新'})
        return jsonify({'status': 'error', 'message': '无效的请求数据'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    port = int(get_env_config('PORT', 7860))
    app.run(host='0.0.0.0', debug=True,port=port)