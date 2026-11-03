// Theme Toggle Logic
const themeToggleBtn = document.getElementById('theme-toggle');
const htmlEl = document.documentElement;

// Initialize theme from localStorage or system preference
const savedTheme = localStorage.getItem('poster-theme') || 
  (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
htmlEl.setAttribute('data-theme', savedTheme);

themeToggleBtn.addEventListener('click', () => {
  const currentTheme = htmlEl.getAttribute('data-theme');
  const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
  htmlEl.setAttribute('data-theme', nextTheme);
  localStorage.setItem('poster-theme', nextTheme);
});

// Toast Notification Logic
const toast = document.getElementById('toast');
let toastTimer = null;

function showToast(message) {
  if (toastTimer) clearTimeout(toastTimer);
  const toastText = toast.querySelector('span');
  if (toastText) toastText.textContent = message || 'Citação copiada com sucesso!';
  
  toast.classList.add('show');
  toastTimer = setTimeout(() => {
    toast.classList.remove('show');
  }, 2800);
}

// Copy Citation Event Listeners
document.querySelectorAll('.btn-copy').forEach(btn => {
  btn.addEventListener('click', async () => {
    const citation = btn.getAttribute('data-cite');
    if (!citation) return;

    try {
      await navigator.clipboard.writeText(citation);
      const originalText = btn.textContent;
      btn.textContent = '✓ Copiado';
      btn.style.borderColor = 'var(--accent-teal)';
      
      showToast('Citação copiada para a área de transferência!');

      setTimeout(() => {
        btn.textContent = originalText;
        btn.style.borderColor = '';
      }, 2000);
    } catch (err) {
      // Fallback if clipboard API is restricted
      const textarea = document.createElement('textarea');
      textarea.value = citation;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      showToast('Citação copiada!');
    }
  });
});

// Filtering and Search Logic
const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search');
const filterBtns = document.querySelectorAll('.filter-btn');
const topicCards = document.querySelectorAll('.topic-card');
const noResultsEl = document.getElementById('no-results');

let currentFilter = 'all';
let searchQuery = '';

function applyFilters() {
  let visibleTopicsCount = 0;
  const term = searchQuery.trim().toLowerCase();

  topicCards.forEach(card => {
    const category = card.getAttribute('data-category');
    const matchesCategory = (currentFilter === 'all' || currentFilter === category);

    if (!matchesCategory) {
      card.classList.add('hidden');
      return;
    }

    // Filter individual items within the card if there's a search term
    const refItems = card.querySelectorAll('.ref-item, .timeline-item');
    let hasMatchingItems = false;

    refItems.forEach(item => {
      const searchData = (item.getAttribute('data-search') || '') + ' ' + (item.textContent || '');
      const itemMatches = !term || searchData.toLowerCase().includes(term);

      if (itemMatches) {
        item.style.display = '';
        hasMatchingItems = true;
      } else {
        item.style.display = 'none';
      }
    });

    if (matchesCategory && (hasMatchingItems || !term)) {
      card.classList.remove('hidden');
      visibleTopicsCount++;
    } else {
      card.classList.add('hidden');
    }
  });

  // Handle no results
  if (visibleTopicsCount === 0) {
    noResultsEl.classList.remove('hidden');
  } else {
    noResultsEl.classList.add('hidden');
  }
}

// Search input handling
searchInput.addEventListener('input', (e) => {
  searchQuery = e.target.value;
  if (searchQuery.length > 0) {
    clearSearchBtn.classList.add('visible');
  } else {
    clearSearchBtn.classList.remove('visible');
  }
  applyFilters();
});

clearSearchBtn.addEventListener('click', () => {
  searchInput.value = '';
  searchQuery = '';
  clearSearchBtn.classList.remove('visible');
  searchInput.focus();
  applyFilters();
});

// Filter Tabs Handling
filterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    filterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.getAttribute('data-filter');
    applyFilters();
  });
});
