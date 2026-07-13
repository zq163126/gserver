import os, time, datetime, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image, ImageDraw # 用于绘制红点

# 配置项
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
BASE_URL = os.getenv("BASE_URL")

bot = telebot.TeleBot(TG_BOT_TOKEN)

def draw_red_dot_on_screenshot(file_path, x, y):
    """在截图中指定坐标画一个红点"""
    img = Image.open(file_path)
    draw = ImageDraw.Draw(img)
    r = 10 # 红点半径
    draw.ellipse((x - r, y - r, x + r, y + r), fill='red', outline='red')
    img.save(file_path)

def send_to_tg(message, screenshot=False, driver=None, x=None, y=None):
    if screenshot and driver:
        file_path = "screenshot.png"
        driver.save_screenshot(file_path)
        if x and y:
            draw_red_dot_on_screenshot(file_path, x, y)
        with open(file_path, "rb") as photo:
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

def detect_and_handle_ads(driver):
    js = """
    var ads = document.querySelectorAll('div[style*="z-index: 45"], div[style*="z-index: 50"], .ads, .modal');
    var found = [];
    ads.forEach(function(el) {
        if (el.offsetWidth > 0 && el.offsetHeight > 0) {
            found.push({tagName: el.tagName, id: el.id, className: el.className});
            el.remove();
        }
    });
    return found;
    """
    found_elements = driver.execute_script(js)
    if found_elements: print(f"[LOG] 清理广告: {found_elements}")
    return len(found_elements) > 0

def login(driver):
    driver.get(f"{BASE_URL}/login")
    detect_and_handle_ads(driver)
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(5)
    detect_and_handle_ads(driver)
    
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if el.text.strip().upper() in ["START", "STOP"]), None)
    
    if target and target.text.strip().upper() == "START":
        # 获取坐标
        loc = target.location
        size = target.size
        x, y = int(loc['x'] + size['width'] / 2), int(loc['y'] + size['height'] / 2)
        print(f"[LOG] 准备点击坐标: X={x}, Y={y}")
        
        # 执行点击
        ActionChains(driver).move_to_element(target).click().perform()
        
        time.sleep(10)
        send_to_tg(f"已点击 START，坐标: ({x}, {y})", screenshot=True, driver=driver, x=x, y=y)
    else:
        send_to_tg("无需启动或未找到按钮。", screenshot=True, driver=driver)

    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            renew_btn.click()
            time.sleep(5)
            send_to_tg(f"已续期，到期日: {val}", screenshot=True, driver=driver)
    except Exception as e:
        send_to_tg(f"续期异常: {str(e)}", screenshot=True, driver=driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally:
        driver.quit()
