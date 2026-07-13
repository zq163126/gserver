import os, time, datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 配置项
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
BASE_URL = os.getenv("BASE_URL")

def setup_driver():
    options = Options()
    # 修复 GitHub Actions 环境下的崩溃参数
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def force_hide_ads_css(driver):
    """通过注入 CSS 强制隐藏广告 DIV，等同于在开发工具操作"""
    css = "div[style*='z-index: 45'] { display: none !important; visibility: hidden !important; pointer-events: none !important; }"
    driver.execute_script(f"var s = document.createElement('style'); s.innerHTML = '{css}'; document.head.appendChild(s);")

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
    time.sleep(5)
    force_hide_ads_css(driver)
    
    # 查找按钮并判断文字，仅 START 时点击
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if el.text.strip().upper() in ["START", "STOP"]), None)
            
    if target and target.text.strip().upper() == "START":
        driver.execute_script("arguments[0].click();", target)
        print("[LOG] 已点击 START")

    # 续期页逻辑
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        # 此处保留你原有的续期逻辑
    except Exception as e:
        print(f"[LOG] 续期异常: {e}")

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver):
            manage_server(driver)
    finally:
        driver.quit()
