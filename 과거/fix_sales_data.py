import re
import pandas as pd
from datetime import datetime

def process_sales_data(sales_volume, funded_rate):
    """
    의뢰인 요구사항에 맞게 판매량과 달성률 데이터를 처리하는 함수
    
    1. 판매량: "1000 of 1000 sold" -> 판매량: 1000, 달성률: "1000 of 1000 sold"
    2. 단위 제거: "716 sold" -> "716", "143% Funded" -> "143%"
    """
    processed_sales = sales_volume
    processed_rate = funded_rate
    
    # 1. "X of Y sold" 패턴 처리 (콤마 포함)
    sold_pattern = r'([0-9,]+)\s+of\s+([0-9,]+)\s+sold'
    sold_match = re.search(sold_pattern, sales_volume, re.IGNORECASE)
    
    if sold_match:
        sold_count = sold_match.group(1).replace(',', '')  # 콤마 제거
        total_count = sold_match.group(2).replace(',', '')  # 콤마 제거
        processed_sales = sold_count
        processed_rate = f"{sold_count} of {total_count} sold"
        return processed_sales, processed_rate
    
    # 2. 일반적인 판매량 처리 ("716 sold" -> "716", 콤마 포함)
    sold_only_pattern = r'([0-9,]+)\s+sold'
    sold_only_match = re.search(sold_only_pattern, sales_volume, re.IGNORECASE)
    
    if sold_only_match:
        processed_sales = sold_only_match.group(1).replace(',', '')  # 콤마 제거
    
    # 3. 달성률 처리 ("143% Funded" -> "143%", 콤마 포함)
    funded_pattern = r'([0-9,]+%)\s+Funded'
    funded_match = re.search(funded_pattern, funded_rate, re.IGNORECASE)
    
    if funded_match:
        processed_rate = funded_match.group(1).replace(',', '')  # 콤마 제거
    
    return processed_sales, processed_rate

