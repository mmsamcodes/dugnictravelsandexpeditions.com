(function () {
  const galleries = document.querySelectorAll('.media-showcase .media-grid');

  galleries.forEach((track, galleryIndex) => {
    const showcase = track.closest('.media-showcase');
    const slides = Array.from(track.querySelectorAll('.media-card'));
    if (!showcase || slides.length < 2) return;

    const title = document.title.replace(/\s*[|·].*$/, '').trim();
    const label = `${title || 'Destination'} media gallery`;
    showcase.setAttribute('role', 'region');
    showcase.setAttribute('aria-label', label);
    track.id = `destination-media-${galleryIndex + 1}`;
    track.setAttribute('role', 'group');
    track.setAttribute('aria-label', `${slides.length} media items`);
    track.setAttribute('tabindex', '0');
    track.setAttribute('aria-roledescription', 'carousel');

    slides.forEach((slide, index) => {
      slide.setAttribute('role', 'group');
      slide.setAttribute('aria-roledescription', 'slide');
      slide.setAttribute('aria-label', `${index + 1} of ${slides.length}`);
    });

    const controls = document.createElement('div');
    controls.className = 'media-carousel-controls';
    controls.innerHTML = `
      <button class="btn btn-secondary" type="button" data-carousel-previous aria-label="Previous media item" aria-controls="${track.id}">←</button>
      <span class="media-carousel-status" aria-live="polite">1 / ${slides.length}</span>
      <button class="btn btn-secondary" type="button" data-carousel-next aria-label="Next media item" aria-controls="${track.id}">→</button>
    `;
    showcase.insertBefore(controls, track);

    const previous = controls.querySelector('[data-carousel-previous]');
    const next = controls.querySelector('[data-carousel-next]');
    const status = controls.querySelector('.media-carousel-status');
    let currentIndex = 0;

    function goTo(index) {
      currentIndex = Math.max(0, Math.min(index, slides.length - 1));
      const targetLeft = slides[currentIndex].offsetLeft - slides[0].offsetLeft;
      track.scrollTo({ left: targetLeft, behavior: 'instant' });
      updateControls();
    }

    function updateControls() {
      previous.disabled = currentIndex === 0;
      next.disabled = currentIndex === slides.length - 1;
      status.textContent = `${currentIndex + 1} / ${slides.length}`;
    }

    previous.addEventListener('click', () => goTo(currentIndex - 1));
    next.addEventListener('click', () => goTo(currentIndex + 1));
    track.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') {
        event.preventDefault();
        goTo(currentIndex - 1);
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        goTo(currentIndex + 1);
      }
    });

    let scrollTimer;
    track.addEventListener('scroll', () => {
      window.clearTimeout(scrollTimer);
      scrollTimer = window.setTimeout(() => {
        const trackLeft = track.getBoundingClientRect().left;
        currentIndex = slides.reduce((closestIndex, slide, index) => {
          const distance = Math.abs(slide.getBoundingClientRect().left - trackLeft);
          const closestDistance = Math.abs(slides[closestIndex].getBoundingClientRect().left - trackLeft);
          return distance < closestDistance ? index : closestIndex;
        }, 0);
        updateControls();
      }, 80);
    }, { passive: true });

    updateControls();
  });
})();
