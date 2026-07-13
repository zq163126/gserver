import os
import time
import datetime
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- 配置区域 ---
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
    if PROXY_SOCKS5:
        options.add_argument(f'--proxy-server={PROXY_SOCKS5}')
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
    
    if "dashboard" in driver.current_url:
        return True
    else:
        send_to_tg("登录失败，未跳转至 dashboard", screenshot=True, driver=driver)
        return False

def manage_server(driver):
    wait = WebDriverWait(driver, 15)
    
    # --- 详情页逻辑 ---
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10)
    handle_ads(driver)
    
    print("[LOG] 正在尝试定位 Start/Stop 动态按钮...")
    try:
        # 使用 translate 统一转小写，解决大小写匹配问题
        xpath_query = "//*[contains(translate(text(), 'STARTOP', 'startop'), 'start') or contains(translate(text(), 'STARTOP', 'startop'), 'stop')]"
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_query)))
        
        btn_text = btn.text.strip().upper()
        print(f"[LOG] 检测到按钮文字: '{btn_text}'")
        
        # 逻辑判断：仅当文字为 START 时执行点击
        if btn_text == "START":
            print("[LOG] 状态为 START，执行点击操作。")
            driver.execute_script("arguments[0].click();", btn)
            send_to_tg("服务器已执行启动操作 (START)")
        elif btn_text == "STOP":
            print("[LOG] 状态为 STOP，跳过启动操作。")
            send_to_tg("服务器正在运行中 (STOP)，无需启动。")
        else:
            print(f"[LOG] 按钮状态无法识别: {btn_text}")
    except Exception as e:
        print(f"[LOG] 定位按钮失败: {e}")
        send_to_tg("详情页按钮定位失败，请查看日志与截图。", screenshot=True, driver=driver)

    # --- 续期页逻辑 ---
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    handle_ads(driver)
    
    try:
        expiry_input = wait.until(EC.presence_of_element_located((By.ID, "expires_at")))
        val = expiry_input.get_attribute("value")
        print(f"[LOG] 读取到期时间: {val}")
        
        # 解析时间并判断（假设格式如 14.08.2026）
        expiry_date = datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y")
        if (expiry_date - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Renew')]")))
            driver.execute_script("arguments[0].click();", renew_btn)
            send_to_tg(f"已执行续期。当前到期日: {val}")
        else:
            send_to_tg(f"无需续期，当前到期日: {val}")
    except Exception as e:
        print(f"[LOG] 读取时间或续期失败: {e}")
        send_to_tg("续期操作失败，请查看日志。", screenshot=True, driver=driver)

if __name__ == "__main__":
    if not BASE_URL: exit(1)
    driver = setup_driver()
    try:
        if login(driver):
            manage_server(driver)
    finally:
        driver.quit()
