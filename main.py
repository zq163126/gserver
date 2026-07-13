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
    if PROXY_SOCKS5: options.add_argument(f'--proxy-server={PROXY_SOCKS5}')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def hide_ads_div(driver):
    """最稳妥的去广告：查找所有计算样式 z-index 为 45 的元素并隐藏"""
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
        if count > 0: print(f"[LOG] 实时监测并隐藏了 {count} 个广告元素")
    except Exception as e:
        print(f"[LOG] 隐藏广告 DIV 异常: {e}")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    wait = WebDriverWait(driver, 10)

    # --- 1. 启动操作 ---
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(5)
    
    # 查找前先去广告
    hide_ads_div(driver)
    
    try:
        # 尝试查找
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start') or contains(., 'STOP')]")))
        if "STOP" in btn.text:
            send_to_tg("服务器正在工作中 (STOP)，无需启动。")
        else:
            btn.click()
            send_to_tg("已点击 Start 按钮。")
    except Exception:
        # 如果第一次找不到，很可能是广告刚弹出来，立刻再扫一次并重试
        print("[LOG] 初次查找失败，正在进行二次广告清理并重试...")
        hide_ads_div(driver)
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start') or contains(., 'STOP')]")))
        btn.click()
        send_to_tg("二次清理后已点击 Start 按钮。")

    # --- 2. 续期操作 ---
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    hide_ads_div(driver)
    
    try:
        expiry_input = wait.until(EC.presence_of_element_located((By.ID, "expires_at")))
        expiry_str = expiry_input.get_attribute("value")
        expiry_date = datetime.datetime.strptime(expiry_str.split(" - ")[0], "%d.%m.%Y")
        
        if (expiry_date - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Renew')]")))
            renew_btn.click()
            send_to_tg(f"已续期。新到期日: {expiry_str}")
    except Exception as e:
        print(f"[LOG] 续期失败: {e}")
        send_to_tg("续期页查找失败，请查看截图", screenshot=True, driver=driver)

if __name__ == "__main__":
    if not BASE_URL: exit(1)
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally: driver.quit()
