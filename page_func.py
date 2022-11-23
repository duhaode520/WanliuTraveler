from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urllib.parse import quote
import time
import datetime
import warnings
import random

from sqlalchemy import true
from utils import TimeCloseEnum
warnings.filterwarnings('ignore')

def login(driver, user_name, password, retry=0):
    if retry == 3:
        return '门户登录失败\n'

    print('门户登录中...')
    # 先登录
    appURL = "https://yanyuan.pku.edu.cn/site/generalApp/details?id=40"
    driver.get(appURL)

    try:
        # 这里登陆后跳转到登陆界面
        WebDriverWait(driver, 5).until(
            EC.url_changes(appURL))
        
        # 点击登陆
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "user_name")))
        driver.find_element(By.ID, "user_name").send_keys(user_name)
        time.sleep(0.1)
        driver.find_element(By.ID, "password").send_keys(password)
        time.sleep(0.1)
        driver.find_element(By.ID, "logon_button").click()

        # 跳转回预约的界面
        WebDriverWait(driver, 10).until(EC.url_matches(appURL))
        print('门户登录成功')
        return '门户登录成功\n'
    except:
        print('Retrying...')
        login(driver, user_name, password, retry + 1)

def judge_time_limit(to_time, back_time):
    now = datetime.datetime.today()
    time_hour = datetime.datetime.strptime(
        str(now).split()[1][:-7], "%H:%M:%S")
    # 去程班车12:00开始抢
    time_11_55 = datetime.datetime.strptime(
        "11:55:00", "%H:%M:%S")
    # 返程班车15:00开始抢
    time_14_55 = datetime.datetime.strptime(
        "14:55:00", "%H:%M:%S")
    status = {'to': True, 'back': True}
    if (len(to_time) > 0) and (time_hour < time_14_55):
        print("只能在当天14:55后预约第二天的去程班车")
        log_str = "只能在当天14:55后预约第二天的去程班车\n"
        status['back'] = False 
    if (len(back_time) > 0) and (time_hour < time_11_55):
        print("只能在当天11:55后预约返程班车")
        log_str = "只能在当天11:55后预约返程班车\n"
        status['to'] = False
    
    if status['to']:
        print("可以预约去程班车")
        log_str = "可以预约去程班车\n"
    if status['back']:
        print("可以预约返程班车")
        log_str = "可以预约返程班车\n"

    return status ,log_str


def appoint(driver, appoint_time_list, type):
    print('预约中...')
    log_str = '预约中...\n'
    log_str += wait_for_ready(type)
    driver.fresh()
    WebDriverWait.until(
        EC.visibility_of_all_elements_located((By.CLASS_NAME, "statusFont")))

    # 点击预约
    appoint_time, click_log = click_appoint(driver, appoint_time_list)
    log_str += click_log
    return log_str
    
def click_appoint(driver, appoint_time_list):
    times = driver.find_elements(By.CLASS_NAME, "activeTime")
    times = [i.text.split(' ')[-1] for i in times]
    status = driver.find_elements(By.CLASS_NAME, "statusFont")

    flag = False
    log_str = ""
    for appoint_time in appoint_time_list:
        for i in range(len(times)):
            if times[i] == appoint_time:
                appointClass = status[i].get_attribute('class')[-1]
                if appointClass != "nowAppoint":
                    log_str += "{appoint_time}班车 预约失败！原因：{status[i].text}\n"
                    print( "{appoint_time}班车 预约失败！原因：{status[i].text}\n")
                    break;
                else:
                    status[i].find_element(By.CLASS_NAME, 'appointbtn').click()
                    flag = check_appoint_status(driver, i)
                    break
        if flag:
            break
    if flag:
        log_str += "{appoint_time}班车 预约成功！"
        print( "{appoint_time}班车 预约成功！")
        return appoint_time, log_str
    else:
        return None, log_str 

def check_appoint_status(driver, i):
    status = driver.find_elements(By.CLASS_NAME, "statusFont")
    if status[i].find_element(By.CLASS_NAME, 'cancelbtn'):
        return True
    else:
        return False

