from playwright.async_api import async_playwright, TimeoutError # 변경
from playwright_stealth import Stealth # 변경
import json
from datetime import datetime
import glob
import os
import re # 정규 표현식 모듈 추가
import asyncio # 비동기 처리를 위해 asyncio 모듈 추가
from urllib.parse import urlparse # URL 파싱을 위해 추가

# 날짜 포맷 정규화 함수 (debug_page.py에서 복사)
def normalize_date(date_str):
    if not date_str or date_str == '정보 없음':
        return '정보 없음'
    parts = date_str.split(' / ')
    project_end_date_part = parts[0].strip()
    try:
        project_end_date_clean = ' '.join(project_end_date_part.split(' ')[:3])
        dt_object = datetime.strptime(project_end_date_clean.replace(',', ''), '%B %d %Y')
        return dt_object.strftime('%Y-%m-%d')
    except ValueError:
        pass
    if 'Ships ' in date_str:
        ship_date_part = date_str.split('Ships ')[-1].strip()
        try:
            dt_object = datetime.strptime(ship_date_part.replace(',', ''), '%B %d %Y')
            return dt_object.strftime('%Y-%m-%d')
        except ValueError:
            pass
    try:
        dt_object = datetime.strptime(date_str.replace(',', ''), '%B %d %Y')
        return dt_object.strftime('%Y-%m-%d')
    except ValueError:
        return '정보 없음'

# 제품군별 가격 매핑 (달러 기준)
CATEGORY_PRICES = {
    "hoodies": 59.99,
    "knitted crewnecks": 59.99,
    "t-shirts": 29.99,
    "enamel pins": 19.99,
    "vinyl figures": 29.99,
    "plushies": 29.99,
    "longbois": 36.99,
    "doughbois": 39.99,
    "jumbo plushies": 39.99,
    "keychain plushies": 15.99,
    "sweatpants": 54.99,
    "ball cap": 24.99,
    # 한국어 제품군명도 추가 (혹시 모를 경우를 대비)
    "후디": 59.99,
    "니트 크루넥": 59.99,
    "티셔츠": 29.99,
    "에나멜 핀": 19.99,
    "비닐 피규어": 29.99,
    "플러시": 29.99,
    "롱보이": 36.99,
    "도우보이": 39.99,
    "점보 플러시": 39.99,
    "키체인 플러시": 15.99,
    "스웨트팬츠": 54.99,
    "볼 캡": 24.99
}

def get_category_price(category):
    """제품군에 따른 가격을 반환합니다."""
    if not category or category == "제품군을 찾을 수 없습니다.":
        return 0.0
    
    # 소문자로 변환하여 매칭
    category_lower = category.lower()
    
    # 직접 매칭 시도
    if category_lower in CATEGORY_PRICES:
        return CATEGORY_PRICES[category_lower]
    
    # 부분 매칭 시도 (예: "Hoodies" -> "hoodies")
    for key in CATEGORY_PRICES:
        if key in category_lower or category_lower in key:
            return CATEGORY_PRICES[key]
    
    # 매칭되지 않는 경우 기본값 반환
    print(f"경고: 제품군 '{category}'에 대한 가격 정보를 찾을 수 없습니다.")
    return 29.99  # 기본값으로 플러시 가격 사용

