import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError
from playwright_stealth import stealth_sync
from datetime import datetime
import time

def find_missing_end_dates(excel_file_path="최종합본_수정_20250629_223209.xlsx"):
    """
    종료일이 누락된 행들을 찾는 함수
    """
    try:
        df = pd.read_excel(excel_file_path)
        print(f"엑셀 파일 로드 완료: {len(df)}행")
        
        # 종료일 컬럼 찾기
        end_date_col = None
        url_col = None
        
        for col in df.columns:
            if '종료일' in str(col):
                end_date_col = col
            elif 'URL' in str(col):
                url_col = col
        
        if end_date_col is None or url_col is None:
            print(f"종료일 컬럼: {end_date_col}, URL 컬럼: {url_col}")
            print("필요한 컬럼을 찾을 수 없습니다.")
            return []
        
        # 종료일이 누락되거나 문제가 있는 행들 찾기
        missing_urls = []
        for idx, row in df.iterrows():
            end_date = str(row[end_date_col]) if pd.notna(row[end_date_col]) else ""
            url = str(row[url_col]) if pd.notna(row[url_col]) else ""
            
            # 종료일이 없거나 기본값인 경우
            if not end_date or end_date in ["해당 없음", "종료일 없음", "nan", ""]:
                missing_urls.append((idx + 1, url))  # 1-based index
        
        print(f"종료일 누락된 행: {len(missing_urls)}개")
        return missing_urls
        
    except Exception as e:
        print(f"파일 읽기 중 오류: {e}")
        return []

