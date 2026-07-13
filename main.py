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

def hide_ads_if_exists(driver):
    """先检查是否存在广告，存在则注入 CSS 隐藏"""
    js = """
    var ads = document.querySelectorAll('div[style*="z-index: 45"], div[style*="z-index: 50"]');
    if (ads.length > 0) {
        var style = document.createElement('style');
        style.innerHTML = 'div[style*="z-index: 45"], div[style*="z-index: 50"] { display: none !important; pointer-events: none !important; }';
        document.head.appendChild(style);
        return true;
    }
    return false;
    """
    found = driver.execute_script(js)
    if found: print("[LOG] 监测到广告，已应用 CSS 隐藏")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(8)
    if "dashboard" in driver.current_url:
        send_to_tg("登录成功", screenshot=True, driver=driver)
        return True
    return False

def manage_server(driver):
    # 1. 详情页
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10)
    hide_ads_if_exists(driver)
    
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if el.text.strip().upper() in ["START", "STOP"]), None)
            
    if target and target.text.strip().upper() == "START":
        try:
            target.click() # 尝试普通点击
        except:
            driver.execute_script("arguments[0].click();", target) # 若失败用 JS 强制点
        
        time.sleep(10) # 等待启动
        send_to_tg("已点击启动 (START)，当前状态截图：", screenshot=True, driver=driver)
    else:
        send_to_tg(f"按钮状态: {target.text if target else '未找到'}，无需启动。", screenshot=True, driver=driver)

    # 2. 续期页
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(8)
    hide_ads_if_exists(driver)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            renew_btn.click()
            time.sleep(5)
            send_to_tg(f"已自动续期，到期日: {val}", screenshot=True, driver=driver)
    except Exception as e:
        send_to_tg(f"续期处理异常: {str(e)}", screenshot=True, driver=driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally:
        driver.quit()
