import os, time, datetime, telebot
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
    options.add_argument("--window-size=1920,1080")
    if PROXY_SOCKS5: options.add_argument(f'--proxy-server={PROXY_SOCKS5}')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def process_ads(driver):
    """检测并隐藏广告"""
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

def safe_action(driver, locator, action_type="click", timeout=10):
    """带重试的查找操作"""
    for attempt in range(2):
        print(f"[LOG] 尝试定位 {locator}, 第 {attempt+1} 次")
        
        # 执行去广告
        found = process_ads(driver)
        if found: print("[LOG] 检测并隐藏了广告")
        
        try:
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.element_to_be_clickable(locator))
            if action_type == "click":
                element.click()
                print(f"[LOG] 点击成功: {locator}")
            return element
        except Exception:
            print(f"[LOG] 第 {attempt+1} 次查找 {locator} 失败")
            if attempt == 0:
                time.sleep(3) # 等待广告弹出或加载
                continue
    
    # 两次都失败
    print(f"[LOG] !!! 致命错误：无法找到元素 {locator}")
    driver.save_screenshot("failure.png")
    with open("failure.png", "rb") as photo:
        bot.send_photo(TG_CHAT_ID, photo, caption=f"[gameserver] 无法定位元素: {locator}")
    raise Exception(f"定位元素失败: {locator}")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    # 启动页
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(10)
    try:
        btn = safe_action(driver, (By.XPATH, "//button[contains(., 'Start') or contains(., 'STOP')]"), "find")
        if "Start" in btn.text:
            safe_action(driver, (By.XPATH, "//button[contains(., 'Start')]"), "click")
            send_to_tg("已执行启动操作。")
    except Exception as e:
        print(f"[LOG] 启动页流程中断: {e}")

    # 续期页
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    try:
        expiry = safe_action(driver, (By.ID, "expires_at"), "find")
        val = expiry.get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).days <= 2:
            safe_action(driver, (By.XPATH, "//button[contains(text(), 'Renew')]"), "click")
            send_to_tg("续期已完成。")
    except Exception as e:
        print(f"[LOG] 续期页流程中断: {e}")

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally: driver.quit()
