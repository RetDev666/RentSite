const fs = require('fs');

const files = ['ad1.html', 'ad2.html', 'ad3.html'];

const results = [];

for (let i = 0; i < files.length; i++) {
  const content = fs.readFileSync(files[i], 'utf8');

  // Title
  let titleMatch = content.match(/<h1[^>]*id=["']viewad-title["'][^>]*>([\s\S]*?)<\/h1>/i);
  let title = titleMatch ? titleMatch[1].replace(/<[^>]+>/g, '').trim() : '';

  // Price
  let priceMatch = content.match(/<h2[^>]*id=["']viewad-price["'][^>]*>([\s\S]*?)<\/h2>/i);
  let price = priceMatch ? priceMatch[1].replace(/<[^>]+>/g, '').trim() : '';

  // Description
  let descMatch = content.match(/<p[^>]*id=["']viewad-description-text["'][^>]*>([\s\S]*?)<\/p>/i);
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

  // Location / Postal code
  let locMatch = content.match(/<span[^>]*id=["']viewad-locality["'][^>]*>([\s\S]*?)<\/span>/i);
  let location = locMatch ? locMatch[1].replace(/<[^>]+>/g, '').trim() : '';

  // Image URLs
  // Look for gallery images: data-imgsrc or in viewad-image or all ebayimg URLs
  let imgUrls = [];
  
  // match data-imgsrc or src in viewad-gallery
  const galleryMatches = [...content.matchAll(/data-imgsrc=["']([^"']+)["']/gi)];
  for (let m of galleryMatches) {
    let url = m[1].replace(/\$_[0-9]+\.JPG/i, '$_59.JPG');
    if (!imgUrls.includes(url)) imgUrls.push(url);
  }

  const allEbayMatches = [...content.matchAll(/https:\/\/(?:img\.kleinanzeigen\.de|i\.ebayimg\.com)[^"'\s<>\\]+?\.(?:jpg|jpeg|png|JPG|JPEG)(?:\?[^"'\s<>\\]*)?/gi)].map(x => x[0]);
  for (let u of allEbayMatches) {
    let url = u.replace(/\$_[0-9]+\.JPG/i, '$_59.JPG');
    if (!imgUrls.includes(url) && !url.includes('logo') && !url.includes('icon') && !url.includes('avatar')) {
      imgUrls.push(url);
    }
  }

  results.push({
    index: i + 1,
    file: files[i],
    title,
    price,
    location,
    description,
    images: imgUrls
  });
}

fs.writeFileSync('extracted_full.json', JSON.stringify(results, null, 2), 'utf8');

for (const r of results) {
  console.log(`\n=================== ITEM ${r.index} ===================`);
  console.log('TITLE:', r.title);
  console.log('PRICE:', r.price);
  console.log('LOCATION:', r.location);
  console.log('IMAGES COUNT:', r.images.length);
  console.log('SAMPLE IMAGES:', r.images.slice(0, 3));
  console.log('\n--- DESCRIPTION ---\n' + r.description + '\n-------------------');
}
