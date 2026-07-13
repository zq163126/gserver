import os
import time
import datetime
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# 配置区域：从 GitHub Secrets 读取
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
BASE_URL = os.getenv("BASE_URL")

bot = telebot.TeleBot(TG_BOT_TOKEN)

def send_to_tg(message, screenshot=False, driver=None):
    if screenshot and driver:
        driver.save_screenshot("screenshot.png")
        with open("screenshot.png", "rb") as photo:
            bot.send_photo(TG_CHAT_ID, photo, caption=message)
    else:
        bot.send_message(TG_CHAT_ID, message)

def setup_driver():
    options = Options()
    # options.add_argument("--headless") # 如需无头模式可开启
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def handle_ads(driver):
    """去广告函数：在每个操作前调用"""
    try:
        # 1. 尝试查找并点击 'No Thanks' 按钮
        # 查找所有按钮，判断文字包含 'No Thanks' 且处于可点击状态
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "No Thanks" in btn.text and btn.is_enabled():
                btn.click()
                print("已通过按钮关闭广告")
                time.sleep(2)
                return
        
        # 2. 兜底：隐藏广告 DIV (z-index: 45)
        ads_div = driver.find_elements(By.CSS_SELECTOR, "div[style*='z-index: 45']")
        if ads_div:
            driver.execute_script("arguments[0].style.display = 'none';", ads_div[0])
            print("已通过隐藏DIV方式处理广告")
    except Exception as e:
        print(f"广告处理过程跳过: {e}")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    
    # 登录按钮：使用鲁棒性较强的CSS选择器
    login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_btn.click()
    
    time.sleep(5)
    if "dashboard" in driver.current_url:
        return True
    else:
        send_to_tg("登录失败，未跳转至dashboard，请检查网页状态", screenshot=True, driver=driver)
        return False

def manage_server(driver):
    # 1. 启动操作
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10)
    handle_ads(driver)
    
    start_btn = driver.find_element(By.XPATH, "//button[contains(., 'Start')]")
    if "Start" in start_btn.text:
        start_btn.click()
        send_to_tg("服务器已执行启动操作")

    # 2. 续期操作
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    handle_ads(driver)
    
    expiry_input = driver.find_element(By.ID, "expires_at")
    expiry_str = expiry_input.get_attribute("value")
    # 解析日期，格式为: 15.07.2026
    expiry_date = datetime.datetime.strptime(expiry_str.split(" - ")[0], "%d.%m.%Y")
    
    if (expiry_date - datetime.datetime.now()).days <= 2:
        renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
        renew_btn.click()
        time.sleep(2)
        send_to_tg(f"已执行续期操作，当前到期日期: {expiry_str}")

if __name__ == "__main__":
    if not BASE_URL:
        print("错误：环境变量 BASE_URL 未设置")
        exit(1)
        
    driver = setup_driver()
    try:
        if login(driver):
            manage_server(driver)
    finally:
        driver.quit()
