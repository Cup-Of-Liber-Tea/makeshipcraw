import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def extract_past_products_enhanced_scroll():
    """
    강화된 무한 스크롤로 Makeship의 past 페이지에서 모든 상품을 추출하는 함수
    """
    url = "https://www.makeship.com/shop/past"
    
    # Chrome 옵션 설정 (headless 해제하여 실제 동작 확인)
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 디버깅을 위해 헤드리스 모드 해제
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    
    try:
        print("강화된 Chrome 드라이버 설정 중...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 자동화 감지 방지
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Past 상품 페이지에 접속 중... ({url})")
        driver.get(url)
        
        # 충분한 초기 로딩 대기
        print("초기 페이지 로딩 대기 중...")
        time.sleep(10)
        
        print("강화된 무한 스크롤 시작...")
        
        all_product_links = set()
        previous_count = 0
        stable_count = 0
        max_stable_iterations = 5
        total_scrolls = 0
        max_total_scrolls = 100
        
        while stable_count < max_stable_iterations and total_scrolls < max_total_scrolls:
            total_scrolls += 1
            
            # 현재 페이지 높이 가져오기
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            # 여러 가지 스크롤 방법 시도
            print(f"스크롤 시도 {total_scrolls}...")
            
            # 방법 1: 천천히 스크롤
            current_position = 0
            scroll_increment = 500
            
            while current_position < last_height:
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                current_position += scroll_increment
                time.sleep(0.5)
            
            # 방법 2: 맨 아래로 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # 방법 3: 위로 스크롤 후 다시 아래로 (사용자 제안 방법)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            # 방법 4: JavaScript로 강제 스크롤 이벤트 발생
            driver.execute_script("""
                window.dispatchEvent(new Event('scroll'));
                window.dispatchEvent(new Event('resize'));
            """)
            time.sleep(2)
            
            # 방법 5: 페이지 끝에서 추가 스크롤
            for i in range(5):
                driver.execute_script(f"window.scrollBy(0, {100 * (i + 1)});")
                time.sleep(0.5)
            
            # 새로운 높이 확인
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # 현재 상품 링크 수집
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            current_links = set()
            
            # 모든 가능한 패턴으로 링크 수집
            patterns = [
                'a[href*="/products/"]',
                '.product-card a',
                '.product-item a',
                '.campaign-card a',
                '.grid-item a',
                '[data-product] a',
                '.product-link a'
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
                        
                        clean_url = full_url.split('?')[0]
                        current_links.add(clean_url)
            
            # 모든 링크에서 상품 링크 찾기 (백업)
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
                    current_links.add(clean_url)
            
            # 현재까지 수집된 링크 업데이트
            all_product_links.update(current_links)
            current_count = len(all_product_links)
            
            print(f"  → 현재 총 {current_count}개 상품 발견 (이번 스크롤로 {current_count - previous_count}개 추가)")
            print(f"  → 페이지 높이: {last_height} → {new_height}")
            
            # 상품 수가 증가했는지 확인
            if current_count > previous_count:
                stable_count = 0  # 새로운 상품이 있으면 카운터 리셋
                print(f"  → 새로운 상품 발견! 계속 스크롤...")
            else:
                stable_count += 1
                print(f"  → 새로운 상품 없음 ({stable_count}/{max_stable_iterations})")
            
            previous_count = current_count
            
            # 페이지 높이가 변하지 않고 상품도 증가하지 않으면 종료
            if new_height == last_height and stable_count >= 2:
                print("  → 페이지 높이와 상품 수 모두 변화 없음. 추가 시도...")
                # 추가 강제 스크롤 시도
                for i in range(10):
                    driver.execute_script(f"window.scrollTo(0, {new_height + i * 100});")
                    time.sleep(0.3)
        
        print(f"\n스크롤 완료! 총 {total_scrolls}번의 스크롤 시도")
        return sorted(list(all_product_links))
        
    except WebDriverException as e:
        print(f"Selenium WebDriver 오류: {e}")
        return []
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return []
    finally:
        if driver:
            print("5초 후 브라우저를 닫습니다...")
            time.sleep(5)  # 결과 확인을 위한 대기
            driver.quit()

def save_enhanced_past_products(links, filename="makeship_past_products_enhanced.txt"):
    """
    강화된 추출 결과를 파일로 저장
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Makeship Past 상품 링크 목록 - 강화된 무한 스크롤 (총 {len(links)}개)\n")
            f.write("=" * 70 + "\n\n")
            f.write("※ 강화된 무한 스크롤 알고리즘으로 수집된 모든 지난 상품들\n")
            f.write("※ 여러 스크롤 방법과 패턴 매칭을 사용하여 최대한 많은 상품 수집\n\n")
            
            for i, link in enumerate(links, 1):
                f.write(f"{i}. {link}\n")
        
        print(f"\n강화된 Past 상품 링크들이 '{filename}' 파일에 저장되었습니다.")
        
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

def main():
    """
    메인 실행 함수
    """
    print("Makeship Past 상품 강화된 무한 스크롤 추출 시작...")
    print("이 과정은 시간이 오래 걸릴 수 있습니다. 브라우저 창이 열리니 확인해보세요.")
    
    # 강화된 Past 상품 추출
    past_links = extract_past_products_enhanced_scroll()
    
    if past_links:
        print(f"\n" + "=" * 70)
        print(f"🎉 총 {len(past_links)}개의 Past 상품 링크를 찾았습니다!")
        print("=" * 70)
        
        # 처음 15개 링크 미리보기
        print("\n처음 15개 상품 미리보기:")
        for i, link in enumerate(past_links[:15], 1):
            product_name = link.split('/')[-1].replace('-', ' ').title()
            print(f"{i:2d}. {product_name}")
            print(f"    {link}")
        
        if len(past_links) > 15:
            print(f"\n... 및 {len(past_links) - 15}개 추가 상품")
        
        # 파일로 저장
        save_enhanced_past_products(past_links)
        
        # 이전 결과와 비교
        try:
            with open("makeship_past_products.txt", 'r', encoding='utf-8') as f:
                previous_content = f.read()
                previous_count = previous_content.count('https://www.makeship.com/products/')
            
            print(f"\n📊 비교 결과:")
            print(f"   이전 추출: {previous_count}개")
            print(f"   이번 추출: {len(past_links)}개")
            print(f"   차이: {len(past_links) - previous_count}개 {'증가' if len(past_links) > previous_count else '동일' if len(past_links) == previous_count else '감소'}")
            
        except FileNotFoundError:
            print("\n이전 추출 결과 파일을 찾을 수 없습니다.")
        
    else:
        print("Past 상품을 찾을 수 없습니다.")

if __name__ == "__main__":
    main()
