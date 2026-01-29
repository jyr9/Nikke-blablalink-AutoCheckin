import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

# --- 全局常量 ---
TIMESLEEP = 0.5  # 定义一个统一的等待时间，方便管理


def highlight_element(driver, element, duration=0.5):
    """
    使用JavaScript高亮显示一个元素，持续指定时间。
    :param driver: WebDriver 实例
    :param element: 要高亮的网页元素
    :param duration: 高亮持续时间（秒）
    """
    try:
        # 保存原始边框样式
        original_style = element.get_attribute("style")
        # 应用高亮样式：3像素、红色、实线边框
        highlight_style = "border: 3px solid red; box-shadow: 0px 0px 8px red;"
        driver.execute_script(f"arguments[0].setAttribute('style', arguments[1]);", element,
                              original_style + highlight_style)

        # 等待指定时间，让肉眼可以看到高亮效果
        time.sleep(duration)

        # 恢复元素的原始样式
        driver.execute_script("arguments[0].setAttribute('style', arguments[1]);", element, original_style)
    except Exception as e:
        # 如果元素失效或出现其他问题，则忽略高亮，避免脚本中断
        # print(f"高亮元素时出错: {e}")
        pass


def setup_driver(profile_path):
    """
    配置并初始化 Chrome 浏览器驱动。

    该函数会设置 Chrome 的用户数据目录，使得浏览器可以加载指定的配置文件（如已登录的会话），
    并添加了一些优化选项来启动浏览器。

    :param profile_path: 字符串，Chrome 用户配置文件的路径。
    :return: 初始化后的 WebDriver 实例。
    """
    print("--- 正在启动浏览器 ---")
    options = Options()
    # 使用指定的 Chrome 用户配置文件，这样可以免去登录过程
    options.add_argument(f"user-data-dir={profile_path}")
    # 以下选项有助于避免一些潜在问题
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    print("浏览器启动成功。")
    return driver


def daily_check_in(driver, wait):
    """
    智能判断签到状态并执行相应操作。
    - 使用高精度XPath，避免與其他任務混淆。
    - V3版：根據回饋，直接點擊icon-gift.png圖標元素，而非其父容器。
    """
    time.sleep(2)
    print("\n--- 开始检查“每日签到”状态 ---")
    try:
        # 1. 檢查“已完成”圖標是否存在。此邏輯保持不變，因為它已經很精確。
        #    XPath含義: 在'每日簽到'所在的任務行中，尋找class包含 'icon-gift-true.png' 的div。
        already_checked_in_icon_locator = (
            By.XPATH,
            "//div[@data-cname='index' and .//div[contains(text(), '每日簽到')]]//div[contains(@class, 'icon-gift-true.png')]"
        )

        already_checked_in_elements = driver.find_elements(*already_checked_in_icon_locator)

        # 2. 根據是否找到“已签到”圖標來執行不同邏輯
        if len(already_checked_in_elements) > 0:
            print("✅ 检测到 'icon-gift-true.png'，今日已签到，无需重复操作。")
            highlight_element(driver, already_checked_in_elements[0])
            return
        else:
            print("检测到 'icon-gift.png' 或未找到完成圖標，准备执行签到操作...")

            # 3. 【核心修改】構造一個XPath，直接指向“每日簽到”這一行中需要點擊的 “未完成” 圖標div。
            #    XPath含義：在'每日簽到'所在的任務行(div[@data-cname='index'])中，
            #    找到那個class屬性包含 'icon-gift.png' 的div元素。
            button_to_click_locator = (
                By.XPATH,
                "//div[@data-cname='index' and .//div[contains(text(), '每日簽到')]]//div[contains(@class, 'icon-gift.png')]"
            )

            # 等待這個具體的圖標元素變為可點擊狀態
            confirmElement = wait.until(
                EC.element_to_be_clickable(button_to_click_locator)
            )

            highlight_element(driver, confirmElement)
            driver.execute_script("arguments[0].click();", confirmElement)
            print("成功点击签到图标 (icon-gift.png)。")

    except TimeoutException:
        print("❌ 页面上未找到“每日签到”功能区或其相关按钮，跳过此任务。")
    except Exception as e:
        print(f"❌ 执行“每日签到”检查时出现意外错误: {e}")

    time.sleep(TIMESLEEP)


