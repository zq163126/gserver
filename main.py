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

def send_to_tg_with_blue_dot(message, driver, x=0, y=0):
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

def find_and_click(driver, keywords):
    """严谨的查找点击流程"""
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if any(s in el.text.strip().upper() for s in keywords)), None)
    
    if target and target.is_displayed():
        btn_text = target.text.strip()
        print(f"[LOG] 找到目标: '{btn_text}', 准备执行点击...")
        
        loc = target.location
        size = target.size
        cx, cy = int(loc['x'] + size['width'] / 2), int(loc['y'] + size['height'] / 2)
        
        # 使用 move_to_element 代替 offset，这是最稳定的点击方式，绝不越界
        actions = ActionChains(driver)
        actions.move_to_element(target).pause(random.uniform(0.5, 1.2)).click().perform()
        
        print(f"[LOG] 点击成功: '{btn_text}' at ({cx}, {cy})")
        return True, cx, cy
    else:
        print(f"[LOG] 未找到包含关键字 {keywords} 的可点击元素")
        return False, 0, 0

def force_remove_and_disable_ads(driver):
    js = """
    var elements = document.querySelectorAll('div[class*="fixed"]');
    elements.forEach(function(el) { el.remove(); });
    """
    driver.execute_script(js)

def login(driver):
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(8)
    force_remove_and_disable_ads(driver)
    
    # 按照严谨流程操作
    # 1. 尝试找 STOP
    success, x, y = find_and_click(driver, ["STOP"])
    if success:
        time.sleep(10)
        # 2. 尝试找 KILL
        success, x, y = find_and_click(driver, ["KILL"])
        if not success:
            send_to_tg_with_blue_dot("STOP点击成功，但未找到KILL按钮，流程中断。", driver)
            return
        time.sleep(10)
    
    # 3. 找 START
    success, x, y = find_and_click(driver, ["START"])
    if success:
        send_to_tg_with_blue_dot("已成功执行重启流程 (STOP->KILL->START)", driver, x, y)
    else:
        send_to_tg_with_blue_dot("重启流程失败：未找到START按钮。", driver)

    # 续期处理
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(8)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            success, x, y = find_and_click(driver, ["RENEW"])
            if success: send_to_tg_with_blue_dot(f"续期成功，到期日: {val}", driver, x, y)
        else:
            print(f"[LOG] 无需续期，到期日: {val}")
    except Exception as e:
        send_to_tg_with_blue_dot(f"续期异常: {str(e)}", driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally:
        driver.quit()
