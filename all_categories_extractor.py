import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import time

def get_makeship_categories():
    """
    Makeship의 모든 카테고리를 가져오는 함수
    """
    categories = {
        'hoodies': 'https://www.makeship.com/shop/hoodies',
        'plushies': 'https://www.makeship.com/shop/plushies',
        'pins': 'https://www.makeship.com/shop/pins',
        'shirts': 'https://www.makeship.com/shop/shirts',
        'accessories': 'https://www.makeship.com/shop/accessories',
        'figures': 'https://www.makeship.com/shop/figures',
        'bags': 'https://www.makeship.com/shop/bags',
        'stickers': 'https://www.makeship.com/shop/stickers',
        'keychains': 'https://www.makeship.com/shop/keychains',
        'featured': 'https://www.makeship.com/shop/featured',
        'petitions': 'https://www.makeship.com/shop/petitions'
    }
    return categories

def extract_makeship_products_by_category(category_name, category_url):
    """
    특정 카테고리의 Makeship 상품 링크들을 추출하는 함수
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    try:
        print(f"[{category_name}] 카테고리 페이지에 접속 중...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(category_url)
        
        # 페이지 로딩 대기
        time.sleep(3)
        
        # 페이지 소스 가져오기
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        product_links = []
        
        # 다양한 상품 링크 패턴 시도
        link_patterns = [
            'a[href*="/products/"]',
            'a[href*="/campaign/"]',
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
                    
                    # 중복 제거 및 쿼리 파라미터 제거
                    clean_url = full_url.split('?')[0]
                    if clean_url not in product_links:
                        product_links.append(clean_url)
        
        # 백업 방법: 모든 링크 검사
        if not product_links:
            print(f"[{category_name}] 특정 패턴으로 찾지 못해 모든 링크를 검사합니다...")
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
        
        return product_links
        
    except WebDriverException as e:
        print(f"[{category_name}] Selenium WebDriver 오류: {e}")
        return []
    except Exception as e:
        print(f"[{category_name}] 예상치 못한 오류 발생: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def extract_all_categories():
    """
    모든 카테고리의 상품 링크를 추출하는 함수
    """
    categories = get_makeship_categories()
    all_products = {}
    
    for category_name, category_url in categories.items():
        print(f"\n{'='*60}")
        print(f"카테고리 처리 중: {category_name.upper()}")
        print(f"URL: {category_url}")
        print(f"{'='*60}")
        
        products = extract_makeship_products_by_category(category_name, category_url)
        all_products[category_name] = products
        
        if products:
            print(f"[{category_name}] {len(products)}개의 상품을 찾았습니다:")
            for i, product in enumerate(products[:5], 1):  # 처음 5개만 출력
                print(f"  {i}. {product}")
            if len(products) > 5:
                print(f"  ... 및 {len(products) - 5}개 더")
        else:
            print(f"[{category_name}] 상품을 찾을 수 없습니다.")
        
        # 카테고리 간 간격
        time.sleep(2)
    
    return all_products

def save_all_products_to_files(all_products):
    """
    모든 카테고리의 상품들을 개별 파일로 저장하는 함수
    """
    for category_name, products in all_products.items():
        if products:
            filename = f"makeship_{category_name}_links.txt"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Makeship {category_name.upper()} 상품 링크 목록 (총 {len(products)}개)\n")
                    f.write("=" * 60 + "\n\n")
                    
                    for i, link in enumerate(products, 1):
                        f.write(f"{i}. {link}\n")
                
                print(f"[{category_name}] 링크들이 '{filename}' 파일에 저장되었습니다.")
                
            except Exception as e:
                print(f"[{category_name}] 파일 저장 중 오류 발생: {e}")

def save_summary_file(all_products):
    """
    모든 카테고리의 요약 정보를 저장하는 함수
    """
    try:
        with open("makeship_all_categories_summary.txt", 'w', encoding='utf-8') as f:
            f.write("Makeship 전체 카테고리 상품 요약\n")
            f.write("=" * 60 + "\n\n")
            
            total_products = 0
            for category_name, products in all_products.items():
                f.write(f"{category_name.upper()}: {len(products)}개 상품\n")
                total_products += len(products)
            
            f.write(f"\n총 상품 수: {total_products}개\n")
            f.write("\n" + "=" * 60 + "\n\n")
            
            for category_name, products in all_products.items():
                if products:
                    f.write(f"[{category_name.upper()}]\n")
                    for i, product in enumerate(products, 1):
                        f.write(f"  {i}. {product}\n")
                    f.write("\n")
        
        print(f"전체 요약이 'makeship_all_categories_summary.txt' 파일에 저장되었습니다.")
        
    except Exception as e:
        print(f"요약 파일 저장 중 오류 발생: {e}")

def main():
    """
    메인 실행 함수
    """
    print("Makeship 전체 카테고리 상품 링크 추출 시작...")
    print("이 작업은 시간이 오래 걸릴 수 있습니다...")
    
    # 모든 카테고리 상품 추출
    all_products = extract_all_categories()
    
    # 결과 요약
    print(f"\n{'='*60}")
    print("추출 완료 - 결과 요약:")
    print(f"{'='*60}")
    
    total_products = 0
    for category_name, products in all_products.items():
        print(f"{category_name.upper()}: {len(products)}개 상품")
        total_products += len(products)
    
    print(f"\n총 {total_products}개의 상품 링크를 추출했습니다.")
    
    # 파일로 저장
    save_all_products_to_files(all_products)
    save_summary_file(all_products)
    
    print(f"\n{'='*60}")
    print("모든 작업이 완료되었습니다!")
    print("각 카테고리별 파일과 전체 요약 파일을 확인해주세요.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
