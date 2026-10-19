const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const PORT = process.env.PORT || 8080;
const PUBLIC_DIR = __dirname;

const MIME_TYPES = {
  '.html': 'text/html; charset=UTF-8',
  '.css': 'text/css; charset=UTF-8',
  '.js': 'application/javascript; charset=UTF-8',
  '.json': 'application/json',
  '.m3u': 'text/plain; charset=UTF-8',
  '.m3u8': 'application/vnd.apple.mpegurl',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  // Always enable CORS for local requests
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const reqUrl = new URL(req.url, `http://${req.headers.host}`);

  // Endpoint: IPTV Local Proxy (/api/proxy?url=...)
  if (reqUrl.pathname === '/api/proxy') {
    const targetUrlStr = reqUrl.searchParams.get('url');
    if (!targetUrlStr) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end('Missing "url" parameter');
      return;
    }

    try {
      const targetUrl = new URL(targetUrlStr);
      const httpModule = targetUrl.protocol === 'https:' ? https : http;

      const headers = {
        'User-Agent': reqUrl.searchParams.get('user-agent') || req.headers['user-agent'] || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*'
      };

      if (reqUrl.searchParams.has('referer')) {
        headers['Referer'] = reqUrl.searchParams.get('referer');
      }

      const proxyReq = httpModule.get(targetUrl.href, { headers }, (proxyRes) => {
        // Handle Redirects (301, 302, 307, 308)
        if ([301, 302, 303, 307, 308].includes(proxyRes.statusCode) && proxyRes.headers.location) {
          let redirectUrl = proxyRes.headers.location;
          if (!redirectUrl.startsWith('http')) {
            redirectUrl = new URL(redirectUrl, targetUrl.origin).href;
          }
          let proxyRedirect = `/api/proxy?url=${encodeURIComponent(redirectUrl)}`;
          if (headers['Referer']) proxyRedirect += `&referer=${encodeURIComponent(headers['Referer'])}`;
          if (reqUrl.searchParams.has('user-agent')) proxyRedirect += `&user-agent=${encodeURIComponent(reqUrl.searchParams.get('user-agent'))}`;
          
          res.writeHead(302, { 'Location': proxyRedirect });
          res.end();
          return;
        }

        const contentType = proxyRes.headers['content-type'] || '';

        // If M3U / M3U8 manifest, rewrite inner stream URLs to pass through /api/proxy
        if (contentType.includes('mpegurl') || contentType.includes('m3u') || targetUrl.pathname.endsWith('.m3u8') || targetUrl.pathname.endsWith('.m3u')) {
          let body = '';
          proxyRes.setEncoding('utf8');
          proxyRes.on('data', chunk => body += chunk);
          proxyRes.on('end', () => {
            const customHeaders = {
              referer: reqUrl.searchParams.get('referer'),
              userAgent: reqUrl.searchParams.get('user-agent')
            };
            const rewrittenBody = rewriteM3uManifest(body, targetUrl, customHeaders);
            res.writeHead(proxyRes.statusCode, {
              'Content-Type': 'application/vnd.apple.mpegurl',
              'Access-Control-Allow-Origin': '*'
            });
            res.end(rewrittenBody);
          });
        } else {
          // Pipe binary video/audio chunks (.ts, .mp4, .aac) directly
          res.writeHead(proxyRes.statusCode, {
            'Content-Type': contentType || 'video/MP2T',
            'Access-Control-Allow-Origin': '*'
          });
          proxyRes.pipe(res);
        }
      });

      proxyReq.setTimeout(6000, () => {
        proxyReq.destroy(new Error('Connection Timeout (Stream indisponível)'));
      });

      proxyReq.on('error', (err) => {
        console.error('Proxy Error:', err.message);
        if (!res.headersSent) {
          res.writeHead(504, { 'Content-Type': 'text/plain' });
          res.end(`Proxy Error: ${err.message}`);
        }
      });

    } catch (err) {
      res.writeHead(400, { 'Content-Type': 'text/plain' });
      res.end(`Invalid URL: ${err.message}`);
    }
    return;
  }

  // Static File Serving
  let filePath = path.join(PUBLIC_DIR, reqUrl.pathname === '/' ? 'index.html' : reqUrl.pathname);
  filePath = path.normalize(filePath);

  // Security check to prevent directory traversal
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('404 Not Found');
      } else {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end(`Server Error: ${err.code}`);
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

/**
 * Rewrites URLs in M3U8 manifest files so segment and playlist links pass through the local proxy
 */
function rewriteM3uManifest(manifestText, baseUrl, customHeaders = {}) {
  const extraParams = [];
  if (customHeaders.referer) extraParams.push(`referer=${encodeURIComponent(customHeaders.referer)}`);
  if (customHeaders.userAgent) extraParams.push(`user-agent=${encodeURIComponent(customHeaders.userAgent)}`);
  const extraQuery = extraParams.length ? '&' + extraParams.join('&') : '';

  const lines = manifestText.split('\n');
  const rewrittenLines = lines.map(line => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      // Handle URI= in #EXT-X-KEY or #EXT-X-MEDIA if present
      if (trimmed.includes('URI="')) {
        return trimmed.replace(/URI="([^"]+)"/g, (match, p1) => {
          const absoluteUrl = resolveUrl(p1, baseUrl);
          return `URI="/api/proxy?url=${encodeURIComponent(absoluteUrl)}${extraQuery}"`;
        });
      }
      return line;
    }

    // Line is a segment URL or sub-manifest URL
    const absoluteUrl = resolveUrl(trimmed, baseUrl);
    return `/api/proxy?url=${encodeURIComponent(absoluteUrl)}${extraQuery}`;
  });

  return rewrittenLines.join('\n');
}

function resolveUrl(urlStr, baseUrl) {
  try {
    if (urlStr.startsWith('http://') || urlStr.startsWith('https://')) {
      return urlStr;
    }
    return new URL(urlStr, baseUrl.href).href;
  } catch (e) {
    return urlStr;
  }
}

server.listen(PORT, () => {
  console.log(`\n==================================================`);
  console.log(`   Servidor TVM IPTV rodando com Proxy Local CORS!`);
  console.log(`   Acesse: http://localhost:${PORT}/`);
  console.log(`==================================================\n`);
});
