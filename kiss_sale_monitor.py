import requests
from bs4 import BeautifulSoup
import os
import re
import sys
import time
from urllib.parse import urljoin
from collections import defaultdict

def exit_program():
    input("\nPress 'Enter' to exit...")
    sys.exit(0)

def read_favorite_websites(filepath='kiss_favorite.txt'):
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def classify_urls(urls):
    url_types = defaultdict(list)
    for url in urls:
        if '/cres/' in url:
            url_types['cres'].append(url)
        else:
            url_types['com3d2'].append(url)
    return url_types

def get_shop_cookies(shop_type, max_retries=3):
    base_url = "https://com3d2-shop.s-court.me"
    init_url = {
        'cres': f"{base_url}/cres/top/tag/none/tc/1/",
        'com3d2': f"{base_url}/top/tag/none/tc/1/"
    }.get(shop_type)
    
    for _ in range(max_retries):
        try:
            response = requests.get(init_url, 
                                  headers={'User-Agent': 'Mozilla/5.0'},
                                  timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if shop_type == 'cres':
                selector = 'a.index_btn[href*="/cres/top/tag/none/tc/1"]'
            else:
                selector = 'a.index_btn[href*="/top/tag/none/tc/1"]'
                
            link = soup.select_one(selector)
            if not link:
                raise ValueError(f"Redirect link not found for {shop_type}")
            
            redirect_url = urljoin(base_url, link['href'])
            response = requests.get(redirect_url, 
                                  headers={'User-Agent': 'Mozilla/5.0'},
                                  timeout=15)
            return response.cookies
            
        except Exception as e:
            print(f"Cookie init failed ({shop_type}): {str(e)}")
            time.sleep(2)
    
    raise ConnectionError(f"Failed to get {shop_type} cookies after {max_retries} retries")

def parse_price(element):
    price_text = element.get_text(separator=' ', strip=True)
    prices = re.findall(r'¥([\d,]+)', price_text)
    
    return {
        'original': prices[0].replace(',', '') if len(prices) > 1 else None,
        'current': prices[-1].replace(',', ''),
        'on_sale': '⇒' in price_text
    }

def format_price(value):
    try:
        return f"¥{int(value):,}" if value else None
    except:
        return None

def safe_request(url, cookies, max_retries=3):
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url,
                                   headers=headers,
                                   cookies=cookies,
                                   timeout=15)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            print(f"Timeout (attempt {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise
        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise

def process_batch(urls, shop_type):
    print(f"\nProcessing {len(urls)} {shop_type.upper()} items...")
    sale_items = []
    
    try:
        cookies = get_shop_cookies(shop_type)
    except Exception as e:
        print(f"Failed to process {shop_type} items: {str(e)}")
        return []
    
    for idx, url in enumerate(urls, 1):
        print(f"  ({idx}/{len(urls)}) {url}")
        
        try:
            response = safe_request(url, cookies)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            name = soup.find('h2').text.strip() if soup.find('h2') else "Unknown Product"
            price_element = soup.select_one('.price.text-start.fw-bold[style*="font-size:24px"]')
            
            if not price_element:
                print("Price element not found")
                continue
                
            price_info = parse_price(price_element)
            product = {
                'name': name,
                'price': f"{format_price(price_info['original'])} ⇒ {format_price(price_info['current'])}" 
                        if price_info['original'] else format_price(price_info['current']),
                'on_sale': price_info['on_sale']
            }
            
            if product['on_sale']:
                sale_items.append(product)
                print(f"  Found sale: {product['name']} - {product['price']}")
            else:
                print(f"  Found: {product['name']} - {product['price']}")
                
        except Exception as e:
            print(f"  Error processing: {str(e)}")
    
    return sale_items

def main():
    websites = read_favorite_websites()
    if not websites:
        exit_program()
    
    url_types = classify_urls(websites)
    processing_order = ['cres', 'com3d2']
    
    all_sales = []
    
    for shop_type in processing_order:
        urls = url_types.get(shop_type, [])
        if urls:
            sales = process_batch(urls, shop_type)
            all_sales.extend(sales)
    
    if all_sales:
        print("\nFinal Sale Items:")
        for item in all_sales:
            print(f"{item['name']} - {item['price']}")
    else:
        print("\nNo sale items found")
    
    exit_program()

if __name__ == "__main__":
    main()