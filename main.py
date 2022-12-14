from configparser import ConfigParser
from os import stat
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as Chrome_Options
from selenium.webdriver.edge.options import Options as Edge_Options
from selenium.webdriver.firefox.options import Options as Firefox_Options
import warnings
import sys
import multiprocessing as mp
from env_check import *
from page_func import *
from notice import *

warnings.filterwarnings('ignore')
has_appointed = {"to": False, "back": False}

def sys_path(browser):
    path = 'driver'
    if browser == "chrome":
        if sys.platform.startswith('win'):
            return os.path.join(path, 'chromedriver.exe')
        elif sys.platform.startswith('linux'):
            return os.path.join(path, 'chromedriver.bin')
        else:
            raise Exception('不支持该系统')
    elif browser == "firefox":
        if sys.platform.startswith('win'):
            return os.path.join(path, 'geckodriver.exe')
        elif sys.platform.startswith('linux'):
            return os.path.join(path, 'geckodriver.bin')
        else:
            raise Exception('不支持该系统')
    elif browser == "edge":
        if sys.platform.startswith('win'):
            return os.path.join(path, 'msedgedriver.exe')
        elif sys.platform.startswith('linux'):
            return os.path.join(path, 'msedgedriver.bin')
        else:
            raise Exception('不支持该系统')
    else:
        raise Exception('不支持该浏览器')


def load_config(config):
    conf = ConfigParser()
    conf.read(config, encoding='utf8')

    user_name = conf['login']['user_name']
    password = conf['login']['password']
    date = conf['time']['date']
    to_time = conf['time']['to_time']
    back_time = conf['time']['back_time']
    wechat_notice = conf.getboolean('wechat', 'wechat_notice')
    sckey = conf['wechat']['SCKEY']

    return (user_name, password, date, to_time, back_time, wechat_notice, sckey)


def log_status(config, start_time, log_str):
    print("记录日志")
    now = datetime.datetime.now()
    print(now)
    print('%s.log' % config.split('.')[0])
    with open('%s.log' % config.split('.')[0], 'a', encoding='utf-8') as fw:
        fw.write(str(now)+"\n")
        fw.write("%s\n" % str(start_time))
        fw.write(log_str+"\n")
    print("记录日志成功\n")


def page(config, browser="chrome"):
    user_name, password, date, to_time, back_time, wechat_notice, sckey = load_config(config)
    
    log_str = ""
    web_status = True
    # appoint_status = {'to': True, 'back': True}
    appoint_status, log_exceeds = judge_time_limit(to_time, back_time)
    # 不再重复预约
    if has_appointed["to"]:
        appoint_status["to"] = False
    if has_appointed["back"]:
        appoint_status["back"] = False

    # log_str += log_exceeds
    if not (appoint_status['to'] or appoint_status['back']):
        # 时间没到
        log_status(config, [to_time.split('/'),
                            back_time.split('/')], log_exceeds)
        time.sleep(30)
        return False
    
    # 开始运行
    if browser == "chrome":
        chrome_options = Chrome_Options()
        # chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(
            options=chrome_options,
            executable_path=sys_path(browser="chrome"))
            # service_args=['--ignore-ssl-errors=true', '--ssl-protocol=TLSv1'])
        print('chrome launched\n')
    elif browser == "firefox":
        firefox_options = Firefox_Options()
        firefox_options.add_argument("--headless")
        driver = webdriver.Firefox(
            options=firefox_options,
            executable_path=sys_path(browser="firefox"))
        print('firefox launched\n')
    elif browser == 'edge':
        edge_options = Edge_Options()
        edge_options.add_argument("--headless")
        driver = webdriver.Edge(
            executable_path=sys_path(browser="edge"))
    else:
        raise Exception("不支持此类浏览器")

    if web_status:
        try:
            log_str += login(driver, user_name, password, retry=0)
        except:
            log_str += "登录失败\n"
            web_status = False

    appoint_to, appoint_back = None, None
    if web_status:
        to_time_list = to_time.split('/')
        back_time_list = back_time.split('/')
        try:
            if appoint_status['to']:
                appoint_to, log_to = appoint(driver, to_time_list, type="to")
                log_str += log_to
            if appoint_status['back']:
                appoint_back, log_back = appoint(driver, back_time_list, type='back')
                log_str += log_back
        except Exception as e:
            print(e)
            log_str += "预约班车失败\n"
            print("预约班车失败\n")
            web_status = False
    # if web_status and wechat_notice:
    #     try:
    #         log_str += wechat_notification(user_name,
    #                                        venue, venue_num, to_time, back_time, sckey)
    #     except:
    #         log_str += "微信通知失败\n"
    #         print("微信通知失败\n")
    # driver.quit()
    log_status(config, [appoint_to, appoint_back], log_str)
    if appoint_to:
        has_appointed["to"] = True
    if appoint_back:
        has_appointed["back"] = True
    return web_status

def task(config, browser):
    status = False
    while not status:
        status = page(config, browser)
        if (has_appointed["to"] and has_appointed["back"]):
            break
      
    print("所有班车均已经预约成功")

if __name__ == '__main__':
    browser = "chrome"

    lst_conf = env_check()
    # print(lst_conf)
    # multi_run(lst_conf, browser)
    # # sequence_run(lst_conf, browser)
    task('config0.ini', browser)
