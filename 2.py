import json
import pandas as pd
import os
from datetime import datetime
import glob

def load_json_files():
    """현재 폴더의 한글 파일명 JSON 파일들을 로드"""
    # 한글 파일명을 가진 JSON 파일들을 명시적으로 지정
    korean_json_files = [
        '플러시.json',
        '키체인플러시.json', 
        '인기상품.json',
        '에나멜핀.json',
        '신상품.json',
        '출시예정.json',
        '점보플러시.json',
        '비닐피규어.json',
        '후디.json',
        '롱보이.json',
        '도우보이.json',
        '티셔츠.json',
        '니트_크루넥.json',
        '지난상품.json'
    ]
    
    # 실제 존재하는 파일들만 필터링
    json_files = [f for f in korean_json_files if os.path.exists(f)]
    all_data = []
    
    print(f"발견된 한글 JSON 파일: {len(json_files)}개")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # JSON 구조에 따라 제품 목록 추출
            if '제품_목록' in data:
                products = data['제품_목록']
                print(f"{json_file}: {len(products)}개 제품")
                all_data.extend(products)
            else:
                # 단일 제품 데이터인 경우
                print(f"{json_file}: 단일 제품")
                all_data.append(data)
                
        except Exception as e:
            print(f"{json_file} 로드 중 오류: {e}")
    
    return all_data, json_files

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
        '판매량',
        '달성률',
        '프로젝트_종료일',
        '배송_시작일'
    ]
    
    # 존재하는 컬럼만 선택
    available_columns = [col for col in column_order if col in df.columns]
    df = df[available_columns]
    
    # 엑셀 파일로 저장
    try:
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Products', index=False)
            
            # 워크시트 서식 설정
            worksheet = writer.sheets['Products']
            
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
                
                adjusted_width = min(max_length + 2, 50)  # 최대 50자로 제한
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