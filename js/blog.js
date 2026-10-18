(function () {
  const postsGrid = document.getElementById('blog-posts-grid');
  const modal = document.getElementById('blog-modal');
  const modalContent = document.getElementById('blog-modal-content');
  let postsById = new Map();

  if (!postsGrid) {
    return;
  }

  document.addEventListener('click', handleDocumentClick);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeModal();
    }
  });

  loadPosts();

  async function loadPosts() {
    try {
      const response = await fetch('/api/posts');
      if (!response.ok) {
        throw new Error(`Could not load stories (HTTP ${response.status}).`);
      }

      const posts = await response.json();
      if (!Array.isArray(posts)) {
        throw new Error('The stories response was not a list.');
      }

      postsById = new Map(posts.map((post) => [String(post.id), post]));
      renderPosts(posts);
    } catch (error) {
      console.error('Unable to load blog stories.', error);
      postsGrid.innerHTML = '<p class="empty-state">Stories could not be loaded right now. Please try again later.</p>';
    }
  }

  function renderPosts(posts) {
    if (!posts.length) {
      postsGrid.innerHTML = '<p class="empty-state">No stories have been published yet.</p>';
      return;
    }

    postsGrid.innerHTML = posts.map((post) => {
      const media = renderMedia(post, true);
      const shareUrl = post.share_url || new URL(`/blog/${encodeURIComponent(post.id)}`, window.location.origin).href;
      const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(`${post.title || 'Travel story'} ${shareUrl}`)}`;
      return `
        <article class="blog-card" data-open-post="${escapeHtml(post.id)}">
          <div class="blog-card__media">${media || '<div class="blog-card__placeholder">Trip story</div>'}</div>
          <div class="blog-card__body">
            <div class="blog-card__meta">
              <span class="pill">${escapeHtml(post.category || 'Travel story')}</span>
              <span>${escapeHtml(post.date || 'Recently published')}</span>
            </div>
            <h3>${escapeHtml(post.title || '')}</h3>
            <p>${escapeHtml(post.excerpt || post.content || '')}</p>
            <div class="blog-card__footer">
              <span>${escapeHtml(post.location || 'Destination shared')}</span>
              <span class="blog-card__read">Read story →</span>
            </div>
            <a class="blog-share-link" href="${escapeHtml(whatsappUrl)}" target="_blank" rel="noopener noreferrer">Share on WhatsApp</a>
          </div>
        </article>
      `;
    }).join('');
  }

  function renderMedia(post, preview = false) {
    const items = Array.isArray(post.media_items)
      ? post.media_items
      : (post.media_filename
        ? [{ filename: post.media_filename, type: post.media_type || 'image' }]
        : []);
    if (!items.length) {
      return '';
    }

    const renderItem = (item) => {
      const mediaUrl = `/media/${encodeURIComponent(item.filename)}`;
      if (item.type === 'video') {
        return `<video controls preload="metadata" playsinline aria-label="${escapeHtml(post.title || 'Travel story')} video" src="${mediaUrl}"></video>`;
      }
      return `<img src="${mediaUrl}" alt="${escapeHtml(post.title || 'Travel story')}" loading="lazy" />`;
    };

    if (preview) {
      return `${renderItem(items[0])}${items.length > 1
        ? `<span class="blog-card__media-count">${items.length} gallery items</span>`
        : ''}`;
    }

    return `<div class="blog-media-gallery">${items.map((item) => `
      <figure class="blog-media-gallery__item">${renderItem(item)}</figure>
    `).join('')}</div>`;
  }

  function handleDocumentClick(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    if (target.matches('[data-close-modal]')) {
      closeModal();
      return;
    }

    if (target.closest('a, button, video')) {
      return;
    }

    const postCard = target.closest('[data-open-post]');
    if (postCard) {
      openPost(postCard.getAttribute('data-open-post'));
    }
  }

  function openPost(postId) {
    const post = postsById.get(String(postId));
    if (!post || !modal || !modalContent) {
      return;
    }

    const media = renderMedia(post);
    const shareUrl = post.share_url || new URL(`/blog/${encodeURIComponent(post.id)}`, window.location.origin).href;
    const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(`${post.title || 'Travel story'} ${shareUrl}`)}`;
    modalContent.innerHTML = `
      <div class="post-modal">
        <div class="post-modal__meta">
          <span class="pill">${escapeHtml(post.category || 'Travel story')}</span>
          <span>${escapeHtml(post.date || 'Recently published')}</span>
        </div>
        ${media ? `<div class="post-modal__media">${media}</div>` : ''}
        <h2>${escapeHtml(post.title || '')}</h2>
        <p class="post-modal__location">${escapeHtml(post.location || 'Destination shared')}</p>
        <p>${escapeHtml(post.excerpt || '')}</p>
        <div class="post-modal__content">${escapeHtml(post.content || '')}</div>
        <div class="post-modal__actions">
          <a class="btn btn-primary" href="${escapeHtml(whatsappUrl)}" target="_blank" rel="noopener noreferrer">Share on WhatsApp</a>
          <a class="btn btn-secondary" href="${escapeHtml(shareUrl)}">Open shareable story page</a>
        </div>
      </div>
    `;

    modal.classList.remove('is-hidden');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('modal-open');
  }

  function closeModal() {
    if (!modal || modal.classList.contains('is-hidden')) {
      return;
    }
    modal.classList.add('is-hidden');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-open');
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }
})();
