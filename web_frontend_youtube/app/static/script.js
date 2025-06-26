document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT ---
    // Holds the current state of the UI. All user actions modify this state.
    const state = {
        currentPage: 1,
        isLoading: false,
        hasMore: true,
        activeView: 'unwatched', // Default view on load
        viewMode: 'cards', // 'cards' or 'list'
        sortBy: 'date-desc',
        searchQuery: '',
    };

    // --- DOM ELEMENTS ---
    const videoGrid = document.getElementById('video-grid');
    const loader = document.getElementById('loader');
    const endOfResultsMessage = document.getElementById('end-of-results');
    const contentTitle = document.getElementById('content-title');
    const searchInput = document.getElementById('search-input');
    const sortSelect = document.getElementById('sort-select');
    const navLinks = document.querySelectorAll('.nav-link');
    const viewButtons = document.querySelectorAll('.view-btn');
    const themeToggleButton = document.getElementById('theme-toggle');

    // --- THEME MANAGER ---
    // Handles light/dark/auto theme switching.
    class ThemeManager {
        constructor() {
            this.theme = localStorage.getItem('theme') || 'auto';
            this.sunIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>`;
            this.moonIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>`;
            this.applyTheme();
        }

        applyTheme() {
            const root = document.documentElement;
            if (this.theme === 'auto') {
                root.removeAttribute('data-color-scheme');
                const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                themeToggleButton.innerHTML = prefersDark ? this.moonIcon : this.sunIcon;
            } else {
                root.setAttribute('data-color-scheme', this.theme);
                themeToggleButton.innerHTML = this.theme === 'dark' ? this.moonIcon : this.sunIcon;
            }
            localStorage.setItem('theme', this.theme);
        }

        toggle() {
            const themes = ['auto', 'light', 'dark'];
            this.theme = themes[(themes.indexOf(this.theme) + 1) % themes.length];
            this.applyTheme();
        }
    }
    const themeManager = new ThemeManager();

    // --- DATA FETCHING & RENDERING ---

    /**
     * Fetches videos from the API based on the current state.
     * @param {boolean} isNewSearch - If true, clears existing content before fetching.
     */
    async function fetchVideos(isNewSearch = false) {
        if (state.isLoading) return;
        state.isLoading = true;

        if (isNewSearch) {
            state.currentPage = 1;
            state.hasMore = true;
            videoGrid.innerHTML = '';
            endOfResultsMessage.style.display = 'none';
        }

        loader.style.display = 'flex';

        const params = new URLSearchParams({
            page: state.currentPage,
            view: state.activeView,
            search: state.searchQuery,
            sort_by: state.sortBy,
        });

        try {
            const response = await fetch(`/api/feeds?${params.toString()}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();

            if (data.feeds.length === 0 && state.currentPage === 1) {
                videoGrid.innerHTML = `<p style="text-align: center; color: var(--color-text-secondary); grid-column: 1 / -1;">No videos found for this view.</p>`;
            } else {
                data.feeds.forEach(video => {
                    videoGrid.insertAdjacentHTML('beforeend', getVideoCardHTML(video));
                });
            }

            state.hasMore = data.has_more;
            if (!state.hasMore) {
                endOfResultsMessage.style.display = 'block';
            }
        } catch (error) {
            console.error('Error fetching videos:', error);
            videoGrid.innerHTML = `<p style="text-align: center; color: var(--color-error); grid-column: 1 / -1;">Failed to load videos. Please try again later.</p>`;
        } finally {
            state.isLoading = false;
            loader.style.display = 'none';
        }
    }

    /**
     * Generates the HTML for a single video card.
     * @param {object} video - The video data object.
     * @returns {string} The HTML string for the video card.
     */
    function getVideoCardHTML(video) {
        const isListView = state.viewMode === 'list';
        const cardClass = `video-card ${isListView ? 'list-view' : ''} ${video.watched ? 'read' : ''}`;
        const thumbnail = video.thumbnail_url || 'https://placehold.co/1280x720/000000/FFFFFF?text=No+Thumbnail';

        return `
        <div class="${cardClass}" data-url="${video.link}" data-watched="${video.watched}" data-bookmarked="${video.bookmarked}">
        <a href="${video.link}" target="_blank" rel="noopener noreferrer" class="video-thumbnail" onclick="handleThumbnailClick(event)">
        <img src="${thumbnail}" alt="${escapeHtml(video.title)}" loading="lazy" onerror="this.onerror=null;this.src='https://placehold.co/1280x720/000000/FFFFFF?text=Error';">
        </a>
        <div class="video-content">
        <h3 class="video-title">${escapeHtml(video.title)}</h3>
        <div class="video-meta">
        <span class="video-channel">${escapeHtml(video.author)}</span>
        <span class="video-date">${video.date}</span>
        </div>
        <div class="video-actions">
        <button class="action-btn bookmark-btn ${video.bookmarked ? 'active' : ''}" onclick="toggleBookmark(event)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>
        <span class="btn-text">${video.bookmarked ? 'Bookmarked' : 'Bookmark'}</span>
        </button>
        <button class="action-btn watch-btn" onclick="toggleWatched(event)">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
        <span class="btn-text">${video.watched ? 'Mark Unwatched' : 'Mark Watched'}</span>
        </button>
        </div>
        </div>
        </div>
        `;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // --- EVENT HANDLERS & UI UPDATES ---

    /**
     * Updates the UI and fetches new data when a filter changes.
     * @param {function} updateAction - A function that modifies the state.
     */
    function handleFilterChange(updateAction) {
        updateAction();
        fetchVideos(true);
        updateUI();
    }

    /**
     * Updates static parts of the UI like titles and active states.
     */
    function updateUI() {
        // Update content title
        const currentLink = document.querySelector(`.nav-link[data-view="${state.activeView}"]`);
        contentTitle.textContent = currentLink ? currentLink.textContent : 'Videos';

        // Update active nav link
        navLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.view === state.activeView);
        });
    }

    // --- GLOBAL ACTION FUNCTIONS (attached to window for inline onclick) ---

    window.handleThumbnailClick = (event) => {
        const card = event.currentTarget.closest('.video-card');
        if (card && !JSON.parse(card.dataset.watched)) {
            performWatchAction(card, 'read'); // Mark as read on click
        }
        // The default action (opening the link) will proceed.
    };

    window.toggleBookmark = async (event) => {
        event.stopPropagation();
        const button = event.currentTarget;
        const card = button.closest('.video-card');
        if (!card || button.disabled) return;

        const isBookmarked = JSON.parse(card.dataset.bookmarked);
        const action = isBookmarked ? 'remove' : 'add';
        button.disabled = true;

        try {
            const response = await fetch('/bookmark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: card.dataset.url, action }),
            });
            const data = await response.json();
            if (data.success) {
                card.dataset.bookmarked = (action === 'add');
                button.classList.toggle('active', action === 'add');
                button.querySelector('.btn-text').textContent = action === 'add' ? 'Bookmarked' : 'Bookmark';
                // If in bookmarks view and removing, hide the card.
                if (state.activeView === 'bookmarked' && action === 'remove') {
                    card.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error toggling bookmark:', error);
        } finally {
            button.disabled = false;
        }
    };

    window.toggleWatched = (event) => {
        event.stopPropagation();
        const card = event.currentTarget.closest('.video-card');
        if(!card) return;

        const isWatched = JSON.parse(card.dataset.watched);
        const action = isWatched ? 'unread' : 'read';
        performWatchAction(card, action);
    };

    async function performWatchAction(card, action) {
        const button = card.querySelector('.watch-btn');
        if (!card || button.disabled) return;

        button.disabled = true;

        try {
            const response = await fetch('/mark_watched', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: card.dataset.url, action }),
            });
            const data = await response.json();
            if (data.success) {
                const isNowWatched = (action === 'read');
                card.dataset.watched = isNowWatched;
                card.classList.toggle('read', isNowWatched);
                button.querySelector('.btn-text').textContent = isNowWatched ? 'Mark Unwatched' : 'Mark Watched';

                // Hide card if it no longer matches the current view
                if ((state.activeView === 'unwatched' && isNowWatched) || (state.activeView === 'watched' && !isNowWatched)) {
                    card.style.display = 'none';
                }
            }
        } catch (error) {
            console.error('Error toggling watched state:', error);
        } finally {
            button.disabled = false;
        }
    }


    // --- EVENT LISTENERS ---

    // Infinite scroll
    window.addEventListener('scroll', () => {
        if (state.isLoading || !state.hasMore) return;
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
            state.currentPage++;
            fetchVideos(false);
        }
    }, { passive: true });

    // Navigation
    navLinks.forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            handleFilterChange(() => state.activeView = link.dataset.view);
        });
    });

    // View mode (cards/list)
    viewButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (state.viewMode === btn.dataset.viewMode) return;
            state.viewMode = btn.dataset.viewMode;
            videoGrid.classList.toggle('list-view', state.viewMode === 'list');
            viewButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Sorting
    sortSelect.addEventListener('change', () => {
        handleFilterChange(() => state.sortBy = sortSelect.value);
    });

    // Search (with debounce)
    let searchTimeout;
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            handleFilterChange(() => state.searchQuery = searchInput.value.trim());
        }, 300);
    });

    document.getElementById('search-btn').addEventListener('click', () => {
        handleFilterChange(() => state.searchQuery = searchInput.value.trim());
    });

    // Theme toggle
    themeToggleButton.addEventListener('click', () => themeManager.toggle());
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => themeManager.applyTheme());


    // --- INITIALIZATION ---
    function initialize() {
        updateUI();
        fetchVideos(true);
    }

    initialize();
});
