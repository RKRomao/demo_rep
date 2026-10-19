/**
 * Servidor HTTP Node.js com Base de Dados SQL Nativa (node:sqlite)
 * Fornece API de Login (HTTP GET), Registo de Utilizadores e Visualizador SQL
 */

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const url = require('node:url');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

const PORT = process.env.PORT || 3000;
const DB_PATH = path.join(__dirname, 'database.sqlite');
const PUBLIC_DIR = __dirname;

// ==========================================================================
// 1. Inicialização da Base de Dados SQL
// ==========================================================================
const db = new DatabaseSync(DB_PATH);
const sqlQueryLog = [];

function logSql(query, params = [], durationMs = 0) {
  const entry = {
    id: Date.now() + Math.random().toString(36).substring(2, 5),
    timestamp: new Date().toLocaleTimeString(),
    query,
    params: params.map(p => (typeof p === 'string' && p.length > 30 ? p.substring(0, 15) + '...' : p)),
    duration: durationMs.toFixed(2) + 'ms'
  };
  sqlQueryLog.unshift(entry);
  if (sqlQueryLog.length > 25) sqlQueryLog.pop();
  console.log(`[SQL ${entry.timestamp}] ${query} | Params:`, params);
}

// Criar tabela de utilizadores se não existir
const initTableStart = performance.now();
const createTableQuery = `
  CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
`;
db.exec(createTableQuery);
logSql("CREATE TABLE IF NOT EXISTS users (...)", [], performance.now() - initTableStart);

// Função auxiliar para hash de senha
function hashPassword(password) {
  return crypto.createHash('sha256').update(password + '_salt_demo_2026').digest('hex');
}

// Inserir utilizador de demonstração se a tabela estiver vazia
const countStmt = db.prepare('SELECT COUNT(*) as count FROM users');
const rowCount = countStmt.get();
if (rowCount && rowCount.count === 0) {
  const seedPass = hashPassword('demo123!');
  const seedStmt = db.prepare('INSERT INTO users (name, username, email, password_hash) VALUES (?, ?, ?, ?)');
  seedStmt.run('Ana Silva', 'anasilva', 'ana.silva@exemplo.com', seedPass);
  logSql("INSERT INTO users (name, username, email, password_hash) VALUES ('Ana Silva', 'anasilva', ...)", []);
}

// ==========================================================================
// 2. Utilitários de Resposta HTTP & Parsing
// ==========================================================================
function sendJson(res, statusCode, data) {
  const payload = JSON.stringify(data);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  });
  res.end(payload);
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
      if (body.length > 1e6) {
        req.destroy();
        reject(new Error('Corpo da requisição demasiado grande'));
      }
    });
    req.on('end', () => {
      if (!body) return resolve({});
      try {
        if (req.headers['content-type'] && req.headers['content-type'].includes('application/json')) {
          resolve(JSON.parse(body));
        } else {
          // urlencoded form
          const params = new URLSearchParams(body);
          const obj = {};
          for (const [k, v] of params.entries()) obj[k] = v;
          resolve(obj);
        }
      } catch (e) {
        resolve({});
      }
    });
  });
}