def extract_product_data_fixed(page, url):
    """수정된 제품 데이터 추출 함수"""
    try:
        page.goto(url, wait_until='load', timeout=60000)
        page.wait_for_selector('[class*="ProductDetails__ProductTitle"]', timeout=30000)
    except Exception:
        print(f"페이지 로드 실패: {url}")
        return None

    # 기본 정보 추출
    try:
        product_name = page.locator('[class*="ProductDetails__ProductTitle"]').inner_text(timeout=3000)
    except:
        product_name = "제품명 없음"

    try:
        ip_name_element = page.locator('a:has-text("By:")')
        ip_name_text = ip_name_element.inner_text(timeout=3000)
        ip_name = ip_name_text.replace('By: ', '').strip()
    except:
        ip_name = "IP명 없음"

    try:
        category = page.locator('[class*="ProductInfo__ProductHeaderWrapper"] a[href*="/shop/"] p, [class*="ProductInfo__ProductHeaderWrapper"] a[href*="/collections/"] p').first.inner_text(timeout=3000)
    except:
        category = "제품군 없음"

    # 판매량 추출 (여러 패턴 시도)
    sales_volume = "판매량 없음"
    try:
        # 패턴 1: "X of Y sold"
        sold_pattern_locator = page.locator('p:has-text("of"), p:has-text("sold")')
        if sold_pattern_locator.count() > 0:
            sales_volume = sold_pattern_locator.first.inner_text(timeout=3000)
        else:
            # 패턴 2: 일반 sold 텍스트
            sales_locator = page.locator('p:has-text("sold")')
            if sales_locator.count() > 0:
                sales_volume = sales_locator.first.inner_text(timeout=3000)
    except:
        pass

    # 달성률 추출
    funded_rate = "달성률 없음"
    try:
        funded_locator = page.locator('p:has-text("% Funded"), p:has-text("Funded")')
        if funded_locator.count() > 0:
            funded_rate = funded_locator.first.inner_text(timeout=3000)
    except:
        pass

    # 데이터 처리
    processed_sales, processed_rate = process_sales_data(sales_volume, funded_rate)

    # 종료일 추출 (여러 패턴 시도)
    end_date = "종료일 없음"
    status = "상태 불명"
    
    try:
        # 패턴 1: 기존 카운트다운 날짜
        end_date_element = page.locator('[class*="ProductPageCountdown__CountdownDate"]')
        if end_date_element.count() > 0:
            end_date_text = end_date_element.inner_text(timeout=3000)
            end_date = end_date_text.replace('Ends on ', '').strip()
            status = "진행 중"
        else:
            # 패턴 2: 새로운 셀렉터 시도
            specific_selector = page.locator('#__next > div._app__ContainerWrapper-meusgd-0.kPTMSg > div > div._app__ContentWrapper-meusgd-2.hIhdAc > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.bstoHm > div > div:nth-child(3) > div > p')
            if specific_selector.count() > 0:
                end_date_text = specific_selector.inner_text(timeout=3000)
                # "Ends on" 텍스트 제거하고 날짜만 추출
                if "ends on" in end_date_text.lower() or "ends" in end_date_text.lower():
                    end_date = end_date_text.replace('Ends on ', '').replace('ends on ', '').replace('Ends ', '').replace('ends ', '').strip()
                    status = "진행 중"
                else:
                    end_date = end_date_text.strip()
                    status = "진행 중"
            else:
                # 패턴 3: 정확한 날짜 패턴 검색
                try:
                    # 페이지 전체 텍스트에서 정확한 날짜 패턴 찾기
                    page_text = page.locator('body').inner_text(timeout=5000)
                    
                    import re
                    # 정확한 종료일 패턴들
                    date_patterns = [
                        r'Ends on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Ends on January 15, 2025"
                        r'Campaign ends\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Campaign ends January 15, 2025"
                        r'End Date:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "End Date: January 15, 2025"
                        r'Funding ends\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Funding ends January 15, 2025"
                        r'Available until\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Available until January 15, 2025"
                    ]
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, page_text, re.IGNORECASE)
                        if match:
                            end_date = match.group(1).strip()
                            status = "진행 중"
                            break
                    
                    # 만약 위 패턴으로 찾지 못했다면, 종료 상태 확인
                    if end_date == "종료일 없음":
                        if re.search(r'Campaign\s+(ended|complete|closed)', page_text, re.IGNORECASE):
                            end_date = "캠페인 종료됨"
                            status = "종료"
                        elif re.search(r'Sold\s+out', page_text, re.IGNORECASE):
                            end_date = "품절"
                            status = "종료"
                        elif re.search(r'No longer available', page_text, re.IGNORECASE):
                            end_date = "판매 종료"
                            status = "종료"
                        else:
                            end_date = "해당 없음"
                            status = "종료"
                except:
                    end_date = "해당 없음"
                    status = "종료"
    except Exception as e:
        print(f"종료일 추출 중 오류: {e}")
        end_date = "종료일 없음"
        status = "상태 불명"

    try:
        shipping_date = page.locator('[class*="commonFunctions__ShipDateText"]').inner_text(timeout=3000)
    except:
        shipping_date = "배송일 없음"

    try:
        ip_link_elements = page.locator('[class*="CreatorMessage__CreatorMessageWrapper"] a')
        if ip_link_elements.count() > 0:
            ip_link = ip_link_elements.first.get_attribute('href', timeout=3000)
            if ip_link and ip_link.startswith('/'):
                ip_link = f"https://www.makeship.com{ip_link}"
        else:
            ip_link = "IP 링크 없음"
    except:
        ip_link = "IP 링크 없음"

    return {
        "제품_URL": url,
        "진행_여부": status,
        "제품군": category,
        "제품명": product_name,
        "IP명": ip_name,
        "IP_소개_링크": ip_link,
        "판매량": processed_sales,
        "달성률": processed_rate,
        "프로젝트_종료일": end_date,
        "배송_시작일": shipping_date
    }

# 테스트
if __name__ == "__main__":
    # 테스트 케이스
    test_cases = [
        ("1000 of 1000 sold", "달성률 없음"),
        ("716 sold", "143% Funded"),
        ("500 of 750 sold", "67% Funded"),
        ("완판", "100% Funded")
    ]
    
    for sales, rate in test_cases:
        processed_sales, processed_rate = process_sales_data(sales, rate)
        print(f"원본: {sales} | {rate}")
        print(f"처리: {processed_sales} | {processed_rate}")
        print("---")