def navigate_to_outpost(driver, wait):
    """
    导航到“前哨基地”。

    :param driver: WebDriver 实例。
    :param wait: WebDriverWait 实例。
    :return: None
    """
    print("\n--- 开始导航至“前哨基地” ---")

    try:
        navigate_to_outpost_url = "https://www.blablalink.com/?plate_type=outpost"
        driver.get(navigate_to_outpost_url)
        print(f"成功导航到前哨基地")
    except Exception as e:
        print(f"执行“导航到前哨基地”出现意外错误: {e}")

    time.sleep(TIMESLEEP)


def switch_to_latest_posts(driver, wait):
    """
    将帖子列表从默认排序“热门”切换到“最新”排序。
    此版本使用文本内容定位，增强了脚本的稳定性。
    """
    print("\n--- 开始切换帖子排序为“最新” ---")

    post_xpath = "//div[contains(@class, 'card-item')]"
    try:
        # 记录切换前的第一个帖子元素，用于后续判断列表是否已刷新
        try:
            first_post_before_click = wait.until(EC.presence_of_element_located((By.XPATH, post_xpath)))
        except TimeoutException:
            first_post_before_click = None
            print("切换前未能定位到帖子，将仅执行切换操作。")

        # 1. 定位“热门”按钮：通过其包含的文本“熱門”来查找。
        #    这个XPath寻找一个<button>元素，其内部任何位置(.)包含了文本'熱門'。
        hot_button_xpath = "//button[contains(., '熱門')]"
        hot_button = wait.until(EC.element_to_be_clickable((By.XPATH, hot_button_xpath)))
        highlight_element(driver, hot_button)  # 高亮点击的元素
        hot_button.click()
        print("成功点击排序方式按钮（通过文本'熱門'定位）。")

        # 2. 在弹出的列表中选择“最新”。
        #    这个XPath寻找一个<li>元素（列表项），其内部任何位置包含了文本'最新'。
        latest_button_xpath = "//li[contains(., '最新')]"
        latest_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, latest_button_xpath))
        )
        highlight_element(driver, latest_button)  # 高亮点击的元素
        latest_button.click()
        print("成功点击切换为“最新”排序（通过文本'最新'定位）。")

        # 等待列表刷新
        if first_post_before_click:
            print("等待帖子列表刷新...")
            wait.until(EC.staleness_of(first_post_before_click))

        # 确认新列表已加载
        wait.until(EC.presence_of_element_located((By.XPATH, post_xpath)))
        print("帖子列表已成功刷新为“最新”。")

    except TimeoutException as e:
        print(f"❌ 切换到“最新”帖子时超时: 可能是未能找到'熱門'或'最新'按钮。错误: {e}")
    except Exception as e:
        print(f"❌ 切换到“最新”帖子时出现意外错误: {e}")
    time.sleep(TIMESLEEP)


