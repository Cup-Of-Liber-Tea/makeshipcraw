import json
import pandas as pd
import os
from datetime import datetime
import glob
import re

def load_json_files():
    """현재 폴더의 Makeship 관련 JSON 파일들을 로드"""
    # 'makeship_all_products_YYYYMMDD_HHMMSS.json' 패턴과 'makeship_[카테고리]_[타임스탬프].json' 패턴의 파일들을 모두 찾음
    json_files = glob.glob('makeship_all_products_*.json') + \
                 glob.glob('makeship_*_*.json') # 모든 makeship_로 시작하는 json 파일 포함 (카테고리별 파일 포함)
    
    # 중복 제거 및 정렬
    json_files = sorted(list(set(json_files)))

    all_data = []
    
    print(f"발견된 Makeship JSON 파일: {len(json_files)}개")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # JSON 구조에 따라 제품 목록 추출
            if '제품_목록' in data:
                products = data['제품_목록']
                print(f"{json_file}: {len(products)}개 제품")
            else:
                # 단일 제품 데이터인 경우 (과거 파일 형식 호환)
                print(f"{json_file}: 단일 제품 또는 알 수 없는 형식")
                products = [data]

            # 각 제품 데이터에 대해 형식 변환 적용
            for product in products:
                if '프로젝트_종료일' in product: # 프로젝트 종료일 날짜 형식 변환
                    product['프로젝트_종료일'] = normalize_date(product['프로젝트_종료일'])
                if '배송_시작일' in product: # 배송 시작일 날짜 형식 변환
                    product['배송_시작일'] = normalize_date(product['배송_시작일'])
                if '판매량' in product: # 판매량 숫자 형식 변환
                    product['판매량'] = convert_to_numeric(product['판매량'])
                if '달성률' in product: # 달성률 숫자 형식 변환
                    product['달성률'] = convert_to_numeric(product['달성률'])
                # 판매량이 0이면 매출도 0으로 처리
                if '판매량' in product and '매출' in product:
                    if product['판매량'] == 0:
                        product['매출'] = 0
            
            all_data.extend(products)
                
        except Exception as e:
            print(f"{json_file} 로드 중 오류: {e}")
    
    return all_data, json_files

def normalize_date(date_str):
    """
    다양한 날짜 문자열 형식을 'YYYY-MM-DD' 형식으로 변환합니다.
    - 'YYYY-MM-DD' (이미 정규화된 형식)
    - 'July 1, 5:00AM GMT+9 / Ships September 23, 2025'
    - 'September 17, 2022'
    - 'July 1, 2022'
    - '해당 없음'
    등을 처리할 수 있도록 개선합니다.
    """
    if not date_str or date_str in ['정보 없음', '해당 없음', '상태 확인 중 오류']:
        return date_str if date_str else '정보 없음'

    # 1. 이미 YYYY-MM-DD 형식인 경우 그대로 반환
    if isinstance(date_str, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str

    # 2. ' / ' 기준으로 나누어 프로젝트 종료일과 배송 시작일 분리
    parts = date_str.split(' / ')
    
    # 프로젝트 종료일 처리 (첫 번째 부분)
    project_end_date_part = parts[0].strip()
    try:
        # '5:00AM GMT+9'와 같은 시간/GMT 정보 제거
        project_end_date_clean = ' '.join(project_end_date_part.split(' ')[:3])
        # 'July 1, 2022' 형식 파싱
        dt_object = datetime.strptime(project_end_date_clean.replace(',', ''), '%B %d %Y')
        return dt_object.strftime('%Y-%m-%d')
    except ValueError:
        pass # 파싱 실패 시 다음 형식 시도

    # 3. 'Ships September 23, 2025' 같은 형식 처리
    if 'Ships ' in date_str:
        ship_date_part = date_str.split('Ships ')[-1].strip()
        try:
            # 'September 23, 2025' 형식 파싱
            dt_object = datetime.strptime(ship_date_part.replace(',', ''), '%B %d %Y')
            return dt_object.strftime('%Y-%m-%d')
        except ValueError:
            pass # 파싱 실패 시 다음 형식 시도
    
    # 4. Fallback: 일반적인 날짜 형식 시도
    try:
        dt_object = datetime.strptime(date_str.replace(',', ''), '%B %d %Y')
        return dt_object.strftime('%Y-%m-%d')
    except ValueError:
        # 변환 실패 시 원본 반환
        return date_str

def convert_to_numeric(value_str):
    """문자열에서 숫자만 추출하여 정수 또는 실수로 변환합니다."""
    # 이미 숫자인 경우 그대로 반환
    if isinstance(value_str, (int, float)):
        return value_str
    
    if not value_str or value_str == '정보 없음':
        return 0
    
    # 문자열이 아닌 경우 0 반환
    if not isinstance(value_str, str):
        return 0

    clean_value = value_str.replace(',', '').replace(' sold', '').strip()
    try:
        # 달성률 (%)가 포함된 경우
        if '%' in clean_value:
            return float(clean_value.replace('%', ''))
        else:
            # 정수 또는 실수로 변환 시도
            if '.' in clean_value:
                return float(clean_value)
            else:
                return int(clean_value)
    except ValueError:
        return 0

def remove_duplicates_by_url(products):
    """제품 URL로 중복 제거 (최신 데이터 유지)"""
    unique_products = {}
    
    for product in products:
        url = product.get('제품_URL', '')
        if url:
            # 동일한 URL이 있으면 덮어쓰기 (최신 데이터 유지)
            unique_products[url] = product
    
    return list(unique_products.values())

def create_excel_from_products(products, filename):
    """제품 데이터를 엑셀 파일로 생성"""
    if not products:
        print(f"데이터가 없어서 {filename} 파일을 생성할 수 없습니다.")
        return
    
    # 데이터프레임 생성
    df = pd.DataFrame(products)
    
    # 컬럼 순서 정리
    column_order = [
        '제품_URL',
        '진행_여부', 
        '제품군',
        '제품명',
        'IP명',
        'IP_소개_링크',
        '제품_가격',
        '판매량',
        '달성률',
        '매출',
        '프로젝트_종료일',
        '배송_시작일'
    ]
    
    # 존재하는 컬럼만 선택
    available_columns = [col for col in column_order if col in df.columns]
    df = df[available_columns]

    # 숫자형 컬럼 타입 확인 및 변환
    for col in ['판매량', '달성률', '매출']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 제품 가격도 숫자로 변환
    if '제품_가격' in df.columns:
        df['제품_가격'] = pd.to_numeric(df['제품_가격'], errors='coerce').fillna(0)

    # 날짜 컬럼을 datetime 객체로 변환
    for col in ['프로젝트_종료일', '배송_시작일']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce', format='%Y-%m-%d')
    
    # 엑셀 파일로 저장
    try:
        from openpyxl.styles import numbers
        
        with pd.ExcelWriter(filename, engine='openpyxl', datetime_format='yyyy-mm-dd') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # 워크시트 서식 설정
            worksheet = writer.sheets['Products']
            
            # 컬럼별 형식 지정
            for idx, col in enumerate(df.columns, start=1):
                col_letter = worksheet.cell(row=1, column=idx).column_letter
                
                # 숫자 형식 지정
                if col in ['판매량', '매출']:
                    for row in range(2, len(df) + 2):
                        cell = worksheet.cell(row=row, column=idx)
                        cell.number_format = '#,##0'  # 천단위 구분 정수
                
                elif col == '달성률':
                    for row in range(2, len(df) + 2):
                        cell = worksheet.cell(row=row, column=idx)
                        cell.number_format = '0.0"%"'  # 소수점 첫째자리 + %
                
                elif col == '제품_가격':
                    for row in range(2, len(df) + 2):
                        cell = worksheet.cell(row=row, column=idx)
                        cell.number_format = '$#,##0.00'  # 달러 형식
                
                # 날짜 형식 지정
                elif col in ['프로젝트_종료일', '배송_시작일']:
                    for row in range(2, len(df) + 2):
                        cell = worksheet.cell(row=row, column=idx)
                        cell.number_format = 'yyyy-mm-dd'
            
            # 컬럼 너비 자동 조정
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"✅ {filename} 생성 완료 ({len(df)}개 제품)")
        
    except Exception as e:
        print(f"❌ {filename} 생성 중 오류: {e}")

