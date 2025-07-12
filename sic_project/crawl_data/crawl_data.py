import os
import json
import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urlunparse

# Lấy đường dẫn từ thu mục data
def get_output_file():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    output_dir = os.path.join(parent_dir, "data")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, "all_news_combined.json")

# Cuộn thu thập links
def scroll_until_enough_links(driver, selector, limit=25, max_scrolls=10, delay=1.5):
    seen = set()
    links = []
    scrolls = 0
    while len(links) < limit and scrolls < max_scrolls:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for el in elements:
            href = el.get_attribute("href")
            if href and href not in seen and "video" not in href:
                links.append(href)
                seen.add(href)
                if len(links) >= limit:
                    break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)
        scrolls += 1
    return links

# Nếu gặp lỗi thì tự động thử lại một số lần trước khi bỏ cuộc
def visit_with_retry(driver, url, retries=3, delay=2):
    for _ in range(retries):
        try:
            driver.get(url)
            return True
        except Exception as e:
            print(f"🔁 Lỗi khi load {url}, thử lại... {e}")
            time.sleep(delay)
    return False

# Khởi tạo driver
# def setup_driver(headless=True):
#     options = Options()
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
#     if headless:
#         options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--window-size=1920,1080")
#     return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def setup_driver(headless=True):
    options = Options()
    options.add_argument("user-agent=Mozilla/5.0")
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)



# Cuộn 5 lần để tải load lại nội dung
def scroll_down(driver, times=5, delay=2):
    for _ in range(times):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(delay)
        
# Lưu dữ liệu
def save_all_data(all_data):
    output_file = get_output_file()
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            old_data = json.load(f)
    except:
        old_data = []

    existing_urls = set(item["url"] for item in old_data if "url" in item)
    new_data = [item for item in all_data if item["url"] not in existing_urls]

    combined_data = old_data + new_data
    for idx, item in enumerate(combined_data, 1):
        item["id"] = idx

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Đã lưu {len(new_data)} bài báo mới (tổng cộng {len(combined_data)}) vào '{output_file}'")


# Làm sạch url để loại bỏ các url trùng
def clean_url(url):
    # Xoá phần #fragment nếu có
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))

# Crawl VNexpress
def crawl_vnexpress(driver, limit):
    url = "https://vnexpress.vn/"
    if not visit_with_retry(driver, url):
        return []
    
    scroll_down(driver, times=2)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'article')))

    selector = 'article.item-news h3.title-news a, article.article-list a.title-news'
    links = scroll_until_enough_links(driver, selector, limit=limit, max_scrolls=15, delay=2)
    links = list(set([clean_url(link) for link in links]))
    print(f"🔍 VNExpress: Thu thập {len(links)} link")

    results = []

    # Truy cập từng bài viết
    for idx, link in enumerate(links, start=1):
        try:
            if not visit_with_retry(driver, link):
                continue
            time.sleep(1.5)

            # Tiêu đề
            try:
                title = driver.find_element(By.CSS_SELECTOR, 'h1.title-detail').text.strip()
            except:
                title = ""

            # Mô tả (thường là đoạn đầu nội dung)
            try:
                description = driver.find_element(By.CSS_SELECTOR, 'p.description').text.strip()
            except:
                try:
                    description = driver.find_element(By.CSS_SELECTOR, 'article.fck_detail p').text.strip()
                except:
                    description = ""

            # Nội dung bài viết
            try:
                content_elements = driver.find_elements(By.CSS_SELECTOR, 'article.fck_detail p')
                content = '\n'.join([el.text.strip() for el in content_elements if el.text.strip() != ""])
            except:
                content = ""

            # Tags (chuyên mục)
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'ul.breadcrumb li a'))
                )
                tag_elements = driver.find_elements(By.CSS_SELECTOR, 'ul.breadcrumb li a')

                tag_texts = []
                for el in tag_elements:
                    text = el.text.strip()
                    if not text:
                        # Thử lấy text trong thẻ con nếu có
                        text = el.get_attribute("innerText").strip()
                    if text.lower() != "trang chủ" and text != "":
                        tag_texts.append(text)

                tags = tag_texts
                if not tags:
                    print(f"⚠️ Breadcrumb chỉ chứa 'Trang chủ' hoặc không có thẻ hợp lệ: {driver.current_url}")
            except Exception as e:
                tags = []
                print(f"❌ Lỗi khi lấy breadcrumb/tags: {e}")

            # Thời gian đăng
            try:
                time_posted = driver.find_element(By.CSS_SELECTOR, 'span.date').text.strip()
            except:
                time_posted = "Không có thời gian"
                    
            # Tác giả
            try:
                author = driver.find_element(By.CSS_SELECTOR, 'p.Normal[style*="text-align:right"] strong').text.strip()
            except:
                author = ""

            # Lấy ảnh
            image_url = ""
            try:
                image = driver.find_element(By.CSS_SELECTOR, 'img[itemprop="contentUrl"]')
                image_url = image.get_attribute('data-src') or image.get_attribute('src')
            except:
                pass

            if not title or not content:
                continue

            # Ghi lại kết quả
            print(f"{idx}. {title}")
            results.append({
                "id": idx,
                "title": title,
                "url": link,
                "description": description,
                "content": content,
                "tags": tags,
                "time_posted": time_posted,
                "author": author,
                "image": image_url
            })

        except Exception as e:
            print(f"⚠️ Lỗi khi xử lý {link}: {e}")

    return results

