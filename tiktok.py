import csv
import time
import psycopg2
import random
import logging

from undetected_chromedriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from fake_useragent import UserAgent
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from TikTokCommentsFetcher.config import DBNAME, USER, PASSWORD, HOST, PORT, TABLE_NAME, INTERNET_SPEED_LEVEL
from TikTokCommentsFetcher.database import create_table

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
USER_TEXTS_FILE = 'user_texts.txt'
COMMENTS_CSV_FILE = 'comments.csv'


def create_driver(proxy_list: list = None, headless=True, user_agent=True, options=None):
    """Создание WebDriver."""
    if not options:
        options = ChromeOptions()
    if proxy_list:
        random_proxy = random.choice(proxy_list)
        options.add_argument(f'--proxy-server=http://{random_proxy["host"]}:{random_proxy["port"]}')
        options.add_argument(f'--proxy-auth={random_proxy["proxy_username"]}:{random_proxy["proxy_password"]}}}')
    if user_agent:
        options.add_argument(f'user-agent={UserAgent().random}')
    if headless:
        options.add_argument('--headless=new')

    options.add_argument("--window-size=1920,1080")
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument("--disable-extensions")
    options.add_argument("--start-maximized")
    options.add_argument('--disable-dev-shm-usage')
    driver = Chrome(options=options)
    return driver


def write_to_file(texts, filename):
    """Запись текстов в файл."""
    with open(filename, 'a', encoding='utf-8') as file:
        for text in texts:
            file.write(text + '\n')


def read_from_file(filename):
    """Чтение текстов из файла."""
    with open(filename, 'r', encoding='utf-8') as file:
        texts = file.read().splitlines()
    return texts


def get_comments_count(driver):
    """Получение количества комментариев."""
    comment_container = driver.find_element(By.CSS_SELECTOR, "[data-e2e='search-comment-container']")
    comment_divs = comment_container.find_elements(By.CSS_SELECTOR, 'div')
    return len(comment_divs)


def id_by_link(link: str):
    """Извлечение ID из ссылки."""
    return link.split('/')[3].split('?')[0]


def export_comments_to_csv(user_ids, user_links, user_names, comment_texts, comment_dates, comment_likes):
    """Экспорт комментариев в CSV файл."""
    with open(COMMENTS_CSV_FILE, 'w', encoding='utf-8') as out:
        writer = csv.writer(out)
        for row in zip(user_ids, user_links, user_names, comment_texts, comment_dates, comment_likes):
            writer.writerow(row)


