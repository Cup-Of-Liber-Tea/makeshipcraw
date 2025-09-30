from playwright.async_api import async_playwright, TimeoutError
from playwright_stealth import Stealth
import asyncio
import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

# --- 1.py에서 복사해온 상수 시작 ---

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

# --- 1.py에서 복사해온 상수 끝 ---

def get_category_price(category):
    if not category or category == "제품군을 찾을 수 없습니다.":
        return 0.0
    category_lower = category.lower()
    if category_lower in CATEGORY_PRICES:
        return CATEGORY_PRICES[category_lower]
    for key in CATEGORY_PRICES:
        if key in category_lower or category_lower in key:
            return CATEGORY_PRICES[key]
    print(f"경고: 제품군 '{category}'에 대한 가격 정보를 찾을 수 없습니다.")
    return 29.99

def calculate_revenue(sales_volume, category, product_price):
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
        
        sales_match = re.search(r'(\d+)', str(sales_volume).replace(',', ''))
        if sales_match:
            sales_count = int(sales_match.group(1))
            actual_price = 0.0
            if product_price and product_price != "가격을 찾을 수 없습니다.":
                price_match = re.search(r'(\d+\.?\d*)', str(product_price).replace(',', ''))
                if price_match:
                    actual_price = float(price_match.group(1))
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

def load_proxies_from_file(filename="proxy.txt"):
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

# --- 1.py에서 복사해온 상수 끝 ---

# 이후 헬퍼 함수 및 메인 로직이 추가될 예정

