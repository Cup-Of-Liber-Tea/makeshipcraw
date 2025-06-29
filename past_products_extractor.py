import time
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

def extract_past_products_with_infinite_scroll():
    """
    Makeship의 past 페이지에서 무한 스크롤을 통해 모든 상품을 추출하는 함수
    """
    url = "https://www.makeship.com/shop/past"
    
    # Chrome 옵션 설정
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 브라우저 창 보이도록 주석 처리
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    
    try:
        print("Selenium Chrome 드라이버 설정 중...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print(f"Past 상품 페이지에 접속 중... ({url})")
        driver.get(url)
        
        # 초기 로딩 대기
        time.sleep(5)
        
        print("무한 스크롤을 통한 모든 상품 로딩 시작...")
        
        previous_product_count = 0
        no_change_count = 0
        max_no_change = 3  # 3번 연속 변화가 없으면 종료
        scroll_attempts = 0
        max_scroll_attempts = 50  # 최대 스크롤 시도 횟수
        max_products = 805  # 805개 이상이면 초기화되므로 여기서 멈춤
        all_discovered_links = set()  # 지금까지 발견된 모든 링크 저장
        
        while scroll_attempts < max_scroll_attempts and no_change_count < max_no_change:
            scroll_attempts += 1
            
            # 현재 상품 수 확인
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 상품 링크 찾기
            product_links = set()
            link_patterns = [
                'a[href*="/products/"]',
                '.product-card a',
                '.product-item a',
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
                        
                        clean_url = full_url.split('?')[0]
                        product_links.add(clean_url)
            
            current_product_count = len(product_links)
            
            # 모든 발견된 링크를 누적 저장
            all_discovered_links.update(product_links)
            
            print(f"스크롤 시도 {scroll_attempts}: 현재 페이지 {current_product_count}개, 총 누적 {len(all_discovered_links)}개 상품 발견")
            
            # 805개에 도달하거나 현재 상품 수가 급격히 줄어들면 (초기화 감지) 종료
            if len(all_discovered_links) >= max_products:
                print(f"  → 목표 상품 수({max_products}개)에 도달했습니다!")
                break
            
            if current_product_count < 100 and len(all_discovered_links) > 500:
                print(f"  → 페이지 초기화가 감지되었습니다. 수집을 종료합니다.")
                break
            
            # 상품 수가 변하지 않으면 카운터 증가
            if current_product_count == previous_product_count:
                no_change_count += 1
                print(f"  → 상품 수 변화 없음 ({no_change_count}/{max_no_change})")
            else:
                no_change_count = 0  # 변화가 있으면 카운터 리셋
                new_count = current_product_count - previous_product_count
                print(f"  → 새로운 상품 {new_count}개 발견!")
            
            previous_product_count = current_product_count
            
            # Home 키로 페이지 맨 위로 이동
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.HOME)
            time.sleep(1)
            
            # End 키로 페이지 맨 아래로 이동
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
            time.sleep(3)
            
            # 추가 End 키 입력으로 더 많은 콘텐츠 로드 시도
            for i in range(3):
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
                time.sleep(1)
        
        # 최종 상품 목록 반환 (누적된 모든 링크)
        print(f"\n수집 완료! 총 {len(all_discovered_links)}개의 고유 상품을 발견했습니다.")
        return sorted(list(all_discovered_links))
        
    except WebDriverException as e:
        print(f"Selenium WebDriver 오류: {e}")
        return []
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def save_past_products_to_file(links, filename="makeship_past_products.txt"):
    """
    past 상품 링크들을 파일로 저장하는 함수
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Makeship Past 상품 링크 목록 (총 {len(links)}개)\n")
            f.write("=" * 60 + "\n")
            f.write("※ Home/End 키 무한 스크롤로 수집된 지난 상품들\n")
            f.write("※ 805개 한계점에서 자동 중단하여 수집\n")
            f.write(f"※ 수집 일시: {time.strftime('%Y년 %m월 %d일 %H시 %M분')}\n\n")
            
            for i, link in enumerate(links, 1):
                f.write(f"{i}. {link}\n")
        
        print(f"\nPast 상품 링크들이 '{filename}' 파일에 저장되었습니다.")
        
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

def main():
    """
    메인 실행 함수
    """
    print("Makeship Past 상품 무한 스크롤 추출 시작...")
    print("805개 한계점에서 자동으로 중단됩니다.")
    print("이 과정은 시간이 걸릴 수 있습니다. 잠시만 기다려주세요.")
    
    # Past 상품 추출
    past_links = extract_past_products_with_infinite_scroll()
    
    if past_links:
        print(f"\n" + "=" * 60)
        print(f"✅ 총 {len(past_links)}개의 Past 상품 링크를 수집했습니다!")
        print("=" * 60)
        
        # 처음 15개 링크 미리보기
        print(f"\n처음 15개 상품 미리보기:")
        for i, link in enumerate(past_links[:15], 1):
            product_name = link.split('/')[-1].replace('-', ' ').title()
            print(f"{i:2d}. {product_name}")
        
        if len(past_links) > 15:
            print(f"... 및 {len(past_links) - 15}개 추가 상품")
        
        # 파일로 저장
        save_past_products_to_file(past_links)
        
        print(f"\n🎉 성공적으로 {len(past_links)}개의 Past 상품을 추출했습니다!")
        print("805개 한계 내에서 최대한 많은 상품을 수집했습니다.")
        
    else:
        print("❌ Past 상품을 찾을 수 없습니다.")
        print("웹사이트 구조가 변경되었거나 접근이 제한되었을 수 있습니다.")

if __name__ == "__main__":
    main()