def like_posts(driver, wait, num_to_like=5):
    """
    对帖子列表中的前 N 个帖子执行点赞操作。
    此版本经过审查，确认XPath稳定，并增加了高亮显示功能。

    :param driver: WebDriver 实例。
    :param wait: WebDriverWait 实例。
    :param num_to_like: 整数，希望点赞的帖子数量。
    :return: None
    """
    print(f"\n--- 开始执行“点赞”任务（目标：{num_to_like}个） ---")
    # 这个XPath非常稳定，因为它依赖于一个专门用于标识的 data-cname 属性
    like_button_xpath = "//span[@data-cname='like']"
    post_xpath = "//div[contains(@class, 'card-item')]"

    try:
        # 等待帖子列表加载完成
        wait.until(EC.presence_of_element_located((By.XPATH, post_xpath)))

        # 查找所有点赞按钮
        initial_likes = wait.until(EC.presence_of_all_elements_located((By.XPATH, like_button_xpath)))

        # 确定实际要点击的数量
        num_to_click = min(num_to_like, len(initial_likes))

        if num_to_click == 0:
            print("页面上没有找到可点赞的按钮。")
            return  # 提前返回，避免不必要的循环

        print(f"找到了 {len(initial_likes)} 个点赞按钮，准备点击其中的 {num_to_click} 个。")

        liked_count = 0
        for i in range(num_to_click):
            try:
                # 每次循环重新查找所有按钮，这是避免 StaleElementReferenceException 的好习惯
                all_like_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, like_button_xpath)))

                if i >= len(all_like_buttons):
                    print(f"无法找到第 {i + 1} 个点赞按钮，可能列表已刷新或数量不足。")
                    break

                button_to_click = all_like_buttons[i]

                # --- 新增代码：高亮将要点击的元素 ---
                highlight_element(driver, button_to_click)
                # 使用 JavaScript 点击，可以避免元素被遮挡等问题
                driver.execute_script("arguments[0].click();", button_to_click)
                print(f"成功点击第 {i + 1} 个点赞按钮。")
                liked_count += 1

                time.sleep(0.5)  # 等待0.5秒，让点赞操作生效，也避免操作过快

            except StaleElementReferenceException:
                print(f"🟡 点击第 {i + 1} 个点赞按钮时元素已过时，将在下一次循环中尝试重新定位。")
                continue  # 跳过本次循环，在下一次循环中会重新获取按钮列表
            except Exception as e:
                print(f"❌ 点击第 {i + 1} 个点赞按钮时出错: {e}")

        print(f"--- “点赞”任务完成，共成功操作 {liked_count} 次 ---")

    except Exception as e:
        print(f"❌ “点赞”任务执行过程中出现严重错误: {e}")

    time.sleep(TIMESLEEP)


