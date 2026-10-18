const fs = require('fs');
const path = require('path');

const files = [
  'C:\\Users\\UserOK\\.gemini\\antigravity-cli\\brain\\67e3896c-5ea9-41a2-82dd-76a166acde94\\.system_generated\\steps\\22\\content.md',
  'C:\\Users\\UserOK\\.gemini\antigravity-cli\\brain\\67e3896c-5ea9-41a2-82dd-76a166acde94\\.system_generated\\steps\\26\\content.md',
  'C:\\Users\\UserOK\\.gemini\\antigravity-cli\\brain\\67e3896c-5ea9-41a2-82dd-76a166acde94\\.system_generated\\steps\\28\\content.md'
];

const results = [];

for (let i = 0; i < files.length; i++) {
  const filePath = files[i];
  if (!fs.existsSync(filePath)) {
    console.error('File not found:', filePath);
    continue;
  }
  const text = fs.readFileSync(filePath, 'utf8');

  // Title
  let titleMatch = text.match(/<h1[^>]*id=["']viewad-title["'][^>]*>([\s\S]*?)<\/h1>/i);
  let title = titleMatch ? titleMatch[1].replace(/<[^>]+>/g, '').trim() : '';
  if (!title) {
    let tMatch = text.match(/<title>([\s\S]*?)<\/title>/i);
    title = tMatch ? tMatch[1].replace(/<[^>]+>/g, '').trim() : '';
  }

  // Price
  let priceMatch = text.match(/<h2[^>]*id=["']viewad-price["'][^>]*>([\s\S]*?)<\/h2>/i);
  let price = priceMatch ? priceMatch[1].replace(/<[^>]+>/g, '').trim() : '';

  // Description
  let descMatch = text.match(/<p[^>]*id=["']viewad-description-text["'][^>]*>([\s\S]*?)<\/p>/i);
  let description = '';
  if (descMatch) {
    description = descMatch[1]
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]+>/g, '')
      .replace(/&amp;/g, '&')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .trim();
  }

  // Images
  const imgRegex = /https:\/\/(?:img\.kleinanzeigen\.de|i\.ebayimg\.com)\/[^\s"'<>\\]+?\.(?:jpg|jpeg|png|JPG|JPEG)/g;
  let matches = text.match(imgRegex) || [];
  let images = [];
  for (let u of matches) {
    // Convert small thumbnail to high-res if ebayimg
    u = u.replace(/\$_[0-9]+\.JPG/i, '$_59.JPG');
    if (!images.includes(u)) {
      images.push(u);
    }
  }

  results.push({
    index: i + 1,
    title,
    price,
    description,
    images: images.slice(0, 15)
  });
}

fs.writeFileSync('extracted_kleinanzeigen.json', JSON.stringify(results, null, 2), 'utf8');
console.log('Successfully saved to extracted_kleinanzeigen.json');
for (const r of results) {
  console.log(`\n=== ITEM ${r.index} ===`);
  console.log('Title:', r.title);
  console.log('Price:', r.price);
  console.log('Images count:', r.images.length);
  console.log('First 3 images:', r.images.slice(0, 3));
  console.log('Description preview:\n', r.description.slice(0, 300));
}
