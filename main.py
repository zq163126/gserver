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
    formatted = f"[gameserver] {message}"
    if screenshot and driver:
        driver.save_screenshot("screenshot.png")
        with open("screenshot.png", "rb") as photo:
            bot.send_photo(TG_CHAT_ID, photo, caption=formatted)
    else:
        bot.send_message(TG_CHAT_ID, formatted)

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    if PROXY_SOCKS5: options.add_argument(f'--proxy-server={PROXY_SOCKS5}')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def handle_ads(driver):
    """隐藏所有 z-index 为 45 的广告元素"""
    script = """
    let count = 0;
    document.querySelectorAll('div, always-on-top-app').forEach(el => {
        if (window.getComputedStyle(el).zIndex == 45) {
            el.style.display = 'none';
            count++;
        }
    });
    return count;
    """
    try:
        count = driver.execute_script(script)
        if count > 0: print(f"[LOG] 已隐藏 {count} 个广告元素")
    except Exception as e:
        print(f"[LOG] 去广告异常: {e}")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    wait = WebDriverWait(driver, 15)
    
    # 1. 详情页逻辑
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(8)
    handle_ads(driver)
    
    print("[LOG] 正在查找启动/停止按钮...")
    try:
        # 兼容按钮标签：button, div, span, a
        btn = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Start') or contains(text(), 'STOP')]")))
        print(f"[LOG] 找到按钮，文字内容为: '{btn.text}'")
        send_to_tg(f"已检测到按钮状态: {btn.text}")
    except Exception as e:
        print("[LOG] 未找到按钮，当前页面所有可点击元素文本:")
        elements = driver.find_elements(By.CSS_SELECTOR, "button, a, div")
        for el in elements:
            if el.text.strip(): print(f" - {el.text.strip()}")
        send_to_tg("查找按钮失败，请查看LOG日志")

    # 2. 续期页逻辑
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    handle_ads(driver)
    
    try:
        expiry_input = wait.until(EC.presence_of_element_located((By.ID, "expires_at")))
        val = expiry_input.get_attribute("value")
        print(f"[LOG] 读取到期时间: {val}")
        send_to_tg(f"当前到期日: {val}")
    except Exception as e:
        print(f"[LOG] 读取时间失败: {e}")
        send_to_tg("读取续期时间失败")

if __name__ == "__main__":
    if not BASE_URL: exit(1)
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally:
        driver.quit()
