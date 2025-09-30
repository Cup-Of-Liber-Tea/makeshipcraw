# 한국어 제품군을 제품명 키워드 기반으로 영어 카테고리로 변경
import json
from datetime import datetime

input_file = 'makeship_all_products_20250930_111644_fixed.json'
output_file = f'makeship_all_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}_fixed.json'

with open(input_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 변경 대상 한국어 제품군
korean_categories = ['지난 상품', '인기 상품', '신상품', '출시 예정']

# 제품명 키워드 -> 영어 카테고리 매핑
keyword_mapping = {
    'hoodie': 'hoodies',
    'vinyl': 'vinyl figures',
    'keychain': 'keychain plushies',
    'doughboi': 'doughbois',
    'longboi': 'longbois',
    'pin': 'enamel pins',
    'plush': 'plushies',
}

updated_count = 0

# 한국어 제품군을 가진 제품 검사
for product in data['제품_목록']:
    if product['제품군'] in korean_categories:
        product_name_lower = product['제품명'].lower()
        
        # 제품명에 키워드가 있으면 제품군 변경
        for keyword, new_category in keyword_mapping.items():
            if keyword in product_name_lower:
                old_category = product['제품군']
                product['제품군'] = new_category
                print(f"변경: {product['제품명']} | {old_category} → {new_category}")
                updated_count += 1
                break

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n총 {updated_count}개 제품의 제품군 변경 완료")
print(f"저장: {output_file}")