def fix_excel_sales_data(excel_file_path="최종합본.xlsx"):
    """
    기존 엑셀 파일의 판매량/달성률 컬럼을 수정하는 함수
    """
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(excel_file_path)
        print(f"엑셀 파일 로드 완료: {len(df)}행")
        
        # 컬럼명 확인
        print("컬럼명:", df.columns.tolist())
        
        # 판매량과 달성률 컬럼이 있는지 확인
        sales_col = None
        rate_col = None
        
        for col in df.columns:
            if '판매량' in str(col):
                sales_col = col
            elif '달성률' in str(col):
                rate_col = col
        
        if sales_col is None or rate_col is None:
            print(f"판매량 컬럼: {sales_col}, 달성률 컬럼: {rate_col}")
            print("필요한 컬럼을 찾을 수 없습니다.")
            return
        
        print(f"수정할 컬럼 - 판매량: {sales_col}, 달성률: {rate_col}")
        
        # 데이터 수정
        modified_count = 0
        for idx, row in df.iterrows():
            original_sales = str(row[sales_col]) if pd.notna(row[sales_col]) else ""
            original_rate = str(row[rate_col]) if pd.notna(row[rate_col]) else ""
            
            if original_sales and original_rate:
                processed_sales, processed_rate = process_sales_data(original_sales, original_rate)
                
                # 수정이 필요한 경우만 업데이트
                if processed_sales != original_sales or processed_rate != original_rate:
                    df.at[idx, sales_col] = processed_sales
                    df.at[idx, rate_col] = processed_rate
                    modified_count += 1
                    print(f"행 {idx+1} 수정: {original_sales} -> {processed_sales}, {original_rate} -> {processed_rate}")
        
        if modified_count > 0:
            # 수정된 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"최종합본_수정_{timestamp}.xlsx"
            df.to_excel(new_filename, index=False)
            print(f"\n수정 완료! {modified_count}개 행이 수정되었습니다.")
            print(f"저장된 파일: {new_filename}")
        else:
            print("수정할 데이터가 없습니다.")
            
    except Exception as e:
        print(f"엑셀 처리 중 오류: {e}")

if __name__ == "__main__":
    # 선택: 테스트만 실행하려면 1, 엑셀 수정하려면 2
    choice = input("1: 테스트 실행, 2: 엑셀 수정 (1 또는 2): ")
    
    if choice == "1":
        # 테스트 케이스 실행
        test_cases = [
            ("1000 of 1000 sold", "달성률 없음"),
            ("716 sold", "143% Funded"),
            ("500 of 750 sold", "67% Funded"),
            ("완판", "100% Funded")
        ]
        
        for sales, rate in test_cases:
            processed_sales, processed_rate = process_sales_data(sales, rate)
            print(f"원본: {sales} | {rate}")
            print(f"처리: {processed_sales} | {processed_rate}")
            print("---")
    
    elif choice == "2":
        # 엑셀 파일 수정
        fix_excel_sales_data()
    
    else:
        print("잘못된 선택입니다.")

