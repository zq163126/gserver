import os, time, datetime, telebot, json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 配置项
EMAIL = os.getenv("EMAIL")
PASSWORD = "你的固定密码"  # 严格按要求：固定密码
WINDOW_POS_FILE = "window_pos.json"

def get_window_pos():
    if os.path.exists(WINDOW_POS_FILE):
        with open(WINDOW_POS_FILE, "r") as f:
            return json.load(f)
    return {"x": 100, "y": 100}

def save_window_pos(driver):
    pos = driver.get_window_position()
    with open(WINDOW_POS_FILE, "w") as f:
        json.dump(pos, f)

def setup_driver():
    options = Options()
    pos = get_window_pos() # 严格按要求：记忆窗口位置
    options.add_argument(f"--window-position={pos['x']},{pos['y']}")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def force_hide_ads_css(driver):
    """严格按要求：类似开发工具的强制隐藏"""
    css = "div[style*='z-index: 45'] { display: none !important; visibility: hidden !important; pointer-events: none !important; }"
    driver.execute_script(f"var s = document.createElement('style'); s.innerHTML = '{css}'; document.head.appendChild(s);")

def login(driver):
    driver.get(f"{os.getenv('BASE_URL')}/login")
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    # 访问详情页
    driver.get(f"{os.getenv('BASE_URL')}/gameserver/611226956150741300/details")
    time.sleep(5)
    force_hide_ads_css(driver)
    
    # 严格按要求：查找按钮并判断文字，仅 START 时点击
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if el.text.strip().upper() in ["START", "STOP"]), None)
            
    if target and target.text.strip().upper() == "START":
        driver.execute_script("arguments[0].click();", target)
        print("[LOG] 已点击 START")

    # 续期页逻辑
    driver.get(f"{os.getenv('BASE_URL')}/service/611226958331781095/renew")
    time.sleep(5)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        # 续期逻辑...
    except Exception as e:
        print(f"[LOG] 续期异常: {e}")

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver):
            manage_server(driver)
            save_window_pos(driver) # 严格按要求：保存位置
    finally:
        driver.quit()
