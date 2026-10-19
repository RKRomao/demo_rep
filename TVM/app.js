/**
 * TVM - IPTV Reader & Controller
 * Application Logic & HLS Player Integration
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- Application State ---
  const state = {
    channels: [],
    filteredChannels: [],
    categories: ['Todos', 'Favoritos'],
    currentCategory: 'Todos',
    searchQuery: '',
    currentIndex: -1,
    favorites: new Set(JSON.parse(localStorage.getItem('tvm_favorites') || '[]')),
    hls: null,
    remoteOpen: false,
    useCorsProxy: true,
    aspectRatios: ['contain', 'cover', 'fill'],
    currentAspectIdx: 0,
    digitBuffer: '',
    digitTimer: null
  };

  // --- DOM Elements ---
  const dom = {
    video: document.getElementById('video-element'),
    playerPlaceholder: document.getElementById('player-placeholder'),
    channelList: document.getElementById('channel-list'),
    channelCount: document.getElementById('channel-count'),
    searchInput: document.getElementById('search-input'),
    categoryTabs: document.getElementById('category-tabs'),
    
    // Banner & Info
    bannerTitle: document.getElementById('banner-title'),
    currentTitle: document.getElementById('current-title'),
    currentCategory: document.getElementById('current-category'),
    currentLogo: document.getElementById('current-logo'),
    statGroup: document.getElementById('stat-group'),
    statQuality: document.getElementById('stat-quality'),
    statStatus: document.getElementById('stat-status'),
    
    // Player Controls
    btnPlayPause: document.getElementById('btn-play-pause'),
    btnPrev: document.getElementById('btn-prev'),
    btnNext: document.getElementById('btn-next'),
    btnFav: document.getElementById('btn-fav'),
    btnMute: document.getElementById('btn-mute'),
    volumeSlider: document.getElementById('volume-slider'),
    btnAspect: document.getElementById('btn-aspect'),
    btnPip: document.getElementById('btn-pip'),
    btnFullscreen: document.getElementById('btn-fullscreen'),
    
    // Remote & Header Actions
    btnCheckHealth: document.getElementById('btn-check-health'),
    btnToggleCors: document.getElementById('btn-toggle-cors'),
    btnToggleRemote: document.getElementById('btn-toggle-remote'),
    remoteDrawer: document.getElementById('remote-drawer'),
    btnCloseRemote: document.getElementById('btn-close-remote'),
    
    // Modals
    btnLoadPlaylist: document.getElementById('btn-load-playlist'),
    modalImport: document.getElementById('modal-import'),
    btnCloseModal: document.getElementById('btn-close-modal'),
    playlistUrlInput: document.getElementById('playlist-url-input'),
    btnFetchUrl: document.getElementById('btn-fetch-url'),
    playlistFileInput: document.getElementById('playlist-file-input'),
    fileDropzone: document.getElementById('file-dropzone'),
    rawM3uInput: document.getElementById('raw-m3u-input'),
    btnParseRaw: document.getElementById('btn-parse-raw'),
    btnLoadSample: document.getElementById('btn-load-sample'),
    toastContainer: document.getElementById('toast-container')
  };

  // --- Initialization ---
  init();

  function init() {
    setupEventListeners();
    setupRemotePad();
    
    // Always load clean sample playlist on start
    loadSamplePlaylist();
  }

  // --- Event Listeners Setup ---
  function setupEventListeners() {
    // Search
    dom.searchInput.addEventListener('input', (e) => {
      state.searchQuery = e.target.value.toLowerCase();
      applyFilters();
    });

    // Player Controls
    dom.btnPlayPause.addEventListener('click', togglePlayPause);
    dom.btnPrev.addEventListener('click', playPreviousChannel);
    dom.btnNext.addEventListener('click', playNextChannel);
    dom.btnFav.addEventListener('click', toggleCurrentFavorite);
    
    dom.btnMute.addEventListener('click', toggleMute);
    dom.volumeSlider.addEventListener('input', (e) => {
      const vol = parseFloat(e.target.value);
      dom.video.volume = vol;
      dom.video.muted = (vol === 0);
      updateVolumeIcon();
    });

    dom.btnAspect.addEventListener('click', cycleAspectRatio);
    dom.btnPip.addEventListener('click', togglePip);
    dom.btnFullscreen.addEventListener('click', toggleFullscreen);

    // Check Channel Health & Filter Working Streams
    if (dom.btnCheckHealth) {
      dom.btnCheckHealth.addEventListener('click', () => {
        checkAllChannelsHealth();
      });
    }

    // CORS Toggle
    if (dom.btnToggleCors) {
      dom.btnToggleCors.addEventListener('click', () => {
        state.useCorsProxy = !state.useCorsProxy;
        if (state.useCorsProxy) {
          dom.btnToggleCors.innerHTML = '<i class="ph-bold ph-shield-check"></i> Proxy CORS: ON';
          dom.btnToggleCors.classList.add('btn-primary');
          showToast('Proxy CORS Ativado');
        } else {
          dom.btnToggleCors.innerHTML = '<i class="ph-bold ph-shield"></i> Proxy CORS: OFF';
          dom.btnToggleCors.classList.remove('btn-primary');
          showToast('Proxy CORS Desativado');
        }
        if (state.currentIndex >= 0) {
          playChannel(state.currentIndex);
        }
      });
    }

    // Remote Drawer Toggle
    dom.btnToggleRemote.addEventListener('click', () => toggleRemote(true));
    dom.btnCloseRemote.addEventListener('click', () => toggleRemote(false));

    // Modals
    dom.btnLoadPlaylist.addEventListener('click', () => dom.modalImport.classList.add('open'));
    dom.btnCloseModal.addEventListener('click', () => dom.modalImport.classList.remove('open'));
    
    dom.btnFetchUrl.addEventListener('click', fetchPlaylistFromUrl);
    
    dom.fileDropzone.addEventListener('click', () => dom.playlistFileInput.click());
    dom.playlistFileInput.addEventListener('change', handleFileSelect);
    
    dom.btnParseRaw.addEventListener('click', () => {
      const text = dom.rawM3uInput.value.trim();
      if (text) {
        parseAndLoadM3U(text);
        dom.modalImport.classList.remove('open');
        showToast('Lista personalizada carregada!');
      }
    });

    dom.btnLoadSample.addEventListener('click', () => {
      loadSamplePlaylist();
      dom.modalImport.classList.remove('open');
    });

    // Video Events
    dom.video.addEventListener('play', () => {
      dom.btnPlayPause.innerHTML = '<i class="ph-bold ph-pause"></i>';
      dom.statStatus.innerHTML = '<i class="ph-bold ph-broadcast"></i> Reproduzindo';
    });

    dom.video.addEventListener('pause', () => {
      dom.btnPlayPause.innerHTML = '<i class="ph-bold ph-play"></i>';
      dom.statStatus.innerHTML = '<i class="ph-bold ph-pause-circle"></i> Pausado';
    });

    dom.video.addEventListener('loadedmetadata', () => {
      if (dom.video.videoWidth && dom.video.videoHeight) {
        dom.statQuality.textContent = `${dom.video.videoWidth}x${dom.video.videoHeight}`;
      }
    });

    dom.video.addEventListener('error', (e) => {
      console.warn('Video element error:', e);
      dom.statStatus.innerHTML = '<i class="ph-bold ph-warning-circle"></i> Erro no Stream';
    });

    // Global Keyboard Shortcuts
    document.addEventListener('keydown', handleGlobalKeydown);
  }

  // --- M3U / M3U8 Parser ---
  function parseM3U(m3uText) {
    const lines = m3uText.split(/\r?\n/);
    const channels = [];
    let currentChannel = null;
    let channelNumber = 1;
    const categoriesSet = new Set();

    for (let i = 0; i < lines.length; i++) {
      let line = lines[i].trim();
      if (!line) continue;

      if (line.startsWith('#EXTINF:')) {
        currentChannel = {
          id: `ch_${channelNumber}`,
          number: channelNumber,
          title: 'Canal sem nome',
          logo: '',
          group: 'Outros',
          url: '',
          status: 'unknown',
          userAgent: '',
          referer: ''
        };

        // Extract attributes using Regex
        const logoMatch = line.match(/tvg-logo="([^"]+)"/i);
        if (logoMatch) currentChannel.logo = logoMatch[1];

        const groupMatch = line.match(/group-title="([^"]+)"/i);
        if (groupMatch) {
          currentChannel.group = groupMatch[1];
          categoriesSet.add(groupMatch[1]);
        }

        const nameMatch = line.match(/tvg-name="([^"]+)"/i);
        if (nameMatch) currentChannel.title = nameMatch[1];

        const uaMatch = line.match(/http-user-agent="([^"]+)"/i);
        if (uaMatch) currentChannel.userAgent = uaMatch[1];

        const refMatch = line.match(/http-referrer="([^"]+)"/i);
        if (refMatch) currentChannel.referer = refMatch[1];

        // Title after the comma
        const commaIndex = line.lastIndexOf(',');
        if (commaIndex !== -1) {
          const parsedTitle = line.substring(commaIndex + 1).trim();
          if (parsedTitle) currentChannel.title = parsedTitle;
        }
      } else if (line.startsWith('#EXTVLCOPT:')) {
        if (currentChannel) {
          const uaOpt = line.match(/http-user-agent=(.+)/i);
          if (uaOpt) currentChannel.userAgent = uaOpt[1].trim();
          const refOpt = line.match(/http-referrer=(.+)/i);
          if (refOpt) currentChannel.referer = refOpt[1].trim();
        }
      } else if (!line.startsWith('#') && line.length > 5) {
        // Line is stream URL
        if (currentChannel) {
          currentChannel.url = line;
          channels.push(currentChannel);
          channelNumber++;
          currentChannel = null;
        } else {
          // Plain URL without #EXTINF
          channels.push({
            id: `ch_${channelNumber}`,
            number: channelNumber,
            title: `Canal ${channelNumber}`,
            logo: '',
            group: 'Geral',
            url: line
          });
          categoriesSet.add('Geral');
          channelNumber++;
        }
      }
    }

    const sortedCategories = ['Todos', 'Favoritos', ...Array.from(categoriesSet).sort()];
    return { channels, categories: sortedCategories };
  }

  function parseAndLoadM3U(m3uText) {
    const result = parseM3U(m3uText);
    if (!result.channels.length) {
      showToast('Nenhum canal válido encontrado na lista!');
      return;
    }

    state.channels = result.channels;
    state.categories = result.categories;
    state.currentCategory = 'Todos';

    // Save to localStorage
    try {
      localStorage.setItem('tvm_current_m3u', m3uText);
    } catch (e) {
      console.warn('Storage limit exceeded');
    }

    renderCategoryTabs();
    applyFilters();
    showToast(`Carregados ${state.channels.length} canais!`);

    // Auto play first channel
    if (state.channels.length > 0) {
      playChannel(0);
    }
  }

  function loadSamplePlaylist() {
    fetch('sample_playlist.m3u')
      .then(res => res.text())
      .then(text => {
        parseAndLoadM3U(text);
        showToast('Lista IPTV de Portugal (Verificada) carregada!');
      })
      .catch(err => {
        console.error('Failed to load sample playlist:', err);
        showToast('Erro ao carregar lista.');
      });
  }

  function fetchPlaylistFromUrl() {
    const url = dom.playlistUrlInput.value.trim();
    if (!url) {
      showToast('Por favor insira um URL válido.');
      return;
    }

    showToast('Baixando lista IPTV...');
    fetch(url)
      .then(res => res.text())
      .then(text => {
        parseAndLoadM3U(text);
        dom.modalImport.classList.remove('open');
      })
      .catch(err => {
        console.error('Error fetching playlist:', err);
        showToast('Erro ao obter URL. Verifique as permissões de CORS.');
      });
  }

  function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (evt) => {
      parseAndLoadM3U(evt.target.result);
      dom.modalImport.classList.remove('open');
      showToast(`Arquivo "${file.name}" carregado!`);
    };
    reader.readAsText(file);
  }

  // --- Rendering UI ---
  function renderCategoryTabs() {
    dom.categoryTabs.innerHTML = '';
    state.categories.forEach(cat => {
      const btn = document.createElement('button');
      btn.className = `tab-btn ${cat === state.currentCategory ? 'active' : ''}`;
      btn.textContent = cat;
      btn.addEventListener('click', () => {
        state.currentCategory = cat;
        renderCategoryTabs();
        applyFilters();
      });
      dom.categoryTabs.appendChild(btn);
    });
  }

  function applyFilters() {
    let list = state.channels;

    // Filter by Category
    if (state.currentCategory === 'Favoritos') {
      list = list.filter(ch => state.favorites.has(ch.id) || state.favorites.has(ch.url));
    } else if (state.currentCategory === 'On-line (Ativos)') {
      list = list.filter(ch => ch.status === 'online');
    } else if (state.currentCategory !== 'Todos') {
      list = list.filter(ch => ch.group === state.currentCategory);
    }

    // Filter by Search Query
    if (state.searchQuery) {
      list = list.filter(ch => 
        ch.title.toLowerCase().includes(state.searchQuery) ||
        ch.group.toLowerCase().includes(state.searchQuery) ||
        ch.number.toString().includes(state.searchQuery)
      );
    }

    state.filteredChannels = list;
    renderChannelList();
  }

  function renderChannelList() {
    dom.channelList.innerHTML = '';
    dom.channelCount.textContent = `${state.filteredChannels.length} canais`;

    if (!state.filteredChannels.length) {
      dom.channelList.innerHTML = `
        <div style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
          <i class="ph-bold ph-television" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
          Nenhum canal encontrado nesta categoria.
        </div>
      `;
      return;
    }

    state.filteredChannels.forEach((ch, idx) => {
      const isCurrent = state.currentIndex >= 0 && state.channels[state.currentIndex]?.id === ch.id;
      const isFav = state.favorites.has(ch.id) || state.favorites.has(ch.url);

      const card = document.createElement('div');
      card.className = `channel-card ${isCurrent ? 'active' : ''}`;
      
      const logoHtml = ch.logo 
        ? `<img src="${ch.logo}" alt="" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"><i class="ph-bold ph-tv" style="display:none;"></i>`
        : `<i class="ph-bold ph-tv"></i>`;

      let statusDot = '';
      if (ch.status === 'online') {
        statusDot = `<span class="status-dot online" title="Sinal Ativo"></span>`;
      } else if (ch.status === 'offline') {
        statusDot = `<span class="status-dot offline" title="Indisponível / Off-line"></span>`;
      } else if (ch.status === 'checking') {
        statusDot = `<span class="status-dot checking" title="Verificando..."></span>`;
      }

      card.innerHTML = `
        <div class="channel-num">${ch.number}</div>
        <div class="channel-logo">${logoHtml}</div>
        <div class="channel-details">
          <div class="channel-title">${statusDot}${escapeHtml(ch.title)}</div>
          <div class="channel-group">${escapeHtml(ch.group)}</div>
        </div>
        <button class="channel-fav ${isFav ? 'active' : ''}" title="Favorito">
          <i class="ph-fill ph-star"></i>
        </button>
      `;

      // Select Channel
      card.addEventListener('click', (e) => {
        if (e.target.closest('.channel-fav')) return; // Ignore fav button click
        const realIndex = state.channels.findIndex(c => c.id === ch.id);
        if (realIndex !== -1) playChannel(realIndex);
      });

      // Toggle Fav
      card.querySelector('.channel-fav').addEventListener('click', () => {
        toggleFavorite(ch.id);
      });

      dom.channelList.appendChild(card);
    });
  }

  // --- Channel Playback Logic ---
  function playChannel(index) {
    if (index < 0 || index >= state.channels.length) return;

    state.currentIndex = index;
    const channel = state.channels[index];

    // Hide placeholder
    if (dom.playerPlaceholder) {
      dom.playerPlaceholder.style.display = 'none';
    }

    // Update UI Meta
    dom.bannerTitle.textContent = `${channel.number}. ${channel.title}`;
    dom.currentTitle.textContent = `${channel.number}. ${channel.title}`;
    dom.currentCategory.textContent = channel.group;
    dom.statGroup.textContent = channel.group;
    dom.statStatus.innerHTML = '<i class="ph-bold ph-spinner ph-spin"></i> Carregando...';
    
    if (channel.logo) {
      dom.currentLogo.src = channel.logo;
      dom.currentLogo.style.display = 'block';
    } else {
      dom.currentLogo.style.display = 'none';
    }

    // Favorite Button state
    const isFav = state.favorites.has(channel.id) || state.favorites.has(channel.url);
    dom.btnFav.style.color = isFav ? '#ffca28' : '#fff';

    // Highlight in Sidebar
    renderChannelList();

    // Scroll to current channel card in sidebar if visible
    const activeCard = dom.channelList.querySelector('.channel-card.active');
    if (activeCard) {
      activeCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // Stream Execution via local Node.js CORS Proxy
    let streamUrl = channel.url;
    let proxyTried = false;

    if (channel.url.startsWith('http://') || channel.url.startsWith('https://')) {
      streamUrl = `/api/proxy?url=${encodeURIComponent(channel.url)}`;
      if (channel.userAgent) streamUrl += `&user-agent=${encodeURIComponent(channel.userAgent)}`;
      if (channel.referer) streamUrl += `&referer=${encodeURIComponent(channel.referer)}`;
      proxyTried = true;
    }
    
    // Destroy previous HLS instance if active
    if (state.hls) {
      state.hls.destroy();
      state.hls = null;
    }

    if (streamUrl.includes('.m3u8') || streamUrl.includes('hls') || channel.url.includes('.m3u8')) {
      if (Hls.isSupported()) {
        const hls = new Hls({
          enableWorker: true,
          lowLatencyMode: true
        });
        hls.loadSource(streamUrl);
        hls.attachMedia(dom.video);
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          safePlay();
        });
        hls.on(Hls.Events.ERROR, (event, data) => {
          if (data.fatal) {
            switch (data.type) {
              case Hls.ErrorTypes.NETWORK_ERROR:
                if (!proxyTried && (channel.url.startsWith('http://') || channel.url.startsWith('https://'))) {
                  proxyTried = true;
                  showToast('Servidor com CORS bloqueado. Ativando Proxy Local...');
                  const proxiedUrl = `/api/proxy?url=${encodeURIComponent(channel.url)}`;
                  hls.loadSource(proxiedUrl);
                  hls.startLoad();
                } else {
                  channel.status = 'offline';
                  renderChannelList();
                  dom.statStatus.innerHTML = '<i class="ph-bold ph-warning-circle"></i> Indisponível (404)';
                  showToast(`Canal "${channel.title}" está indisponível/off-line.`);
                  hls.destroy();
                }
                break;
              case Hls.ErrorTypes.MEDIA_ERROR:
                hls.recoverMediaError();
                break;
              default:
                channel.status = 'offline';
                renderChannelList();
                dom.statStatus.innerHTML = '<i class="ph-bold ph-warning-circle"></i> Erro de Conexão';
                hls.destroy();
                break;
            }
          }
        });
        state.hls = hls;
      } else if (dom.video.canPlayType('application/vnd.apple.mpegurl')) {
        // Safari native HLS
        dom.video.src = streamUrl;
        safePlay();
      }
    } else {
      // Direct MP4 / MP3 stream
      dom.video.src = streamUrl;
      safePlay();
    }
  }

  function playNextChannel() {
    if (!state.channels.length) return;
    let nextIdx = state.currentIndex + 1;
    if (nextIdx >= state.channels.length) nextIdx = 0;
    playChannel(nextIdx);
  }

  function playPreviousChannel() {
    if (!state.channels.length) return;
    let prevIdx = state.currentIndex - 1;
    if (prevIdx < 0) prevIdx = state.channels.length - 1;
    playChannel(prevIdx);
  }

  function safePlay() {
    const promise = dom.video.play();
    if (promise !== undefined) {
      promise.catch(err => {
        if (err.name === 'AbortError') {
          // Expected behavior when rapidly switching channels or resetting source
          return;
        }
        if (err.name === 'NotAllowedError') {
          showToast('Clique no player para iniciar o vídeo (Interação do usuário requerida pelo navegador).');
        } else {
          console.log('Video play info:', err.message);
        }
      });
    }
  }

  function togglePlayPause() {
    if (dom.video.paused) {
      safePlay();
    } else {
      dom.video.pause();
    }
  }

  function toggleMute() {
    dom.video.muted = !dom.video.muted;
    updateVolumeIcon();
  }

  function updateVolumeIcon() {
    if (dom.video.muted || dom.video.volume === 0) {
      dom.btnMute.innerHTML = '<i class="ph-bold ph-speaker-slash"></i>';
    } else if (dom.video.volume < 0.5) {
      dom.btnMute.innerHTML = '<i class="ph-bold ph-speaker-low"></i>';
    } else {
      dom.btnMute.innerHTML = '<i class="ph-bold ph-speaker-high"></i>';
    }
  }

  function cycleAspectRatio() {
    state.currentAspectIdx = (state.currentAspectIdx + 1) % state.aspectRatios.length;
    const mode = state.aspectRatios[state.currentAspectIdx];
    dom.video.style.objectFit = mode;
    showToast(`Proporção de vídeo: ${mode.toUpperCase()}`);
  }

  function togglePip() {
    if (document.pictureInPictureElement) {
      document.exitPictureInPicture();
    } else if (dom.video && dom.video.requestPictureInPicture) {
      dom.video.requestPictureInPicture();
    }
  }

  function toggleFullscreen() {
    const container = document.querySelector('.player-wrapper');
    if (!document.fullscreenElement) {
      if (container.requestFullscreen) container.requestFullscreen();
    } else {
      if (document.exitFullscreen) document.exitFullscreen();
    }
  }

  // --- Favorites Management ---
  function toggleFavorite(id) {
    if (state.favorites.has(id)) {
      state.favorites.delete(id);
      showToast('Canal removido dos Favoritos');
    } else {
      state.favorites.add(id);
      showToast('Canal adicionado aos Favoritos!');
    }
    localStorage.setItem('tvm_favorites', JSON.stringify(Array.from(state.favorites)));
    renderChannelList();
    if (state.currentIndex >= 0) {
      const channel = state.channels[state.currentIndex];
      const isFav = state.favorites.has(channel.id);
      dom.btnFav.style.color = isFav ? '#ffca28' : '#fff';
    }
  }

  function toggleCurrentFavorite() {
    if (state.currentIndex >= 0) {
      toggleFavorite(state.channels[state.currentIndex].id);
    }
  }

  // --- Remote Control Drawer & Virtual Remote ---
  function toggleRemote(open) {
    state.remoteOpen = open;
    if (open) {
      dom.remoteDrawer.classList.add('open');
    } else {
      dom.remoteDrawer.classList.remove('open');
    }
  }

  function setupRemotePad() {
    const padContainer = document.getElementById('remote-pad-keys');
    if (!padContainer) return;

    padContainer.addEventListener('click', (e) => {
      const btn = e.target.closest('.r-btn');
      if (!btn) return;

      const key = btn.dataset.key;
      const action = btn.dataset.action;

      if (key !== undefined) {
        handleDigitInput(key);
      } else if (action) {
        handleRemoteAction(action);
      }
    });
  }

  function handleDigitInput(digit) {
    state.digitBuffer += digit;
    showToast(`Canal: ${state.digitBuffer}`);

    clearTimeout(state.digitTimer);
    state.digitTimer = setTimeout(() => {
      const targetNum = parseInt(state.digitBuffer, 10);
      const targetIndex = state.channels.findIndex(ch => ch.number === targetNum);
      if (targetIndex !== -1) {
        playChannel(targetIndex);
      } else {
        showToast(`Canal ${targetNum} não encontrado!`);
      }
      state.digitBuffer = '';
    }, 1200);
  }

  function handleRemoteAction(action) {
    switch (action) {
      case 'power':
        if (!dom.video.paused) {
          dom.video.pause();
          showToast('TV em Standby');
        } else {
          dom.video.play();
        }
        break;
      case 'ch-up':
        playNextChannel();
        break;
      case 'ch-down':
        playPreviousChannel();
        break;
      case 'vol-up':
        dom.video.volume = Math.min(1, dom.video.volume + 0.1);
        dom.volumeSlider.value = dom.video.volume;
        updateVolumeIcon();
        break;
      case 'vol-down':
        dom.video.volume = Math.max(0, dom.video.volume - 0.1);
        dom.volumeSlider.value = dom.video.volume;
        updateVolumeIcon();
        break;
      case 'mute':
        toggleMute();
        break;
      case 'play-pause':
        togglePlayPause();
        break;
      case 'fav':
        toggleCurrentFavorite();
        break;
      case 'cat-fav':
        state.currentCategory = 'Favoritos';
        renderCategoryTabs();
        applyFilters();
        break;
      case 'cat-movies':
        state.currentCategory = 'Filmes';
        renderCategoryTabs();
        applyFilters();
        break;
      case 'cat-sports':
        state.currentCategory = 'Esportes';
        renderCategoryTabs();
        applyFilters();
        break;
      case 'cat-news':
        state.currentCategory = 'Notícias';
        renderCategoryTabs();
        applyFilters();
        break;
    }
  }

  // --- Keyboard Shortcuts ---
  function handleGlobalKeydown(e) {
    if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault();
        playPreviousChannel();
        break;
      case 'ArrowDown':
        e.preventDefault();
        playNextChannel();
        break;
      case ' ':
        e.preventDefault();
        togglePlayPause();
        break;
      case 'f':
      case 'F':
        toggleFullscreen();
        break;
      case 'm':
      case 'M':
        toggleMute();
        break;
      case 'r':
      case 'R':
        toggleRemote(!state.remoteOpen);
        break;
      default:
        if (e.key >= '0' && e.key <= '9') {
          handleDigitInput(e.key);
        }
        break;
    }
  }

  // --- Stream Health Checking ---
  async function checkAllChannelsHealth() {
    if (!state.channels.length) {
      showToast('Nenhum canal para verificar.');
      return;
    }

    showToast('Verificando conexões de todos os canais...');
    if (dom.btnCheckHealth) {
      dom.btnCheckHealth.innerHTML = '<i class="ph-bold ph-spinner ph-spin"></i> Verificando...';
      dom.btnCheckHealth.disabled = true;
    }

    state.channels.forEach(ch => ch.status = 'checking');
    renderChannelList();

    let onlineCount = 0;
    const batchSize = 5;

    for (let i = 0; i < state.channels.length; i += batchSize) {
      const batch = state.channels.slice(i, i + batchSize);
      await Promise.all(batch.map(async (ch) => {
        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 4500);
          
          let testUrl = ch.url;
          if (state.useCorsProxy && (ch.url.startsWith('http://') || ch.url.startsWith('https://'))) {
            testUrl = `/api/proxy?url=${encodeURIComponent(ch.url)}`;
            if (ch.userAgent) testUrl += `&user-agent=${encodeURIComponent(ch.userAgent)}`;
            if (ch.referer) testUrl += `&referer=${encodeURIComponent(ch.referer)}`;
          }

          const res = await fetch(testUrl, {
            method: 'GET',
            signal: controller.signal
          });
          clearTimeout(timeoutId);

          if (res.ok) {
            ch.status = 'online';
            onlineCount++;
          } else {
            ch.status = 'offline';
          }
        } catch (err) {
          ch.status = 'offline';
        }
      }));
      renderChannelList();
    }

    if (!state.categories.includes('On-line (Ativos)')) {
      state.categories.splice(2, 0, 'On-line (Ativos)');
      renderCategoryTabs();
    }

    if (dom.btnCheckHealth) {
      dom.btnCheckHealth.innerHTML = '<i class="ph-bold ph-pulse"></i> Testar Conexões';
      dom.btnCheckHealth.disabled = false;
    }

    showToast(`Verificação concluída! ${onlineCount} canais ON-LINE.`);
    state.currentCategory = 'On-line (Ativos)';
    renderCategoryTabs();
    applyFilters();
  }

  // --- Utility Functions ---
  function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    dom.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 3000);
  }

  function escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
});
