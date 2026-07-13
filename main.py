import os, time, datetime, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
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

def force_remove_ads(driver):
    """强制物理删除所有广告相关元素，并在 LOG 输出清理详情"""
    js = """
    var ads = document.querySelectorAll('div[style*="z-index: 45"], div[style*="z-index: 50"], .ads, .modal');
    var removed = [];
    ads.forEach(function(el) {
        removed.push(el.tagName + '.' + el.className);
        el.remove();
    });
    return removed;
    """
    removed_list = driver.execute_script(js)
    if removed_list:
        print(f"[LOG] 探测到广告并已物理销毁: {removed_list}")
    else:
        print("[LOG] 未发现广告，继续执行")

def login(driver):
    driver.get(f"{BASE_URL}/login")
    force_remove_ads(driver)
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(5)
    force_remove_ads(driver)
    
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if el.text.strip().upper() in ["START", "STOP"]), None)
    
    if target and target.text.strip().upper() == "START":
        loc = target.location
        size = target.size
        cx, cy = int(loc['x'] + size['width'] / 2), int(loc['y'] + size['height'] / 2)
        print(f"[LOG] 目标坐标 (蓝点位置): X={cx}, Y={cy}")
        
        # 强制 JS 触发点击，不经过复杂的 Actions
        driver.execute_script("arguments[0].click();", target)
        
        time.sleep(10)
        send_to_tg(f"已执行启动点击，目标中心坐标({cx}, {cy})，请核实截图。", screenshot=True, driver=driver)
    else:
        send_to_tg("未找到启动按钮。", screenshot=True, driver=driver)

    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    force_remove_ads(driver)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            driver.execute_script("arguments[0].click();", renew_btn)
            time.sleep(5)
            send_to_tg(f"续期完成，到期日: {val}", screenshot=True, driver=driver)
    except Exception as e:
        send_to_tg(f"续期异常: {e}", screenshot=True, driver=driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally:
        driver.quit()