def calculate_revenue(sales_volume, category, product_price):
    """판매량, 제품군, 실제 제품 가격을 기반으로 매출을 계산합니다."""
    try:
        # 판매량이 정보 없음인 경우만 0 반환
        if not sales_volume or sales_volume == "판매량 정보를 찾을 수 없습니다.":
            return 0.0
        
        # Sold Out인 경우 최소 목표 수량(200개)로 가정하여 매출 계산
        if sales_volume == "Sold Out":
            sales_count = 200  # Sold Out은 최소 목표 달성을 의미하므로 200개로 가정
            
            # 실제 크롤링한 가격이 있으면 사용, 없으면 제품군별 하드코딩 가격 사용
            actual_price = 0.0
            if product_price and product_price != "가격을 찾을 수 없습니다.":
                price_match = re.search(r'(\d+\.?\d*)', str(product_price).replace(',', ''))
                if price_match:
                    actual_price = float(price_match.group(1))
            
            if actual_price == 0.0:
                actual_price = get_category_price(category)
            
            revenue = sales_count * actual_price
            print(f"'Sold Out' 제품 - 최소 {sales_count}개 판매 가정, 가격: ${actual_price}, 매출: ${revenue:.2f}")
            return round(revenue, 2)
        
        # 판매량에서 숫자만 추출
        sales_match = re.search(r'(\d+)', str(sales_volume).replace(',', ''))
        if sales_match:
            sales_count = int(sales_match.group(1))
            
            # 실제 크롤링한 가격이 있으면 사용, 없으면 제품군별 하드코딩 가격 사용
            actual_price = 0.0
            if product_price and product_price != "가격을 찾을 수 없습니다.":
                # 크롤링한 가격에서 숫자만 추출
                price_match = re.search(r'(\d+\.?\d*)', str(product_price).replace(',', ''))
                if price_match:
                    actual_price = float(price_match.group(1))
            
            # 실제 가격이 없거나 0이면 제품군별 하드코딩 가격 사용
            if actual_price == 0.0:
                actual_price = get_category_price(category)
            
            revenue = sales_count * actual_price
            return round(revenue, 2)
        else:
            return 0.0
    except Exception as e:
        print(f"매출 계산 중 오류: {e}")
        return 0.0

def process_sales_data(sales_raw_text, funded_raw_text):
    processed_sales = "판매량 정보를 찾을 수 없습니다."
    processed_rate = "달성률 정보를 찾을 수 없습니다."

    # 1. 판매량 파싱
    if sales_raw_text and sales_raw_text != "정보 없음":
        sold_of_pattern = r'([0-9,]+)\s+of\s+([0-9,]+)\s+sold'
        sold_of_match = re.search(sold_of_pattern, sales_raw_text, re.IGNORECASE)
        if sold_of_match:
            processed_sales = sold_of_match.group(1).replace(',', '')
        else:
            sold_only_pattern = r'([0-9,]+)\s+sold'
            sold_only_match = re.search(sold_only_pattern, sales_raw_text, re.IGNORECASE)
            if sold_only_match:
                processed_sales = sold_only_match.group(1).replace(',', '')
            elif "Sold Out" in sales_raw_text:
                processed_sales = "Sold Out"

    # 2. 달성률 파싱
    if funded_raw_text and funded_raw_text != "정보 없음":
        funded_pattern = r'([0-9,]+%)(?:\s*\+)?\s+Funded' # '+' 기호 처리 추가
        funded_match = re.search(funded_pattern, funded_raw_text, re.IGNORECASE)
        if funded_match:
            processed_rate = funded_match.group(1).replace(',', '')
        elif "Sold Out" in funded_raw_text:
            processed_rate = "Sold Out"

    # 3. 판매량 기반 달성률 계산 (X of Y sold -> X/Y 비율) - 명시적인 달성률이 없을 때만 시도
    if processed_rate == "달성률 정보를 찾을 수 없습니다." and processed_sales != "판매량 정보를 찾을 수 없습니다." and processed_sales != "Sold Out" and "of" in sales_raw_text:
        sold_of_pattern = r'([0-9,]+)\s+of\s+([0-9,]+)\s+sold'
        sold_of_match = re.search(sold_of_pattern, sales_raw_text, re.IGNORECASE)
        if sold_of_match:
            x_val = int(sold_of_match.group(1).replace(',', ''))
            y_val_str = sold_of_match.group(2).replace(',', '')
            y_val = int(y_val_str) if y_val_str.isdigit() else 0
            if y_val > 0:
                processed_rate = f"{(x_val / y_val * 100):.1f}%"
            else:
                processed_rate = "0.0%"

    # 모든 정보가 없을 경우 최종적으로 Sold Out 처리
    if processed_sales == "판매량 정보를 찾을 수 없습니다." and processed_rate == "달성률 정보를 찾을 수 없습니다." and ("Sold Out" in sales_raw_text or "Sold Out" in funded_raw_text):
        processed_sales = "Sold Out"
        processed_rate = "Sold Out"

    return processed_sales, processed_rate

