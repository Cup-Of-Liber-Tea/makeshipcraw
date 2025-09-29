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
        if not sales_volume or sales_volume in ["판매량 정보를 찾을 수 없습니다.", "Sold Out"]:
            return 0.0
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
                print(f"제품군 '{category}' 하드코딩 가격 사용: ${actual_price}")

            if sales_volume == "Sold Out":
                estimated_price = get_category_price(category)
                revenue = sales_count * (estimated_price * 1000) # 추정 가격에 1000을 곱하여 매출 계산
                print(f"판매량이 'Sold Out'일 경우, 제품군 '{category}'의 추정 가격 ${estimated_price}에 1000을 곱하여 매출을 계산했습니다.")
                return round(revenue, 2)

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
        funded_pattern = r'([0-9,]+%)\s+Funded'
        funded_match = re.search(funded_pattern, funded_raw_text, re.IGNORECASE)
        if funded_match:
            processed_rate = funded_match.group(1).replace(',', '')
        elif "Sold Out" in funded_raw_text:
            processed_rate = "Sold Out"

    # 3. 판매량 기반 달성률 계산 (X of Y sold -> X/Y 비율)
    if processed_sales != "판매량 정보를 찾을 수 없습니다." and processed_sales != "Sold Out" and "of" in sales_raw_text:
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
                try:
                    category_locator = page.locator('[class*="ProductInfo__ProductHeaderWrapper"] a[href*="/shop/"] p, [class*="ProductInfo__ProductHeaderWrapper"] a[href*="/collections/"] p').first
                    if await category_locator.count() > 0:
                        product_data["제품군"] = await category_locator.inner_text(timeout=3000)
                    print(f"제품군: {product_data['제품군']}")
                except Exception as e:
                    print(f"제품군 추출 실패: {e}")

                # --- 프로젝트 종료일 및 진행 여부 ---
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
                
                # 배송 시작일
                try:
                    shipping_date = "배송 시작일 정보를 찾을 수 없습니다."
                    primary_shipping_date_locator = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div.ProductInfo__PostPurchaseDetailsWrapper-sc-pdgh6r-9.jthCJt > div > div > p')
                    if await primary_shipping_date_locator.count() > 0:
                        shipping_date_text = await primary_shipping_date_locator.inner_text(timeout=3000)
                        shipping_date = shipping_date_text.replace('Ships ', '').strip()
                    if shipping_date == "배송 시작일 정보를 찾을 수 없습니다.":
                        fallback_shipping_date_locator = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div.commonFunctions__HybridMessagingContainer-sc-e97hvy-8.gpFhIO')
                        if await fallback_shipping_date_locator.count() > 0:
                            shipping_date_text = await fallback_shipping_date_locator.inner_text(timeout=3000)
                            shipping_date = shipping_date_text.replace('Ships ', '').strip()
                    product_data["배송_시작일"] = normalize_date(shipping_date)
                    print(f"배송 시작일: {product_data['배송_시작일']}")
                except Exception as e:
                    print(f"배송 시작일 추출 실패: {e}")

                # IP 소개 링크
                try:
                    ip_link_elements = page.locator('[class*="CreatorMessage__CreatorMessageWrapper"] a')
                    if await ip_link_elements.count() > 0:
                        ip_link = await ip_link_elements.first.get_attribute('href', timeout=3000)
                        if ip_link and ip_link.startswith('/'):
                            ip_link = f"https://www.makeship.com{ip_link}"
                        product_data["IP_소개_링크"] = ip_link
                    print(f"IP 소개 링크: {product_data['IP_소개_링크']}")
                except Exception as e:
                    print(f"IP 소개 링크 추출 실패: {e}")

                # 제품 가격
                product_price_temp = "가격을 찾을 수 없습니다."
                try:
                    # 1. 기존의 primary_price_locator (nth-child(5) 버전) 시도
                    if product_price_temp == "가격을 찾을 수 없습니다.":
                        old_primary_price_locator = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div:nth-child(5) > div > div > div > div.CompleteCollectionComponent__CompleteCollectionDetailRow-sc-pxn9vj-13.ffmDLt > div.CompleteCollectionComponent__TotalPriceWrapper-sc-pxn9vj-19.cDyXqm > div > p > font:nth-child(2) > font:nth-child(1)')
                        if await old_primary_price_locator.count() > 0:
                            product_price_temp = (await old_primary_price_locator.inner_text(timeout=3000)).replace('$', '').strip()
                        
                    # 2. 사용자께서 요청하신 새로운 선택자 1 (`.ProductDetails__ProductDetailsWrapper... > p`) 시도
                    if product_price_temp == "가격을 찾을 수 없습니다.":
                        new_price_locator_1 = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div.ProductDetails__ProductDetailsWrapper-sc-1r20xdj-0.bUehNf > div > p')
                        if await new_price_locator_1.count() > 0:
                            product_price_temp = (await new_price_locator_1.inner_text(timeout=3000)).replace('$', '').strip()
                    
                    # 3. 사용자께서 요청하신 새로운 선택자 2 (`.ProductInfo__ProductHeaderWrapper... > div > p`) 시도
                    if product_price_temp == "가격을 찾을 수 없습니다.":
                        new_price_locator_2 = page.locator('#__next > div._app__ContainerWrapper-sc-meusgd-0.fdDSJw > div > div._app__ContentWrapper-sc-meusgd-2.iURiPk > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.kYqEeP > div > div.ProductInfo__ProductHeaderWrapper-sc-pdgh6r-2.jUpShe > div > div > p')
                        if await new_price_locator_2.count() > 0:
                            product_price_temp = (await new_price_locator_2.inner_text(timeout=3000)).replace('$', '').strip()

                    # 4. "Total Price:" 텍스트를 포함하는 요소 찾기
                    if product_price_temp == "가격을 찾을 수 없습니다.":
                        fallback_price_locator_text = page.locator(r'text=/Total Price: \$[0-9,.]+/i')
                        if await fallback_price_locator_text.count() > 0:
                            price_text = await fallback_price_locator_text.inner_text(timeout=3000)
                            match = re.search(r'\$[0-9,.]+', price_text)
                            if match:
                                product_price_temp = match.group(0).replace('$', '').strip()
                            
                    # 5. 일반적인 가격 선택자 시도
                    if product_price_temp == "가격을 찾을 수 없습니다.":
                        general_price_locator = page.locator('[class*="ProductInfo__Price"]')
                        if await general_price_locator.count() > 0:
                            product_price_temp = (await general_price_locator.inner_text(timeout=3000)).replace('$', '').strip()
                except Exception as e:
                    print(f"제품 가격 추출 실패: {e}")

                if product_price_temp == "가격을 찾을 수 없습니다.":
                    estimated_price = get_category_price(product_data["제품군"])
                    product_data["제품_가격"] = f"{estimated_price:.2f}"
                    print(f"경고: 제품 가격을 찾을 수 없어 제품군 '{product_data['제품군']}'의 추정 가격 ${product_data['제품_가격']}로 대체했습니다.")
                else:
                    product_data["제품_가격"] = product_price_temp
                print(f"제품 가격: {product_data['제품_가격']}")

                # 매출 계산
                product_data["매출"] = calculate_revenue(product_data["판매량"], product_data["제품군"], product_data["제품_가격"])
                print(f"매출: ${product_data['매출']}")

                print("\n--- 최종 추출된 정보 ---")
                for key, value in product_data.items():
                    print(f"{key}: {value}")
                
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
    # test_url = "https://www.makeship.com/products/inky-cap-keychain-plushie"
    test_url = "https://www.makeship.com/products/a-date-with-death-grim-reaper-hoodie"
    # test_url = "https://www.makeship.com/products/absolute-cinema-plushie"
    asyncio.run(debug_page_structure(test_url))