def wait_for_ready(type):
    if type == "to":
        prepare_time = datetime.time(11, 55, 0)
        ready_time = datetime.time(12, 0, 0)
    elif type == "back":
        prepare_time = datetime.time(14, 55, 0)
        ready_time = datetime.time(15, 0, 0)
    else:
        raise ValueError("type must be 'to' or 'back'")
    flag = judge_close_time(prepare_time, ready_time)
    if flag == TimeCloseEnum.EARLY:
        print("只能在当天11:55后预约去程班车")
        log_str = "只能在当天11:55后预约去程班车\n"
        return log_str
    elif flag == TimeCloseEnum.READY:
        while True:
            flag = judge_close_time(prepare_time, ready_time)
            if flag == TimeCloseEnum.RIGHT:
                break
            else:
                time.sleep(0.5)
        return "可以预约\n"
    
        
def judge_close_time(standard_time, check_time):
    now = datetime.datetime.today()
    time_hour = datetime.datetime.strptime(
        str(now).split()[1][:-7], "%H:%M:%S")
    if time_hour < standard_time:
        return TimeCloseEnum.EARLY
    elif standard_time < time_hour < check_time:
        return TimeCloseEnum.READY
    elif time_hour > check_time:
        return TimeCloseEnum.RIGHT

def book(driver, start_time_list, end_time_list, delta_day_list, venue_num=-1):
    print("查找空闲场地")
    log_str = "查找空闲场地\n"

    def judge_close_to_time_12():
        now = datetime.datetime.today()
        time_hour = datetime.datetime.strptime(
            str(now).split()[1][:-7], "%H:%M:%S")
        time_11_55 = datetime.datetime.strptime(
            "11:55:00", "%H:%M:%S")
        time_12 = datetime.datetime.strptime(
            "12:00:00", "%H:%M:%S")
        # time_11_55 = datetime.datetime.strptime(
        #     str(now).split()[1][:-7], "%H:%M:%S")
        # time_12 = time_11_55+datetime.timedelta(minutes=1)
        if time_hour < time_11_55:
            return 0
        elif time_11_55 < time_hour < time_12:
            return 1
        elif time_hour > time_12:
            return 2

    def judge_in_time_range(start_time, end_time, venue_time_range):
        vt = venue_time_range.split('-')
        vt_start_time = datetime.datetime.strptime(vt[0], "%H:%M")
        vt_end_time = datetime.datetime.strptime(vt[1], "%H:%M")
        if start_time <= vt_start_time and vt_end_time <= end_time:
            return True
        else:
            return False

    def move_to_date(delta_day):
        for i in range(delta_day):
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/form/div/div/button[2]/i")))
            driver.find_element(By.XPATH,
                '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/form/div/div/button[2]/i').click()
            time.sleep(0.1)

    def click_free(start_time, end_time, venue_num, table_num):
        trs = driver.find_elements(By.TAG_NAME, 'tr')
        # 防止表格没加载出来
        no_table_flag = 0
        while trs[1].find_elements(By.TAG_NAME,
                'td')[0].find_element(By.TAG_NAME, 'div').text == "时间段":
            no_table_flag += 1
            time.sleep(0.2)
            trs = driver.find_elements(By.TAG_NAME, 'tr')
            if no_table_flag > 10:
                driver.refresh()
                no_table_flag = 0
                move_to_date(delta_day)
        trs_list = []
        for i in range(1, len(trs)-2):
            vt = trs[i].find_elements(By.TAG_NAME, 
                'td')[0].find_element(By.TAG_NAME, 'div').text
            if judge_in_time_range(start_time, end_time, vt):
                trs_list.append(trs[i].find_elements(By.TAG_NAME, 'td'))
        if len(trs_list) == 0:
            return False, -1, 0

        j_list = [x for x in range(1, len(trs_list[0]))]
        print(venue_num, table_num, j_list)
        if venue_num != -1 and (venue_num-table_num in j_list):
            flag = False
            for i in range(len(trs_list)):
                class_name = trs_list[i][venue_num-table_num].find_element(By.TAG_NAME, 'div').get_attribute('class')
                print(class_name)
                if class_name.split()[2] == 'free':
                    flag = True
                    break
        elif venue_num != -1 and (venue_num-table_num not in j_list):
            return False, venue_num, table_num + len(j_list)
        else:
            # 随机点一列free的，防止每次都点第一列
            random.shuffle(j_list)
            print(j_list)
            for j in j_list:
                flag = False
                for i in range(len(trs_list)):
                    class_name = trs_list[i][j].find_element(By.TAG_NAME, 'div').get_attribute('class')
                    print(class_name)
                    if class_name.split()[2] == 'free':
                        flag = True
                        venue_num = j+table_num
                        break
        if flag:
            for i in range(len(trs_list)):
                WebDriverWait(driver, 10).until_not(
                    EC.visibility_of_element_located((By.CLASS_NAME,
                                                      "loading.ivu-spin.ivu-spin-large.ivu-spin-fix.fade-leave-active.fade-leave-to")))
                trs_list[i][venue_num-table_num].find_element(By.TAG_NAME, 'div').click()
            return True, venue_num, table_num + len(j_list)
        return False, venue_num, table_num + len(j_list)

    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(1)
    WebDriverWait(driver, 10).until_not(
        EC.visibility_of_element_located((By.CLASS_NAME, "loading.ivu-spin.ivu-spin-large.ivu-spin-fix")))
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/form/div/div/div/div[1]/div/div/input')))
    # 若接近但是没到12点，停留在此页面
    flag = judge_close_to_time_12()
    if flag == 1:
        while True:
            flag = judge_close_to_time_12()
            if flag == 2:
                break
            else:
                time.sleep(0.5)
        driver.refresh()
        WebDriverWait(driver, 5).until_not(
            EC.visibility_of_element_located((By.CLASS_NAME, "loading.ivu-spin.ivu-spin-large.ivu-spin-fix")))

    for k in range(len(start_time_list)):
        start_time = start_time_list[k]
        end_time = end_time_list[k]
        delta_day = delta_day_list[k]

        if k != 0:
            driver.refresh()
            time.sleep(0.5)

        move_to_date(delta_day)

        start_time = datetime.datetime.strptime(
            start_time.split('-')[1], "%H%M")
        end_time = datetime.datetime.strptime(end_time.split('-')[1], "%H%M")
        print("开始时间:%s" % str(start_time).split()[1])
        print("结束时间:%s" % str(end_time).split()[1])

        status, venue_num, table_num = click_free(
            start_time, end_time, venue_num, 0)
        # 如果第一页没有，就往后翻，直到不存在下一页
        while not status:
            next_table = driver.find_elements(By.XPATH, 
                '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/div[3]/div[1]/div/div/div/div/div/table/thead/tr/td[6]/div/span/i')
            WebDriverWait(driver, 10).until_not(
                EC.visibility_of_element_located((By.CLASS_NAME, "loading.ivu-spin.ivu-spin-large.ivu-spin-fix")))
            time.sleep(0.1)
            if len(next_table) > 0:
                driver.find_element(By.XPATH, 
                    '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/div[3]/div[1]/div/div/div/div/div/table/thead/tr/td[6]/div/span/i').click()
                status, venue_num, table_num = click_free(
                    start_time, end_time, venue_num, table_num)
            else:
                break
        if status:
            log_str += "找到空闲场地，场地编号为%d\n" % venue_num
            print("找到空闲场地，场地编号为%d\n" % venue_num)
            now = datetime.datetime.now()
            today = datetime.datetime.strptime(str(now)[:10], "%Y-%m-%d")
            date = today+datetime.timedelta(days=delta_day)
            return status, log_str, str(date)[:10]+str(start_time)[10:], str(date)[:10]+str(end_time)[10:], venue_num
        else:
            log_str += "没有空余场地\n"
            print("没有空余场地\n")
    return status, log_str, None, None, None


