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
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "No Thanks" in btn.text and btn.is_enabled():
                btn.click()
                time.sleep(2)
                return
        ads_div = driver.find_elements(By.CSS_SELECTOR, "div[style*='z-index: 45']")
        if ads_div:
            driver.execute_script("arguments[0].style.display = 'none';", ads_div[0])
    except Exception as e:
        print(f"广告处理过程异常: {e}")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    wait = WebDriverWait(driver, 20)
    
    # 1. 启动操作
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10) # 强制等待10秒，等待数据读取
    send_to_tg("已打开详情页，等待数据加载完成并处理广告。", screenshot=True, driver=driver)
    handle_ads(driver)
    
    try:
        start_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start') or contains(., 'STOP')]")))
        if "Start" in start_btn.text:
            start_btn.click()
            time.sleep(3) # 等待点击后生效
            send_to_tg("检测到 Start 按钮，已点击启动服务器。")
        else:
            send_to_tg("服务器当前状态为 STOP，无需执行启动操作。")
    except Exception as e:
        send_to_tg(f"启动操作失败: {str(e)}", screenshot=True, driver=driver)

    # 2. 续期操作
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    handle_ads(driver)
    
    try:
        expiry_input = wait.until(EC.presence_of_element_located((By.ID, "expires_at")))
        expiry_str = expiry_input.get_attribute("value")
        expiry_date = datetime.datetime.strptime(expiry_str.split(" - ")[0], "%d.%m.%Y")
        
        if (expiry_date - datetime.datetime.now()).days <= 2:
            send_to_tg(f"当前到期日: {expiry_str}，即将到期，执行续期...")
            renew_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Renew')]")))
            renew_btn.click()
            time.sleep(5) # 等待续期动作执行
            
            # 确认续期效果
            driver.refresh()
            time.sleep(5)
            new_expiry = driver.find_element(By.ID, "expires_at").get_attribute("value")
            send_to_tg(f"续期操作完成。更新后的到期日期为: {new_expiry}")
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