def extract_end_date_only(page, url):
    """
    종료일만 추출하는 함수 - 개선된 버전
    """
    try:
        page.goto(url, wait_until='load', timeout=60000)
        page.wait_for_selector('[class*="ProductDetails__ProductTitle"]', timeout=30000)
    except Exception:
        print(f"페이지 로드 실패: {url}")
        return "페이지 로드 실패"

    # 종료일 추출 - 더 포괄적인 접근
    try:
        # 먼저 페이지의 모든 텍스트를 가져와서 분석
        page_text = page.locator('body').inner_text(timeout=5000)
        
        # 날짜 패턴 찾기 (다양한 형식)
        import re
        
        # 패턴들 - 더 포괄적으로 개선
        date_patterns = [
            r'Ends on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Ends on January 15, 2025"
            r'Ended:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',   # "Ended: January 15, 2025"
            r'Ends:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',    # "Ends: January 15, 2025"
            r'End Date:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', # "End Date: January 15, 2025"
            r'Campaign ends\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', # "Campaign ends January 15, 2025"
            r'Campaign ended\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', # "Campaign ended January 15, 2025"
            r'Ended on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Ended on January 15, 2025"
            r'Completed:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', # "Completed: January 15, 2025"
            r'Finished:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',  # "Finished: January 15, 2025"
            r'([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*[\-\—]\s*End', # "January 15, 2025 - End"
            r'([A-Za-z]+\s+\d{1,2},\s+\d{4})\s*[\-\—]\s*Ended', # "January 15, 2025 - Ended"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # 상태 확인 - 더 세분화된 종료 상태
        status_patterns = [
            (r'Campaign\s+ended\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', 1),  # 날짜 포함
            (r'Ended\s+on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', 1),  # 날짜 포함
            (r'Campaign\s+ended', 0),  # 일반 종료
            (r'This\s+campaign\s+has\s+ended', 0),
            (r'Campaign\s+complete', 0),
            (r'Sold\s+out', 0),
            (r'No\s+longer\s+available', 0),
            (r'Campaign\s+closed', 0),
        ]
        
        for pattern, has_date in status_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                if has_date and len(match.groups()) > 0:
                    return match.group(1).strip()  # 구체적 날짜 반환
                else:
                    return "캠페인 종료됨"
        
        # 진행 중인지 확인
        if re.search(r'days?\s+left', page_text, re.IGNORECASE):
            return "진행 중 (구체적 종료일 없음)"
        
        # 특정 DOM 요소에서 찾기
        selectors_to_try = [
            '[class*="countdown"]',
            '[class*="Countdown"]', 
            '[class*="timer"]',
            '[class*="Timer"]',
            '[class*="end-date"]',
            '[class*="EndDate"]',
            '[data-testid*="countdown"]',
            '[data-testid*="end"]'
        ]
        
        for selector in selectors_to_try:
            elements = page.locator(selector)
            if elements.count() > 0:
                text = elements.first.inner_text(timeout=3000)
                date_match = re.search(r'([A-Za-z]+\s+\d{1,2},\s+\d{4})', text)
                if date_match:
                    return date_match.group(1).strip()
        
        return "종료일 정보 없음"
        
    except Exception as e:
        return f"종료일 추출 중 오류: {str(e)[:50]}"

def fix_missing_end_dates(excel_file_path="최종합본_수정_20250629_223209.xlsx", max_urls=50):
    """
    종료일이 누락된 URL들을 다시 스크래핑해서 종료일을 업데이트하는 함수
    """
    missing_urls = find_missing_end_dates(excel_file_path)
    
    if not missing_urls:
        print("종료일이 누락된 행이 없습니다.")
        return
    
    print(f"총 {len(missing_urls)}개 URL 중 최대 {max_urls}개 처리합니다.")
    urls_to_process = missing_urls[:max_urls]
    
    # 엑셀 파일 다시 로드
    df = pd.read_excel(excel_file_path)
    
    # 종료일 컬럼 찾기
    end_date_col = None
    for col in df.columns:
        if '종료일' in str(col):
            end_date_col = col
            break
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        stealth_sync(context)
        page = context.new_page()
        
        updated_count = 0
        
        for row_idx, url in urls_to_process:
            print(f"처리 중: 행 {row_idx} - {url[:50]}...")
            
            end_date = extract_end_date_only(page, url)
            
            if end_date and end_date not in ["종료일 찾을 수 없음", "페이지 로드 실패"]:
                # DataFrame 업데이트 (0-based index)
                df.at[row_idx - 1, end_date_col] = end_date
                updated_count += 1
                print(f"  ✅ 업데이트: {end_date}")
            else:
                print(f"  ❌ 실패: {end_date}")
            
            # 요청 간 딜레이
            time.sleep(1)
        
        browser.close()
    
    if updated_count > 0:
        # 수정된 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"최종합본_종료일수정_{timestamp}.xlsx"
        df.to_excel(new_filename, index=False)
        print(f"\\n종료일 수정 완료! {updated_count}개 행이 업데이트되었습니다.")
        print(f"저장된 파일: {new_filename}")
    else:
        print("업데이트된 행이 없습니다.")

def fix_missing_end_dates_batch(excel_file_path="최종합본_수정_20250629_223209.xlsx", batch_size=100):
    """
    종료일이 누락된 URL들을 배치로 처리하는 함수 (안전한 대량 처리)
    """
    missing_urls = find_missing_end_dates(excel_file_path)
    
    if not missing_urls:
        print("종료일이 누락된 행이 없습니다.")
        return
    
    total_urls = len(missing_urls)
    print(f"총 {total_urls}개 URL을 배치 단위({batch_size}개씩)로 처리합니다.")
    
    # 엑셀 파일 다시 로드
    df = pd.read_excel(excel_file_path)
    
    # 종료일 컬럼 찾기
    end_date_col = None
    for col in df.columns:
        if '종료일' in str(col):
            end_date_col = col
            break
    
    total_updated = 0
    
    # 배치별로 처리
    for batch_num in range(0, total_urls, batch_size):
        batch_end = min(batch_num + batch_size, total_urls)
        batch_urls = missing_urls[batch_num:batch_end]
        
        print(f"\n=== 배치 {batch_num//batch_size + 1}: {batch_num + 1}~{batch_end}번째 URL 처리 ===")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            stealth_sync(context)
            page = context.new_page()
            
            batch_updated = 0
            
            for i, (row_idx, url) in enumerate(batch_urls, 1):
                current_num = batch_num + i
                print(f"[{current_num}/{total_urls}] 처리 중: 행 {row_idx} - {url[:50]}...")
                
                try:
                    end_date = extract_end_date_only(page, url)
                    
                    if end_date and end_date not in ["종료일 찾을 수 없음", "페이지 로드 실패", "종료일 정보 없음"]:
                        # DataFrame 업데이트 (0-based index)
                        df.at[row_idx - 1, end_date_col] = end_date
                        batch_updated += 1
                        total_updated += 1
                        print(f"  ✅ 업데이트: {end_date}")
                    else:
                        print(f"  ❌ 실패: {end_date}")
                    
                    # 요청 간 딜레이
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"  ❌ 오류: {str(e)[:50]}")
                    continue
            
            browser.close()
            
            print(f"배치 {batch_num//batch_size + 1} 완료: {batch_updated}개 업데이트")
            
            # 중간 저장 (배치마다)
            if batch_updated > 0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_filename = f"최종합본_종료일배치_{batch_num//batch_size + 1}_{timestamp}.xlsx"
                df.to_excel(temp_filename, index=False)
                print(f"중간 저장: {temp_filename}")
    
    # 최종 저장
    if total_updated > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"최종합본_종료일전체완료_{timestamp}.xlsx"
        df.to_excel(final_filename, index=False)
        print(f"\n🎉 전체 처리 완료! {total_updated}개 행이 업데이트되었습니다.")
        print(f"최종 파일: {final_filename}")
    else:
        print("업데이트된 행이 없습니다.")