def post_emoji_comment(driver, wait):
    """
    进入第一个帖子的详情页，并发布一个表情作为评论。
    此版本通过先定位评论面板，然后在面板内部进行操作，解决了遮罩层拦截点击的问题。
    同时使用JavaScript点击以提高稳定性。

    :param driver: WebDriver 实例。
    :param wait: WebDriverWait 实例。
    :return: None
    """
    print("\n--- 开始执行“撰写评论（发送表情）”任务 ---")
    try:
        # 1. 点击第一个帖子的标题进入帖子
        first_post_title_locator = (
            By.XPATH,
            "(//div[contains(@class, 'card-item')]//div[contains(@class, 'font-bold') and contains(@class, 'line-clamp-2')])[1]"
        )
        first_post_title = wait.until(EC.element_to_be_clickable(first_post_title_locator))
        highlight_element(driver, first_post_title)
        driver.execute_script("arguments[0].click();", first_post_title)
        print("步骤 1: 成功点击标题，进入帖子详情页面。")

        # 2. 点击“发布我的看法”以弹出评论面板
        # 这个定位器查找一个可点击的div，它内部包含"發佈我的看法"这个文本
        publish_view_button_locator = (By.XPATH, "//div[contains(text(), '發佈我的看法')]")
        publish_view_button = wait.until(EC.element_to_be_clickable(publish_view_button_locator))
        highlight_element(driver, publish_view_button)
        driver.execute_script("arguments[0].click();", publish_view_button)
        print("步骤 2: 已点击“發佈我的看法”，等待评论面板加载...")

        # --- 核心改动：先定位到整个评论面板 ---
        # 策略：这个面板有唯一的“評論”标题和“發送”按钮，以此作为定位依据。
        comment_panel_locator = (By.XPATH, "//div[.//div[text()='評論'] and .//span[text()='發送']]")
        comment_panel = wait.until(EC.visibility_of_element_located(comment_panel_locator))

        # 3. 在评论面板内部，点击"最近"按钮
        # 策略：在已定位的 comment_panel 内部查找。注意XPath开头的 "." 代表从当前元素开始搜索。
        recent_emoji_tab_locator = (
        By.XPATH, ".//div[contains(@class, 'overflow-x-auto')]//div[contains(@class, 'cursor-pointer')][1]")
        recent_emoji_tab = wait.until(EC.element_to_be_clickable(comment_panel.find_element(*recent_emoji_tab_locator)))
        highlight_element(driver, recent_emoji_tab)
        driver.execute_script("arguments[0].click();", recent_emoji_tab)
        print("步骤 3: 已点击“最近”分类。")
        time.sleep(TIMESLEEP)  # 等待表情列表加载

        # 4. 在评论面板内部，选择第一个表情
        # 策略：同样在 comment_panel 内部查找。
        first_emoji_locator = (By.XPATH,
                               ".//div[contains(@class, 'overflow-y-auto') and contains(@class, 'flex-wrap')]//div[contains(@class, 'cursor-pointer')][1]")
        first_emoji = wait.until(EC.element_to_be_clickable(comment_panel.find_element(*first_emoji_locator)))
        highlight_element(driver, first_emoji)
        driver.execute_script("arguments[0].click();", first_emoji)
        print("步骤 4: 已选择第一个表情。")
        time.sleep(TIMESLEEP)

        # 5. 在评论面板内部，点击"發送"来发送
        # 策略：同样在 comment_panel 内部查找。
        send_button_locator = (By.XPATH, ".//span[text()='發送']")
        send_button = wait.until(EC.element_to_be_clickable(comment_panel.find_element(*send_button_locator)))
        highlight_element(driver, send_button)
        driver.execute_script("arguments[0].click();", send_button)
        print("步骤 5: 评论已成功发送。")

        # 等待评论面板关闭
        wait.until(EC.invisibility_of_element_located(comment_panel_locator))

        # 从帖子页面返回列表
        driver.back()
        # 增加一个等待，确保返回后的列表页面已加载完成
        # 这是一个好习惯，能确保下一个任务开始时，页面元素已准备就绪
        post_list_locator = (By.XPATH, "//div[contains(@class, 'card-item')]")
        wait.until(EC.presence_of_element_located(post_list_locator))
        print("--- “撰写评论”任务完成 ---")

    except TimeoutException as e:
        print(f"❌ 执行“撰写评论”任务时超时，未能找到目标元素。请检查页面结构或文本是否已更改。错误: {e}")
        try:
            print("尝试通过浏览器后退功能恢复...")
            driver.back()
            time.sleep(1)
        except Exception as back_e:
            print(f"浏览器后退失败: {back_e}")
    except Exception as e:
        print(f"❌ 执行“撰写评论”任务时出现意外错误: {e}")

    time.sleep(TIMESLEEP)