// ==========================================================================
// 3. Servidor HTTP
// ==========================================================================
const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;
  const method = req.method;

  // Tratar requisições preflight CORS
  if (method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    res.end();
    return;
  }

  // --- API: Login (HTTP GET conforme pedido ou POST) ---
  if (pathname === '/api/login') {
    let credentials = {};
    if (method === 'GET') {
      credentials = parsedUrl.query;
    } else if (method === 'POST') {
      credentials = await parseBody(req);
    } else {
      return sendJson(res, 405, { error: 'Método não permitido. Use GET ou POST.' });
    }

    const usernameOrEmail = (credentials.username || credentials.user || '').trim();
    const password = credentials.password || credentials.pass || '';

    if (!usernameOrEmail || !password) {
      return sendJson(res, 400, {
        success: false,
        error: 'Utilizador/e-mail e palavra-passe são obrigatórios.'
      });
    }

    const tStart = performance.now();
    const query = 'SELECT id, name, username, email, password_hash, created_at FROM users WHERE (username = ? OR email = ?)';
    
    try {
      const selectStmt = db.prepare(query);
      const user = selectStmt.get(usernameOrEmail, usernameOrEmail);
      const duration = performance.now() - tStart;
      logSql(query, [usernameOrEmail, usernameOrEmail], duration);

      if (!user) {
        return sendJson(res, 401, {
          success: false,
          error: 'Utilizador não encontrado na base de dados SQL.',
          sqlExecuted: query
        });
      }

      const inputHash = hashPassword(password);
      if (user.password_hash !== inputHash) {
        return sendJson(res, 401, {
          success: false,
          error: 'Palavra-passe incorreta para este utilizador.',
          sqlExecuted: query
        });
      }

      // Sucesso na autenticação
      const sessionToken = 'jwt_' + crypto.randomBytes(16).toString('hex');
      return sendJson(res, 200, {
        success: true,
        method: method,
        message: 'Login efetuado com sucesso via SQL!',
        user: {
          id: user.id,
          name: user.name,
          username: user.username,
          email: user.email,
          created_at: user.created_at
        },
        token: sessionToken,
        sqlDebug: {
          queryExecuted: query,
          params: [usernameOrEmail],
          duration: `${duration.toFixed(2)}ms`,
          dbFile: 'database.sqlite'
        }
      });
    } catch (dbErr) {
      console.error('Erro na base de dados:', dbErr);
      return sendJson(res, 500, { success: false, error: dbErr.message });
    }
  }

  // --- API: Registo de Novo Utilizador (POST ou GET) ---
  if (pathname === '/api/register') {
    let data = {};
    if (method === 'POST') {
      data = await parseBody(req);
    } else if (method === 'GET') {
      data = parsedUrl.query;
    } else {
      return sendJson(res, 405, { error: 'Método não permitido. Use POST ou GET.' });
    }

    const name = (data.name || '').trim();
    const username = (data.username || '').trim().toLowerCase();
    const email = (data.email || '').trim().toLowerCase();
    const password = data.password || '';

    if (!name || !username || !email || !password) {
      return sendJson(res, 400, {
        success: false,
        error: 'Todos os campos (nome, username, email, password) são obrigatórios.'
      });
    }

    if (password.length < 4) {
      return sendJson(res, 400, {
        success: false,
        error: 'A palavra-passe deve conter pelo menos 4 caracteres.'
      });
    }

    const tStart = performance.now();
    const insertQuery = 'INSERT INTO users (name, username, email, password_hash) VALUES (?, ?, ?, ?)';

    try {
      const pHash = hashPassword(password);
      const insertStmt = db.prepare(insertQuery);
      const result = insertStmt.run(name, username, email, pHash);
      const duration = performance.now() - tStart;
      logSql(insertQuery, [name, username, email, '***HASH***'], duration);

      return sendJson(res, 201, {
        success: true,
        message: 'Utilizador registado com sucesso na base de dados SQL!',
        user: {
          id: result.lastInsertRowid,
          name,
          username,
          email
        },
        sqlDebug: {
          queryExecuted: insertQuery,
          newUserId: result.lastInsertRowid,
          duration: `${duration.toFixed(2)}ms`
        }
      });
    } catch (insertErr) {
      const duration = performance.now() - tStart;
      logSql(insertQuery + " -> ERRO", [name, username, email], duration);
      
      let errMsg = insertErr.message;
      if (errMsg.includes('UNIQUE constraint failed: users.username')) {
        errMsg = 'Este nome de utilizador já está registado.';
      } else if (errMsg.includes('UNIQUE constraint failed: users.email')) {
        errMsg = 'Este endereço de e-mail já se encontra registado.';
      }
      return sendJson(res, 409, {
        success: false,
        error: errMsg
      });
    }
  }

  // --- API: Listar Utilizadores Registados no SQL ---
  if (pathname === '/api/users' && method === 'GET') {
    const tStart = performance.now();
    const query = 'SELECT id, name, username, email, created_at FROM users ORDER BY id DESC';
    try {
      const stmt = db.prepare(query);
      const users = stmt.all();
      const duration = performance.now() - tStart;
      logSql(query, [], duration);

      return sendJson(res, 200, {
        success: true,
        total: users.length,
        users,
        sqlDebug: {
          query,
          duration: `${duration.toFixed(2)}ms`
        }
      });
    } catch (err) {
      return sendJson(res, 500, { success: false, error: err.message });
    }
  }

  // --- API: Histórico de Queries SQL Executadas ---
  if (pathname === '/api/sql-logs' && method === 'GET') {
    return sendJson(res, 200, {
      success: true,
      logs: sqlQueryLog,
      totalUsers: db.prepare('SELECT COUNT(*) as c FROM users').get().c
    });
  }

  // --- Ficheiros Estáticos (HTML, CSS, JS) ---
  let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
  
  // Prevenir Directory Traversal
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403);
    return res.end('Acesso proibido');
  }

  const extname = path.extname(filePath);
  const mimeTypes = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml'
  };
  const contentType = mimeTypes[extname] || 'text/plain';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        res.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end('<h1>404 - Ficheiro Não Encontrado</h1>');
      } else {
        res.writeHead(500);
        res.end('Erro interno: ' + err.code);
      }
    } else {
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

server.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`🚀 Servidor Node.js HTTP + Base de Dados SQL Ativo!`);
  console.log(`🌐 Aceda em: http://localhost:${PORT}`);
  console.log(`📁 Base de dados SQL: ${DB_PATH}`);
  console.log(`====================================================`);
});