if __name__ == "__main__":
    print("종료일 누락 문제 해결 도구")
    print("1: 누락된 종료일 확인만")
    print("2: 종료일 다시 스크래핑 (최대 50개)")
    print("3: 종료일 다시 스크래핑 (최대 10개 - 테스트용)")
    print("4: 모든 누락된 종료일 처리 (898개 전체)")
    print("5: 사용자 지정 개수로 처리")
    print("6: 배치 처리로 안전하게 전체 처리 (100개씩)")
    
    choice = input("선택 (1, 2, 3, 4, 5, 6): ")
    
    if choice == "1":
        missing_urls = find_missing_end_dates()
        if missing_urls:
            print("\\n누락된 종료일이 있는 행들:")
            for row_idx, url in missing_urls[:10]:  # 처음 10개만 표시
                print(f"행 {row_idx}: {url[:60]}...")
            if len(missing_urls) > 10:
                print(f"... 외 {len(missing_urls) - 10}개 더")
    
    elif choice == "2":
        fix_missing_end_dates(max_urls=50)
    
    elif choice == "3":
        fix_missing_end_dates(max_urls=10)
    
    elif choice == "4":
        print("⚠️ 898개 URL을 모두 처리합니다. 시간이 오래 걸릴 수 있습니다.")
        confirm = input("계속하시겠습니까? (y/n): ")
        if confirm.lower() == 'y':
            fix_missing_end_dates(max_urls=898)
        else:
            print("취소되었습니다.")
    
    elif choice == "5":
        try:
            max_count = int(input("처리할 URL 개수를 입력하세요: "))
            fix_missing_end_dates(max_urls=max_count)
        except ValueError:
            print("올바른 숫자를 입력해주세요.")
    
    elif choice == "6":
        print("⚠️ 898개 URL을 배치로 안전하게 처리합니다.")
        print("100개씩 처리하며, 각 배치마다 중간 저장됩니다.")
        confirm = input("계속하시겠습니까? (y/n): ")
        if confirm.lower() == 'y':
            fix_missing_end_dates_batch()
        else:
            print("취소되었습니다.")
    
    else:
        print("잘못된 선택입니다.")