def fix_missing_end_dates(excel_file_path="최종합본_수정_20250629_223209.xlsx", max_urls=50):
    """
    종료일이 누락된 행들을 찾아서 다시 스크래핑하는 함수
    """
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync
    
    try:
        # 엑셀 파일 읽기
        df = pd.read_excel(excel_file_path)
        print(f"엑셀 파일 로드 완료: {len(df)}행")
        
        # 종료일이 누락된 행 찾기
        missing_end_dates = df[
            (df['프로젝트_종료일'].isna()) | 
            (df['프로젝트_종료일'] == '') |
            (df['프로젝트_종료일'] == '해당 없음') |
            (df['프로젝트_종료일'] == '종료일 없음') |
            (df['프로젝트_종료일'].astype(str).str.contains('찾을 수 없습니다', na=False))
        ]
        
        print(f"종료일이 누락된 행: {len(missing_end_dates)}개")
        
        if len(missing_end_dates) == 0:
            print("종료일이 누락된 행이 없습니다.")
            return
        
        # 처리할 URL 수 제한
        urls_to_process = missing_end_dates['제품_URL'].head(max_urls).tolist()
        print(f"처리할 URL: {len(urls_to_process)}개")
        
        # Playwright로 종료일 다시 추출
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            stealth_sync(page)
            
            updated_count = 0
            
            for i, url in enumerate(urls_to_process, 1):
                print(f"[{i}/{len(urls_to_process)}] 처리 중: {url}")
                
                try:
                    # 페이지 로드
                    page.goto(url, wait_until='load', timeout=30000)
                    page.wait_for_timeout(2000)  # 2초 대기
                    
                    # 종료일 추출 (개선된 로직 사용)
                    end_date = "종료일 정보 없음"
                    
                    # 패턴 1: 기존 카운트다운 날짜
                    try:
                        end_date_element = page.locator('[class*="ProductPageCountdown__CountdownDate"]')
                        if end_date_element.count() > 0:
                            end_date_text = end_date_element.inner_text(timeout=3000)
                            end_date = end_date_text.replace('Ends on ', '').strip()
                    except:
                        pass
                    
                    # 패턴 2: 새로운 셀렉터
                    if end_date == "종료일 정보 없음":
                        try:
                            specific_selector = page.locator('#__next > div._app__ContainerWrapper-meusgd-0.kPTMSg > div > div._app__ContentWrapper-meusgd-2.hIhdAc > div > div > div.handle__ProductInfoWrapper-sc-1y81hk8-2.bstoHm > div > div:nth-child(3) > div > p')
                            if specific_selector.count() > 0:
                                end_date_text = specific_selector.inner_text(timeout=3000)
                                if any(keyword in end_date_text.lower() for keyword in ['ends', 'end', '2024', '2025']):
                                    end_date = end_date_text.replace('Ends on ', '').replace('ends on ', '').replace('Ends ', '').replace('ends ', '').strip()
                        except:
                            pass
                    
                    # 패턴 3: 정확한 날짜 패턴만 찾기
                    if end_date == "종료일 정보 없음":
                        try:
                            # 페이지 전체 텍스트에서 정확한 날짜 패턴 찾기
                            page_text = page.locator('body').inner_text(timeout=5000)
                            
                            import re
                            # 정확한 종료일 패턴들
                            date_patterns = [
                                r'Ends on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Ends on January 15, 2025"
                                r'Campaign ends\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Campaign ends January 15, 2025"
                                r'End Date:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "End Date: January 15, 2025"
                                r'Funding ends\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Funding ends January 15, 2025"
                                r'Available until\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Available until January 15, 2025"
                            ]
                            
                            for pattern in date_patterns:
                                match = re.search(pattern, page_text, re.IGNORECASE)
                                if match:
                                    end_date = match.group(1).strip()
                                    break
                            
                            # 만약 위 패턴으로 찾지 못했다면, 종료 상태 확인
                            if end_date == "종료일 정보 없음":
                                # 캠페인 종료 키워드 찾기
                                if re.search(r'Campaign\s+(ended|complete|closed)', page_text, re.IGNORECASE):
                                    end_date = "캠페인 종료됨"
                                elif re.search(r'Sold\s+out', page_text, re.IGNORECASE):
                                    end_date = "품절"
                                elif re.search(r'No longer available', page_text, re.IGNORECASE):
                                    end_date = "판매 종료"
                        except:
                            pass
                    
                    # 엑셀에서 해당 행 업데이트
                    row_index = df[df['제품_URL'] == url].index[0]
                    if end_date != "종료일 정보 없음":
                        df.at[row_index, '프로젝트_종료일'] = end_date
                        updated_count += 1
                        print(f"  → 종료일 업데이트: {end_date}")
                    else:
                        print(f"  → 종료일 정보 없음")
                        
                except Exception as e:
                    print(f"  → 오류: {e}")
                    continue
            
            browser.close()
        
        # 업데이트된 파일 저장
        if updated_count > 0:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"최종합본_종료일보완_{timestamp}.xlsx"
            df.to_excel(new_filename, index=False)
            print(f"\n종료일 보완 완료! {updated_count}개 행이 업데이트되었습니다.")
            print(f"저장된 파일: {new_filename}")
        else:
            print("업데이트된 종료일이 없습니다.")
            
    except Exception as e:
        print(f"종료일 보완 중 오류: {e}")

if __name__ == "__main__":
    # 선택: 테스트(1), 엑셀 수정(2), 종료일 보완(3)
    choice = input("1: 테스트 실행, 2: 엑셀 수정, 3: 종료일 보완 (1, 2, 또는 3): ")
    
    if choice == "1":
        # 테스트 케이스 실행
        test_cases = [
            ("1000 of 1000 sold", "달성률 없음"),
            ("716 sold", "143% Funded"),
            ("500 of 750 sold", "67% Funded"),
            ("완판", "100% Funded")
        ]
        
        for sales, rate in test_cases:
            processed_sales, processed_rate = process_sales_data(sales, rate)
            print(f"원본: {sales} | {rate}")
            print(f"처리: {processed_sales} | {processed_rate}")
            print("---")
    
    elif choice == "2":
        # 엑셀 파일 수정
        fix_excel_sales_data()
    
    elif choice == "3":
        # 종료일 보완
        max_urls = int(input("처리할 최대 URL 수 (기본값 50): ") or "50")
        fix_missing_end_dates(max_urls=max_urls)
    
    else:
        print("잘못된 선택입니다.")
