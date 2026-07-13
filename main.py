import os
import time
import datetime
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 配置区域
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
BASE_URL = os.getenv("BASE_URL")
PROXY_SOCKS5 = os.getenv("PROXY_SOCKS5")

bot = telebot.TeleBot(TG_BOT_TOKEN)

def send_to_tg(message, screenshot=False, driver=None):
    formatted_message = f"[gameserver] {message}"
    if screenshot and driver:
        driver.save_screenshot("screenshot.png")
        with open("screenshot.png", "rb") as photo:
            bot.send_photo(TG_CHAT_ID, photo, caption=formatted_message)
    else:
        bot.send_message(TG_CHAT_ID, formatted_message)

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    if PROXY_SOCKS5:
        options.add_argument(f'--proxy-server={PROXY_SOCKS5}')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def hide_ads(driver):
    try:
        ads_divs = driver.find_elements(By.CSS_SELECTOR, "div[style*='z-index: 45']")
        for div in ads_divs:
            driver.execute_script("arguments[0].style.display = 'none';", div)
            print(f"[LOG] 广告 DIV 已隐藏")
    except Exception as e:
        print(f"[LOG] 广告处理异常: {e}")

def safe_action(driver, locator, action_type="click", timeout=20):
    """封装：查找元素前先隐藏广告，并记录详细 LOG"""
    print(f"[LOG] 正在尝试定位元素: {locator}")
    hide_ads(driver)
    
    try:
        wait = WebDriverWait(driver, timeout)
        element = wait.until(EC.element_to_be_clickable(locator))
        print(f"[LOG] 成功定位元素: {locator}")
        
        if action_type == "click":
            element.click()
            print(f"[LOG] 成功执行点击操作: {locator}")
        return element
    except Exception as e:
        print(f"[LOG] 操作失败，定位目标: {locator}, 错误信息: {e}")
        raise e

def login(driver):
    driver.get(f"{BASE_URL}/login")
    hide_ads(driver)
    send_to_tg("已打开登录页", screenshot=True, driver=driver)
    
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    print("[LOG] 已提交登录表单")
    
    time.sleep(5)
    success = "dashboard" in driver.current_url
    send_to_tg(f"登录结果: {'成功' if success else '失败'}", screenshot=True, driver=driver)
    return success

def manage_server(driver):
    # 1. 启动操作
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10)
    hide_ads(driver)
    send_to_tg("已打开详情页", screenshot=True, driver=driver)
    
    try:
        start_btn = safe_action(driver, (By.XPATH, "//button[contains(., 'Start') or contains(., 'STOP')]"), action_type="find")
        
        if "Start" in start_btn.text:
            safe_action(driver, (By.XPATH, "//button[contains(., 'Start')]"), action_type="click")
            time.sleep(3)
            send_to_tg("启动按钮点击操作已完成。", screenshot=True, driver=driver)
        else:
            print("[LOG] 服务器已在运行，无需启动")
            send_to_tg("服务器处于运行状态 (STOP)，无需启动。")
    except Exception as e:
        send_to_tg(f"启动操作异常: {str(e)}", screenshot=True, driver=driver)

    # 2. 续期操作
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    hide_ads(driver)
    send_to_tg("已打开续期页面", screenshot=True, driver=driver)
    
    try:
        expiry_input = safe_action(driver, (By.ID, "expires_at"), action_type="find")
        expiry_str = expiry_input.get_attribute("value")
        print(f"[LOG] 读取到期时间: {expiry_str}")
        
        expiry_date = datetime.datetime.strptime(expiry_str.split(" - ")[0], "%d.%m.%Y")
        
        if (expiry_date - datetime.datetime.now()).days <= 2:
            safe_action(driver, (By.XPATH, "//button[contains(text(), 'Renew')]"), action_type="click")
            time.sleep(5)
            driver.refresh()
            time.sleep(5)
            new_expiry = safe_action(driver, (By.ID, "expires_at"), action_type="find").get_attribute("value")
            send_to_tg(f"续期完成。新到期日: {new_expiry}", screenshot=True, driver=driver)
        else:
            print(f"[LOG] 无需续期")
            send_to_tg(f"无需续期，当前到期日: {expiry_str}")
    except Exception as e:
        send_to_tg(f"续期操作异常: {str(e)}", screenshot=True, driver=driver)

if __name__ == "__main__":
    if not BASE_URL: exit(1)
    driver = setup_driver()
    try:
        if login(driver):
            manage_server(driver)
    finally:
        driver.quit()
