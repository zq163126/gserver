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

def handle_ads_if_exists(driver):
    """
    逻辑：查找广告，有则隐藏，无则跳过。
    """
    try:
        # 1. 检查 No Thanks
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for btn in buttons:
            if "No Thanks" in btn.text and btn.is_enabled():
                btn.click()
                time.sleep(2)
                print("[LOG] 已点击 No Thanks")
        
        # 2. 检查 z-index: 45 的遮罩
        ads_div = driver.find_elements(By.CSS_SELECTOR, "div[style*='z-index: 45']")
        if ads_div:
            driver.execute_script("arguments[0].style.display = 'none';", ads_div[0])
            print("[LOG] 已隐藏广告遮罩")
    except Exception as e:
        print(f"[LOG] 去广告步骤异常: {e}")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    
    if "dashboard" in driver.current_url:
        return True
    else:
        send_to_tg("登录失败，未跳转至dashboard", screenshot=True, driver=driver)
        return False

def manage_server(driver):
    wait = WebDriverWait(driver, 20)
    
    # 1. 访问详情页
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(5)
    
    # 检查广告并去广告
    handle_ads_if_exists(driver)
    
    # 查找 START/STOP 按钮
    try:
        btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Start') or contains(., 'STOP')]")))
        btn_text = btn.text
        
        if "STOP" in btn_text:
            send_to_tg("服务器正在工作中 (STOP)，无需启动。")
        else:
            btn.click()
            send_to_tg("已点击 Start 按钮启动服务器。")
    except Exception as e:
        print(f"[LOG] 详情页操作失败: {e}")
        send_to_tg("详情页操作失败，请查看截图", screenshot=True, driver=driver)

    # 2. 访问 Renew 页
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    
    # 检查广告并去广告
    handle_ads_if_exists(driver)
    
    try:
        expiry_input = wait.until(EC.presence_of_element_located((By.ID, "expires_at")))
        expiry_str = expiry_input.get_attribute("value")
        expiry_date = datetime.datetime.strptime(expiry_str.split(" - ")[0], "%d.%m.%Y")
        
        # 判断是否小于 2 小时 (这里使用天数计算，若要精确小时，可改为 total_seconds)
        if (expiry_date - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Renew')]")))
            renew_btn.click()
            time.sleep(2)
            send_to_tg(f"已执行续期。当前到期日: {expiry_str}")
        else:
            send_to_tg(f"无需续期，当前到期日: {expiry_str}")
    except Exception as e:
        print(f"[LOG] 续期页操作失败: {e}")
        send_to_tg("续期页操作失败，请查看截图", screenshot=True, driver=driver)

if __name__ == "__main__":
    if not BASE_URL: exit(1)
    driver = setup_driver()
    try:
        if login(driver):
            manage_server(driver)
    finally:
        driver.quit()
