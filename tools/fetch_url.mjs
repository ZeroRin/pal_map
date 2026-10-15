// 通用下载器: node tools/fetch_url.mjs <url> <outPath>
// 使用 Node 自带 TLS (OpenSSL), 绕开 Windows schannel 凭证限制
import { writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

const [url, out] = process.argv.slice(2);
if (!url || !out) {
  console.error('usage: node fetch_url.mjs <url> <outPath>');
  process.exit(2);
}
try {
  const res = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
      'Accept': '*/*',
      'Referer': 'https://paldb.cc/cn/Palpagos_Islands',
    },
  });
  if (!res.ok) {
    console.error(`HTTP ${res.status} ${res.statusText}`);
    process.exit(1);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  await mkdir(dirname(out), { recursive: true });
  await writeFile(out, buf);
  console.log(`OK ${res.status} ${buf.length} bytes -> ${out}  [${res.headers.get('content-type')}]`);
} catch (e) {
  console.error('FAILED: ' + (e && e.message));
  process.exit(1);
}
