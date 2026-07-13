import os, time, datetime, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
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

def detect_and_hide_ads(driver):
    """
    逻辑：扫描页面，如果发现广告遮罩则隐藏并返回 True，否则返回 False
    """
    script = """
    let ads = document.querySelectorAll('div, always-on-top-app');
    let found = false;
    ads.forEach(el => {
        if (window.getComputedStyle(el).zIndex >= 45) {
            el.style.display = 'none';
            found = true;
        }
    });
    return found;
    """
    return driver.execute_script(script)

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    # 访问详情页
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    
    # --- 广告侦测测试 (2分钟) ---
    print("[LOG] 开始广告侦测测试 (持续120秒)...")
    for i in range(24): # 每5秒扫一次
        time.sleep(5)
        if detect_and_hide_ads(driver):
            print(f"[LOG] {datetime.datetime.now().strftime('%H:%M:%S')} - 发现并隐藏了广告！")
        else:
            print(f"[LOG] {datetime.datetime.now().strftime('%H:%M:%S')} - 当前页面暂无广告")
    
    # 侦测完后，尝试查找按钮
    print("[LOG] 侦测结束，尝试查找按钮...")
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span]")
    target = None
    for el in elements:
        txt = el.text.strip().upper()
        if "START" in txt or "STOP" in txt:
            target = el
            break
            
    if target:
        print(f"[LOG] 找到按钮，文本: {target.text}")
        if "START" in target.text.upper():
            driver.execute_script("arguments[0].click();", target)
            send_to_tg("已启动服务器")
    else:
        send_to_tg("侦测后仍无法找到按钮", screenshot=True, driver=driver)

    # 续期逻辑
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    if detect_and_hide_ads(driver): print("[LOG] 续期页发现广告并已清理")
    
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            driver.execute_script("arguments[0].click();", renew_btn)
            send_to_tg(f"已执行续期，到期日: {val}")
    except Exception as e:
        send_to_tg(f"续期失败: {e}", screenshot=True, driver=driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally: driver.quit()
