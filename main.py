import os, time, datetime, telebot, random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# --- 依赖项 ---
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 配置项
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
BASE_URL = os.getenv("BASE_URL")

bot = telebot.TeleBot(TG_BOT_TOKEN)

def send_to_tg_with_blue_dot(message, driver, x=0, y=0):
    file_path = "screenshot.png"
    driver.save_screenshot(file_path)
    if PIL_AVAILABLE and (x != 0 or y != 0):
        img = Image.open(file_path)
        draw = ImageDraw.Draw(img)
        r = 20
        draw.ellipse((x - r, y - r, x + r, y + r), fill='blue', outline='blue')
        img.save(file_path)
    with open(file_path, "rb") as photo:
        bot.send_photo(TG_CHAT_ID, photo, caption=f"[gameserver] {message}")

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def force_remove_and_disable_ads(driver):
    """恢复的去广告模块"""
    js = """
    var elements = document.querySelectorAll('div[class*="fixed"]');
    var removed = [];
    elements.forEach(function(el) {
        var style = window.getComputedStyle(el);
        if (style.position === 'fixed') {
            removed.push(el.className);
            el.remove();
        }
    });
    var style = document.createElement('style');
    style.innerHTML = 'div[class*="fixed"] { display: none !important; pointer-events: none !important; }';
    document.head.appendChild(style);
    return removed;
    """
    try:
        removed_list = driver.execute_script(js)
        if removed_list: print(f"[LOG] 已销毁全屏遮罩: {removed_list}")
    except Exception as e:
        print(f"[LOG] 广告清理脚本错误: {e}")

def find_and_click(driver, keywords):
    """逻辑：查找元素并点击，确保不越界"""
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if any(s in el.text.strip().upper() for s in keywords)), None)
    
    if target and target.is_displayed():
        loc = target.location
        size = target.size
        cx, cy = int(loc['x'] + size['width'] / 2), int(loc['y'] + size['height'] / 2)
        
        ActionChains(driver).move_to_element(target).pause(random.uniform(0.5, 1.2)).click().perform()
        print(f"[LOG] 已点击: {keywords}, 坐标: ({cx}, {cy})")
        return True, cx, cy
    return False, 0, 0

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server_process(driver):
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(8)
    force_remove_and_disable_ads(driver)
    
    for action_name, keywords in [("STOP", ["STOP"]), ("KILL", ["KILL"]), ("START", ["START"])]:
        success, x, y = find_and_click(driver, keywords)
        if success:
            print(f"[LOG] {action_name} 操作成功")
            time.sleep(10)
        else:
            print(f"[LOG] 未找到 {action_name} 按钮，流程中断")
            send_to_tg_with_blue_dot(f"重启流程中断：未能执行 {action_name} 操作", driver)
            return False
    
    send_to_tg_with_blue_dot("服务器已成功重启 (STOP->KILL->START)", driver, x, y)
    return True

def renew_server_process(driver):
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(8)
    force_remove_and_disable_ads(driver)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            success, x, y = find_and_click(driver, ["RENEW"])
            if success:
                send_to_tg_with_blue_dot(f"续期成功，到期日: {val}", driver, x, y)
            else:
                send_to_tg_with_blue_dot("续期失败：未找到RENEW按钮", driver)
        else:
            print(f"[LOG] 无需续期，到期日: {val}")
    except Exception as e:
        send_to_tg_with_blue_dot(f"续期异常: {str(e)}", driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver):
            manage_server_process(driver)
            renew_server_process(driver)
    finally:
        driver.quit()
