import json

# 한국어 -> 영어 카테고리 매핑
CATEGORY_TRANSLATION = {
    "후디": "hoodies",
    "니트 크루넥": "knitted crewnecks",
    "티셔츠": "t-shirts",
    "에나멜 핀": "enamel pins",
    "비닐 피규어": "vinyl figures",
    "비닐피규어": "vinyl figures",
    "플러시": "plushies",
    "롱보이": "longbois",
    "도우보이": "doughbois",
    "점보 플러시": "jumbo plushies",
    "점보플러시": "jumbo plushies",
    "키체인 플러시": "keychain plushies",
    "키체인플러시": "keychain plushies",
    "스웨트팬츠": "sweatpants",
    "볼 캡": "ball cap"
}

def load_category_mapping(reference_file):
    """참고 파일에서 URL별 카테고리 매핑 생성 (영어로 변환)"""
    with open(reference_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    url_to_category = {}
    
    for category, urls in data.items():
        # 한국어 카테고리를 영어로 변환
        english_category = CATEGORY_TRANSLATION.get(category, category)
        
        for url in urls:
            url_to_category[url] = english_category
    
    print(f"참고 파일에서 {len(url_to_category)}개 URL의 카테고리 매핑 로드 완료")
    return url_to_category

def fix_visit_categories(target_file, reference_file, output_file):
    """Visit 또는 정보 없음 카테고리를 참고 파일 기준으로 수정"""
    
    # 참고 파일에서 URL-카테고리 매핑 로드
    url_to_category = load_category_mapping(reference_file)
    
    # 대상 파일 로드
    with open(target_file, 'r', encoding='utf-8') as f:
        target_data = json.load(f)
    
    products = target_data.get('제품_목록', [])
    
    fixed_count = 0
    not_found_count = 0
    not_found_urls = []
    
    for product in products:
        current_category = product.get('제품군')
        
        # Visit 또는 정보 없음인 경우 수정 시도
        if current_category in ['Visit', '정보 없음']:
            url = product.get('제품_URL')
            
            if url in url_to_category:
                original_category = product['제품군']
                product['제품군'] = url_to_category[url]
                fixed_count += 1
                print(f"✅ 수정: {url}")
                print(f"   {original_category} → {product['제품군']}")
            else:
                not_found_count += 1
                not_found_urls.append(url)
                print(f"⚠️  매핑 없음: {url}")
    
    # 수정된 데이터 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(target_data, f, ensure_ascii=False, indent=2)
    
    # 결과 출력
    print(f"\n{'='*60}")
    print(f"✅ 수정 완료: {fixed_count}개")
    print(f"⚠️  매핑 없음: {not_found_count}개")
    print(f"📄 저장 파일: {output_file}")
    
    if not_found_urls:
        print(f"\n매핑되지 않은 URL 목록:")
        for url in not_found_urls[:10]:
            print(f"  - {url}")
        if len(not_found_urls) > 10:
            print(f"  ... 외 {len(not_found_urls) - 10}개")

if __name__ == '__main__':
    target_file = 'makeship_all_products_20250930_043142.json'
    reference_file = 'makeship_all_products_20250929_180719.json'
    output_file = 'makeship_all_products_20250930_043142_fixed.json'
    
    fix_visit_categories(target_file, reference_file, output_file)