# Crawl dantri
def crawl_dantri(driver, limit):
    url = "https://dantri.com.vn/"
    if not visit_with_retry(driver, url):
        return []

    scroll_down(driver, times=2)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'article')))

    selector = 'article.article-item h3.article-title a'
    links = scroll_until_enough_links(driver, selector, limit=limit, max_scrolls=15, delay=2)
    links = list(set([clean_url(link) for link in links]))
    print(f"🔍 Dân trí: Thu thập {len(links)} link")

    results = []

    for idx, link in enumerate(links, start=1):
        try: 
            if not visit_with_retry(driver, link):
                continue
            time.sleep(1.5)

            # Tiêu đề
            try:
                title = driver.find_element(By.CSS_SELECTOR, 'h1.title-page.detail').text.strip()
            except:
                title = ""

            # Mô tả (thường là đoạn đầu nội dung)
            try:
                description = driver.find_element(By.CSS_SELECTOR, 'h2.singular-sapo').text.strip()
            except:
                try:
                    description = driver.find_element(By.CSS_SELECTOR, 'article.fck_detail p').text.strip()
                except:
                    description = ""

            # Nội dung bài viết
            try:
                content_elements = driver.find_elements(By.CSS_SELECTOR, 'div.singular-content')
                content = '\n'.join([el.text.strip() for el in content_elements if el.text.strip() != ""])
            except:
                content = ""

            # Tags (chuyên mục)
            try:
                tag_elements = driver.find_elements(By.CSS_SELECTOR, 'ul.dt-list-none li a')
                tags = [tag.text.strip().title() for tag in tag_elements if tag.text.strip()]
            except:
                tags = []

            # Thời gian đăng
            try:
                time_posted = driver.find_element(By.CSS_SELECTOR, 'time.author-time').text.strip()
            except:
                time_posted = "Không có thời gian"
            
            # Tác giả
            try:
                author_elements = driver.find_elements(By.CSS_SELECTOR, 'div.author-name a b')
                authors = [author.text.strip() for author in author_elements if author.text.strip()]
            except:
                authors = []

            # Lấy ảnh
            try:
                image_element = driver.find_element(By.CSS_SELECTOR, 'figure.image.align-center img')
                image_url = image_element.get_attribute('data-src') or image_element.get_attribute('src')
            except:
                image_url = ""

            if not title or not content:
                continue

            # Ghi lại kết quả
            print(f"{idx}. {title}")
            results.append({
                "id": idx,
                "title": title,
                "url": link,
                "description": description,
                "content": content,
                "tags": tags,
                "time_posted": time_posted,
                "author": authors,
                "image": image_url
            })

        except Exception as e:
            print(f"⚠️ Lỗi khi xử lý {link}: {e}")
    return results

