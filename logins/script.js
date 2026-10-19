/**
 * Node.js + SQL Localhost Auth System & Simulator
 * Handles Login (HTTP GET), Registration (SQL INSERT), and Live SQLite Inspector
 */

document.addEventListener('DOMContentLoaded', () => {
  // Navigation Tabs & Views
  const navTabs = document.querySelectorAll('.nav-tab');
  const viewSections = document.querySelectorAll('.view-section');

  // Auth Switcher (Login <-> Registo)
  const btnModeLogin = document.getElementById('btn-mode-login');
  const btnModeRegister = document.getElementById('btn-mode-register');
  const panelLogin = document.getElementById('auth-panel-login');
  const panelRegister = document.getElementById('auth-panel-register');
  const switchToRegBtns = document.querySelectorAll('.switch-to-reg-btn');
  const switchToLoginBtns = document.querySelectorAll('.switch-to-login-btn');

  // Form Elements - Login
  const loginForm = document.getElementById('login-form');
  const loginUserInput = document.getElementById('login-username');
  const loginPassInput = document.getElementById('login-password');
  const loginRememberInput = document.getElementById('login-remember');
  const loginSubmitBtn = document.getElementById('login-submit-btn');

  // Form Elements - Register
  const registerForm = document.getElementById('register-form');
  const regNameInput = document.getElementById('reg-name');
  const regUserInput = document.getElementById('reg-username');
  const regEmailInput = document.getElementById('reg-email');
  const regPassInput = document.getElementById('reg-password');
  const regSubmitBtn = document.getElementById('reg-submit-btn');

  // Feedback State
  const authCard = document.getElementById('login-card');
  const authSuccessState = document.getElementById('auth-success-state');
  const successTitle = document.getElementById('success-title');
  const successMessage = document.getElementById('success-message');
  const successUserDisplay = document.getElementById('success-user-display');
  const btnAuthReset = document.getElementById('btn-auth-reset');
  const btnSeeInSql = document.getElementById('btn-see-in-sql');

  // Inspector Elements
  const liveMethodTag = document.getElementById('live-method-tag');
  const liveUrlPreview = document.getElementById('live-url-preview');
  const liveSqlPreview = document.getElementById('live-sql-preview');
  const responsePreview = document.getElementById('response-preview');
  const statusTag = document.getElementById('status-tag');

  // SQL View Elements
  const sqlTableBody = document.getElementById('sql-table-body');
  const sqlLogTerminal = document.getElementById('sql-log-terminal');
  const btnRefreshSql = document.getElementById('btn-refresh-sql');

  // Simulator Elements
  const packetTraveler = document.getElementById('packet-traveler');
  const packetBadge = document.getElementById('packet-badge');
  const packetInfo = document.getElementById('packet-info');
  const netNodes = document.querySelectorAll('.net-node');
  const stepDots = document.querySelectorAll('.dot');
  const btnPlay = document.getElementById('btn-play');
  const btnPrev = document.getElementById('btn-prev');
  const btnNext = document.getElementById('btn-next');
  const btnRestart = document.getElementById('btn-restart');

  const stepCounterText = document.getElementById('step-counter-text');
  const stepStateTag = document.getElementById('step-state-tag');
  const stepTitle = document.getElementById('step-title');
  const stepWhatText = document.getElementById('step-what-text');
  const stepWhyText = document.getElementById('step-why-text');
  const stepInsightText = document.getElementById('step-insight-text');
  const stepCodePreview = document.getElementById('step-code-preview');

  /* ==========================================================================
     1. Interactive Particle Canvas Background
     ========================================================================== */
  const canvas = document.getElementById('particles-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    window.addEventListener('resize', () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    });

    const particles = [];
    const count = 40;
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        radius: Math.random() * 2 + 1,
        vx: (Math.random() - 0.5) * 0.6,
        vy: (Math.random() - 0.5) * 0.6,
        alpha: Math.random() * 0.5 + 0.2
      });
    }

    function animateParticles() {
      ctx.clearRect(0, 0, width, height);
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(165, 180, 252, ${p.alpha})`;
        ctx.fill();

        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dist = Math.hypot(p.x - p2.x, p.y - p2.y);
          if (dist < 110) {
            ctx.strokeStyle = `rgba(99, 102, 241, ${0.15 * (1 - dist / 110)})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.stroke();
          }
        }
      }
      requestAnimationFrame(animateParticles);
    }
    animateParticles();
  }

  /* ==========================================================================
     2. Top Navigation Tabs
     ========================================================================== */
  function switchNavTab(targetTabId) {
    navTabs.forEach((tab) => {
      const isActive = tab.id === targetTabId;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    const viewMap = {
      'tab-auth': 'view-auth',
      'tab-sql': 'view-sql',
      'tab-process': 'view-process',
      'tab-compare': 'view-compare'
    };

    const targetViewId = viewMap[targetTabId];
    viewSections.forEach((sec) => {
      sec.classList.toggle('active', sec.id === targetViewId);
    });

    if (targetTabId === 'tab-sql') {
      loadSqlTable();
      loadSqlLogs();
    }
    if (targetTabId === 'tab-process') {
      goToStep(currentStep);
    }
  }

  navTabs.forEach((tab) => {
    tab.addEventListener('click', () => switchNavTab(tab.id));
  });

  if (btnSeeInSql) {
    btnSeeInSql.addEventListener('click', () => switchNavTab('tab-sql'));
  }

  /* ==========================================================================
     3. Auth Mode Switcher (Login <-> Register)
     ========================================================================== */
  function setAuthMode(mode) {
    clearErrors();
    authSuccessState.style.display = 'none';

    if (mode === 'login') {
      btnModeLogin.classList.add('active');
      btnModeLogin.setAttribute('aria-selected', 'true');
      btnModeRegister.classList.remove('active');
      btnModeRegister.setAttribute('aria-selected', 'false');

      panelLogin.style.display = 'block';
      panelRegister.style.display = 'none';
      updateLiveInspectorForLogin();
    } else {
      btnModeRegister.classList.add('active');
      btnModeRegister.setAttribute('aria-selected', 'true');
      btnModeLogin.classList.remove('active');
      btnModeLogin.setAttribute('aria-selected', 'false');

      panelRegister.style.display = 'block';
      panelLogin.style.display = 'none';
      updateLiveInspectorForRegister();
    }
  }

  btnModeLogin.addEventListener('click', () => setAuthMode('login'));
  btnModeRegister.addEventListener('click', () => setAuthMode('register'));

  switchToRegBtns.forEach((btn) => btn.addEventListener('click', () => setAuthMode('register')));
  switchToLoginBtns.forEach((btn) => btn.addEventListener('click', () => setAuthMode('login')));

  /* ==========================================================================
     4. Password Visibility Toggles
     ========================================================================== */
  document.querySelectorAll('.toggle-password').forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (!input) return;

      const isPass = input.getAttribute('type') === 'password';
      input.setAttribute('type', isPass ? 'text' : 'password');

      const eye = btn.querySelector('.eye-icon');
      if (eye) {
        eye.innerHTML = isPass
          ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
               <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
               <line x1="1" y1="1" x2="23" y2="23"></line>
             </svg>`
          : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
               <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
               <circle cx="12" cy="7" r="3"></circle>
             </svg>`;
      }
    });
  });

  // Method Selector (GET vs POST for login)
  let currentLoginMethod = 'GET';
  const btnLoginMethodGet = document.getElementById('btn-login-method-get');
  const btnLoginMethodPost = document.getElementById('btn-login-method-post');
  const loginHeaderBadge = document.getElementById('login-header-badge');
  const loginHeaderDot = document.getElementById('login-header-dot');
  const loginHeaderText = document.getElementById('login-header-text');
  const loginCardSubtitle = document.getElementById('login-card-subtitle');
  const loginBtnLabel = document.getElementById('login-btn-label');

  function setLoginMethod(method) {
    currentLoginMethod = method;
    if (method === 'GET') {
      if (btnLoginMethodGet) btnLoginMethodGet.classList.add('active');
      if (btnLoginMethodPost) btnLoginMethodPost.classList.remove('active');
      if (loginHeaderBadge) loginHeaderBadge.className = 'get-badge';
      if (loginHeaderDot) loginHeaderDot.className = 'pulse-dot';
      if (loginHeaderText) loginHeaderText.textContent = 'Método: HTTP GET • SQL SELECT';
      if (loginCardSubtitle) loginCardSubtitle.innerHTML = 'Autenticação com envio via Query String (<strong>HTTP GET</strong>)';
      if (loginBtnLabel) loginBtnLabel.textContent = 'Entrar com GET & SQL';
    } else {
      if (btnLoginMethodPost) btnLoginMethodPost.classList.add('active');
      if (btnLoginMethodGet) btnLoginMethodGet.classList.remove('active');
      if (loginHeaderBadge) loginHeaderBadge.className = 'get-badge post-badge';
      if (loginHeaderDot) loginHeaderDot.className = 'pulse-dot post-dot';
      if (loginHeaderText) loginHeaderText.textContent = 'Método: HTTP POST • SQL SELECT';
      if (loginCardSubtitle) loginCardSubtitle.innerHTML = 'Autenticação segura via Request Body (<strong>HTTP POST</strong>)';
      if (loginBtnLabel) loginBtnLabel.textContent = 'Entrar com POST & SQL';
    }
    updateLiveInspectorForLogin();
  }

  if (btnLoginMethodGet) btnLoginMethodGet.addEventListener('click', () => setLoginMethod('GET'));
  if (btnLoginMethodPost) btnLoginMethodPost.addEventListener('click', () => setLoginMethod('POST'));

  /* ==========================================================================
     5. Real-Time Inspector Updates
     ========================================================================== */
  function updateLiveInspectorForLogin() {
    const user = loginUserInput.value.trim() || 'anasilva';
    const pass = loginPassInput.value ? '••••••••' : 'demo123!';
    
    if (currentLoginMethod === 'GET') {
      const qs = `?username=${encodeURIComponent(user)}&password=${encodeURIComponent(pass)}`;
      if (liveMethodTag) {
        liveMethodTag.textContent = 'GET';
        liveMethodTag.className = 'method-tag';
      }
      if (liveUrlPreview) {
        liveUrlPreview.textContent = `/api/login${qs}`;
      }
      if (packetBadge) {
        packetBadge.textContent = 'GET';
        packetBadge.style.background = '#38bdf8';
        packetBadge.style.color = '#0b0f19';
      }
      if (packetInfo) {
        packetInfo.textContent = `?user=${user}&pass=${pass}`;
      }
    } else {
      if (liveMethodTag) {
        liveMethodTag.textContent = 'POST';
        liveMethodTag.className = 'method-tag post';
      }
      if (liveUrlPreview) {
        liveUrlPreview.textContent = `/api/login [Request Body: JSON]`;
      }
      if (packetBadge) {
        packetBadge.textContent = 'POST';
        packetBadge.style.background = '#06b6d4';
        packetBadge.style.color = '#ffffff';
      }
      if (packetInfo) {
        packetInfo.textContent = `Body: { user: "${user}", pass: "***" }`;
      }
    }

    if (liveSqlPreview) {
      liveSqlPreview.textContent = `SELECT * FROM users WHERE (username = '${user}' OR email = '${user}');`;
    }
  }

  function updateLiveInspectorForRegister() {
    const user = regUserInput.value.trim() || 'novo.user';
    const name = regNameInput.value.trim() || 'Nome Completo';
    const email = regEmailInput.value.trim() || 'email@exemplo.com';

    if (liveMethodTag) {
      liveMethodTag.textContent = 'POST';
      liveMethodTag.className = 'method-tag post';
    }
    if (liveUrlPreview) {
      liveUrlPreview.textContent = `/api/register [Request Body: JSON]`;
    }
    if (liveSqlPreview) {
      liveSqlPreview.textContent = `INSERT INTO users (name, username, email, password_hash) VALUES ('${name}', '${user}', '${email}', '***SHA256***');`;
    }
  }

  loginUserInput.addEventListener('input', updateLiveInspectorForLogin);
  loginPassInput.addEventListener('input', updateLiveInspectorForLogin);

  regNameInput.addEventListener('input', updateLiveInspectorForRegister);
  regUserInput.addEventListener('input', updateLiveInspectorForRegister);
  regEmailInput.addEventListener('input', updateLiveInspectorForRegister);

  updateLiveInspectorForLogin();

  /* ==========================================================================
     6. Validation Helpers
     ========================================================================== */
  function clearErrors() {
    document.querySelectorAll('.field-error-msg').forEach((el) => {
      el.classList.remove('show');
      el.textContent = '';
    });
    authCard.classList.remove('shake');
  }

  function showError(fieldId, msg) {
    const errorEl = document.getElementById(`${fieldId}-error`);
    if (errorEl) {
      errorEl.textContent = msg;
      errorEl.classList.add('show');
    }
    authCard.classList.remove('shake');
    void authCard.offsetWidth;
    authCard.classList.add('shake');
  }

  /* ==========================================================================
     7. Form Submission: LOGIN (HTTP GET ou POST Dinâmico)
     ========================================================================== */
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const username = loginUserInput.value.trim();
    const password = loginPassInput.value;

    if (!username) {
      showError('login-username', 'Por favor, insira o seu utilizador ou e-mail.');
      return;
    }
    if (!password) {
      showError('login-password', 'Por favor, insira a sua palavra-passe.');
      return;
    }

    loginSubmitBtn.classList.add('loading');
    loginSubmitBtn.disabled = true;
    if (statusTag) statusTag.textContent = `A consultar SQL via ${currentLoginMethod}...`;

    const startTime = performance.now();

    try {
      let res;
      if (currentLoginMethod === 'GET') {
        const params = new URLSearchParams({
          username: username,
          password: password,
          remember: loginRememberInput.checked ? '1' : '0'
        });
        res = await fetch(`/api/login?${params.toString()}`, { method: 'GET' });
      } else {
        res = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: username,
            password: password,
            remember: loginRememberInput.checked ? '1' : '0'
          })
        });
      }

      const data = await res.json();
      const duration = Math.round(performance.now() - startTime);

      loginSubmitBtn.classList.remove('loading');
      loginSubmitBtn.disabled = false;

      if (responsePreview) {
        responsePreview.textContent = JSON.stringify(data, null, 2);
      }

      if (res.ok && data.success) {
        if (statusTag) {
          statusTag.textContent = `200 OK (${data.method || currentLoginMethod} em ${duration}ms)`;
          statusTag.className = 'status-tag active';
        }

        panelLogin.style.display = 'none';
        panelRegister.style.display = 'none';
        authSuccessState.style.display = 'block';

        successTitle.textContent = `Login com ${data.method || currentLoginMethod} Realizado!`;
        successMessage.textContent = `Autenticado com sucesso via SQL como ${data.user.name} (@${data.user.username}) usando método HTTP ${data.method || currentLoginMethod}.`;
        successUserDisplay.textContent = data.user.email;

        loadSqlLogs();
      } else {
        if (statusTag) {
          statusTag.textContent = `Erro ${res.status}`;
          statusTag.className = 'status-tag error';
        }
        showError('login-password', data.error || 'Falha na autenticação.');
      }
    } catch (err) {
      loginSubmitBtn.classList.remove('loading');
      loginSubmitBtn.disabled = false;
      showError('login-password', 'Não foi possível ligar ao servidor local em localhost:3000');
    }
  });

  /* ==========================================================================
     8. Form Submission: REGISTO (HTTP POST -> SQL INSERT)
     ========================================================================== */
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearErrors();

    const name = regNameInput.value.trim();
    const username = regUserInput.value.trim();
    const email = regEmailInput.value.trim();
    const password = regPassInput.value;

    if (!name) return showError('reg-name', 'Por favor, insira o seu nome completo.');
    if (!username) return showError('reg-username', 'Por favor, defina um nome de utilizador.');
    if (!email) return showError('reg-email', 'Por favor, insira um e-mail válido.');
    if (!password || password.length < 4) {
      return showError('reg-password', 'A palavra-passe deve conter pelo menos 4 caracteres.');
    }

    regSubmitBtn.classList.add('loading');
    regSubmitBtn.disabled = true;
    if (statusTag) statusTag.textContent = 'A executar SQL INSERT...';

    const startTime = performance.now();

    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, username, email, password })
      });
      const data = await res.json();
      const duration = Math.round(performance.now() - startTime);

      regSubmitBtn.classList.remove('loading');
      regSubmitBtn.disabled = false;

      if (responsePreview) {
        responsePreview.textContent = JSON.stringify(data, null, 2);
      }

      if (res.ok && data.success) {
        if (statusTag) {
          statusTag.textContent = `201 Created (${duration}ms)`;
          statusTag.className = 'status-tag active';
        }

        panelLogin.style.display = 'none';
        panelRegister.style.display = 'none';
        authSuccessState.style.display = 'block';

        successTitle.textContent = 'Conta Registada no SQL!';
        successMessage.textContent = `Utilizador inserido com sucesso na tabela users (ID #${data.user.id}).`;
        successUserDisplay.textContent = `${data.user.name} (@${data.user.username})`;

        // Pre-fill login form for convenience
        loginUserInput.value = data.user.username;
        loginPassInput.value = password;

        loadSqlTable();
        loadSqlLogs();
      } else {
        if (statusTag) {
          statusTag.textContent = `Erro ${res.status}`;
          statusTag.className = 'status-tag error';
        }
        showError('reg-username', data.error || 'Erro ao registar utilizador.');
      }
    } catch (err) {
      regSubmitBtn.classList.remove('loading');
      regSubmitBtn.disabled = false;
      showError('reg-username', 'Não foi possível ligar ao servidor local em localhost:3000');
    }
  });

  if (btnAuthReset) {
    btnAuthReset.addEventListener('click', () => {
      setAuthMode('login');
    });
  }

  /* ==========================================================================
     9. SQL Database Viewer & Live Query Logs
     ========================================================================== */
  async function loadSqlTable() {
    if (!sqlTableBody) return;
    try {
      const res = await fetch('/api/users');
      const data = await res.json();
      if (!data.success || !data.users) return;

      if (data.users.length === 0) {
        sqlTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-dim); padding: 20px;">Nenhum utilizador encontrado na tabela SQL.</td></tr>`;
        return;
      }

      sqlTableBody.innerHTML = data.users.map((u) => `
        <tr>
          <td><span class="user-id-badge">#${u.id}</span></td>
          <td><strong style="color: #f8fafc;">${escapeHtml(u.name)}</strong></td>
          <td><code style="color: #38bdf8;">@${escapeHtml(u.username)}</code></td>
          <td>${escapeHtml(u.email)}</td>
          <td><div class="hash-cell" title="Armazenado como hash seguro">sha256:••••••••••••••••</div></td>
          <td style="font-size: 0.76rem; color: #94a3b8;">${u.created_at || 'Recentemente'}</td>
        </tr>
      `).join('');
    } catch (err) {
      sqlTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #f87171; padding: 20px;">Erro ao carregar dados do servidor Node.js.</td></tr>`;
    }
  }

  async function loadSqlLogs() {
    if (!sqlLogTerminal) return;
    try {
      const res = await fetch('/api/sql-logs');
      const data = await res.json();
      if (!data.success || !data.logs) return;

      sqlLogTerminal.innerHTML = data.logs.map((log) => `
        <div class="log-entry">
          <span class="log-time">[${log.timestamp}]</span>
          <span class="log-query"><strong>SQL &gt;</strong> ${escapeHtml(log.query)}</span>
          <span class="log-duration">${log.duration}</span>
        </div>
      `).join('');
    } catch (err) {
      console.error('Erro ao ler logs SQL:', err);
    }
  }

  if (btnRefreshSql) {
    btnRefreshSql.addEventListener('click', () => {
      loadSqlTable();
      loadSqlLogs();
    });
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>'"]/g, (tag) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag));
  }

  /* ==========================================================================
     10. Interactive Network Flow Simulator: "O Que Acontece & O Porquê"
     ========================================================================== */
  const stepsData = [
    {
      step: 1,
      tag: "1. Serialização no Cliente",
      title: "O Navegador anexa os dados diretamente na URL",
      what: "Ao submeter com <code>method=\"GET\"</code>, o navegador percorre os campos de texto e constrói uma <em>Query String</em> diretamente a seguir ao <code>?</code> na barra de endereços.",
      why: "A especificação HTTP define que o método GET serve para <strong>solicitar recursos</strong> e não aceita corpo de mensagem (Request Body). Para que o cliente passe parâmetros ao servidor num GET, a RFC obriga a que viajem como parte da URI.",
      insight: "Isto é excelente para pesquisas ou paginação (ex: <code>?q=carros&amp;page=2</code>), mas expõe a senha a qualquer pessoa que olhe para o ecrã!",
      code: () => `GET /api/login?username=${encodeURIComponent(loginUserInput.value.trim() || 'anasilva')}&password=${encodeURIComponent(loginPassInput.value || 'demo123!')} HTTP/1.1`,
      badge: "GET",
      trackPercent: "0%",
      packetText: () => `?user=${(loginUserInput.value.trim() || 'anasilva').split('@')[0]}`,
      nodeId: "node-1"
    },
    {
      step: 2,
      tag: "2. Trânsito de Rede e Roteamento",
      title: "O Pedido viaja através de routers, DNS e proxies",
      what: "O computador estabelece uma ligação TCP (porta 3000) e envia a linha de requisição. A URL completa viaja através de todos os pontos intermediários da rede.",
      why: "Os intermediários de rede precisam de inspecionar a linha de requisição HTTP para saber qual o servidor de destino e se o recurso já se encontra guardado em memória cache.",
      insight: "Se a ligação for HTTP simples (sem SSL/TLS), qualquer pessoa na mesma rede Wi-Fi consegue ler a senha em texto claro ao inspecionar os pacotes com Wireshark.",
      code: () => `Host: localhost:3000\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\nAccept: application/json`,
      badge: "ROTA",
      trackPercent: "25%",
      packetText: () => "Em trânsito para localhost:3000...",
      nodeId: "node-2"
    },
    {
      step: 3,
      tag: "3. Risco: Histórico do Browser & Logs de Servidor",
      title: "A URL completa com a senha fica gravada permanentemente",
      what: "O navegador guarda a URL no Histórico de Navegação e na barra de preenchimento automático. Do lado da infraestrutura, servidores gravam a URL no ficheiro <code>access.log</code>.",
      why: "Porque para o servidor e para o browser, a Query String faz parte do endereço único do recurso (Uniform Resource Identifier). Logo, todas as regras de auditoria de tráfego registam a URL na totalidade.",
      insight: "Mesmo que o utilizador feche a página, a senha continuará gravada no ficheiro de logs do servidor e no histórico do browser de quem acedeu.",
      code: () => `127.0.0.1 - - [23/Sep/2026:11:18:00 +0100] "GET /api/login?username=anasilva&password=demo123! HTTP/1.1" 200 412`,
      badge: "ALERTA",
      trackPercent: "50%",
      packetText: () => "Gravado em access.log!",
      nodeId: "node-3"
    },
    {
      step: 4,
      tag: "4. Servidor Node.js & Base de Dados SQL",
      title: "O Servidor lê a Query e executa SELECT no SQLite",
      what: "O servidor Node.js extrai as variáveis de <code>parsedUrl.query</code>, calcula o hash SHA-256 e executa: <code>SELECT * FROM users WHERE (username = ?)</code> na base de dados <code>database.sqlite</code>.",
      why: "O backend precisa de validar se o utilizador existe e se a senha cifrada corresponde exatamente ao registo na base de dados SQL antes de conceder a sessão.",
      insight: "No Node.js, os dados do GET chegam via URL, enquanto os dados do formulário de registo (POST) chegam com segurança dentro do corpo da mensagem.",
      code: () => `const stmt = db.prepare('SELECT * FROM users WHERE (username = ?)');\nconst user = stmt.get('anasilva');\nif (user.password_hash === hash(password)) { ... }`,
      badge: "SQL",
      trackPercent: "75%",
      packetText: () => "SELECT * FROM users...",
      nodeId: "node-4"
    },
    {
      step: 5,
      tag: "5. Resposta HTTP Retornada ao Cliente",
      title: "O Servidor responde com Código 200 OK e Sessão",
      what: "O servidor Node.js devolve o payload JSON com <code>200 OK</code> e o token de sessão, finalizando o ciclo de requisição.",
      why: "O protocolo HTTP é 'stateless' (não guarda estado por padrão). Por isso, cada resposta deve informar expressamente o cliente sobre o sucesso e entregar a chave de identificação para pedidos futuros.",
      insight: "O navegador recebe o pacote de volta, fecha o loading e apresenta o ecrã de boas-vindas com a sessão iniciada.",
      code: () => `HTTP/1.1 200 OK\nContent-Type: application/json\n\n{ "success": true, "token": "jwt_...", "user": { "name": "Ana Silva" } }`,
      badge: "200 OK",
      trackPercent: "100%",
      packetText: () => "200 OK: Sessão Criada!",
      nodeId: "node-5"
    }
  ];

  let currentStep = 1;
  let isAutoPlaying = false;
  let autoPlayTimer = null;

  function goToStep(stepNumber) {
    currentStep = Math.max(1, Math.min(5, stepNumber));
    const stepData = stepsData[currentStep - 1];

    netNodes.forEach((node) => {
      const nodeStep = parseInt(node.getAttribute('data-step'), 10);
      node.classList.toggle('active', nodeStep === currentStep);
    });

    stepDots.forEach((dot) => {
      const dotStep = parseInt(dot.getAttribute('data-step'), 10);
      dot.classList.toggle('active', dotStep === currentStep);
    });

    if (packetTraveler) {
      packetTraveler.style.left = stepData.trackPercent;
    }
    if (packetBadge) {
      packetBadge.textContent = stepData.badge;
      if (stepData.badge === 'ALERTA') {
        packetBadge.style.background = '#f59e0b';
        packetBadge.style.color = '#000';
      } else if (stepData.badge === '200 OK') {
        packetBadge.style.background = '#10b981';
        packetBadge.style.color = '#fff';
      } else {
        packetBadge.style.background = '#38bdf8';
        packetBadge.style.color = '#0b0f19';
      }
    }
    if (packetInfo) {
      packetInfo.textContent = stepData.packetText();
    }

    if (stepCounterText) stepCounterText.textContent = `ETAPA ${stepData.step} DE 5`;
    if (stepStateTag) stepStateTag.textContent = stepData.tag;
    if (stepTitle) stepTitle.textContent = stepData.title;
    if (stepWhatText) stepWhatText.innerHTML = stepData.what;
    if (stepWhyText) stepWhyText.innerHTML = stepData.why;
    if (stepInsightText) stepInsightText.innerHTML = stepData.insight;
    if (stepCodePreview) stepCodePreview.textContent = stepData.code();
  }

  if (btnNext) {
    btnNext.addEventListener('click', () => {
      stopAutoSimulation();
      goToStep(currentStep < 5 ? currentStep + 1 : 1);
    });
  }

  if (btnPrev) {
    btnPrev.addEventListener('click', () => {
      stopAutoSimulation();
      goToStep(currentStep > 1 ? currentStep - 1 : 5);
    });
  }

  if (btnRestart) {
    btnRestart.addEventListener('click', () => {
      stopAutoSimulation();
      goToStep(1);
    });
  }

  netNodes.forEach((node) => {
    node.addEventListener('click', () => {
      stopAutoSimulation();
      const step = parseInt(node.getAttribute('data-step'), 10);
      goToStep(step);
    });
  });

  stepDots.forEach((dot) => {
    dot.addEventListener('click', () => {
      stopAutoSimulation();
      const step = parseInt(dot.getAttribute('data-step'), 10);
      goToStep(step);
    });
  });

  function startAutoSimulation() {
    isAutoPlaying = true;
    if (btnPlay) {
      btnPlay.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <rect x="6" y="4" width="4" height="16"></rect>
          <rect x="14" y="4" width="4" height="16"></rect>
        </svg>
        <span>Pausar</span>
      `;
    }
    clearInterval(autoPlayTimer);
    autoPlayTimer = setInterval(() => {
      if (currentStep >= 5) {
        goToStep(1);
      } else {
        goToStep(currentStep + 1);
      }
    }, 2800);
  }

  function stopAutoSimulation() {
    isAutoPlaying = false;
    clearInterval(autoPlayTimer);
    if (btnPlay) {
      btnPlay.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        <span>Animar Fluxo</span>
      `;
    }
  }

  if (btnPlay) {
    btnPlay.addEventListener('click', () => {
      if (isAutoPlaying) {
        stopAutoSimulation();
      } else {
        startAutoSimulation();
      }
    });
  }

  // Initialize
  goToStep(1);
  loadSqlTable();
  loadSqlLogs();
});
