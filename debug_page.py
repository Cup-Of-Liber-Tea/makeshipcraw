from playwright.sync_api import sync_playwright
import time

def debug_page_structure(url):
    """
    페이지 구조를 디버깅해서 종료일 관련 요소를 찾는 함수
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headless=False로 브라우저 확인
        page = browser.new_page()
        
        try:
            print(f"페이지 로딩: {url}")
            page.goto(url, wait_until='load', timeout=60000)
            page.wait_for_selector('[class*="ProductDetails__ProductTitle"]', timeout=30000)
            
            print("\\n=== 페이지 제목 ===")
            title = page.locator('[class*="ProductDetails__ProductTitle"]').inner_text()
            print(title)
            
            print("\\n=== 모든 텍스트에서 'end' 검색 ===")
            end_elements = page.locator('text=/.*end.*/')
            count = end_elements.count()
            print(f"'end' 포함 요소 {count}개 발견")
            for i in range(min(5, count)):
                text = end_elements.nth(i).inner_text()
                print(f"  {i+1}: {text[:100]}...")
            
            print("\\n=== 모든 텍스트에서 날짜 패턴 검색 ===")
            date_elements = page.locator('text=/.*\\d{1,2}.*\\d{4}.*/')
            count = date_elements.count()
            print(f"날짜 패턴 요소 {count}개 발견")
            for i in range(min(5, count)):
                text = date_elements.nth(i).inner_text()
                print(f"  {i+1}: {text[:100]}...")
            
            print("\\n=== countdown 관련 클래스 ===")
            countdown_elements = page.locator('[class*="countdown"], [class*="Countdown"]')
            count = countdown_elements.count()
            print(f"countdown 클래스 요소 {count}개 발견")
            for i in range(min(3, count)):
                text = countdown_elements.nth(i).inner_text()
                print(f"  {i+1}: {text[:100]}...")
            
            print("\\n=== 진행 상태 관련 텍스트 ===")
            status_keywords = ["ended", "completed", "finished", "closed", "live", "active"]
            for keyword in status_keywords:
                elements = page.locator(f'text=/{keyword}/i')
                if elements.count() > 0:
                    text = elements.first.inner_text()
                    print(f"  {keyword}: {text[:50]}...")
            
            # 5초 대기해서 페이지 확인
            print("\\n브라우저에서 페이지를 확인하세요. 5초 후 종료됩니다...")
            time.sleep(5)
            
        except Exception as e:
            print(f"오류: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    # 테스트할 URL
    test_url = "https://www.makeship.com/products/bumblepurr-plushie"
    debug_page_structure(test_url)
