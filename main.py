import os, time, datetime, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 配置区域
EMAIL, PASSWORD = os.getenv("EMAIL"), os.getenv("PASSWORD")
TG_BOT_TOKEN, TG_CHAT_ID = os.getenv("TG_BOT_TOKEN"), os.getenv("TG_CHAT_ID")
BASE_URL, PROXY_SOCKS5 = os.getenv("BASE_URL"), os.getenv("PROXY_SOCKS5")
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

def hide_ads(driver):
    """穿透 Shadow DOM 的强力去广告逻辑"""
    script = """
    function hideElements(root) {
        // 查找所有 z-index: 45 的 div
        let all = root.querySelectorAll('div');
        all.forEach(el => {
            if (window.getComputedStyle(el).zIndex == 45) {
                el.style.display = 'none';
            }
        });
        // 查找所有自定义的 always-on-top-app
        let shadows = root.querySelectorAll('always-on-top-app');
        shadows.forEach(s => {
            if (s.shadowRoot) hideElements(s.shadowRoot);
            s.style.display = 'none';
        });
    }
    hideElements(document);
    """
    try:
        driver.execute_script(script)
        print("[LOG] 已执行深度去广告（包含 Shadow DOM）")
    except Exception as e:
        print(f"[LOG] 去广告执行错误: {e}")

def safe_action(driver, locator, action_type="click", timeout=15):
    """查找/点击前的去广告预处理"""
    hide_ads(driver)
    wait = WebDriverWait(driver, timeout)
    try:
        element = wait.until(EC.element_to_be_clickable(locator))
        if action_type == "click":
            element.click()
            print(f"[LOG] 点击成功: {locator}")
        return element
    except Exception as e:
        print(f"[LOG] 定位失败: {locator}")
        raise e

def login(driver):
    driver.get(f"{BASE_URL}/login")
    hide_ads(driver)
    send_to_tg("已打开登录页", screenshot=True, driver=driver)
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    # 启动页
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(5)
    hide_ads(driver)
    send_to_tg("已打开详情页", screenshot=True, driver=driver)
    
    try:
        # 优化查找逻辑：使用 CSS 定位 Start 按钮
        btn = safe_action(driver, (By.XPATH, "//button[contains(., 'Start') or contains(., 'STOP')]"), "find")
        if "Start" in btn.text:
            safe_action(driver, (By.XPATH, "//button[contains(., 'Start')]"), "click")
            send_to_tg("已点击 Start 按钮。")
    except Exception as e:
        send_to_tg(f"启动失败: {str(e)}", screenshot=True, driver=driver)

    # 续期页
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    hide_ads(driver)
    send_to_tg("已打开续期页", screenshot=True, driver=driver)
    try:
        expiry = safe_action(driver, (By.ID, "expires_at"), "find")
        val = expiry.get_attribute("value")
        # 续期逻辑...
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).days <= 2:
            safe_action(driver, (By.XPATH, "//button[contains(text(), 'Renew')]"), "click")
            send_to_tg(f"续期已完成。")
    except Exception as e:
        send_to_tg(f"续期失败: {str(e)}", screenshot=True, driver=driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally: driver.quit()