def export_comments_to_db(user_ids, user_links, user_names, comment_texts, comment_dates, comment_likes):
    """Экспорт комментариев в базу данных."""
    conn = psycopg2.connect(dbname=DBNAME, user=USER, password=PASSWORD,
                            host=HOST, port=PORT)
    cur = conn.cursor()

    try:
        for values in zip(user_ids, user_links, user_names, comment_texts, comment_dates, comment_likes):
            cur.execute(f"""
                INSERT INTO {TABLE_NAME} (user_id, user_link, user_name, comment_text, comment_date, comment_like)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, values)

            conn.commit()
    except Exception as ex:
        logger.error(f"Error during database export: {ex}")
    finally:
        cur.close()
        conn.close()


def search_comments(driver):
    """Поиск комментариев и их экспорт."""
    last_comments_count = get_comments_count(driver)

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        if INTERNET_SPEED_LEVEL == "GREAT":
            time.sleep(5.0)
        elif INTERNET_SPEED_LEVEL == "GOOD":
            time.sleep(10.0)
        elif INTERNET_SPEED_LEVEL == "NORMAL":
            time.sleep(20.0)
        elif INTERNET_SPEED_LEVEL == "BAD":
            time.sleep(35.0)
        elif INTERNET_SPEED_LEVEL == "VERY BAD":
            time.sleep(60.0)

        new_comments_count = get_comments_count(driver)

        if new_comments_count == last_comments_count:
            try:
                user_ids = []
                user_names = []
                user_links = []
                comment_texts = []
                comment_dates = []
                comment_likes = []

                texts = read_from_file(USER_TEXTS_FILE)

                comment_container = driver.find_element(By.CSS_SELECTOR, "[data-e2e='search-comment-container']")
                comment_divs = comment_container.find_element(By.XPATH, './div').find_elements(By.XPATH, './div')
                for comment_div in comment_divs:

                    user_id = None
                    user_link = None
                    user_name = None
                    comment_text = None
                    comment_date = None
                    comment_like = None

                    comment = comment_div.find_element(By.XPATH, './div')
                    if comment:
                        comment_text_div = comment.find_elements(By.XPATH, './div')[0]
                        if comment_text_div:
                            comment_text = comment_text_div.find_elements(By.XPATH, './p')[0].find_element(
                                By.XPATH, './span').text
                            if not comment_text or not any(text.lower() in comment_text.lower() for text in texts):
                                continue

                        user_link_div = comment.find_elements(By.XPATH, './div')[0]
                        if user_link_div:
                            user_link = user_link_div.find_elements(By.XPATH, './a')[0].get_attribute("href")
                            if user_link:
                                user_id = id_by_link(user_link)

                        user_name_div = comment.find_elements(By.XPATH, './div')[0]
                        if user_name_div:
                            user_name = user_name_div.find_element(By.XPATH, './a').find_element(
                                By.XPATH, './span').text

                        comment_date_div = comment.find_elements(By.XPATH, './div')[0]
                        if comment_date_div:
                            comment_date = comment_date_div.find_elements(By.XPATH, './p')[1].find_elements(
                                By.XPATH, './span')[0].text

                        comment_like_div = comment.find_elements(By.XPATH, './div')[0]
                        if comment_like_div:
                            comment_like = comment_like_div.find_elements(By.XPATH, './p')[1].find_element(
                                By.XPATH, './div').find_element(By.XPATH, './span').text

                    user_ids.append(user_id)
                    user_links.append(user_link)
                    user_names.append(user_name)
                    comment_texts.append(comment_text)
                    comment_dates.append(comment_date)
                    comment_likes.append(comment_like)

                export_comments_to_csv(user_ids, user_links, user_names, comment_texts, comment_dates, comment_likes)
                export_comments_to_db(user_ids, user_links, user_names, comment_texts, comment_dates, comment_likes)
            except Exception as ex:
                driver.save_screenshot('error_2.png')
                logger.error(f"Error during comment export: {ex}")

            break

        last_comments_count = new_comments_count

        if INTERNET_SPEED_LEVEL == "GREAT":
            time.sleep(5.0)
        elif INTERNET_SPEED_LEVEL == "GOOD":
            time.sleep(10.0)
        elif INTERNET_SPEED_LEVEL == "NORMAL":
            time.sleep(15.0)
        elif INTERNET_SPEED_LEVEL == "BAD":
            time.sleep(20.0)
        elif INTERNET_SPEED_LEVEL == "VERY BAD":
            time.sleep(25.0)


def parse_comments_by_link(link: str):
    """Парсинг комментариев по ссылке."""
    driver = create_driver()
    create_table()

    try:
        if link:
            driver.get(link)

            if INTERNET_SPEED_LEVEL == "GREAT":
                time.sleep(5.0)
            elif INTERNET_SPEED_LEVEL == "GOOD":
                time.sleep(10.0)
            elif INTERNET_SPEED_LEVEL == "NORMAL":
                time.sleep(15.0)
            elif INTERNET_SPEED_LEVEL == "BAD":
                time.sleep(20.0)
            elif INTERNET_SPEED_LEVEL == "VERY BAD":
                time.sleep(25.0)

            outer_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "tiktok-cookie-banner"))
            )

            shadow_root = driver.execute_script("return arguments[0].shadowRoot", outer_element)
            shadow_root.find_element(By.CLASS_NAME, "tiktok-cookie-banner").find_element(
                By.CLASS_NAME, 'button-wrapper').find_elements(By.TAG_NAME, 'button')[1].click()

            if INTERNET_SPEED_LEVEL == "GREAT":
                time.sleep(5.0)
            elif INTERNET_SPEED_LEVEL == "GOOD":
                time.sleep(6.0)
            elif INTERNET_SPEED_LEVEL == "NORMAL":
                time.sleep(7.0)
            elif INTERNET_SPEED_LEVEL == "BAD":
                time.sleep(8.0)
            elif INTERNET_SPEED_LEVEL == "VERY BAD":
                time.sleep(9.0)

            login_modal_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, 'login-modal'))
            )

            login_modal_element.find_element(
                By.CSS_SELECTOR, "[data-e2e='modal-close-inner-button']").click()

            if INTERNET_SPEED_LEVEL == "GREAT":
                time.sleep(5.0)
            elif INTERNET_SPEED_LEVEL == "GOOD":
                time.sleep(6.0)
            elif INTERNET_SPEED_LEVEL == "NORMAL":
                time.sleep(7.0)
            elif INTERNET_SPEED_LEVEL == "BAD":
                time.sleep(8.0)
            elif INTERNET_SPEED_LEVEL == "VERY BAD":
                time.sleep(9.0)

            search_comments(driver)
    except TimeoutException:
        pass
    except Exception as ex:
        driver.save_screenshot('error_1.png')
        logger.error(f"Error during comment parsing: {ex}")
    finally:
        driver.close()
        driver.quit()


def get_data():
    """Ввод данных от пользователя."""
    user_texts = []
    while True:
        text = input("Введите текст который будет искаться в комментариях (для завершения введите 'exit'): ")
        if text.lower() == 'exit':
            break
        user_texts.append(text)
    write_to_file(user_texts, USER_TEXTS_FILE)

    link = input("Введите ссылку: ")

    parse_comments_by_link(link)


if __name__ == '__main__':
    get_data()
