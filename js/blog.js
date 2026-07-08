(function () {
  const STORAGE_KEY = 'dugnicBlogPosts';
  const AUTH_KEY = 'dugnicBlogAuth';
  const DB_NAME = 'dugnicBlogDB';
  const DB_VERSION = 1;
  const MEDIA_STORE = 'blog-media';
  const DEFAULT_CREDENTIALS = { username: 'admin', password: 'dugnic2026' };

  const defaultPosts = [
    {
      id: 'sample-1',
      title: 'A refined safari escape in Ruaha',
      category: 'Safari',
      location: 'Ruaha, Tanzania',
      date: '2026-07-01',
      excerpt: 'A slow, design-led safari with private game drives, stellar sunsets, and stays that feel both grounded and luxurious.',
      content: 'Ruaha is one of those rare places that feels almost cinematic in its scale. We pair private guiding with comfortable lodges, flexible pacing, and exclusive access to remote landscapes so every day feels intentional rather than rushed. It is a destination for travelers who want both wonder and calm.',
      media: null
    },
    {
      id: 'sample-2',
      title: 'Island days and cultural evenings in Zanzibar',
      category: 'Beach & Culture',
      location: 'Zanzibar, Tanzania',
      date: '2026-06-20',
      excerpt: 'From spice farms to sea-view dinners, this itinerary blends ocean time with thoughtful cultural encounters.',
      content: 'Zanzibar continues to be one of the most compelling stops in East Africa. We shape stays around the rhythm of the traveler, sometimes with uninterrupted beach time and other times with market visits, food-led experiences, and sunlit boat excursions. The result is a balance of ease and discovery.',
      media: null
    }
  ];

  let posts = [];
  let draft = createEmptyDraft();
  let editingId = null;
  let isAuthenticated = localStorage.getItem(AUTH_KEY) === 'true';
  let mediaUrlCache = new Map();

  const blogPostsGrid = document.getElementById('blog-posts-grid');
  const blogModal = document.getElementById('blog-modal');
  const blogModalContent = document.getElementById('blog-modal-content');
  const blogAdminPanel = document.getElementById('blog-admin-panel');
  const blogAdminContent = document.getElementById('blog-admin-content');

  async function init() {
    bindEvents();
    posts = await loadPosts();
    renderPosts();
    if (blogAdminContent) {
      renderAdminState();
    }
  }

  function bindEvents() {
    document.addEventListener('click', handleDocumentClick);
    document.addEventListener('keydown', handleEscape);

    const adminButtons = document.querySelectorAll('.blog-admin-toggle');
    adminButtons.forEach((button) => {
      button.addEventListener('click', openAdminPanel);
    });

    if (blogAdminContent) {
      blogAdminContent.addEventListener('input', handleAdminInput);
      blogAdminContent.addEventListener('change', handleAdminInput);
      blogAdminContent.addEventListener('submit', handleFormSubmit);
      blogAdminContent.addEventListener('click', handleAdminAction);
    }
  }

  function handleDocumentClick(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    if (target.matches('[data-close-modal]')) {
      closeModal(target.closest('.modal-backdrop'));
      return;
    }

    if (target.closest('[data-open-post]')) {
      const postId = target.closest('[data-open-post]').getAttribute('data-open-post');
      openPostModal(postId);
    }
  }

  function handleEscape(event) {
    if (event.key === 'Escape') {
      if (blogModal && !blogModal.classList.contains('is-hidden')) {
        closeModal(blogModal);
      }
      if (blogAdminPanel && !blogAdminPanel.classList.contains('is-hidden')) {
        closeModal(blogAdminPanel);
      }
    }
  }

  function openAdminPanel() {
    if (!blogAdminPanel) {
      return;
    }

    blogAdminPanel.classList.remove('is-hidden');
    blogAdminPanel.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
    renderAdminState();
  }

  function closeModal(modal) {
    if (!modal) {
      return;
    }
    modal.classList.add('is-hidden');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
  }

  function renderAdminState() {
    if (!blogAdminContent) {
      return;
    }

    if (!isAuthenticated) {
      blogAdminContent.innerHTML = buildLoginMarkup();
      return;
    }

    blogAdminContent.innerHTML = buildDashboardMarkup();
    syncFormToDraft();
    renderPreview();
    renderAdminPostList();
  }

  function buildLoginMarkup() {
    return `
      <div class="admin-login">
        <div class="eyebrow">Private dashboard</div>
        <h2>Welcome back, admin</h2>
        <p>Use the browser-based dashboard to publish trip stories, upload media, and preview each post before it goes live.</p>
        <form id="login-form" class="blog-form">
          <label>
            <span>Username</span>
            <input type="text" name="username" placeholder="admin" required />
          </label>
          <label>
            <span>Password</span>
            <input type="password" name="password" placeholder="Enter your password" required />
          </label>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">Enter dashboard</button>
          </div>
          <p class="helper-text">Demo login: admin / dugnic2026</p>
        </form>
      </div>
    `;
  }

  function buildDashboardMarkup() {
    return `
      <div class="admin-dashboard">
        <div class="admin-dashboard__form">
          <div class="admin-panel__header">
            <div>
              <div class="eyebrow">Content dashboard</div>
              <h2>${editingId ? 'Update a story' : 'Create a story'}</h2>
            </div>
            <button type="button" class="btn btn-secondary" data-action="logout">Log out</button>
          </div>
          <form id="blog-form" class="blog-form">
            <label>
              <span>Story title</span>
              <input type="text" name="title" value="${escapeHtml(draft.title)}" placeholder="A new safari story" required />
            </label>
            <div class="field-row">
              <label>
                <span>Category</span>
                <select name="category">
                  <option value="Safari" ${selectIf(draft.category, 'Safari')}>Safari</option>
                  <option value="Beach & Culture" ${selectIf(draft.category, 'Beach & Culture')}>Beach & Culture</option>
                  <option value="Adventure" ${selectIf(draft.category, 'Adventure')}>Adventure</option>
                  <option value="Family" ${selectIf(draft.category, 'Family')}>Family</option>
                  <option value="Custom Itinerary" ${selectIf(draft.category, 'Custom Itinerary')}>Custom Itinerary</option>
                </select>
              </label>
              <label>
                <span>Location</span>
                <input type="text" name="location" value="${escapeHtml(draft.location)}" placeholder="Kenya, Rwanda, Zanzibar..." />
              </label>
            </div>
            <label>
              <span>Publish date</span>
              <input type="date" name="date" value="${escapeHtml(draft.date)}" />
            </label>
            <label>
              <span>Short intro</span>
              <textarea name="excerpt" rows="3" placeholder="A polished introduction for the homepage card...">${escapeHtml(draft.excerpt)}</textarea>
            </label>
            <label>
              <span>Full story</span>
              <textarea name="content" rows="6" placeholder="Tell the story, share details, and add trip highlights...">${escapeHtml(draft.content)}</textarea>
            </label>
            <label class="upload-field">
              <span>Upload a photo or video</span>
              <input type="file" name="media" accept="image/*,video/*" />
            </label>
            <div class="form-actions">
              <button type="submit" class="btn btn-primary">${editingId ? 'Update story' : 'Publish to homepage'}</button>
              <button type="button" class="btn btn-secondary" data-action="reset">Start over</button>
            </div>
          </form>
        </div>
        <div class="admin-dashboard__preview">
          <div id="blog-preview" class="preview-card"></div>
          <div class="saved-posts">
            <div class="saved-posts__header">
              <h3>Saved stories</h3>
              <span>${posts.length} live</span>
            </div>
            <div id="blog-admin-list" class="saved-posts__list"></div>
          </div>
        </div>
      </div>
    `;
  }

  function handleAdminInput(event) {
    const target = event.target;
    if (!(target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement)) {
      return;
    }

    if (target.name === 'media') {
      handleMediaUpload(target.files?.[0]);
      return;
    }

    if (target.name) {
      draft[target.name] = target.value;
      renderPreview();
    }
  }

  function handleAdminAction(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    const action = target.getAttribute('data-action');
    if (action === 'logout') {
      localStorage.removeItem(AUTH_KEY);
      isAuthenticated = false;
      editingId = null;
      draft = createEmptyDraft();
      renderAdminState();
      return;
    }

    if (action === 'reset') {
      editingId = null;
      draft = createEmptyDraft();
      renderAdminState();
      return;
    }

    if (action === 'edit-post') {
      const postId = target.getAttribute('data-id');
      editPost(postId);
      return;
    }

    if (action === 'delete-post') {
      const postId = target.getAttribute('data-id');
      deletePost(postId);
      return;
    }
  }

  async function handleFormSubmit(event) {
    event.preventDefault();

    if (!isAuthenticated) {
      handleLoginSubmit(event);
      return;
    }

    const form = event.target;
    const formData = new FormData(form);
    const nextPost = {
      id: editingId || `post-${Date.now()}`,
      title: String(formData.get('title') || '').trim(),
      category: String(formData.get('category') || 'Safari').trim(),
      location: String(formData.get('location') || '').trim(),
      date: String(formData.get('date') || '').trim(),
      excerpt: String(formData.get('excerpt') || '').trim(),
      content: String(formData.get('content') || '').trim(),
      media: draft.media ? { ...draft.media } : null
    };

    if (!nextPost.title || !nextPost.content) {
      renderPreview('Add a title and story content to publish.');
      return;
    }

    if (editingId) {
      posts = posts.map((post) => (post.id === editingId ? nextPost : post));
    } else {
      posts = [nextPost, ...posts];
    }

    await persistPosts();
    editingId = null;
    draft = createEmptyDraft();
    renderAdminState();
    renderPosts();
  }

  function handleLoginSubmit(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const username = String(formData.get('username') || '').trim();
    const password = String(formData.get('password') || '').trim();

    if (username === DEFAULT_CREDENTIALS.username && password === DEFAULT_CREDENTIALS.password) {
      isAuthenticated = true;
      localStorage.setItem(AUTH_KEY, 'true');
      renderAdminState();
    } else {
      blogAdminContent.innerHTML = buildLoginMarkup().replace('helper-text', 'helper-text error-text');
      const retryForm = blogAdminContent.querySelector('#login-form');
      if (retryForm) {
        retryForm.addEventListener('submit', handleLoginSubmit);
      }
    }
  }

  function handleMediaUpload(file) {
    if (!file) {
      if (draft.media?.previewUrl) {
        URL.revokeObjectURL(draft.media.previewUrl);
      }
      draft.media = null;
      renderPreview();
      return;
    }

    if (draft.media?.previewUrl) {
      URL.revokeObjectURL(draft.media.previewUrl);
    }

    draft.media = {
      type: file.type.startsWith('video/') ? 'video' : 'image',
      blob: file,
      name: file.name,
      mimeType: file.type,
      size: file.size,
      previewUrl: URL.createObjectURL(file)
    };
    renderPreview();
  }

  function renderPreview(message) {
    const preview = document.getElementById('blog-preview');
    if (!preview) {
      return;
    }

    const content = draft.content || '';
    const heading = draft.title || 'Your new story preview';
    const intro = draft.excerpt || 'A polished summary will appear here as you fill in the form.';
    const category = draft.category || 'Safari';
    const location = draft.location || 'Your destination';
    const date = draft.date || 'Draft';
    const mediaMarkup = renderMediaMarkup(draft.media, heading, 'preview-card__media');

    preview.innerHTML = `
      <div class="preview-card__head">
        <span class="pill">${category}</span>
        <span class="preview-card__date">${date || 'Draft'}</span>
      </div>
      ${mediaMarkup ? `<div class="preview-card__media">${mediaMarkup}</div>` : ''}
      <h3>${heading}</h3>
      <p class="preview-card__location">${location}</p>
      <p>${escapeHtml(intro)}</p>
      <p class="preview-card__content">${escapeHtml(content.length > 180 ? `${content.slice(0, 180)}…` : content)}</p>
      ${message ? `<p class="helper-text">${message}</p>` : ''}
    `;
  }

  function renderPosts() {
    if (!blogPostsGrid) {
      return;
    }

    if (!posts.length) {
      blogPostsGrid.innerHTML = '<p class="empty-state">No stories yet. The admin dashboard can add the first post.</p>';
      return;
    }

    blogPostsGrid.innerHTML = posts
      .map((post) => buildPostCard(post))
      .join('');
  }

  function buildPostCard(post) {
    const mediaMarkup = renderMediaMarkup(post.media, post.title, 'blog-card__media');

    return `
      <article class="blog-card" data-open-post="${post.id}">
        <div class="blog-card__media">${mediaMarkup || '<div class="blog-card__placeholder">Trip story</div>'}</div>
        <div class="blog-card__body">
          <div class="blog-card__meta">
            <span class="pill">${escapeHtml(post.category)}</span>
            <span>${escapeHtml(post.date || 'Draft')}</span>
          </div>
          <h3>${escapeHtml(post.title)}</h3>
          <p>${escapeHtml(post.excerpt || post.content || 'A new travel story is ready to explore.')}</p>
          <div class="blog-card__footer">
            <span>${escapeHtml(post.location || 'Destination shared')}</span>
            <span class="blog-card__read">Read story →</span>
          </div>
        </div>
      </article>
    `;
  }

  function openPostModal(postId) {
    const post = posts.find((entry) => entry.id === postId);
    if (!post || !blogModal || !blogModalContent) {
      return;
    }

    const mediaMarkup = renderMediaMarkup(post.media, post.title, 'post-modal__media');

    blogModalContent.innerHTML = `
      <div class="post-modal">
        <div class="post-modal__meta">
          <span class="pill">${escapeHtml(post.category || 'Travel story')}</span>
          <span>${escapeHtml(post.date || 'Draft')}</span>
        </div>
        ${mediaMarkup ? `<div class="post-modal__media">${mediaMarkup}</div>` : ''}
        <h2>${escapeHtml(post.title)}</h2>
        <p class="post-modal__location">${escapeHtml(post.location || 'Destination shared')}</p>
        <p>${escapeHtml(post.excerpt || '')}</p>
        <div class="post-modal__content">${escapeHtml(post.content || '')}</div>
      </div>
    `;

    blogModal.classList.remove('is-hidden');
    blogModal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
  }

  function renderAdminPostList() {
    const list = document.getElementById('blog-admin-list');
    if (!list) {
      return;
    }

    if (!posts.length) {
      list.innerHTML = '<p class="empty-state">Nothing published yet.</p>';
      return;
    }

    list.innerHTML = posts
      .map((post) => `
        <div class="saved-post-item">
          <div>
            <strong>${escapeHtml(post.title)}</strong>
            <p>${escapeHtml(post.excerpt || post.content || 'A story ready to share')}</p>
          </div>
          <div class="saved-post-item__actions">
            <button type="button" class="link-btn" data-action="edit-post" data-id="${post.id}">Edit</button>
            <button type="button" class="link-btn" data-action="delete-post" data-id="${post.id}">Delete</button>
          </div>
        </div>
      `)
      .join('');
  }

  function editPost(postId) {
    const post = posts.find((entry) => entry.id === postId);
    if (!post) {
      return;
    }
    editingId = post.id;
    draft = { ...post };
    renderAdminState();
  }

  async function deletePost(postId) {
    posts = posts.filter((post) => post.id !== postId);
    await persistPosts();
    if (editingId === postId) {
      editingId = null;
      draft = createEmptyDraft();
    }
    renderAdminState();
    renderPosts();
  }

  function renderMediaMarkup(media, altText, wrapperClass) {
    const mediaUrl = getMediaUrl(media, altText);
    if (!mediaUrl) {
      return '';
    }

    if (media?.type === 'video') {
      return `<video controls preload="metadata" playsinline src="${mediaUrl}"></video>`;
    }

    return `<img src="${mediaUrl}" alt="${escapeHtml(altText)}" loading="lazy" />`;
  }

  function getMediaUrl(media, key) {
    if (!media) {
      return '';
    }

    if (media.previewUrl) {
      return media.previewUrl;
    }

    if (media.blob) {
      const cacheKey = media.storageKey || key || 'media';
      if (!mediaUrlCache.has(cacheKey)) {
        mediaUrlCache.set(cacheKey, URL.createObjectURL(media.blob));
      }
      return mediaUrlCache.get(cacheKey);
    }

    if (media.data) {
      return media.data;
    }

    return '';
  }

  async function persistPosts() {
    const serializablePosts = [];
    for (const post of posts) {
      if (post.media?.blob) {
        const storageKey = post.media.storageKey || `${post.id}-media`;
        await saveMediaBlob(storageKey, post.media.blob);
        serializablePosts.push({
          ...post,
          media: {
            type: post.media.type,
            name: post.media.name,
            mimeType: post.media.mimeType,
            size: post.media.size,
            storageKey
          }
        });
      } else if (post.media?.data) {
        serializablePosts.push({
          ...post,
          media: {
            type: post.media.type,
            data: post.media.data,
            name: post.media.name,
            mimeType: post.media.mimeType,
            size: post.media.size
          }
        });
      } else {
        serializablePosts.push({ ...post, media: null });
      }
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(serializablePosts));
  }

  async function loadPosts() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) {
      return defaultPosts.map((post) => ({ ...post, media: normalizeMedia(post.media) }));
    }

    try {
      const parsed = JSON.parse(saved);
      if (!Array.isArray(parsed) || !parsed.length) {
        return defaultPosts.map((post) => ({ ...post, media: normalizeMedia(post.media) }));
      }

      const hydratedPosts = [];
      for (const post of parsed) {
        const normalizedPost = { ...post, media: normalizeMedia(post.media) };
        if (normalizedPost.media?.storageKey) {
          const blob = await getMediaBlob(normalizedPost.media.storageKey);
          normalizedPost.media.blob = blob || null;
        }
        hydratedPosts.push(normalizedPost);
      }
      return hydratedPosts;
    } catch (error) {
      return defaultPosts.map((post) => ({ ...post, media: normalizeMedia(post.media) }));
    }
  }

  function normalizeMedia(media) {
    if (!media) {
      return null;
    }

    if (media.blob || media.previewUrl || media.storageKey) {
      return media;
    }

    return {
      ...media,
      blob: null,
      previewUrl: ''
    };
  }

  function openDatabase() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(MEDIA_STORE)) {
          db.createObjectStore(MEDIA_STORE);
        }
      };

      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  async function saveMediaBlob(key, blob) {
    if (!blob || !('indexedDB' in window)) {
      return;
    }

    const db = await openDatabase();
    const tx = db.transaction(MEDIA_STORE, 'readwrite');
    tx.objectStore(MEDIA_STORE).put(blob, key);
    await new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async function getMediaBlob(key) {
    if (!key || !('indexedDB' in window)) {
      return null;
    }

    const db = await openDatabase();
    const tx = db.transaction(MEDIA_STORE, 'readonly');
    const request = tx.objectStore(MEDIA_STORE).get(key);

    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  }

  function createEmptyDraft() {
    return {
      title: '',
      category: 'Safari',
      location: '',
      date: '',
      excerpt: '',
      content: '',
      media: null
    };
  }

  function syncFormToDraft() {
    const form = document.getElementById('blog-form');
    if (!form) {
      return;
    }

    const fields = form.querySelectorAll('input, textarea, select');
    fields.forEach((field) => {
      const key = field.getAttribute('name');
      if (!key) {
        return;
      }
      if (field.type === 'file') {
        return;
      }
      if (field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement || field instanceof HTMLSelectElement) {
        field.value = draft[key] || '';
      }
    });
  }

  function selectIf(value, target) {
    return value === target ? 'selected' : '';
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  init();
})();
