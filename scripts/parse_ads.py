import re
import json
from pathlib import Path
from bs4 import BeautifulSoup

files = [
    r'C:\Users\UserOK\.gemini\antigravity-cli\brain\67e3896c-5ea9-41a2-82dd-76a166acde94\.system_generated\steps\22\content.md',
    r'C:\Users\UserOK\.gemini\antigravity-cli\brain\67e3896c-5ea9-41a2-82dd-76a166acde94\.system_generated\steps\26\content.md',
    r'C:\Users\UserOK\.gemini\antigravity-cli\brain\67e3896c-5ea9-41a2-82dd-76a166acde94\.system_generated\steps\28\content.md'
]

results = []
for idx, f in enumerate(files, 1):
    text = Path(f).read_text(encoding='utf-8')
    soup = BeautifulSoup(text, 'html.parser')
    
    title = soup.find('h1', id='viewad-title')
    title_text = title.get_text(strip=True) if title else ''
    
    price = soup.find('h2', id='viewad-price')
    price_text = price.get_text(strip=True) if price else ''
    
    desc = soup.find('p', id='viewad-description-text')
    desc_text = desc.get_text('\n', strip=True) if desc else ''
    
    # Extract images from gallery
    images = []
    # Check meta tags or gallery html
    gallery = soup.find('div', id='viewad-image')
    if gallery:
        for img in gallery.find_all('img'):
            src = img.get('src') or img.get('data-imgsrc')
            if src:
                images.append(src)
    
    # Also find all high-res ebayimg urls in the page
    # Typical ebayimg format: https://img.kleinanzeigen.de/api/v1/prod-ads/images/... or https://i.ebayimg.com/00/s/.../$_59.JPG etc.
    raw_images = re.findall(r'https://img\.kleinanzeigen\.de/[^\s\"\'\\]+?\.(?:jpg|jpeg|png)', text)
    raw_images += re.findall(r'https://i\.ebayimg\.com/[^\s\"\'\\]+?\.(?:jpg|jpeg|png|JPG|JPEG)', text)
    
    # filter and deduplicate
    clean_images = []
    for img_url in raw_images:
        # get high res if possible
        if '$_' in img_url:
            # replace thumbnail with large (e.g. $_59.JPG or $_57.JPG)
            img_url = re.sub(r'\$_[0-9]+\.JPG', '$_59.JPG', img_url)
        if img_url not in clean_images:
            clean_images.append(img_url)

    results.append({
        'index': idx,
        'title': title_text,
        'price': price_text,
        'description': desc_text,
        'images': clean_images[:10]
    })

Path('data_extracted.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
print("Extracted successfully!")
for r in results:
    print(f"Item {r['index']}: {r['title']} | {r['price']} | {len(r['images'])} images | desc length {len(r['description'])}")
