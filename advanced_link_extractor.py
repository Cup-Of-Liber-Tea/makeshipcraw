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

def extract_makeship_hoodie_links_selenium():
    """
    Selenium을 사용하여 Makeship의 후디 상품 링크들을 추출하는 함수
    """
    url = "https://www.makeship.com/shop/hoodies"
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 브라우저 창을 띄우지 않음
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = None
    try:
        print("Selenium으로 Makeship 후디 페이지에 접속 중...")
        # Chrome 드라이버 자동 설치 및 설정
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        
        # 페이지 로딩 대기
        wait = WebDriverWait(driver, 10)
        
        # 상품이 로드될 때까지 잠시 대기
        time.sleep(3)
        
        # 페이지 소스 가져오기
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        product_links = []
        
        # 다양한 상품 링크 패턴 시도
        link_patterns = [
            'a[href*="/products/"]',
            'a[href*="hoodie"]',
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
                if href:
                    if href.startswith('/'):
                        full_url = f"https://www.makeship.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # 후디 관련 링크인지 확인
                    if 'hoodie' in full_url.lower() or '/products/' in full_url:
                        if full_url not in product_links:
                            product_links.append(full_url)
        
        # 만약 특정 패턴으로 찾지 못했다면 모든 링크 검사
        if not product_links:
            print("특정 패턴으로 찾지 못해 모든 링크를 검사합니다...")
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if any(keyword in href.lower() for keyword in ['product', 'hoodie', 'campaign']):
                    if href.startswith('/'):
                        full_url = f"https://www.makeship.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    if full_url not in product_links:
                        product_links.append(full_url)
        
        return product_links
        
    except WebDriverException as e:
        print(f"Selenium WebDriver 오류: {e}")
        print("Chrome 드라이버가 설치되지 않았을 수 있습니다.")
        return []
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return []
    finally:
        if driver:
            driver.quit()

def extract_makeship_hoodie_links_requests():
    """
    requests를 사용하여 Makeship의 후디 상품 링크들을 추출하는 함수 (백업 방법)
    """
    url = "https://www.makeship.com/shop/hoodies"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print("requests로 Makeship 후디 페이지에 접속 중...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        product_links = []
        
        # 페이지의 모든 링크를 검사하여 상품 관련 링크 찾기
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            
            # 상품 관련 패턴 확인
            if any(pattern in href.lower() for pattern in ['product', 'hoodie', 'campaign']):
                if href.startswith('/'):
                    full_url = f"https://www.makeship.com{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue
                
                if full_url not in product_links:
                    product_links.append(full_url)
        
        return product_links
        
    except requests.RequestException as e:
        print(f"웹페이지 요청 중 오류 발생: {e}")
        return []
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return []

def save_links_to_file(links, filename="makeship_hoodie_links.txt"):
    """
    추출된 링크들을 파일로 저장하는 함수
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Makeship 후디 상품 링크 목록 (총 {len(links)}개)\n")
            f.write("=" * 50 + "\n\n")
            
            for i, link in enumerate(links, 1):
                f.write(f"{i}. {link}\n")
        
        print(f"링크들이 '{filename}' 파일에 저장되었습니다.")
        
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

def main():
    """
    메인 실행 함수
    """
    print("Makeship 후디 상품 링크 추출 시작...")
    
    # 먼저 Selenium 방법 시도
    links = extract_makeship_hoodie_links_selenium()
    
    # Selenium이 실패하면 requests 방법 사용
    if not links:
        print("Selenium 방법이 실패했습니다. requests 방법을 시도합니다...")
        links = extract_makeship_hoodie_links_requests()
    
    if links:
        print(f"\n총 {len(links)}개의 링크를 찾았습니다:")
        print("-" * 50)
        
        for i, link in enumerate(links, 1):
            print(f"{i}. {link}")
        
        # 파일로 저장
        save_links_to_file(links)
        
    else:
        print("링크를 찾을 수 없습니다.")
        print("웹사이트가 JavaScript를 많이 사용하거나 접근이 제한되었을 수 있습니다.")
        print("Chrome 드라이버 설치가 필요할 수 있습니다: pip install webdriver-manager")

if __name__ == "__main__":
    main()
