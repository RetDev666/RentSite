const fs = require('fs');
const path = require('path');
const https = require('https');

const outDir = path.join(__dirname, '..', 'static', 'uploads');
if (!fs.existsSync(outDir)) {
  fs.mkdirSync(outDir, { recursive: true });
}

function downloadImage(url, destPath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(destPath);
    https.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.kleinanzeigen.de/'
      }
    }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
        https.get(res.headers.location, (redRes) => {
          redRes.pipe(file);
          file.on('finish', () => file.close(resolve));
        }).on('error', (err) => {
          fs.unlink(destPath, () => {});
          reject(err);
        });
        return;
      }
      if (res.statusCode !== 200) {
        file.close();
        fs.unlink(destPath, () => {});
        return reject(new Error(`Status ${res.statusCode}`));
      }
      res.pipe(file);
      file.on('finish', () => file.close(resolve));
    }).on('error', (err) => {
      fs.unlink(destPath, () => {});
      reject(err);
    });
  });
}

const configs = [
  { file: 'ad1.html', prefix: 'badefass' },
  { file: 'ad2.html', prefix: 'kombi' },
  { file: 'ad3.html', prefix: 'fasssauna' }
];

async function run() {
  const modelImages = {};

  for (const cfg of configs) {
    const content = fs.readFileSync(cfg.file, 'utf8');
    const matches = [...content.matchAll(/prod-ads\/images\/([a-f0-9]{2})\/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})/gi)];
    
    // Deduplicate
    const seen = new Set();
    const urls = [];
    for (const m of matches) {
      const sub = m[1];
      const uuid = m[2];
      if (!seen.has(uuid)) {
        seen.add(uuid);
        urls.push(`https://img.kleinanzeigen.de/api/v1/prod-ads/images/${sub}/${uuid}?rule=$_59.JPG`);
      }
    }

    console.log(`\nDownloading ${urls.length} photos for ${cfg.prefix}...`);
    modelImages[cfg.prefix] = [];

    for (let i = 0; i < urls.length; i++) {
      const filename = `${cfg.prefix}-${i + 1}.jpg`;
      const targetPath = path.join(outDir, filename);
      try {
        await downloadImage(urls[i], targetPath);
        const stats = fs.statSync(targetPath);
        if (stats.size > 2000) {
          console.log(`  [OK] ${filename} (${Math.round(stats.size / 1024)} KB)`);
          modelImages[cfg.prefix].push(`/static/uploads/${filename}`);
        } else {
          fs.unlinkSync(targetPath);
        }
      } catch (e) {
        console.error(`  [ERR] ${filename}: ${e.message}`);
      }
    }
  }

  fs.writeFileSync('all_model_images.json', JSON.stringify(modelImages, null, 2), 'utf8');
  console.log('\nDownloaded all photos!');
}

run();
