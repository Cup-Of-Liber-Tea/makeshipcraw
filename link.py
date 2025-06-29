import requests
from bs4 import BeautifulSoup
import time
import re

def extract_makeship_hoodie_links():
    """
    Makeship의 후디 상품 링크들을 추출하는 함수
    """
    url = "https://www.makeship.com/shop/hoodies"
    
    # 헤더 설정 (봇 차단 방지)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print("Makeship 후디 페이지에 접속 중...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 상품 링크를 찾기 위한 다양한 셀렉터 시도
        product_links = []
        
        # 일반적인 상품 링크 패턴들
        link_selectors = [
            'a[href*="/products/"]',
            'a[href*="/shop/"]',
            '.product-card a',
            '.product-item a',
            '.product a',
            '[data-product-id] a',
            '.grid-item a'
        ]
        
        for selector in link_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    # 상대 경로를 절대 경로로 변환
                    if href.startswith('/'):
                        full_url = f"https://www.makeship.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    # 중복 제거
                    if full_url not in product_links:
                        product_links.append(full_url)
        
        # href 속성을 가진 모든 링크 검사 (백업 방법)
        if not product_links:
            print("특정 셀렉터로 찾지 못해 모든 링크를 검사합니다...")
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                # 상품 관련 패턴 필터링
                if any(pattern in href for pattern in ['/products/', '/shop/', 'hoodie', 'product']):
                    if href.startswith('/'):
                        full_url = f"https://www.makeship.com{href}"
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue
                    
                    if full_url not in product_links:
                        product_links.append(full_url)
        
        return product_links
        
    except requests.RequestException as e:
        print(f"웹페이지 요청 중 오류 발생: {e}")
        return []
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return []

def save_links_to_file(links, filename="makeship_hoodie_links.txt"):
    """
    추출된 링크들을 파일로 저장하는 함수
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Makeship 후디 상품 링크 목록 (총 {len(links)}개)\n")
            f.write("=" * 50 + "\n\n")
            
            for i, link in enumerate(links, 1):
                f.write(f"{i}. {link}\n")
        
        print(f"링크들이 '{filename}' 파일에 저장되었습니다.")
        
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")

def main():
    """
    메인 실행 함수
    """
    print("Makeship 후디 상품 링크 추출 시작...")
    
    # 링크 추출
    links = extract_makeship_hoodie_links()
    
    if links:
        print(f"\n총 {len(links)}개의 링크를 찾았습니다:")
        print("-" * 50)
        
        for i, link in enumerate(links, 1):
            print(f"{i}. {link}")
        
        # 파일로 저장
        save_links_to_file(links)
        
    else:
        print("링크를 찾을 수 없습니다.")
        print("웹사이트 구조가 변경되었거나 접근이 제한되었을 수 있습니다.")

if __name__ == "__main__":
    main()