import os, time, datetime, telebot, random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# --- 依赖项检查 ---
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

def send_to_tg_with_blue_dot(message, driver, x, y):
    file_path = "screenshot.png"
    driver.save_screenshot(file_path)
    if PIL_AVAILABLE and x != 0 and y != 0:
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

def human_like_click(driver, target):
    """你提供的标准点击逻辑"""
    loc = target.location
    size = target.size
    cx, cy = int(loc['x'] + size['width'] / 2), int(loc['y'] + size['height'] / 2)
    actions = ActionChains(driver)
    actions.move_by_offset(960, 100).perform()
    actions.move_to_element(target).pause(random.uniform(0.5, 1.2)).click().perform()
    return cx, cy

def force_remove_and_disable_ads(driver):
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

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def get_element_by_text(driver, keywords):
    """辅助查找工具，用于严谨查找 START/STOP/KILL"""
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    return next((el for el in elements if any(s in el.text.strip().upper() for s in keywords)), None)

def manage_server(driver):
    # 详情页处理
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(8)
    force_remove_and_disable_ads(driver)
    
    # 严谨的重启流程：STOP -> KILL -> START
    process_steps = [("STOP", ["STOP"]), ("KILL", ["KILL"]), ("START", ["START"])]
    
    for step_name, keywords in process_steps:
        target = get_element_by_text(driver, keywords)
        if target:
            print(f"[LOG] 找到按钮: {step_name}，准备点击")
            cx, cy = human_like_click(driver, target)
            time.sleep(10) # 点击后给网页反应时间
        else:
            if step_name == "START":
                send_to_tg_with_blue_dot("重启流程结束，START按钮未找到。", driver, 0, 0)
            else:
                print(f"[LOG] 未找到 {step_name}，流程跳过")
    
    # 续期页处理
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(8)
    force_remove_and_disable_ads(driver)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            cx, cy = human_like_click(driver, renew_btn)
            time.sleep(5)
            send_to_tg_with_blue_dot(f"已执行续期操作，到期日: {val}", driver, cx, cy)
        else:
            send_to_tg_with_blue_dot(f"无需续期，到期日: {val}", driver, 0, 0)
    except Exception as e:
        send_to_tg_with_blue_dot(f"续期异常: {str(e)}", driver, 0, 0)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally:
        driver.quit()
