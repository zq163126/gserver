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

def handle_ads(driver):
    """最底层的去广告逻辑，所有操作前均会调用"""
    try:
        # 1. 尝试点击 No Thanks
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "No Thanks" in btn.text and btn.is_enabled():
                btn.click()
                time.sleep(1)
        # 2. 隐藏广告层
        ads_div = driver.find_elements(By.CSS_SELECTOR, "div[style*='z-index: 45']")
        if ads_div:
            driver.execute_script("arguments[0].style.display = 'none';", ads_div[0])
    except Exception:
        pass

# --- 核心封装：强制去广告操作 ---
def safe_find(driver, locator, timeout=20):
    handle_ads(driver)  # 查找元素前去广告
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))

def safe_click(driver, locator):
    handle_ads(driver)  # 点击前去广告
    element = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(locator))
    element.click()

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    # 1. 启动操作
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10) # 等待初始数据加载
    
    try:
        # 查找 Start 按钮 (带去广告)
        start_btn = safe_find(driver, (By.XPATH, "//button[contains(., 'Start') or contains(., 'STOP')]"))
        
        if "Start" in start_btn.text:
            safe_click(driver, (By.XPATH, "//button[contains(., 'Start')]"))
            time.sleep(2)
            send_to_tg("已执行启动操作。")
        else:
            send_to_tg("服务器处于运行状态 (STOP)，无需启动。")
    except Exception as e:
        send_to_tg(f"启动操作失败: {str(e)}", screenshot=True, driver=driver)

    # 2. 续期操作
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    
    try:
        # 获取日期 (带去广告)
        expiry_input = safe_find(driver, (By.ID, "expires_at"))
        expiry_str = expiry_input.get_attribute("value")
        expiry_date = datetime.datetime.strptime(expiry_str.split(" - ")[0], "%d.%m.%Y")
        
        if (expiry_date - datetime.datetime.now()).days <= 2:
            send_to_tg(f"当前到期日: {expiry_str}，执行续期...")
            safe_click(driver, (By.XPATH, "//button[contains(text(), 'Renew')]"))
            time.sleep(5)
            
            driver.refresh()
            new_expiry = safe_find(driver, (By.ID, "expires_at")).get_attribute("value")
            send_to_tg(f"续期操作完成。更新后到期日: {new_expiry}")
        else:
            send_to_tg(f"无需续期，当前到期日: {expiry_str}")
    except Exception as e:
        send_to_tg(f"续期操作失败: {str(e)}", screenshot=True, driver=driver)

if __name__ == "__main__":
    if not BASE_URL: exit(1)
    driver = setup_driver()
    try:
        if login(driver):
            manage_server(driver)
        else:
            send_to_tg("登录失败。")
    finally:
        driver.quit()