async def extract_product_data(page, url):
    """단일 제품 페이지에서 데이터를 추출하는 함수"""
    print(f"URL: {url} 처리 시작...") # 디버그 로그 추가
    try:
        print(f"URL: {url} 페이지 로드 시도 중...") # 디버그 로그 추가
        # 페이지 로딩 전략 변경 및 명시적 대기 추가
        await page.goto(url, wait_until='commit', timeout=30000) # 페이지 로딩 전략을 'commit'으로 변경 (최소 대기)
        print(f"URL: {url} 페이지 로드 완료. 제품 타이틀 셀렉터 대기 중...") # 디버그 로그 추가
        await page.wait_for_selector('[class*="ProductDetails__ProductTitle"]', timeout=30000)
        # 페이지 로딩 후 2초 명시적 대기
        await asyncio.sleep(2)
    except TimeoutError:
        print(f"페이지 로드 시간 초과: {url}")
        return None

    # --- 데이터 추출 ---
    product_data = {
        "제품_URL": url,
        "진행_여부": "정보 없음",
        "제품군": "정보 없음",
        "제품명": "정보 없음",
        "IP명": "정보 없음",
        "IP_소개_링크": "IP 소개 링크를 찾을 수 없습니다.", # 초기화
        "제품_가격": "정보 없음",
        "판매량": "정보 없음",
        "달성률": "정보 없음",
        "매출": 0.0,
        "프로젝트_종료일": "정보 없음",
        "배송_시작일": "정보 없음"
    }
    
    # 제품명
    try:
        product_data["제품명"] = await page.locator('[class*="ProductDetails__ProductTitle"]').inner_text(timeout=3000)
    except Exception as e:
        product_data["제품명"] = "제품명을 찾을 수 없습니다."

    # IP명
    try:
        # 'By:' 텍스트를 포함하는 링크를 찾아 IP 이름만 추출
        ip_name_element = page.locator('a:has-text("By:")')
        ip_name_text = await ip_name_element.inner_text(timeout=3000)
        product_data["IP명"] = ip_name_text.replace('By: ', '').strip()
    except Exception as e:
        product_data["IP명"] = "IP명을 찾을 수 없습니다."

    # 제품군
    try:
        # 제품 헤더 안에서, /collections/ 또는 /shop/ URL을 포함하는 링크의 p 태그를 찾음
        category_locator = page.locator('[class*="ProductInfo__ProductHeaderWrapper"] a[href*="/shop/"] p, [class*="ProductInfo__ProductHeaderWrapper"] a[href*="/collections/"] p, [class*="ProductInfo__ProductHeaderWrapper"] a:has-text("Store")')
        if await category_locator.count() > 0:
            category_text = await category_locator.first.inner_text(timeout=3000)
            # "Visit Creator Store" 또는 "Visit Store" 같은 텍스트 제거
            processed_category = re.sub(r'^Visit\s+.*\s+Store$', '', category_text, flags=re.IGNORECASE).strip()
            if not processed_category:
                # 만약 Visit Store 제거 후 빈 문자열이 되면, 링크의 텍스트 자체를 사용 (단어만)
                link_text = await category_locator.first.inner_text(timeout=3000)
                match = re.search(r'([A-Za-z]+)', link_text)
                if match:
                    processed_category = match.group(1).strip()
                else:
                    processed_category = "제품군을 찾을 수 없습니다."
            product_data["제품군"] = processed_category
    except Exception as e:
        product_data["제품군"] = "제품군 추출 실패: " + str(e)

    # 프로젝트 종료일 및 진행 여부
    try:
        end_date = "해당 없음"
        status = "종료"
        
        # 1. 사용자가 제공한 정확한 선택자 시도
        primary_end_date_locator = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div:nth-child(3) > div > p')
        if await primary_end_date_locator.count() > 0:
            end_date_text = await primary_end_date_locator.inner_text(timeout=3000)
            if "ends on" in end_date_text.lower():
                end_date = end_date_text.replace('Ends on ', '').strip()
                status = "진행 중"
            elif "ended:" in end_date_text.lower():
                end_date = end_date_text.replace('Ended: ', '').strip()
                status = "종료"
            elif "days left" in end_date_text.lower():
                end_date = "진행 중 (남은 일수 표시)"
                status = "진행 중"
            else:
                end_date = end_date_text.strip()
                if re.search(r'[A-Za-z]+\s+\d{1,2},\s+\d{4}', end_date):
                    status = "진행 중"
                else:
                    status = "종료"
        else:
            status = "종료"
        
        # 2. 첫 번째 선택자가 실패했고, end_date가 아직 설정되지 않은 경우, 원래 사용하던 선택자 시도
        #    (primary_end_date_locator가 아무것도 찾지 못했거나 오류 메시지를 반환한 경우)
        if status == "종료" and end_date == "해당 없음": # 첫 번째 시도가 실패한 경우
            fallback_end_date_locator = page.locator('[class*="ProductPageCountdown__CountdownDate"]')
            if await fallback_end_date_locator.count() > 0:
                end_date_text = await fallback_end_date_locator.inner_text(timeout=3000)
                end_date = end_date_text.replace('Ends on ', '').strip()
                status = "진행 중"
            # 대체 선택자도 실패하면 최종적으로 "해당 없음" 유지

        product_data["프로젝트_종료일"] = normalize_date(end_date)
        product_data["진행_여부"] = status
    except Exception as e:
        product_data["프로젝트_종료일"] = "프로젝트 종료일 정보를 찾을 수 없습니다."
        product_data["진행_여부"] = "상태 확인 중 오류"

    # 판매량 및 달성률
    sales_volume_raw = "판매량 정보를 찾을 수 없습니다."
    funded_rate_raw = "달성률 정보를 찾을 수 없습니다."
    try:
        # --- 판매량 및 달성률 추출 ---
        try:
            sales_text_found = ""
            funded_text_found = ""

            # 1. 판매량 특정 선택자들 시도
            sales_locators = [
                ("#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div:nth-child(3) > div > div.ProgressBarContainer__ProgressRow-sc-1slgn8k-2.cbQHDc > p", "판매량-ProgressRow"),
                ("#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div:nth-child(3) > div > div.ProgressBarContainer__PastLimitedCampaignRow-sc-1slgn8k-3.bLtdCY > p", "판매량-PastLimitedCampaignRow"),
                ('p[data-testid="units-sold-text"]', "Units Sold Text"),
                (r'p:has-text("Sold Out")', "Sold Out Text")
            ]
            for selector, name in sales_locators:
                try:
                    text_element = page.locator(selector)
                    if await text_element.count() > 0:
                        current_text = await text_element.first.inner_text(timeout=1000) # 짧은 타임아웃
                        if current_text and current_text.strip():
                            sales_text_found = current_text.strip()
                            print(f"DEBUG: '{name}' 로케이터로 판매량 찾음 -> '{sales_text_found}'")
                            break
                except Exception:
                    pass

            # 2. 달성률 특정 선택자들 시도
            funded_locators = [
                ("#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div:nth-child(3) > div > div.ProgressBarContainer__ProgressRow-sc-1slgn8k-2.cbQHDc > div > p", "달성률-ProgressRow-Funded"),
                (r'p:has-text("% Funded")', "Funded Text"),
            ]
            for selector, name in funded_locators:
                try:
                    text_element = page.locator(selector)
                    if await text_element.count() > 0:
                        current_text = await text_element.first.inner_text(timeout=1000) # 짧은 타임아웃
                        if current_text and current_text.strip():
                            funded_text_found = current_text.strip()
                            print(f"DEBUG: '{name}' 로케이터로 달성률 찾음 -> '{funded_text_found}'")
                            break
                except Exception:
                    pass

            # 3. JavaScript 폴백: 두 정보 모두 찾지 못했을 경우 전체 페이지에서 텍스트 기반 패턴 검색
            if not sales_text_found and not funded_text_found:
                print("DEBUG: 특정 선택자들 실패. JavaScript 폴백 실행.")
                find_visible_sales_text_js = """
                () => {
                    const patterns = [
                        /\\d+\\s+of\\s+\\d+\\s+sold/i,
                        /\\d+,?\\d*\\s+sold/i,
                        /\\d+%\\s+Funded/i,
                        /^Sold\\s+Out$/i
                    ];
                    const paragraphs = document.querySelectorAll('p');
                    for (const p of paragraphs) {
                        const isVisible = !!(p.offsetWidth || p.offsetHeight || p.getClientRects().length);
                        if (isVisible) {
                            for (const pattern of patterns) {
                                if (pattern.test(p.innerText.trim())) {
                                    return p.innerText.trim();
                                }
                            }
                        }
                    }
                    return null;
                }
                """
                js_combined_text = await page.evaluate(find_visible_sales_text_js)
                if js_combined_text:
                    if re.search(r'\d+% Funded', js_combined_text, re.IGNORECASE):
                        funded_text_found = js_combined_text
                    else:
                        sales_text_found = js_combined_text
                    print(f"DEBUG: JavaScript 폴백으로 텍스트 찾음 -> '{js_combined_text}'")

            sales_volume_raw = sales_text_found if sales_text_found else "판매량 정보를 찾을 수 없습니다."
            funded_rate_raw = funded_text_found if funded_text_found else "달성률 정보를 찾을 수 없습니다."

            sales_volume, funded_rate = process_sales_data(sales_volume_raw, funded_rate_raw)
            print(f"판매량: {sales_volume}")
            print(f"달성률: {funded_rate}")
            product_data["판매량"] = sales_volume  # 처리된 판매량 저장
            product_data["달성률"] = funded_rate  # 처리된 달성률 저장

        except Exception as e:
            print(f"URL {page.url}에서 판매량/달성률 추출 실패: {e}")
            product_data["판매량"] = "판매량 정보를 찾을 수 없습니다."
            product_data["달성률"] = "달성률 정보를 찾을 수 없습니다."
    except Exception as e:
        print(f"[상위 try-except] URL {page.url}에서 판매량/달성률 추출 중 치명적인 오류 발생: {e}")
        product_data["판매량"] = "판매량 정보를 찾을 수 없습니다."
        product_data["달성률"] = "달성률 정보를 찾을 수 없습니다."
    
    # 배송 시작일
    try:
        shipping_date = "배송 시작일 정보를 찾을 수 없습니다."
        
        # 1. 사용자께서 존재한다고 말씀해주신 선택자 먼저 시도
        primary_shipping_date_locator = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div.ProductInfo__PostPurchaseDetailsWrapper-sc-pdgh6r-9.jthCJt > div > div > p')
        if await primary_shipping_date_locator.count() > 0:
            shipping_date_text = await primary_shipping_date_locator.inner_text(timeout=3000)
            shipping_date = shipping_date_text.replace('Ships ', '').strip()
        
        # 2. 첫 번째 선택자가 실패했을 경우 (아직 기본값인 경우), '초록색 선택자' 시도
        if shipping_date == "배송 시작일 정보를 찾을 수 없습니다.":
            fallback_shipping_date_locator = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div.commonFunctions__HybridMessagingContainer-sc-e97hvy-8.gpFhIO')
            if await fallback_shipping_date_locator.count() > 0:
                shipping_date_text = await fallback_shipping_date_locator.inner_text(timeout=3000)
                shipping_date = shipping_date_text.replace('Ships ', '').strip()
        
        # 3. 새로운 일반적인 선택자 추가 (배송 관련 텍스트 검색)
        if shipping_date == "배송 시작일 정보를 찾을 수 없습니다.":
            general_shipping_locator = page.locator(r'p:has-text("Ships "), p:has-text("estimated to ship on")')
            if await general_shipping_locator.count() > 0:
                shipping_text = await general_shipping_locator.first.inner_text(timeout=3000)
                # "Ships Month Day, Year." 또는 "estimated to ship on Month Day, Year."에서 날짜 추출
                date_match = re.search(r'([A-Za-z]+\s+\d{1,2},\s+\d{4})', shipping_text)
                if date_match:
                    shipping_date = date_match.group(0).strip()
                else:
                    shipping_date = shipping_text.replace('Ships ', '').strip() # 남은 부분에서 최대한 정보 추출

        product_data["배송_시작일"] = normalize_date(shipping_date)
        print(f"배송 시작일: {product_data['배송_시작일']}")
    except Exception as e:
        print(f"배송 시작일 추출 실패: {e}")

    # IP 소개 링크
    try:
        # 여러 링크가 있을 수 있으므로 첫 번째 링크를 선택
        ip_link_elements = page.locator('[class*="CreatorMessage__CreatorMessageWrapper"] a')
        if await ip_link_elements.count() > 0:
            extracted_link = await ip_link_elements.first.get_attribute('href', timeout=3000)
            if extracted_link and extracted_link.startswith('/'):
                product_data["IP_소개_링크"] = f"https://www.makeship.com{extracted_link}"
            else:
                product_data["IP_소개_링크"] = extracted_link
        # else 블록은 필요 없음 (초기값이 '찾을 수 없음'이므로)
    except Exception as e:
        product_data["IP_소개_링크"] = "IP 소개 링크 추출 실패: " + str(e)

    # 제품 가격
    product_price = "가격을 찾을 수 없습니다."
    try:
        # 1. 사용자께서 제공하신 정확한 선택자 시도 (최우선)
        primary_price_locator = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div.ProductInfo__ProductHeaderWrapper-sc-pdgh6r-2.jUpShe > div > div > p')
        if await primary_price_locator.count() > 0:
            price_text = await primary_price_locator.first.inner_text(timeout=3000)
            match = re.search(r'\$?(\d+\.?\d*)', price_text)
            if match:
                extracted_price = match.group(1).strip()
                # $0.00이 아니고 숫자로 변환 가능한 경우만 사용
                if extracted_price and float(extracted_price) > 0:
                    product_price = extracted_price
                    print(f"DEBUG 가격 추출 (primary): ${product_price}")
        
        # 2. 일반적인 가격 선택자 시도 (폴백)
        if product_price == "가격을 찾을 수 없습니다.":
            general_price_locator = page.locator('[class*="ProductInfo__Price"]')
            if await general_price_locator.count() > 0:
                price_text = await general_price_locator.first.inner_text(timeout=3000)
                match = re.search(r'\$?(\d+\.?\d*)', price_text)
                if match:
                    extracted_price = match.group(1).strip()
                    if extracted_price and float(extracted_price) > 0:
                        product_price = extracted_price
                        print(f"DEBUG 가격 추출 (general): ${product_price}")

        # 3. "Total Price:" 텍스트를 포함하는 요소 찾기 (폴백)
        if product_price == "가격을 찾을 수 없습니다.":
            fallback_price_locator_text = page.locator(r'text=/Total Price: \$[0-9,.]+/i')
            if await fallback_price_locator_text.count() > 0:
                price_text = await fallback_price_locator_text.inner_text(timeout=3000)
                match = re.search(r'\$[0-9,.]+', price_text)
                if match:
                    extracted_price = match.group(0).replace('$', '').strip()
                    if extracted_price and float(extracted_price) > 0:
                        product_price = extracted_price
                        print(f"DEBUG 가격 추출 (Total Price): ${product_price}")
    except Exception as e:
        product_price = "제품 가격 추출 실패: " + str(e)

    # 제품 가격을 찾지 못했거나 0인 경우, 제품군별 하드코딩 가격으로 대체
    try:
        price_float = float(product_price) if product_price != "가격을 찾을 수 없습니다." else 0.0
    except:
        price_float = 0.0
    
    if product_price == "가격을 찾을 수 없습니다." or price_float == 0.0:
        estimated_price = get_category_price(product_data["제품군"])
        product_price = f"{estimated_price:.2f}" # 소수점 둘째 자리까지 표시
        print(f"경고: 제품 가격을 찾을 수 없어 제품군 '{product_data['제품군']}'의 추정 가격 ${product_price}로 대체했습니다.")
    
    product_data["제품_가격"] = product_price

    # 매출 계산 (실제 크롤링한 가격 우선, 없으면 제품군별 하드코딩 가격 사용)
    product_data["매출"] = calculate_revenue(product_data["판매량"], product_data["제품군"], product_data["제품_가격"])
    
    print(f"URL: {url} 데이터 추출 완료.") # 디버그 로그 추가
    return product_data

