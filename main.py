import os, time, datetime, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

EMAIL, PASSWORD = os.getenv("EMAIL"), os.getenv("PASSWORD")
TG_BOT_TOKEN, TG_CHAT_ID = os.getenv("TG_BOT_TOKEN"), os.getenv("TG_CHAT_ID")
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
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def check_and_hide_ads(driver):
    """在任何交互前调用此函数，有则隐藏，无则直接跳过"""
    script = """
    let found = false;
    document.querySelectorAll('div, always-on-top-app').forEach(el => {
        if (window.getComputedStyle(el).zIndex == 45) {
            el.style.display = 'none';
            found = true;
        }
    });
    return found;
    """
    return driver.execute_script(script)

def perform_action(driver, locator, action_type="click"):
    """
    统一交互逻辑：
    1. 交互前先处理广告
    2. 执行操作
    3. 如果失败，处理广告并重试一次
    """
    for attempt in range(2):
        check_and_hide_ads(driver)
        try:
            wait = WebDriverWait(driver, 5)
            element = wait.until(EC.element_to_be_clickable(locator))
            if action_type == "click":
                driver.execute_script("arguments[0].click();", element)
                return element
            return element
        except:
            if attempt == 0:
                print(f"[LOG] 交互失败，可能广告刚弹出，清理后重试...")
                check_and_hide_ads(driver)
    raise Exception(f"定位元素 {locator} 失败")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    # --- 1. 详情页处理 ---
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    
    # 查找按钮并读取文本（先定位不点击）
    xpath_query = "//*[contains(translate(text(), 'STARTOP', 'startop'), 'start') or contains(translate(text(), 'STARTOP', 'startop'), 'stop')]"
    btn = perform_action(driver, (By.XPATH, xpath_query), action_type="find")
    
    btn_text = btn.text.strip().upper()
    print(f"[LOG] 按钮文字: {btn_text}")
    
    if btn_text == "START":
        perform_action(driver, (By.XPATH, xpath_query), action_type="click")
        send_to_tg("已执行服务器启动 (START) 操作。")
    elif btn_text == "STOP":
        send_to_tg("服务器正在运行 (STOP)，无需启动。")

    # --- 2. 续期页处理 ---
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    
    # 读取有效期
    expiry_input = perform_action(driver, (By.ID, "expires_at"), action_type="find")
    val = expiry_input.get_attribute("value")
    
    expiry_date = datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y")
    if (expiry_date - datetime.datetime.now()).total_seconds() <= 7200:
        perform_action(driver, (By.XPATH, "//button[contains(text(), 'Renew')]"), action_type="click")
        send_to_tg(f"已执行续期，当前到期日: {val}")
    else:
        send_to_tg(f"无需续期，当前到期日: {val}")

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally: driver.quit()