def browse_posts(driver, wait, num_to_browse=3):
    """
    循环浏览指定数量的帖子。
    此版本已重构，使用更稳定的XPath来定位帖子标题，并增加了高亮。

    函数会依次点击进入每个帖子的详情页，停留片刻后返回列表页。

    :param driver: WebDriver 实例。
    :param wait: WebDriverWait 实例。
    :param num_to_browse: 整数，要浏览的帖子数量。
    :return: None
    """
    print(f"\n--- 开始执行“循环阅读{num_to_browse}个帖子”的任务 ---")

    post_title_base_xpath = "//div[contains(@class, 'card-item')]//div[contains(@class, 'font-bold') and contains(@class, 'line-clamp-2')]"

    try:
        # 确认帖子列表存在，并获取标题总数
        all_titles = wait.until(EC.presence_of_all_elements_located((By.XPATH, post_title_base_xpath)))
        num_to_actually_browse = min(num_to_browse, len(all_titles))

        if num_to_actually_browse == 0:
            print("页面上未能找到任何帖子。")
            return

        print(f"共找到 {len(all_titles)} 个帖子，准备依次点击浏览前 {num_to_actually_browse} 个。")

        for i in range(num_to_actually_browse):
            try:
                # 每次循环都重新定位当前要点击的帖子标题，这是最关键的一步
                # 构造指向第 i+1 个标题的XPath
                current_title_xpath = f"({post_title_base_xpath})[{i + 1}]"
                post_title_to_click = wait.until(EC.element_to_be_clickable((By.XPATH, current_title_xpath)))

                highlight_element(driver, post_title_to_click)
                driver.execute_script("arguments[0].click();", post_title_to_click)

                time.sleep(1)
                # 从帖子详情页返回
                driver.back()

                print(f"成功阅读并返回第 {i + 1} 个帖子。")
                # 等待列表页完全加载，为下一次循环做准备
                time.sleep(1)

            except StaleElementReferenceException:
                print(f"🟡 处理第 {i + 1} 个帖子时元素已过时，列表可能已刷新，将继续下一个。")
                # 元素过时通常意味着页面已跳转或刷新，直接继续下一次循环通常是安全的
                time.sleep(1)
                continue
            except Exception as e:
                print(f"❌ 处理第 {i + 1} 个帖子时出现错误: {e}")
                print("尝试使用浏览器后退功能恢复，并继续下一个...")
                driver.back()  # 如果点击返回按钮失败，尝试使用浏览器自带的后退
                time.sleep(1.5)  # 等待页面稳定

        print("\n--- 所有帖子的浏览任务已完成 ---")

    except Exception as e:
        print(f"\n❌ 执行浏览任务过程中出现严重错误: {e}")

    time.sleep(TIMESLEEP)


def check_points_page(driver, wait):
    """
    检查积分页面上各个任务的完成状态。
    此版本使用基于文本的相对定位法，并能智能点击“展开”按钮。

    :param driver: WebDriver 实例。
    :param wait: WebDriverWait 实例。
    :return: None
    """
    print("\n--- 开始执行“检查积分页面”任务 ---")
    try:
        points_page_url = "https://www.blablalink.com/points"
        driver.get(points_page_url)
        print(f"已导航到积分页面: {points_page_url}")

        try:
            expand_button_xpath = "//div[contains(@class, 'btn-mask') and contains(@class, 'cursor-pointer') and .//span[contains(@class, 'rotate-180')]]"

            short_wait = WebDriverWait(driver, 5)
            expand_button = short_wait.until(
                EC.element_to_be_clickable((By.XPATH, expand_button_xpath))
            )

            print("检测到“展开”按钮，准备点击...")
            highlight_element(driver, expand_button)
            # 使用JS点击更可靠
            driver.execute_script("arguments[0].click();", expand_button)
            print("✅ 已成功点击“展开”按钮。")
            time.sleep(1)  # 等待展开动画完成
        except TimeoutException:
            # 如果在5秒内找不到这个按钮，我们合理地假设所有任务已经显示，或者页面布局已更改。
            print("ℹ️ 未找到“展开”按钮或按钮不可点击，假设所有任务已显示。")
        except Exception as e:
            print(f"❌ 点击“展开”按钮时出现意外错误: {e}")

        progress_checks = [
            {
                "task_name": "每日签到",
                "identifier_text": "每日簽到",
                "check_type": "presence_and_attribute",
                "target_xpath_relative": ".//div[contains(@class, 'icon-gift-true.png')]",
                "attribute_name": "class",
                "expected_value": "icon-gift-true.png"
            },
            {
                "task_name": "浏览帖子",
                "identifier_text": "瀏覽3個貼文",
                "check_type": "text",
                "target_xpath_relative": ".//div[contains(text(), '/')]",
                "expected_progress": "3 / 3"
            },
            {
                "task_name": "点赞内容",
                "identifier_text": "按讚5個貼文",
                "check_type": "text",
                "target_xpath_relative": ".//div[contains(text(), '/')]",
                "expected_progress": "5 / 5"
            },
            {
                "task_name": "发表评论",
                "identifier_text": "發布1條評論",
                "check_type": "text",
                "target_xpath_relative": ".//div[contains(text(), '/')]",
                "expected_progress": "1 / 1"
            }
        ]

        all_checks_passed = True

        for check in progress_checks:
            task_name = check["task_name"]
            identifier_text = check["identifier_text"]
            print(f"  正在检查 '{task_name}'...")

            try:
                task_row_xpath = f"//div[contains(@class, 'justify-between') and .//*[contains(text(), '{identifier_text}')]]"
                task_row = wait.until(
                    EC.visibility_of_element_located((By.XPATH, task_row_xpath))
                )

                highlight_element(driver, task_row, duration=0.7)

                check_type = check["check_type"]
                target_xpath = check["target_xpath_relative"]

                target_element = task_row.find_element(By.XPATH, target_xpath)

                if check_type == "text":
                    actual_progress = target_element.text.strip()
                    expected_progress = check["expected_progress"]
                    if actual_progress == expected_progress:
                        print(f"  检查通过: '{task_name}' 进度为 '{actual_progress}'，符合预期。")
                    else:
                        print(
                            f"  ❌ 检查失败: '{task_name}' 期望进度为 '{expected_progress}'，实际为 '{actual_progress}'。")
                        all_checks_passed = False

                elif check_type == "presence_and_attribute":
                    attribute_name = check["attribute_name"]
                    expected_value = check["expected_value"]
                    actual_attribute = target_element.get_attribute(attribute_name)
                    if expected_value in actual_attribute:
                        print(f"  检查通过: '{task_name}' 已完成（找到 '{expected_value}'）。")
                    else:
                        print(f"  ❌ 检查失败: '{task_name}' 未完成状态或状态异常。")
                        all_checks_passed = False

            except TimeoutException:
                print(f"  ❌ 检查失败: 无法在页面上找到 '{task_name}' 的任务行或其状态元素。")
                all_checks_passed = False
            except Exception as e:
                print(f"  ❌ 检查出错: 验证 '{task_name}' 时发生意外错误: {e}")
                all_checks_passed = False

        if all_checks_passed:
            print("🎉 恭喜！所有积分任务检查均已通过！")
        else:
            print("⚠️ 注意：部分积分任务检查未通过，请核对以上日志。")

    except Exception as e:
        print(f"执行“检查积分页面”任务时出现严重错误: {e}")
    time.sleep(TIMESLEEP)



