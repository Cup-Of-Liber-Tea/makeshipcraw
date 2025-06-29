from playwright.sync_api import sync_playwright, TimeoutError
from playwright_stealth import stealth_sync

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        stealth_sync(page)
        
        url = 'https://www.makeship.com/products/swordscomic-hoodie'
        try:
            # 페이지 로딩 전략 변경 및 명시적 대기 추가
            page.goto(url, wait_until='load', timeout=60000)
            page.wait_for_selector('[class*="ProductDetails__ProductTitle"]', timeout=30000)
        except TimeoutError:
            print(f"페이지 로드 시간 초과: {url}")
            browser.close()
            return

        # --- 데이터 추출 ---
        
        # 제품명
        try:
            product_name = page.locator('[class*="ProductDetails__ProductTitle"]').inner_text(timeout=5000)
        except Exception as e:
            product_name = f"제품명을 찾을 수 없습니다. 오류: {e}"

        # IP명
        try:
            # 'By:' 텍스트를 포함하는 링크를 찾아 IP 이름만 추출
            ip_name_element = page.locator('a:has-text("By:")')
            ip_name_text = ip_name_element.inner_text(timeout=5000)
            ip_name = ip_name_text.replace('By: ', '').strip()
        except Exception as e:
            ip_name = f"IP명을 찾을 수 없습니다. 오류: {e}"

        # 제품군
        try:
            # 제품 헤더 안에서, /collections/ 또는 /shop/ URL을 포함하는 링크의 p 태그를 찾음
            category = page.locator('[class*="ProductInfo__ProductHeaderWrapper"] a[href*="/shop/"] p, [class*="ProductInfo__ProductHeaderWrapper"] a[href*="/collections/"] p').first.inner_text(timeout=5000)
        except Exception as e:
            category = f"제품군을 찾을 수 없습니다. 오류: {e}"

        # 프로젝트 종료일
        try:
            end_date_element = page.locator('[class*="ProductPageCountdown__CountdownDate"]')
            if end_date_element.count() > 0:
                end_date_text = end_date_element.inner_text(timeout=5000)
                end_date = end_date_text.replace('Ends on ', '').strip()
                status = "진행 중"
            else:
                # 종료된 캠페인을 위한 로직 (나중에 구체화)
                end_date = "해당 없음"
                status = "종료"
        except Exception as e:
            end_date = f"프로젝트 종료일을 찾을 수 없습니다. 오류: {e}"
            status = f"상태 확인 중 오류: {e}"

        # 판매량 (정확한 선택자 사용)
        try:
            # 사용자가 제공한 정확한 선택자 사용
            sales_locator = page.locator('#__next > div._app__ContainerWrapper-meusgd-0.kPTMSg > div > div._app__ContentWrapper-meusgd-2.hIhdAc > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.bstoHm > div > div:nth-child(3) > div > div.ProgressBarContainer__ProgressRow-sc-1slgn8k-2.dYXbKV > p')
            if sales_locator.count() > 0:
                sales_volume = sales_locator.first.inner_text(timeout=5000)
            else:
                # 대체 선택자들
                sales_locator_alt = page.locator(
                    'div.ProgressBarContainer__ProgressRow-sc-1slgn8k-2 p:has-text("sold"), '
                    '[class*="ProgressBarContainer"] p:has-text("sold"), '
                    'p:has-text("sold")'
                )
                sales_volume = sales_locator_alt.first.inner_text(timeout=5000)
        except Exception as e:
            sales_volume = f"판매량을 찾을 수 없습니다. 오류: {e}"
            
        # 달성률
        try:
            # '% funded' 텍스트를 포함하는 선택자
            funded_rate = page.locator('p:has-text("% Funded")').inner_text(timeout=5000)
        except Exception as e:
            funded_rate = f"달성률을 찾을 수 없습니다. 오류: {e}"

        # 배송 시작일
        try:
            shipping_date = page.locator('[class*="commonFunctions__ShipDateText"]').inner_text(timeout=5000)
        except Exception as e:
            shipping_date = f"배송 시작일을 찾을 수 없습니다. 오류: {e}"

        # IP 소개 링크
        try:
            ip_link_element = page.locator('[class*="CreatorMessage__CreatorMessageWrapper"] a')
            ip_link = ip_link_element.get_attribute('href', timeout=5000)
            if ip_link and ip_link.startswith('/'):
                ip_link = f"https://www.makeship.com{ip_link}"
        except Exception as e:
            ip_link = f"IP 소개 링크를 찾을 수 없습니다. 오류: {e}"

        print("--- Makeship 제품 정보 ---")
        print(f"진행 여부: {status}")
        print(f"제품군: {category}")
        print(f"제품명: {product_name}")
        print(f"IP명: {ip_name}")
        print(f"IP 소개 링크: {ip_link}")
        print(f"판매량: {sales_volume}")
        print(f"달성률: {funded_rate}")
        print(f"프로젝트 종료일: {end_date}")
        print(f"배송 시작일: {shipping_date}")

        print("\n--- 스크립트 완료 ---")
        print("결과 확인 후 브라우저를 직접 닫아주세요.")
        browser.close()

if __name__ == '__main__':
    main()