def load_proxies_from_file(filename="proxy.txt"):
    """프록시 목록 파일에서 프록시를 로드합니다."""
    proxies = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+', line):
                    proxies.append(line)
        print(f"'{filename}'에서 {len(proxies)}개의 프록시를 로드했습니다.")
    except FileNotFoundError:
        print(f"오류: 프록시 파일 '{filename}'을 찾을 수 없습니다.")
    except Exception as e:
        print(f"프록시 파일 로드 중 오류 발생: {e}")
    return proxies

def load_urls_from_file():
    """가장 최근에 생성된 makeship_unique_products_*.txt 파일에서 URL을 로드합니다."""
    import glob
    import os
    
    list_of_files = glob.glob('makeship_unique_products_*.txt')
    if not list_of_files:
        print("오류: 'makeship_unique_products_*.txt' 파일을 찾을 수 없습니다.")
        print("먼저 'complete_infinite_extractor.py'를 실행하여 제품 링크를 추출해주세요.")
        return []

    latest_file = max(list_of_files, key=os.path.getctime)
    urls = []
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            for line in f:
                # URL만 포함된 라인 필터링 (숫자. URL 형식 제외)
                if line.strip().startswith("https://www.makeship.com/products/"):
                    urls.append(line.strip())
                # 또는 '1. URL' 형식에서 URL만 추출
                elif line.strip().startswith(tuple(str(i) + '. ' for i in range(10))):
                    parts = line.strip().split('. ', 1)
                    if len(parts) == 2:
                        urls.append(parts[1])
        print(f"'{latest_file}' 파일에서 {len(urls)}개의 URL을 로드했습니다.")
    except Exception as e:
        print(f"URL 파일 로드 중 오류 발생: {e}")
        return []
    return urls