# Crawl Vietnamnet
def crawl_vietnamnet(driver, limit):
    url = "https://vietnamnet.vn/"
    if not visit_with_retry(driver, url):
        return []
    
    scroll_down(driver, times=2)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*=".html"]')))

    selector = 'a[href*=".html"]'
    links = scroll_until_enough_links(driver, selector, limit=limit, max_scrolls=15, delay=2)
    links = list(set([clean_url(link) for link in links]))

    print(f"🔍 Vietnamnet: Thu thập {len(links)} link")
    results = []

    for idx, link in enumerate(links, start=1):
        try:
            if not visit_with_retry(driver, link):
                continue
            time.sleep(1.5)

            # Tiêu đề
            try:
                title = driver.find_element(By.CSS_SELECTOR, 'h1.content-detail-title').text.strip()
            except:
                title = ""

            # Mô tả (thường là đoạn đầu nội dung)
            try:
                description = driver.find_element(By.CSS_SELECTOR, 'h2.content-detail-sapo.sm-sapo-mb-0').text.strip()
            except:
                try:
                    description = driver.find_element(By.CSS_SELECTOR, 'article.fck_detail p').text.strip()
                except:
                    description = ""

            # Nội dung bài viết
            try:
                content_elements = driver.find_elements(By.CSS_SELECTOR, 'div.maincontent')
                content = '\n'.join([el.text.strip() for el in content_elements if el.text.strip() != ""])
            except:
                content = ""

            # Tags (chuyên mục)
            try:
                tag_elements = driver.find_elements(By.CSS_SELECTOR, 'div.bread-crumb-detail a[title]')
                tags = [a.text.strip() for a in tag_elements if a.text.strip()]
            except Exception as e:
                print(f"⚠️ Không lấy được tags: {e}")
                tags = []

            # Thời gian đăng
            try:
                time_posted = driver.find_element(By.CSS_SELECTOR, 'div.bread-crumb-detail__time').text.strip()
            except:
                time_posted = "Không có thời gian"
            
            # Tác giả
            try:
                author_elements = driver.find_elements(By.CSS_SELECTOR, 'div.article-author-multiple__slide div.name a')
                if not author_elements:
                    # Nếu không phải layout nhiều tác giả thì fallback sang layout 1 tác giả
                    author_elements = driver.find_elements(By.CSS_SELECTOR, 'div.article-detail-author-wrapper span.name a')
                
                authors = [author.text.strip() for author in author_elements if author.text.strip()]
            except:
                authors = []

            # Lấy ảnh
            try:
                image_element = driver.find_element(By.CSS_SELECTOR, 'figure.image.vnn-content-image img')
                image_url = image_element.get_attribute('data-original') or image_element.get_attribute('src')
            except:
                image_url = ""

            if not title or not content:
                continue

            # Ghi lại kết quả
            print(f"{idx}. {title}")
            results.append({
                "id": idx,
                "title": title,
                "url": link,
                "description": description,
                "content": content,
                "tags": tags,
                "time_posted": time_posted,
                "author": authors,
                "image": image_url
            })

        except Exception as e:
            print(f"⚠️ Lỗi khi xử lý {link}: {e}")

    return results

# Crawl tất cả các trang - chức năng chính để gọi từ Airflow
def crawl_all_sites(limit=50):
    """
    Hàm chính để crawl tất cả các trang báo
    Args:
        limit (int): Số lượng bài báo tối đa cần crawl từ mỗi trang
    Returns:
        dict: Kết quả crawl từ tất cả các trang
    """
    output_dir = get_output_file()
    driver = setup_driver(headless=True)
    
    try:
        crawlers = {
            "vnexpress": crawl_vnexpress,
            "dantri": crawl_dantri,
            "vietnamnet": crawl_vietnamnet,
        }

        results = {}
        for site, func in crawlers.items():
            print(f"🚀 Bắt đầu crawl: {site.upper()}")
            try:
                data = func(driver, limit=limit)
                if len(data) < limit:
                    print(f"⚠️ Chỉ lấy được {len(data)}/{limit} bài từ {site}")
                
                output_path = os.path.join(output_dir, f"{site}.json")
                save_all_data(data)
                results[site] = {
                    "success": True,
                    "count": len(data),
                    "file_path": output_path
                }
                
            except Exception as e:
                print(f"❌ Lỗi khi crawl {site}: {e}")
                results[site] = {
                    "success": False,
                    "error": str(e)
                }
                import traceback
                traceback.print_exc()
                
        return results
        
    finally:
        driver.quit()
        print("\n✅ Đã đóng trình duyệt.")

# Hàm riêng biệt để crawl từng trang (để có thể gọi độc lập trong Airflow)
def crawl_vnexpress_only(limit=50):
    """Crawl chỉ VNExpress"""
    output_dir = get_output_file()
    driver = setup_driver(headless=True)
    try:
        data = crawl_vnexpress(driver, limit)
        output_path = os.path.join(output_dir, "vnexpress.json")
        save_all_data(data)
        return {"success": True, "count": len(data), "file_path": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        driver.quit()

def crawl_dantri_only(limit=50):
    """Crawl chỉ Dân trí"""
    output_dir = get_output_file()
    driver = setup_driver(headless=True)
    try:
        data = crawl_dantri(driver, limit)
        output_path = os.path.join(output_dir, "dantri.json")
        save_all_data(data)
        return {"success": True, "count": len(data), "file_path": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        driver.quit()

def crawl_vietnamnet_only(limit=50):
    """Crawl chỉ Vietnamnet"""
    output_dir = get_output_file()
    driver = setup_driver(headless=True)
    try:
        data = crawl_vietnamnet(driver, limit)
        output_path = os.path.join(output_dir, "vietnamnet.json")
        save_all_data(data)
        return {"success": True, "count": len(data), "file_path": output_path}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        driver.quit()

if __name__ == "__main__":
    # Chạy thử nghiệm khi file được chạy trực tiếp
    print("🚀 Bắt đầu test crawler...")
    results = crawl_all_sites(limit=25)  # Test với 10 bài mỗi trang
    
    print("\n📊 Kết quả:")
    for site, result in results.items():
        if result["success"]:
            print(f"✅ {site}: {result['count']} bài - {result['file_path']}")
        else:
            print(f"❌ {site}: {result['error']}")