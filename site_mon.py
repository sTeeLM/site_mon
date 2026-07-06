#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import configparser
import logging
import urllib.request

# 标准路径定义
CONFIG_FILE = '/etc/site_mon/config.cfg'
LOG_FILE = '/var/log/site_mon.log'

# 初始化日志 (由于使用 logrotate 轮转，这里仅需要标准输出与写入文件即可)
logger = logging.getLogger("site_mon")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

try:
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception as e:
    print(f"无法写入日志文件 {LOG_FILE}: {e}", file=sys.stderr)
    sys.exit(1)

def load_config():
    """读取指定的配置文件"""
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"配置文件未找到: {CONFIG_FILE}")
        sys.exit(1)
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE, encoding='utf-8')
        return config['monitor']
    except Exception as e:
        logger.error(f"解析配置文件失败: {e}")
        sys.exit(1)

def check_url(url):
    """检测URL状态"""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Site-Monitor/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception as e:
        logger.warning(f"检测到站点异常: {e}")
        return False

def execute_cmd(command):
    """安全执行配置的Shell命令"""
    if not command:
        return
    try:
        logger.info(f"触发动作，执行命令: {command}")
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"命令执行失败, 错误输出: {result.stderr.strip()}")
    except Exception as e:
        logger.error(f"执行命令时发生异常: {e}")

def main():
    logger.info("site_mon 监控服务已启动...")
    conf = load_config()
    
    # 初始化状态标记
    last_status = None

    while True:
        # 支持不重启服务热重载配置
        try:
            conf = load_config()
            url = conf.get('url')
            interval = conf.getint('interval', fallback=60)
            fail_cmd = conf.get('fail_command')
            recover_cmd = conf.get('recover_command')
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}，将使用旧配置继续运行")

        current_status = check_url(url)

        if current_status:
            if last_status is False:
                logger.info(f"站点已恢复正常: {url}")
                execute_cmd(recover_cmd)
            elif last_status is None:
                logger.info(f"首次检测：站点状态正常: {url}")
            last_status = True
        else:
            if last_status is True or last_status is None:
                logger.error(f"站点崩溃！触发异常动作: {url}")
                execute_cmd(fail_cmd)
            last_status = False

        time.sleep(interval)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("服务被用户手动终止。")

