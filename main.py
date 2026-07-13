import os, time, datetime, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
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
    # 窗口位置设置
    options.add_argument("--window-position=100,100") 
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def force_hide_ads_css(driver):
    """注入 CSS 强制屏蔽广告，等同于在开发工具中强制隐藏"""
    css = """
    div[style*='z-index: 45'] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }
    """
    driver.execute_script(f"""
        var style = document.createElement('style');
        style.type = 'text/css';
        style.innerHTML = `{css}`;
        document.head.appendChild(style);
    """)
    print("[LOG] 已注入强制屏蔽 CSS 规则")

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
    
    # 执行一次强制屏蔽
    force_hide_ads_css(driver)
    
    # 查找并点击按钮
    # 使用 find_elements 避免异常导致程序崩溃，遍历查找以确保文字匹配
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = None
    for el in elements:
        txt = el.text.strip().upper()
        if txt == "START" or txt == "STOP":
            target = el
            break
            
    if target:
        btn_text = target.text.strip().upper()
        print(f"[LOG] 找到按钮，文本为: {btn_text}")
        if btn_text == "START":
            driver.execute_script("arguments[0].click();", target)
            send_to_tg("已执行服务器启动 (START) 操作")
        else:
            send_to_tg("服务器处于运行状态 (STOP)，无需启动")
    else:
        print("[LOG] 未找到目标按钮")
        send_to_tg("按钮定位失败，请检查页面截图", screenshot=True, driver=driver)

    # 续期页
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(5)
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        if (datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y") - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            driver.execute_script("arguments[0].click();", renew_btn)
            send_to_tg(f"已执行续期，当前到期日: {val}")
    except Exception as e:
        print(f"[LOG] 续期操作失败: {e}")

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally:
        driver.quit()