def create_individual_excel_files(json_files):
    """각 JSON 파일별로 개별 엑셀 파일 생성"""
    print("\n=== 개별 엑셀 파일 생성 ===")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 제품 데이터 추출
            if '제품_목록' in data:
                products = data['제품_목록']
            else:
                products = [data]
            
            # 각 제품 데이터에 대해 형식 변환 적용
            for product in products:
                if '프로젝트_종료일' in product:
                    product['프로젝트_종료일'] = normalize_date(product['프로젝트_종료일'])
                if '배송_시작일' in product:
                    product['배송_시작일'] = normalize_date(product['배송_시작일'])
                if '판매량' in product:
                    product['판매량'] = convert_to_numeric(product['판매량'])
                if '달성률' in product:
                    product['달성률'] = convert_to_numeric(product['달성률'])
                # 판매량이 0이면 매출도 0으로 처리
                if '판매량' in product and '매출' in product:
                    if product['판매량'] == 0:
                        product['매출'] = 0
            
            # 엑셀 파일명 생성
            excel_filename = json_file.replace('.json', '.xlsx')
            
            # 엑셀 파일 생성
            create_excel_from_products(products, excel_filename)
            
        except Exception as e:
            print(f"❌ {json_file} 처리 중 오류: {e}")

def main():
    print("=== Makeship JSON to Excel 변환기 ===")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. JSON 파일들 로드
    print("\n1. JSON 파일 로드 중...")
    all_products, json_files = load_json_files()
    
    if not all_products:
        print("❌ 변환할 데이터가 없습니다.")
        return
    
    print(f"총 {len(all_products)}개 제품 데이터 로드 완료")
    
    # 2. 중복 제거
    print("\n2. 중복 제거 중...")
    unique_products = remove_duplicates_by_url(all_products)
    removed_count = len(all_products) - len(unique_products)
    print(f"중복 제거 완료: {removed_count}개 중복 제거, {len(unique_products)}개 고유 제품")
    
    # 3. 통합 엑셀 파일 생성
    print("\n3. 통합 엑셀 파일 생성 중...")
    integrated_filename = f"makeship_integrated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    create_excel_from_products(unique_products, integrated_filename)
    
    # 4. 개별 엑셀 파일 생성
    print("\n4. 개별 엑셀 파일 생성 중...")
    create_individual_excel_files(json_files)
    
    # 5. 완료 보고
    print(f"\n=== 변환 완료 ===")
    print(f"📊 통합 엑셀: {integrated_filename}")
    print(f"📁 개별 엑셀: {len(json_files)}개 파일")
    print(f"🔢 총 제품 수: {len(unique_products)}개 (중복 제거 후)")

if __name__ == '__main__':
    main() 