def click_book(driver):
    print("确定预约")
    log_str = "确定预约\n"
    driver.switch_to.window(driver.window_handles[-1])
    WebDriverWait(driver, 10).until_not(
        EC.visibility_of_element_located((By.CLASS_NAME, "loading.ivu-spin.ivu-spin-large.ivu-spin-fix")))
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/div[5]/div/div[2]')))
    driver.find_element(By.XPATH, 
        '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/div[5]/div/div[2]').click()
    print("确定预约成功")
    log_str += "确定预约成功\n"
    return log_str

def check_element_exist(driver, condition, element):
    """_summary_: 检查元素是否存在且可见

    Args:
        driver (_type_): _description_
        condition (_type_): _description_
        element (_type_): _description_

    Returns:
        bool: is_exist
    """
    try:
        ele = driver.find_element(condition, element)
        return ele.is_displayed()
    except:
        return False

def click_submit_order(driver, tt_usr, tt_pwd):
    print("提交订单")
    log_str = "提交订单\n"
    driver.switch_to.window(driver.window_handles[-1])
    WebDriverWait(driver, 10).until_not(
        EC.visibility_of_element_located((By.CLASS_NAME, "loading.ivu-spin.ivu-spin-large.ivu-spin-fix")))
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CLASS_NAME, 'payHandleItem')))
    driver.find_element(By.XPATH, 
        '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/div/div/div[2]').click()
    #result = EC.alert_is_present()(driver)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/div[2]/div/div[2]/div/div[1]/div/img'))
    )

    captcha_time = 0
    while True:
        if captcha_time > 2:
            log_str += "验证失败\n"
            raise Exception("验证失败")
        base_img = driver.find_element(
            By.XPATH, '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/div[2]/div/div[2]/div/div[1]/div/img')
        slide_img = driver.find_element(
            By.XPATH, '/html/body/div[1]/div/div/div[3]/div[2]/div/div[2]/div[2]/div/div[2]/div/div[2]/div/div/div/img')
        base, slide = base_img.get_attribute('src').replace(
            'data:image/png;base64,', ''), slide_img.get_attribute('src').replace('data:image/png;base64,', '')
        scale = base_img.size['width'] / get_size(base)[0]
        x, y = verify(base, slide, tt_usr, tt_pwd)
        dragger = driver.find_element(By.CSS_SELECTOR, 'body > div.fullHeight > div > div > div.coach > div.venueSiteWrap > div > div.reservation-step-two > div.mask > div > div.verifybox-bottom > div > div.verify-bar-area > div > div')
        action = ActionChains(driver)
        action.drag_and_drop_by_offset(dragger, xoffset=x*scale, yoffset=0).perform()
        WebDriverWait(driver, 5).until_not(
            EC.visibility_of_element_located((By.CLASS_NAME, "loading.ivu-spin.ivu-spin-large.ivu-spin-fix")))
        if check_element_exist(driver, By.CLASS_NAME, 'payHandle'):
            break;
        else:
            captcha_time += 1

    print("提交订单成功")
    log_str += "提交订单成功\n"
    return log_str


def click_pay(driver):
    print("付款（校园卡）")
    log_str = "付款（校园卡）\n"
    driver.switch_to.window(driver.window_handles[-1])
    WebDriverWait(driver, 10).until_not(
        EC.visibility_of_element_located((By.CLASS_NAME, "loading.ivu-spin.ivu-spin-large.ivu-spin-fix")))
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.XPATH, '/html/body/div[1]/div/div/div[3]/div[2]/div/div[3]/div[6]/div[1]/div[4]')))
    time.sleep(2)
    driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[3]/div[2]/div/div[3]/div[6]/div[1]/div[4]').click()
    time.sleep(0.5)
    driver.find_element(By.XPATH, 
        '/html/body/div[1]/div/div/div[3]/div[2]/div/div[3]/div[8]/div[2]/button').click()
    print("付款成功")
    log_str += "付款成功\n"
    return log_str


if __name__ == '__main__':
    pass