async def process_url(browser, url, proxy, semaphore, all_products_data, is_rescrape=False):
    async with semaphore:
        # is_rescrape 여부와 관계없이, process_url은 항상 스크래핑을 시도합니다.
        # 건너뛰기 로직은 main 함수에서 이미 처리된 URL을 tasks에 추가하지 않는 방식으로 처리됩니다.

        context = None
        try:
            context = await browser.new_context(proxy={"server": f"http://{proxy}"}) # 컨텍스트 생성 및 프록시 적용
            page = await context.new_page()
            
            # Stealth 적용 (최신 방식)
            stealth_instance = Stealth() # Stealth 클래스 인스턴스 생성
            await stealth_instance.apply_stealth_async(context) # context에 비동기 stealth 적용

            product_data = await extract_product_data(page, url)
            if product_data:
                all_products_data[url] = product_data # 딕셔너리에 추가 또는 업데이트
                # 개별 제품 정보 출력 (JSON 형식으로)
                print(f"\n{'='*80}")
                print(f"✅ [{product_data['진행_여부']}] {product_data['제품명']}")
                print(f"{'='*80}")
                print(json.dumps(product_data, ensure_ascii=False, indent=2))
                print(f"{'='*80}\n")
                return product_data
            else:
                print(f"❌ 제품 데이터 추출 실패: {url}")
                return None
        except Exception as e:
            print(f"URL {url} 처리 중 예외 발생: {e}")
            return None
        finally:
            if context:
                await context.close()

