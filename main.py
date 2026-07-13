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
    """注入 CSS 强制屏蔽广告"""
    css_content = "div[style*='z-index: 45'] { display: none !important; visibility: hidden !important; pointer-events: none !important; }"
    js = "var s = document.createElement('style'); s.innerHTML = arguments[0]; document.head.appendChild(s);"
    driver.execute_script(js, css_content)

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    if "dashboard" in driver.current_url:
        send_to_tg("登录成功")
        return True
    return False

def manage_server(driver):
    # 访问详情页
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10)
    force_hide_ads_css(driver)
    
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if el.text.strip().upper() in ["START", "STOP"]), None)
            
    if target:
        btn_text = target.text.strip().upper()
        if btn_text == "START":
            # 强化点击逻辑：执行多次 JS 点击并等待页面响应
            driver.execute_script("arguments[0].scrollIntoView();", target)
            driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));")
            driver.execute_script("arguments[0].click();")
            time.sleep(5) # 等待页面处理启动请求
            send_to_tg("已执行服务器启动 (START) 操作，并已截图确认状态。", screenshot=True, driver=driver)
        else:
            send_to_tg("服务器处于运行状态 (STOP)，无需启动。")
    else:
        send_to_tg("找不到按钮，已截图。", screenshot=True, driver=driver)

    # 续期逻辑
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    force_hide_ads_css(driver)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            driver.execute_script("arguments[0].click();", renew_btn)
            time.sleep(3)
            send_to_tg(f"已执行续期，当前到期日: {val}", screenshot=True, driver=driver)
    except Exception as e:
        send_to_tg(f"续期操作失败: {e}", screenshot=True, driver=driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally: driver.quit()
