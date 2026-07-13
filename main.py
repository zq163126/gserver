import os, time, datetime, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- 蓝点绘制环境检查 ---
# 只有在你的 .yml 文件中加入了 pip install Pillow，才能导入成功
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
    print("[LOG] Pillow 库已加载，截图标记功能就绪 (蓝点)。")
except ImportError:
    PIL_AVAILABLE = False
    print("[LOG] [警告] 未找到 Pillow 库。截图将无法标记蓝点。请检查 .yml 配置。")

# 配置项
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
BASE_URL = os.getenv("BASE_URL")

bot = telebot.TeleBot(TG_BOT_TOKEN)

def force_remove_and_disable_ads(driver, class_name):
    """
    核武器级去广告：
    1. 物理删除当前 DOM 节点
    2. 注入 CSS 彻底将该 class 设为不可见且不响应事件
    """
    # 将 class 名称的空格替换为点，用于 CSS 选择器
    css_selector = "." + class_name.replace(" ", ".")
    
    js = f"""
    // 1. 物理删除所有匹配的元素
    var ads = document.querySelectorAll('{css_selector}');
    ads.forEach(function(el) {{
        el.remove();
    }});
    
    // 2. 注入全局 CSS 规则，防止其通过 JS 再次生成
    if (!document.getElementById('disable-ad-style')) {{
        var style = document.createElement('style');
        style.id = 'disable-ad-style';
        style.innerHTML = '{css_selector} {{ display: none !important; pointer-events: none !important; visibility: hidden !important; }}';
        document.head.appendChild(style);
    }}
    return ads.length;
    """
    try:
        count = driver.execute_script(js)
        if count > 0:
            print(f"[LOG] 已销毁并永久禁用广告元素 (Class: {class_name})")
    except Exception as e:
        print(f"[LOG] 广告处理脚本执行出错: {e}")

def send_to_tg_with_blue_dot(message, driver, x, y):
    """发送带蓝色标记点的截图 (仅当 Pillow 可用时)"""
    file_path = "screenshot.png"
    driver.save_screenshot(file_path)
    
    if PIL_AVAILABLE:
        try:
            img = Image.open(file_path)
            draw = ImageDraw.Draw(img)
            r = 20 # 点的半径，设大一点更醒目
            # 绘制蓝色实心圆
            draw.ellipse((x - r, y - r, x + r, y + r), fill='blue', outline='blue')
            img.save(file_path)
            print(f"[LOG] 已在截图标记蓝点: ({x}, {y})")
        except Exception as e:
            print(f"[LOG] 绘制蓝点失败: {e}")
    else:
        print("[LOG] Pillow 不可用，跳过蓝点绘制。")
        
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

def login(driver):
    driver.get(f"{BASE_URL}/login")
    # 登录页不确定是否有该广告，先不调用，防止报错
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    time.sleep(5)
    return "dashboard" in driver.current_url

def manage_server(driver):
    # 1. 详情页处理
    driver.get(f"{BASE_URL}/gameserver/611226956150741300/details")
    time.sleep(8) # 留足时间等广告弹出
    
    # 根据你的 LOG，这里是广告的 class 名称，我们针对它处理
    problem_class = "fixed inset-0 flex items-center justify-center overflow-y-auto px-4 py-6 sm:px-0"
    force_remove_and_disable_ads(driver, problem_class)
    
    elements = driver.find_elements(By.XPATH, "//*[self::button or self::div or self::span or self::a]")
    target = next((el for el in elements if el.text.strip().upper() in ["START", "STOP"]), None)
    
    if target and target.text.strip().upper() == "START":
        loc = target.location
        size = target.size
        cx, cy = int(loc['x'] + size['width'] / 2), int(loc['y'] + size['height'] / 2)
        print(f"[LOG] 目标中心坐标 (蓝点位置): X={cx}, Y={cy}")
        
        # 强制 JS 点击
        driver.execute_script("arguments[0].click();", target)
        
        time.sleep(10)
        send_to_tg_with_blue_dot("已执行启动 (START) 点击", driver, cx, cy)
    else:
        # 未找到按钮时也发个截图确认
        driver.save_screenshot("screenshot.png")
        with open("screenshot.png", "rb") as photo:
            bot.send_photo(TG_CHAT_ID, photo, caption="[gameserver] 未找到 START 按钮，或服务器已启动。")

    # 2. 续期页处理
    driver.get(f"{BASE_URL}/service/611226958331781095/renew")
    time.sleep(8)
    # 续期页不确定是否有该广告，暂不调用，防止误伤正常元素
    try:
        val = driver.find_element(By.ID, "expires_at").get_attribute("value")
        expiry_date = datetime.datetime.strptime(val.split(" - ")[0], "%d.%m.%Y")
        if (expiry_date - datetime.datetime.now()).total_seconds() <= 7200:
            renew_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Renew')]")
            driver.execute_script("arguments[0].click();", renew_btn)
            time.sleep(5)
            send_to_tg_with_blue_dot(f"已自动续期，到期日: {val}", driver, 0, 0) # 续期不画蓝点
        else:
            send_to_tg_with_blue_dot(f"无需续期，到期日: {val}", driver, 0, 0)
    except Exception as e:
        send_to_tg(f"续期处理异常: {str(e)}", screenshot=True, driver=driver)

if __name__ == "__main__":
    driver = setup_driver()
    try:
        if login(driver): manage_server(driver)
    finally:
        driver.quit()
