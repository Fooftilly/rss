document.addEventListener('DOMContentLoaded', () => {
    // --- STATE MANAGEMENT ---
    const state = {
        currentPage: 1,
        isLoading: false,
        hasMore: true,
        activeView: 'unwatched',
        viewMode: 'cards',
        sortBy: 'date-desc',
        searchQuery: '',
        subscriptions: [], // Holds subscriptions when modal is open
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

    // Subscription & Action Elements
    const manageSubscriptionsBtn = document.getElementById('manage-subscriptions-btn');
    const subscriptionsModal = document.getElementById('subscriptions-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const subscriptionsListContainer = document.getElementById('subscriptions-list');
    const addSubscriptionForm = document.getElementById('add-subscription-form');
    const subNameInput = document.getElementById('sub-name');
    const subUrlInput = document.getElementById('sub-url');
    const saveSubscriptionsBtn = document.getElementById('save-subscriptions-btn');

    // Modals & Overlays
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingOverlayText = document.getElementById('loading-overlay-text');
    const confirmModal = document.getElementById('confirm-modal');
    const confirmModalTitle = document.getElementById('confirm-modal-title');
    const confirmModalText = document.getElementById('confirm-modal-text');
    const confirmModalCancel = document.getElementById('confirm-modal-cancel');
    const confirmModalOk = document.getElementById('confirm-modal-ok');

    // --- THEME MANAGER ---
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

    // --- UTILITY FUNCTIONS ---
    function escapeHtml(text) {
        if (typeof text !== 'string') return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function showNotification(message, type = 'info', duration = 3500) {
        const container = document.getElementById('notification-container');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;

        container.appendChild(notification);

        setTimeout(() => notification.classList.add('show'), 10);
        setTimeout(() => {
            notification.classList.remove('show');
            notification.addEventListener('transitionend', () => notification.remove());
        }, duration);
    }

    function showConfirmation(title, text) {
        return new Promise((resolve) => {
            confirmModalTitle.textContent = title;
            confirmModalText.textContent = text;
            confirmModal.classList.add('visible');

            const close = (result) => {
                confirmModal.classList.remove('visible');
                confirmModalOk.removeEventListener('click', okListener);
                confirmModalCancel.removeEventListener('click', cancelListener);
                resolve(result);
            };

            const okListener = () => close(true);
            const cancelListener = () => close(false);

            confirmModalOk.addEventListener('click', okListener);
            confirmModalCancel.addEventListener('click', cancelListener);
        });
    }

    // --- DATA FETCHING & RENDERING ---
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
            if (!state.hasMore && data.feeds.length > 0) {
                endOfResultsMessage.style.display = 'block';
            }

            // Auto-load more videos if we have fewer than 6 visible
            setTimeout(() => checkAndLoadMoreVideos(), 100);
        } catch (error) {
            console.error('Error fetching videos:', error);
            videoGrid.innerHTML = `<p style="text-align: center; color: var(--color-error); grid-column: 1 / -1;">Failed to load videos. Please try again later.</p>`;
        } finally {
            state.isLoading = false;
            loader.style.display = 'none';
        }
    }

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
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="2"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>
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

    function reRenderVideoCards() {
        // Get all existing video cards and their data
        const existingCards = Array.from(document.querySelectorAll('.video-card'));
        const videoData = existingCards.map(card => ({
            link: card.dataset.url,
            watched: JSON.parse(card.dataset.watched),
            bookmarked: JSON.parse(card.dataset.bookmarked),
            title: card.querySelector('.video-title').textContent,
            author: card.querySelector('.video-channel').textContent,
            date: card.querySelector('.video-date').textContent,
            thumbnail_url: card.querySelector('.video-thumbnail img').src,
            video_id: extractVideoIdFromUrl(card.dataset.url)
        }));

        // Clear the grid and re-render with new view mode
        videoGrid.innerHTML = '';
        videoData.forEach(video => {
            videoGrid.insertAdjacentHTML('beforeend', getVideoCardHTML(video));
        });
    }

    function extractVideoIdFromUrl(url) {
        // Extract YouTube video ID from URL for thumbnail
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([^&\n?#]+)/,
            /youtube\.com\/v\/([^&\n?#]+)/,
        ];
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        return null;
    }

    // --- UI & FILTER UPDATES ---
    function handleFilterChange(updateAction) {
        updateAction();
        fetchVideos(true);
        updateUI();
    }

    function updateUI() {
        const currentLink = document.querySelector(`.nav-link[data-view="${state.activeView}"]`);
        contentTitle.textContent = currentLink ? currentLink.textContent : 'Videos';
        navLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.view === state.activeView);
        });
    }

    // --- SUBSCRIPTION MANAGER ---
    function renderSubscriptions() {
        subscriptionsListContainer.innerHTML = '';
        if (state.subscriptions.length === 0) {
            subscriptionsListContainer.innerHTML = '<p>No subscriptions found.</p>';
            return;
        }
        const sortedSubs = [...state.subscriptions].sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));

        sortedSubs.forEach((sub) => {
            const item = document.createElement('div');
            item.className = 'subscription-item';
            // Use URL as a unique identifier for removal
            item.dataset.url = sub.url;
            item.innerHTML = `
            <div class="info">
            <span class="name" title="${escapeHtml(sub.name)}">${escapeHtml(sub.name)}</span>
            <span class="url" title="${escapeHtml(sub.url)}">${escapeHtml(sub.url)}</span>
            </div>
            <button class="remove-sub-btn" aria-label="Remove ${escapeHtml(sub.name)}">Remove</button>
            `;
            subscriptionsListContainer.appendChild(item);
        });
    }

    async function openSubscriptionsModal() {
        try {
            const response = await fetch('/api/subscriptions');
            if (!response.ok) throw new Error('Failed to fetch subscriptions.');
            state.subscriptions = await response.json();
            renderSubscriptions();
            subscriptionsModal.classList.add('visible');
        } catch (error) {
            console.error('Error opening subscriptions modal:', error);
            showNotification('Could not load subscriptions.', 'error');
        }
    }

    function closeSubscriptionsModal() {
        subscriptionsModal.classList.remove('visible');
    }

    function handleAddSubscription(event) {
        event.preventDefault();
        const name = subNameInput.value.trim();
        const url = subUrlInput.value.trim();

        const ytRegex = /https?:\/\/(www\.)?youtube\.com\/feeds\/videos\.xml\?channel_id=[\w-]+/;
        if (!name || !url) {
            showNotification('Please provide both a name and a URL.', 'error');
            return;
        }
        if (!ytRegex.test(url)) {
            showNotification('Please provide a valid YouTube Feed URL format.', 'error');
            return;
        }
        if (state.subscriptions.some(sub => sub.url === url || sub.name.toLowerCase() === name.toLowerCase())) {
            showNotification('This subscription already exists.', 'error');
            return;
        }

        state.subscriptions.push({ name, url });
        renderSubscriptions();
        addSubscriptionForm.reset();
        subNameInput.focus();
    }

    subscriptionsListContainer.addEventListener('click', (event) => {
        if (event.target.classList.contains('remove-sub-btn')) {
            const item = event.target.closest('.subscription-item');
            const urlToRemove = item.dataset.url;
            state.subscriptions = state.subscriptions.filter(sub => sub.url !== urlToRemove);
            renderSubscriptions();
        }
    });

    async function handleSaveChanges() {
        saveSubscriptionsBtn.disabled = true;
        saveSubscriptionsBtn.textContent = 'Saving...';
        try {
            const response = await fetch('/api/subscriptions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subscriptions: state.subscriptions }),
            });
            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to save subscriptions.');
            }
            showNotification('Subscriptions saved successfully!', 'success');
            closeSubscriptionsModal();
        } catch(error) {
            console.error('Error saving subscriptions:', error);
            showNotification(`Error: ${error.message}`, 'error', 5000);
        } finally {
            saveSubscriptionsBtn.disabled = false;
            saveSubscriptionsBtn.textContent = 'Save Changes';
        }
    }

    // --- GLOBAL ACTION FUNCTIONS (attached via onclick) ---
    window.handleThumbnailClick = (event) => {
        const card = event.currentTarget.closest('.video-card');
        if (card && !JSON.parse(card.dataset.watched)) {
            performWatchAction(card, 'read');
        }
    };

    window.toggleBookmark = async (event) => {
        event.stopPropagation();
        const button = event.currentTarget;
        const card = button.closest('.video-card');
        if (!card || button.disabled) return;

        const videoUrl = card.dataset.url;
        const isBookmarked = JSON.parse(card.dataset.bookmarked);
        const action = isBookmarked ? 'remove' : 'add';
        button.disabled = true;

        try {
            const response = await fetch('/bookmark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: videoUrl, action }),
            });
            const data = await response.json();
            if (data.success) {
                // Update all cards with the same URL in the current view
                const allCardsWithSameUrl = document.querySelectorAll(`[data-url="${CSS.escape(videoUrl)}"]`);
                allCardsWithSameUrl.forEach(cardElement => {
                    cardElement.dataset.bookmarked = (action === 'add').toString();
                    
                    const cardButton = cardElement.querySelector('.bookmark-btn');
                    if (cardButton) {
                        cardButton.classList.toggle('active', action === 'add');
                        const btnText = cardButton.querySelector('.btn-text');
                        if (btnText) {
                            btnText.textContent = action === 'add' ? 'Bookmarked' : 'Bookmark';
                        }
                    }

                    // Remove cards that should no longer be visible in current view
                    if (state.activeView === 'bookmarked' && action === 'remove') {
                        cardElement.style.transition = 'opacity 0.20s ease';
                        cardElement.style.opacity = '0';
                        setTimeout(() => {
                            cardElement.remove();
                            checkAndLoadMoreVideos();
                        }, 200);
                    }
                });
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
        if (!card || (button && button.disabled)) return;
        if(button) button.disabled = true;

        const videoUrl = card.dataset.url;

        try {
            const response = await fetch('/mark_watched', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: videoUrl, action }),
            });
            const data = await response.json();
            if (data.success) {
                const isNowWatched = (action === 'read');
                
                // Update all cards with the same URL in the current view
                const allCardsWithSameUrl = document.querySelectorAll(`[data-url="${CSS.escape(videoUrl)}"]`);
                allCardsWithSameUrl.forEach(cardElement => {
                    cardElement.dataset.watched = isNowWatched.toString();
                    cardElement.classList.toggle('read', isNowWatched);
                    
                    const cardButton = cardElement.querySelector('.watch-btn');
                    if (cardButton) {
                        const btnText = cardButton.querySelector('.btn-text');
                        if (btnText) {
                            btnText.textContent = isNowWatched ? 'Mark Unwatched' : 'Mark Watched';
                        }
                    }

                    // Remove cards that should no longer be visible in current view
                    if ((state.activeView === 'unwatched' && isNowWatched) || (state.activeView === 'watched' && !isNowWatched)) {
                        cardElement.style.transition = 'opacity 0.15s ease';
                        cardElement.style.opacity = '0';
                        setTimeout(() => {
                            cardElement.remove();
                            checkAndLoadMoreVideos();
                        }, 150);
                    }
                });
            }
        } catch (error) {
            console.error('Error toggling watched state:', error);
        } finally {
            if(button) button.disabled = false;
        }
    }

    // --- AUTO-LOADING LOGIC ---
    function countVisibleVideos() {
        const videoCards = document.querySelectorAll('.video-card');
        return videoCards.length;
    }

    function checkAndLoadMoreVideos() {
        if (state.isLoading || !state.hasMore) return;
        
        const visibleCount = countVisibleVideos();
        if (visibleCount < 6) {
            state.currentPage++;
            fetchVideos(false);
        }
    }

    // --- EVENT LISTENERS ---
    window.addEventListener('scroll', () => {
        if (state.isLoading || !state.hasMore) return;
        if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) {
            state.currentPage++;
            fetchVideos(false);
        }
    }, { passive: true });

    navLinks.forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            if (link.dataset.view) {
                handleFilterChange(() => state.activeView = link.dataset.view);
            }
        });
    });

    viewButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (state.viewMode === btn.dataset.viewMode) return;
            state.viewMode = btn.dataset.viewMode;
            videoGrid.classList.toggle('list-view', state.viewMode === 'list');
            viewButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Re-render existing video cards with the new view mode
            reRenderVideoCards();
        });
    });

    sortSelect.addEventListener('change', () => {
        handleFilterChange(() => state.sortBy = sortSelect.value);
    });

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

    themeToggleButton.addEventListener('click', () => themeManager.toggle());
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => themeManager.applyTheme());

    // Subscription Listeners
    manageSubscriptionsBtn.addEventListener('click', (e) => {
        e.preventDefault();
        openSubscriptionsModal();
    });

    closeModalBtn.addEventListener('click', closeSubscriptionsModal);
    subscriptionsModal.addEventListener('click', (e) => {
        if (e.target === subscriptionsModal) closeSubscriptionsModal();
    });

        addSubscriptionForm.addEventListener('submit', handleAddSubscription);
        saveSubscriptionsBtn.addEventListener('click', handleSaveChanges);

        // --- INITIALIZATION ---
        function initialize() {
            updateUI();
            fetchVideos(true);
        }

        initialize();
});