def main():
    """
    主函数，按顺序执行所有自动化任务。
    """
    # --- 配置区 ---
    chrome_profile_path = r"E:\AutoCheckin_chrome_profile"
    # chrome_profile_path = r"C:\Users\jyr\Desktop\AutoCheckin_chrome_profile"
    target_url = 'https://www.blablalink.com/points'

    driver = None  # 初始化 driver 变量
    try:
        # 1. 初始化浏览器
        driver = setup_driver(chrome_profile_path)
        driver.get(target_url)
        wait = WebDriverWait(driver, 20)  # 设置一个全局的显式等待

        # 留足够的时间让你手动登录
        # time.sleep(1000)

        # 2. 执行每日签到
        daily_check_in(driver, wait)

        # 3. 导航到前哨基地
        navigate_to_outpost(driver, wait)

        # 4. 切换到最新帖子
        switch_to_latest_posts(driver, wait)

        # 5. 点赞 5 个帖子
        like_posts(driver, wait, num_to_like=5)

        # 6. 发表一个表情评论
        post_emoji_comment(driver, wait)

        # 7. 浏览 3 个帖子
        browse_posts(driver, wait, num_to_browse=3)

        print("\n所有任务已成功执行完毕！")

        # 8. 检查积分页面
        check_points_page(driver, wait)

    except Exception as e:
        print(f"\n在主流程中捕获到未处理的异常: {e}")
    finally:
        if driver:
            time.sleep(5)
            driver.quit()
            print("--- 浏览器已关闭 ---")


if __name__ == '__main__':
    main()

# 参考: https://www.cnblogs.com/Kled/p/15652670.html