import os, time, datetime, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 配置项
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
            bot.send_photo(TG_CHAT_ID, photo, caption=f"[gameserver] {message}")
    else:
        bot.send_message(TG_CHAT_ID, f"[gameserver] {message}")

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def force_hide_ads_css(driver):
    css_content = "div[style*='z-index: 45'] { display: none !important; visibility: hidden !important; pointer-events: none !important; }"
    js = "var s = document.createElement('style'); s.innerHTML = arguments[0]; document.head.appendChild(s);"
    driver.execute_script(js, css_content)

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(8) # 增加登录后缓冲
    if "dashboard" in driver.current_url:
        send_to_tg("登录成功", screenshot=True, driver=driver)
        return True
    return False

def manage_server(driver):
    # 1. 详情页处理
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10)
    force_hide_ads_css(driver)
    
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if el.text.strip().upper() in ["START", "STOP"]), None)
            
    if target and target.text.strip().upper() == "START":
        # 升级点击：先聚焦，再用 JS 触发点击，确保触发事件循环
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", target)
        time.sleep(10) # 增加启动后的等待时间
        send_to_tg("已点击启动 (START)，等待状态更新。", screenshot=True, driver=driver)
    else:
        send_to_tg(f"按钮状态为: {target.text if target else '未找到'}，跳过启动。", screenshot=True, driver=driver)

    # 2. 续期页处理
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(8)
    force_hide_ads_css(driver)
    try:
        # 获取续期输入框的时间值
        val_element = driver.find_element(By.ID, "expires_at")
        val = val_element.get_attribute("value")
        
        # 续期判断逻辑
        expiry_date = datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y")
        if (expiry_date - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            driver.execute_script("arguments[0].click();", renew_btn)
            time.sleep(5)
            send_to_tg(f"续期操作已执行，当前显示到期日: {val}", screenshot=True, driver=driver)
        else:
            send_to_tg(f"无需续期，当前到期日: {val}", screenshot=True, driver=driver)
    except Exception as e:
        send_to_tg(f"续期页异常: {str(e)}", screenshot=True, driver=driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally: driver.quit()