async def debug_page_structure(url: str):
    proxies = load_proxies_from_file('proxy.txt')
    async with async_playwright() as p:
        browser = None
        proxy_list = [None] + proxies 
        
        for proxy in proxy_list:
            context = None
            browser = None # Reset browser for each attempt
            try:
                browser = await p.chromium.launch(headless=False)
                
                context_args = {}
                if proxy:
                    print(f"--- 프록시 {proxy} 사용하는 중 ---")
                    proxy_parts = proxy.split(':')
                    proxy_ip = proxy_parts[0]
                    proxy_port = proxy_parts[1]
                    context_args['proxy'] = { "server": f"http://{proxy_ip}:{proxy_port}" }

                context = await browser.new_context(**context_args)
                
                stealth_instance = Stealth()
                await stealth_instance.apply_stealth_async(context)

                page = await context.new_page()

                print(f"페이지 로딩: {url}")
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)

                print("페이지 로드 완료. 제품 타이틀 셀렉터 대기 중...")
                await page.wait_for_selector('[class*="ProductDetails__ProductTitle"]', timeout=30000)
                await asyncio.sleep(2)
                print("\n--- 데이터 추출 시도 및 디버그 정보 ---")

                # (All data extraction logic needs to be inside this try block)
                product_data = {
                    "제품_URL": url,
                    "진행_여부": "정보 없음",
                    "제품군": "정보 없음",
                    "제품명": "정보 없음",
                    "IP명": "정보 없음",
                    "IP_소개_링크": "정보 없음",
                    "제품_가격": "정보 없음",
                    "판매량": "정보 없음",
                    "달성률": "정보 없음",
                    "매출": 0.0,
                    "프로젝트_종료일": "정보 없음",
                    "배송_시작일": "정보 없음"
                }

                # --- 제품명 ---
                try:
                    product_data["제품명"] = await page.locator('[class*="ProductDetails__ProductTitle"]').inner_text(timeout=3000)
                    print(f"제품명: {product_data['제품명']}")
                except Exception as e:
                    print(f"제품명 추출 실패: {e}")
                
                # --- IP명 ---
                try:
                    ip_name_element = page.locator('a:has-text("By:")')
                    if await ip_name_element.count() > 0:
                        ip_name_text = await ip_name_element.inner_text(timeout=3000)
                        product_data["IP명"] = ip_name_text.replace('By: ', '').strip()
                    print(f"IP명: {product_data['IP명']}")
                except Exception as e:
                    print(f"IP명 추출 실패: {e}")

                # --- 제품군 ---
                # 제품 헤더 내에서 /shop/ 또는 /collections/ URL을 포함하는 p 태그, 또는 "Store" 텍스트를 포함하는 a 태그를 찾아 제품군을 추출합니다.
                # "Visit Creator Store"와 같은 불필요한 텍스트를 제거하고, 제거 후 빈 문자열인 경우 링크 텍스트에서 단어만 추출하는 폴백 로직을 포함합니다.
                try:
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
                    print(f"제품군: {product_data['제품군']}")
                except Exception as e:
                    product_data["제품군"] = "제품군 추출 실패: " + str(e)
                    print(f"제품군 추출 실패: {e}")

                # --- 프로젝트 종료일 및 진행 여부 ---
                # 페이지에서 프로젝트 종료일 정보를 추출하고, 이를 기반으로 제품의 진행 상태를 결정합니다.
                # 다양한 종료일 텍스트 패턴에 대응하며, normalize_date 함수를 사용하여 날짜 형식을 표준화합니다.
                try:
                    end_date = "해당 없음"
                    status = "종료"
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
                        fallback_end_date_locator = page.locator('[class*="ProductPageCountdown__CountdownDate"]')
                        if await fallback_end_date_locator.count() > 0:
                            end_date_text = await fallback_end_date_locator.inner_text(timeout=3000)
                            end_date = end_date_text.replace('Ends on ', '').strip()
                            status = "진행 중"
                    
                    product_data["프로젝트_종료일"] = normalize_date(end_date)
                    product_data["진행_여부"] = status
                    print(f"프로젝트 종료일: {product_data['프로젝트_종료일']} (상태: {product_data['진행_여부']})")
                except Exception as e:
                    print(f"프로젝트 종료일/진행 여부 추출 실패: {e}")

                # --- 판매량 및 달성률 추출 ---
                # 페이지에서 판매량과 달성률 정보를 추출하고, 이를 정규 표현식을 사용하여 파싱합니다.
                # 명시적인 달성률(%)이 있을 경우 우선하고, 없을 경우 판매량 기반으로 달성률을 계산합니다.
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
                        (r'p:has-text("% Funded")', "Funded Text")
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
                            # JavaScript 폴백은 하나의 텍스트만 반환하므로, 이를 판매량 또는 달성률로 해석
                            if re.search(r'\d+% Funded', js_combined_text, re.IGNORECASE):
                                funded_text_found = js_combined_text
                            else:
                                sales_text_found = js_combined_text
                            print(f"DEBUG: JavaScript 폴백으로 텍스트 찾음 -> '{js_combined_text}'")

                    # 최종적으로 찾은 raw 텍스트를 process_sales_data에 전달
                    sales_volume_raw = sales_text_found if sales_text_found else "판매량 정보를 찾을 수 없습니다."
                    funded_rate_raw = funded_text_found if funded_text_found else "달성률 정보를 찾을 수 없습니다."

                    # process_sales_data 호출 시 두 개의 raw 텍스트 인자 전달
                    sales_volume, funded_rate = process_sales_data(sales_volume_raw, funded_rate_raw)
                    print(f"판매량: {sales_volume}")
                    print(f"달성률: {funded_rate}")
                    product_data["판매량"] = sales_volume
                    product_data["달성률"] = funded_rate

                except Exception as e:
                    print(f"URL {page.url}에서 판매량/달성률 추출 실패: {e}")
                    product_data["판매량"] = "판매량 정보를 찾을 수 없습니다."
                    product_data["달성률"] = "달성률 정보를 찾을 수 없습니다."
                
                # --- 배송 시작일 ---
                # 페이지에서 배송 시작일 정보를 추출하고, normalize_date 함수를 사용하여 날짜 형식을 표준화합니다.
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

                # --- IP 소개 링크 ---
                # CreatorMessageWrapper 클래스를 가진 요소 내의 링크를 찾아 IP 소개 링크를 추출합니다.
                try:
                    # ip_link는 이미 product_data 초기화 시 "IP 소개 링크를 찾을 수 없습니다."로 설정됨
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
                    print(f"IP 소개 링크 추출 실패: {e}")

                # --- 제품 가격 ---
                # 페이지에서 제품 가격을 추출합니다. 사용자가 제공한 정확한 선택자를 우선 사용하고,
                # 여러 폴백 선택자들을 사용하여 가격 추출의 정확도를 높입니다.
                try:
                    product_price_temp = "가격을 찾을 수 없습니다."
                    # 1. 사용자께서 제공하신 정확한 선택자 시도 (최우선)
                    primary_price_locator = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div.ProductInfo__ProductHeaderWrapper-sc-pdgh6r-2.jUpShe > div > div > p')
                    if await primary_price_locator.count() > 0:
                        price_text = await primary_price_locator.first.inner_text(timeout=3000)
                        print(f"DEBUG 가격 추출 (primary): '{price_text}'")
                        match = re.search(r'\$?(\d+\.?\d*)', price_text)
                        if match:
                            product_price_temp = match.group(1).strip()
                        else:
                            product_price_temp = price_text.replace('$', '').strip() # 달러 기호 제거
                    
                    # 2. 일반적인 가격 선택자 시도 (폴백)
                    if product_price_temp == "가격을 찾을 수 없습니다.":
                        general_price_locator = page.locator('[class*="ProductInfo__Price"]')
                        if await general_price_locator.count() > 0:
                            price_text = await general_price_locator.first.inner_text(timeout=3000)
                            print(f"DEBUG 가격 추출 (general): '{price_text}'")
                            product_price_temp = price_text.replace('$', '').strip()

                    # 3. "Total Price:" 텍스트를 포함하는 요소 찾기 (폴백)
                    if product_price_temp == "가격을 찾을 수 없습니다.":
                        fallback_price_locator_text = page.locator(r'text=/Total Price: \$[0-9,.]+/i')
                        if await fallback_price_locator_text.count() > 0:
                            price_text = await fallback_price_locator_text.inner_text(timeout=3000)
                            print(f"DEBUG 가격 추출 (Total Price): '{price_text}'")
                            match = re.search(r'\$[0-9,.]+', price_text)
                            if match:
                                product_price_temp = match.group(0).replace('$', '').strip()
                            
                    # 4. 달러 기호와 숫자를 포함하는 일반적인 선택자 시도 (최종 폴백)
                    if product_price_temp == "가격을 찾을 수 없습니다.":
                        general_price_with_dollar_locator = page.locator(r'p:has-text("$")', has_text=re.compile(r'\$[0-9]+\.?[0-9]{0,2}'))
                        if await general_price_with_dollar_locator.count() > 0:
                            price_text = await general_price_with_dollar_locator.first.inner_text(timeout=3000)
                            print(f"DEBUG 가격 추출 (dollar locator): '{price_text}'")
                            match = re.search(r'\$?(\d+\.?\d*)', price_text)
                            if match:
                                product_price_temp = match.group(1).strip()
                except Exception as e:
                    print(f"제품 가격 추출 실패: {e}")

                # 제품 가격을 찾지 못했거나 0인 경우, 제품군별 하드코딩 가격으로 대체
                try:
                    price_float = float(product_price_temp) if product_price_temp != "가격을 찾을 수 없습니다." else 0.0
                except:
                    price_float = 0.0
                
                if product_price_temp == "가격을 찾을 수 없습니다." or price_float == 0.0:
                    estimated_price = get_category_price(product_data["제품군"])
                    product_data["제품_가격"] = f"{estimated_price:.2f}"
                    print(f"경고: 제품 가격을 찾을 수 없어 제품군 '{product_data['제품군']}'의 추정 가격 ${product_data['제품_가격']}로 대체했습니다.")
                else:
                    product_data["제품_가격"] = product_price_temp
                print(f"제품 가격: {product_data['제품_가격']}")

                # 매출 계산
                product_data["매출"] = calculate_revenue(product_data["판매량"], product_data["제품군"], product_data["제품_가격"])
                print(f"매출: ${product_data['매출']}")

                # 최종 추출된 정보를 JSON 형식으로 출력
                print(f"\n{'='*80}")
                print(f"✅ [{product_data['진행_여부']}] {product_data['제품명']}")
                print(f"{'='*80}")
                print(json.dumps(product_data, ensure_ascii=False, indent=2))
                print(f"{'='*80}\n")
                
                break # Success, so exit the proxy loop
            
            except Exception as e:
                    print(f"디버그 중 오류 발생 (프록시: {proxy}): {e}")
            finally:
                    if browser:
                        await browser.close()
            
            # If code reaches here, it means an error occurred, and it will try the next proxy.
        
async def main():
    test_url = "https://www.makeship.com/products/inky-cap-keychain-plushie"
    await debug_page_structure(test_url)

if __name__ == '__main__':
    # 테스트할 URL
    
    test_url = "https://www.makeship.com/products/satan-plush"
    
    asyncio.run(debug_page_structure(test_url))
