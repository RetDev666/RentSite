const fs = require('fs');

const files = [
  'C:/Users/UserOK/.gemini/antigravity-cli/brain/67e3896c-5ea9-41a2-82dd-76a166acde94/.system_generated/steps/22/content.md',
  'C:/Users/UserOK/.gemini/antigravity-cli/brain/67e3896c-5ea9-41a2-82dd-76a166acde94/.system_generated/steps/26/content.md',
  'C:/Users/UserOK/.gemini/antigravity-cli/brain/67e3896c-5ea9-41a2-82dd-76a166acde94/.system_generated/steps/28/content.md'
];

for (let i = 0; i < files.length; i++) {
  console.log(`\n================ FILE ${i+1} ================`);
  const content = fs.readFileSync(files[i], 'utf8');
  
  // Find all script tags
  const scripts = [...content.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)];
  console.log('Script tags count:', scripts.length);
  for (let s of scripts) {
    if (s[1].includes('description') || s[1].includes('images') || s[1].includes('price') || s[1].includes('viewad')) {
      console.log('Interesting script snippet:', s[1].slice(0, 300));
    }
  }

  // Find meta tags
  const meta = [...content.matchAll(/<meta\s+[^>]*>/gi)];
  for (let m of meta) {
    if (m[0].includes('description') || m[0].includes('title') || m[0].includes('image') || m[0].includes('price')) {
      console.log('Meta:', m[0]);
    }
  }

  // Check if there is viewad-main or similar content
  const idx = content.indexOf('viewad-');
  console.log('viewad- index:', idx);
  if (idx !== -1) {
    console.log('Around viewad-:', content.slice(idx, idx + 400));
  }
}
