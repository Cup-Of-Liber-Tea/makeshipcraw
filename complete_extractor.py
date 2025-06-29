import requests
from bs4 import BeautifulSoup
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

def extract_makeship_products_by_category(category_urls):
    """
    여러 카테고리에서 Makeship 상품 링크들을 추출하는 함수
    """
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 브라우저 창을 띄우지 않음
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    all_products = {}
    
    try:
        print("Selenium Chrome 드라이버 설정 중...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        for category_name, url in category_urls.items():
            print(f"\n{category_name} 카테고리 처리 중... ({url})")
            
            try:
                driver.get(url)
                time.sleep(3)  # 페이지 로딩 대기
                
                # 페이지 소스 가져오기
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                product_links = []
                
                # 다양한 상품 링크 패턴 시도
                link_patterns = [
                    'a[href*="/products/"]',
                    '.product-card a',
                    '.product-item a',
                    '.product a',
                    '[data-product] a',
                    '.grid-item a',
                    '.campaign-card a'
                ]
                
                for pattern in link_patterns:
                    links = soup.select(pattern)
                    for link in links:
                        href = link.get('href')
                        if href and '/products/' in href:
                            if href.startswith('/'):
                                full_url = f"https://www.makeship.com{href}"
                            elif href.startswith('http'):
                                full_url = href
                            else:
                                continue
                            
                            # 중복 제거 및 쿼리 파라미터 정리
                            clean_url = full_url.split('?')[0]
                            if clean_url not in product_links:
                                product_links.append(clean_url)
                
                # 백업 방법: 모든 링크 검사
                if not product_links:
                    print(f"  특정 패턴으로 찾지 못해 모든 링크를 검사합니다...")
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link['href']
                        if '/products/' in href:
                            if href.startswith('/'):
                                full_url = f"https://www.makeship.com{href}"
                            elif href.startswith('http'):
                                full_url = href
                            else:
                                continue
                            
                            clean_url = full_url.split('?')[0]
                            if clean_url not in product_links:
                                product_links.append(clean_url)
                
                all_products[category_name] = product_links
                print(f"  → {len(product_links)}개의 상품 링크를 찾았습니다.")
                
            except Exception as e:
                print(f"  → {category_name} 카테고리 처리 중 오류: {e}")
                all_products[category_name] = []
        
        return all_products
        
    except WebDriverException as e:
        print(f"Selenium WebDriver 오류: {e}")
        return {}
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return {}
    finally:
        if driver:
            driver.quit()

def save_all_links_to_file(all_products, filename="makeship_all_products.txt"):
    """
    모든 카테고리의 링크들을 파일로 저장하는 함수
    """
    try:
        total_links = sum(len(links) for links in all_products.values())
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Makeship 전체 상품 링크 목록 (총 {total_links}개)\n")
            f.write("=" * 60 + "\n\n")
            
            for category_name, links in all_products.items():
                f.write(f"\n[{category_name}] - {len(links)}개 상품\n")
                f.write("-" * 40 + "\n")
                
                for i, link in enumerate(links, 1):
                    f.write(f"{i}. {link}\n")
                f.write("\n")
        
        print(f"\n모든 링크가 '{filename}' 파일에 저장되었습니다.")
        
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

def get_unique_products(all_products):
    """
    모든 카테고리에서 중복되지 않는 고유한 상품 링크들을 추출
    """
    unique_links = set()
    for links in all_products.values():
        unique_links.update(links)
    return sorted(list(unique_links))

def main():
    """
    메인 실행 함수
    """
    # 카테고리 URL 목록
    category_urls = {
        "후디": "https://www.makeship.com/shop/hoodies",
        "니트 크루넥": "https://www.makeship.com/shop/knitted-crewnecks",
        "티셔츠": "https://www.makeship.com/shop/t-shirts",
        "에나멜 핀": "https://www.makeship.com/shop/enamel-pins",
        "비닐 피규어": "https://www.makeship.com/shop/vinyl-figures",
        "플러시": "https://www.makeship.com/shop/plushies",
        "롱보이": "https://www.makeship.com/shop/longbois",
        "도우보이": "https://www.makeship.com/shop/doughbois",
        "점보 플러시": "https://www.makeship.com/shop/jumbo-plushies",
        "키체인 플러시": "https://www.makeship.com/shop/keychain-plushies",
        "인기 상품": "https://www.makeship.com/shop/top",
        "신상품": "https://www.makeship.com/shop/new",
        "출시 예정": "https://www.makeship.com/shop/comingsoon",
        "지난 상품": "https://www.makeship.com/shop/past"
    }
    
    print("Makeship 전체 카테고리 상품 링크 추출 시작...")
    print(f"총 {len(category_urls)}개의 카테고리를 처리합니다.")
    
    # 모든 카테고리에서 링크 추출
    all_products = extract_makeship_products_by_category(category_urls)
    
    if all_products:
        print(f"\n" + "=" * 60)
        print("카테고리별 결과:")
        print("=" * 60)
        
        total_links = 0
        for category_name, links in all_products.items():
            print(f"{category_name}: {len(links)}개")
            total_links += len(links)
        
        print(f"\n총 상품 링크 수: {total_links}개")
        
        # 고유한 상품들만 추출
        unique_products = get_unique_products(all_products)
        print(f"중복 제거 후 고유 상품 수: {len(unique_products)}개")
        
        # 파일로 저장
        save_all_links_to_file(all_products)
        
        # 고유 상품 목록도 별도 저장
        with open("makeship_unique_products.txt", 'w', encoding='utf-8') as f:
            f.write(f"Makeship 고유 상품 링크 목록 (총 {len(unique_products)}개)\n")
            f.write("=" * 50 + "\n\n")
            for i, link in enumerate(unique_products, 1):
                f.write(f"{i}. {link}\n")
        
        print("고유 상품 목록이 'makeship_unique_products.txt' 파일에도 저장되었습니다.")
        
    else:
        print("상품 링크를 찾을 수 없습니다.")

if __name__ == "__main__":
    main()
