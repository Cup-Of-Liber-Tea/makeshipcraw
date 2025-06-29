import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def extract_category_with_infinite_scroll(category_name, url, max_products=1000):
    """
    특정 카테고리에서 무한 스크롤을 통해 모든 상품을 추출하는 함수
    """
    print(f"\n=== {category_name} 카테고리 처리 중 ===")
    print(f"URL: {url}")
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 백그라운드 실행
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 자동화 감지 방지
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.get(url)
        time.sleep(3)
        
        all_discovered_links = set()
        consecutive_no_change = 0
        max_no_change = 5
        scroll_cycle = 0
        max_cycles = 100
        
        while scroll_cycle < max_cycles and consecutive_no_change < max_no_change:
            scroll_cycle += 1
            
            # 현재 페이지의 상품 링크 수집
            current_links = get_current_product_links(driver)
            
            # 새로 발견된 링크 추가
            new_links = current_links - all_discovered_links
            all_discovered_links.update(current_links)
            
            print(f"  사이클 {scroll_cycle}: 현재 {len(current_links)}개, 누적 {len(all_discovered_links)}개, 신규 {len(new_links)}개")
            
            # 목표 상품 수에 도달하거나 새로운 링크가 없으면
            if len(all_discovered_links) >= max_products:
                print(f"  → 목표 상품 수({max_products}개)에 도달!")
                break
            
            if len(new_links) == 0:
                consecutive_no_change += 1
                print(f"  → 새로운 상품 없음 ({consecutive_no_change}/{max_no_change})")
            else:
                consecutive_no_change = 0
            
            # 현재 상품 수가 급격히 줄어들면 (초기화 감지) 종료
            if len(current_links) < 20 and len(all_discovered_links) > 100:
                print(f"  → 페이지 초기화 감지, 수집 종료")
                break
            
            # 스크롤 동작
            try:
                body = driver.find_element(By.TAG_NAME, 'body')
                
                # Home으로 맨 위로
                body.send_keys(Keys.HOME)
                time.sleep(0.5)
                
                # 점진적 스크롤
                for i in range(3):
                    body.send_keys(Keys.PAGE_DOWN)
                    time.sleep(0.3)
                
                # End로 맨 아래로
                body.send_keys(Keys.END)
                time.sleep(1)
                
                # 추가 End 키 입력
                for i in range(2):
                    body.send_keys(Keys.END)
                    time.sleep(0.5)
                
                time.sleep(2)  # 로딩 시간 확보
                
            except Exception as e:
                print(f"  → 스크롤 중 오류: {e}")
                break
        
        print(f"  ✅ {category_name}: {len(all_discovered_links)}개 상품 수집 완료")
        return sorted(list(all_discovered_links))
        
    except Exception as e:
        print(f"  ❌ {category_name} 오류: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def get_current_product_links(driver):
    """
    현재 페이지에서 상품 링크들을 추출하는 함수
    """
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        product_links = set()
        
        # 다양한 패턴으로 상품 링크 찾기
        patterns = [
            'a[href*="/products/"]',
            '.product-card a',
            '.product-item a',
            '.campaign-card a',
            '.grid-item a',
            '[data-product] a'
        ]
        
        for pattern in patterns:
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
                    
                    # 쿼리 파라미터 제거하여 정리
                    clean_url = full_url.split('?')[0]
                    product_links.add(clean_url)
        
        # 백업 방법: 모든 a 태그 검사
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
                product_links.add(clean_url)
        
        return product_links
        
    except Exception as e:
        return set()

def save_links_clean(links, filename):
    """
    링크만 깔끔하게 저장하는 함수
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for link in links:
                f.write(f"{link}\n")
        print(f"  📁 {len(links)}개 링크가 '{filename}' 파일에 저장되었습니다.")
    except Exception as e:
        print(f"  ❌ 파일 저장 오류: {e}")

def save_category_results(all_results, timestamp):
    """
    카테고리별 결과를 JSON과 텍스트로 저장
    """
    # JSON 형태로 저장
    json_filename = f"makeship_all_products_{timestamp}.json"
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"\n📊 카테고리별 결과가 '{json_filename}' 파일에 저장되었습니다.")
    except Exception as e:
        print(f"❌ JSON 저장 오류: {e}")
    
    # 모든 고유 링크 추출 및 저장
    all_unique_links = set()
    for category_links in all_results.values():
        all_unique_links.update(category_links)
    
    unique_filename = f"makeship_unique_products_{timestamp}.txt"
    save_links_clean(sorted(list(all_unique_links)), unique_filename)
    
    return len(all_unique_links)

def main():
    """
    메인 실행 함수 - 모든 카테고리에 무한 스크롤 적용
    """
    print("🚀 Makeship 전체 카테고리 무한 스크롤 추출기")
    print("모든 카테고리에 무한 스크롤을 적용하여 최대한 많은 상품을 수집합니다.")
    print("="*70)
    
    # 카테고리 URL 목록 (past는 805개 한계 적용)
    category_configs = {
        "후디": {
            "url": "https://www.makeship.com/shop/hoodies", 
            "max_products": 200
        },
        "니트 크루넥": {
            "url": "https://www.makeship.com/shop/knitted-crewnecks", 
            "max_products": 100
        },
        "티셔츠": {
            "url": "https://www.makeship.com/shop/t-shirts", 
            "max_products": 100
        },
        "에나멜 핀": {
            "url": "https://www.makeship.com/shop/enamel-pins", 
            "max_products": 200
        },
        "비닐 피규어": {
            "url": "https://www.makeship.com/shop/vinyl-figures", 
            "max_products": 200
        },
        "플러시": {
            "url": "https://www.makeship.com/shop/plushies", 
            "max_products": 300
        },
        "롱보이": {
            "url": "https://www.makeship.com/shop/longbois", 
            "max_products": 100
        },
        "도우보이": {
            "url": "https://www.makeship.com/shop/doughbois", 
            "max_products": 100
        },
        "점보 플러시": {
            "url": "https://www.makeship.com/shop/jumbo-plushies", 
            "max_products": 100
        },
        "키체인 플러시": {
            "url": "https://www.makeship.com/shop/keychain-plushies", 
            "max_products": 200
        },
        "인기 상품": {
            "url": "https://www.makeship.com/shop/top", 
            "max_products": 200
        },
        "신상품": {
            "url": "https://www.makeship.com/shop/new", 
            "max_products": 200
        },
        "출시 예정": {
            "url": "https://www.makeship.com/shop/comingsoon", 
            "max_products": 200
        },
        "지난 상품": {
            "url": "https://www.makeship.com/shop/past", 
            "max_products": 805  # Past는 805개 한계
        }
    }
    
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    all_results = {}
    
    start_time = time.time()
    
    for category_name, config in category_configs.items():
        category_links = extract_category_with_infinite_scroll(
            category_name, 
            config["url"], 
            config["max_products"]
        )
        
        all_results[category_name] = category_links
        
        # 각 카테고리별로 개별 파일도 저장
        category_filename = f"makeship_{category_name.replace(' ', '_')}_{timestamp}.txt"
        save_links_clean(category_links, category_filename)
        
        # 잠시 대기 (서버 부하 방지)
        time.sleep(2)
    
    # 전체 결과 저장
    total_unique = save_category_results(all_results, timestamp)
    
    end_time = time.time()
    elapsed_time = int(end_time - start_time)
    
    # 최종 결과 출력
    print("\n" + "="*70)
    print("🎉 전체 수집 완료!")
    print("="*70)
    
    total_links = 0
    for category_name, links in all_results.items():
        print(f"{category_name}: {len(links)}개")
        total_links += len(links)
    
    print(f"\n📊 총 상품 링크 수: {total_links}개")
    print(f"🔧 중복 제거 후 고유 상품: {total_unique}개")
    print(f"⏱️  소요 시간: {elapsed_time//60}분 {elapsed_time%60}초")
    
    print(f"\n📁 생성된 파일들:")
    print(f"  - makeship_all_products_{timestamp}.json (카테고리별 상세)")
    print(f"  - makeship_unique_products_{timestamp}.txt (고유 상품 링크만)")
    print(f"  - makeship_[카테고리]_{timestamp}.txt (카테고리별 개별 파일)")

if __name__ == "__main__":
    main()