async def main():
    urls = load_urls_from_file()
    if not urls:
        print("처리할 URL이 없으므로 스크립트를 종료합니다.")
        return

    proxies = load_proxies_from_file()
    if not proxies:
        print("로드된 프록시가 없습니다. 스크립트를 종료합니다.")
        return

    # 이전에 저장된 JSON 파일들을 로드하여 이미 처리된 URL 목록과 "Sold Out" 제품 목록을 가져옵니다.
    print("이전에 처리된 제품 데이터 로드 중...")
    all_products_data = {}
    sold_out_urls_to_rescrape = set()
    json_files = glob.glob('makeship_all_products_*.json')
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "제품_목록" in data:
                    for product in data["제품_목록"]:
                        if "제품_URL" in product:
                            url = product["제품_URL"]
                            all_products_data[url] = product
                            if product.get("판매량") == "Sold Out":
                                sold_out_urls_to_rescrape.add(url)
            print(f"'{json_file}'에서 {len(data.get("제품_목록", []))}개 제품 로드 완료.")
        except Exception as e:
            print(f"'{json_file}' 로드 중 오류 발생: {e}")

    print(f"총 {len(all_products_data)}개의 URL이 이전에 처리되었으며, 그 중 {len(sold_out_urls_to_rescrape)}개가 'Sold Out' 제품입니다.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # 브라우저를 헤드리스 모드로 한 번만 실행 (속도 향상)
        # 세마포어를 사용하여 동시 실행 브라우저 수 제한 (예: 10개로 증가)
        semaphore = asyncio.Semaphore(10)
        
        # --- "Sold Out" 제품 우선 재스크래핑 ---
        if sold_out_urls_to_rescrape:
            print(f"\n=== 'Sold Out' 제품 {len(sold_out_urls_to_rescrape)}개 재스크래핑 시작 ===")
            tasks = []
            for i, url in enumerate(list(sold_out_urls_to_rescrape), 0):
                proxy = proxies[i % len(proxies)]
                tasks.append(process_url(browser, url, proxy, semaphore, all_products_data, is_rescrape=True))
            
            results = await asyncio.gather(*tasks, return_exceptions=True) # 예외 발생 시에도 결과 반환
            completed_sold_out_count = 0
            for result in results:
                if isinstance(result, Exception):
                    print(f"❗️ 'Sold Out' 제품 처리 중 오류 발생: {result}")
                elif result:
                    all_products_data[result["제품_URL"]] = result
                    completed_sold_out_count += 1

            print(f"\n=== 'Sold Out' 제품 재스크래핑 완료. {completed_sold_out_count}/{len(sold_out_urls_to_rescrape)}개 처리. ===")

        # --- 나머지 URL 및 신규 제품 스크래핑 (Sold Out 제외 모든 URL 대상) ---
        print(f"\n=== 나머지 및 신규 제품 스크래핑 시작 (Sold Out 제외 총 {len(urls) - len(sold_out_urls_to_rescrape)}개 URL 대상) ===")
        tasks = []
        for i, url in enumerate(urls, 0):
            # 이미 'Sold Out' 재스크래핑에서 처리된 URL은 건너뛰기
            if url in sold_out_urls_to_rescrape:
                continue

            proxy = proxies[i % len(proxies)] # 라운드 로빈 방식으로 프록시 할당
            tasks.append(process_url(browser, url, proxy, semaphore, all_products_data))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True) # 예외 발생 시에도 결과 반환
            completed_other_count = 0
            for result in results:
                if isinstance(result, Exception):
                    print(f"❗️ 일반 스크래핑 중 오류 발생: {result}")
                elif result:
                    all_products_data[result["제품_URL"]] = result
                    completed_other_count += 1
            print(f"\n=== 나머지 및 신규 제품 스크래핑 완료. {completed_other_count}/{len(tasks)}개 처리. ===")
        else:
            print("Sold Out 제품을 제외하고 추가로 스크래핑할 제품이 없습니다.")
        
        await browser.close() # 모든 작업 후 브라우저 종료
    
    # 모든 데이터를 하나의 JSON 파일로 저장
    if all_products_data:
        final_data = {
            "추출_시간": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "총_제품_수": len(all_products_data),
            "제품_목록": list(all_products_data.values())
        }
        
        filename = f"makeship_all_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            print(f"\n=== 완료 ===")
            print(f"총 {len(all_products_data)}개 제품의 데이터가 '{filename}' 파일로 저장되었습니다.")
        except Exception as e:
            print(f"\nJSON 파일 저장 중 오류 발생: {e}")
    else:
        print("\n추출된 데이터가 없습니다.")

if __name__ == '__main__':
    asyncio.run(main())