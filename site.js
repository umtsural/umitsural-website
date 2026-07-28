(function () {
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  if (finePointer.matches && !reducedMotion.matches) {
    const cursor = document.createElement('img');
    cursor.src = 'favicon.png';
    cursor.className = 'custom-cursor';
    cursor.alt = '';
    cursor.setAttribute('aria-hidden', 'true');
    document.body.appendChild(cursor);
    document.documentElement.classList.add('has-custom-cursor');

    let targetX = -100;
    let targetY = -100;
    let currentX = targetX;
    let currentY = targetY;

    document.addEventListener('mousemove', (event) => {
      targetX = event.clientX;
      targetY = event.clientY;
      cursor.classList.add('is-visible');
    }, { passive: true });

    document.addEventListener('mouseleave', () => {
      cursor.classList.remove('is-visible');
    });

    document.addEventListener('mouseover', (event) => {
      const interactive = event.target.closest('a, button, input, textarea, select, [role="button"]');
      cursor.classList.toggle('is-interactive', Boolean(interactive));
    });

    function renderCursor() {
      currentX += (targetX - currentX) * 0.3;
      currentY += (targetY - currentY) * 0.3;
      cursor.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) translate(-50%, -50%)`;
      window.requestAnimationFrame(renderCursor);
    }

    window.requestAnimationFrame(renderCursor);
  }

  const archiveSection = document.querySelector('.living-archive');
  const archiveItems = document.querySelectorAll('[data-archive-start]');
  const archiveMotion = finePointer.matches && !reducedMotion.matches && window.matchMedia('(min-width: 901px)').matches;

  if (archiveSection && archiveItems.length && archiveMotion) {
    let ticking = false;

    function clamp(value, minimum = 0, maximum = 1) {
      return Math.min(maximum, Math.max(minimum, value));
    }

    function smoothstep(edgeStart, edgeEnd, value) {
      const progress = clamp((value - edgeStart) / Math.max(0.001, edgeEnd - edgeStart));
      return progress * progress * progress * (progress * (progress * 6 - 15) + 10);
    }

    function renderArchive() {
      const rect = archiveSection.getBoundingClientRect();
      const scrollDistance = Math.max(1, archiveSection.offsetHeight - window.innerHeight);
      const progress = clamp(-rect.top / scrollDistance);
      const motionScale = window.innerWidth <= 1100 ? 0.5 : 0.82;

      archiveItems.forEach((item) => {
        const start = Number(item.dataset.archiveStart || 0);
        const exit = 0.84 + start * 0.08;
        const entrance = smoothstep(start, Math.min(start + 0.18, exit), progress);
        const departure = smoothstep(exit, Math.min(exit + 0.15, 1), progress);
        const enterX = Number(item.dataset.archiveEnterX || 0) * motionScale;
        const enterY = Number(item.dataset.archiveEnterY || 0) * motionScale;
        const exitX = Number(item.dataset.archiveExitX || 0) * motionScale;
        const exitY = Number(item.dataset.archiveExitY || 0) * motionScale;
        const translateX = enterX * (1 - entrance) + exitX * departure;
        const translateY = enterY * (1 - entrance) + exitY * departure;
        const scale = 0.955 + entrance * 0.045 - departure * 0.018;
        const opacity = entrance * (1 - departure);

        item.style.opacity = opacity.toFixed(3);
        item.style.transform = `translate3d(${translateX}vw, ${translateY}vh, 0) scale(${scale.toFixed(3)})`;
        item.style.zIndex = item.dataset.archiveZ || '1';
        item.style.pointerEvents = opacity > 0.16 ? 'auto' : 'none';
        item.tabIndex = opacity > 0.16 ? 0 : -1;
      });

      ticking = false;
    }

    function requestArchiveRender() {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(renderArchive);
      }
    }

    window.addEventListener('scroll', requestArchiveRender, { passive: true });
    window.addEventListener('resize', requestArchiveRender, { passive: true });
    requestArchiveRender();
  }

  const artworkSliders = document.querySelectorAll('.artwork-slider');

  if (artworkSliders.length) {
    function updateSliderGeometry(slider) {
      const activeImage = slider.querySelector('img.active');

      if (!activeImage) return;

      const sliderRect = slider.getBoundingClientRect();
      const imageRect = activeImage.getBoundingClientRect();

      slider.style.setProperty('--slider-image-left', `${imageRect.left - sliderRect.left}px`);
      slider.style.setProperty('--slider-image-right', `${sliderRect.right - imageRect.right}px`);
      slider.style.setProperty('--slider-image-center-y', `${imageRect.top - sliderRect.top + imageRect.height / 2}px`);
    }

    function updateAllSliderGeometry() {
      window.requestAnimationFrame(() => {
        artworkSliders.forEach(updateSliderGeometry);
      });
    }

    artworkSliders.forEach((slider) => {
      const observer = new MutationObserver(() => updateSliderGeometry(slider));
      observer.observe(slider, { attributes: true, subtree: true, attributeFilter: ['class'] });

      slider.querySelectorAll('img').forEach((image) => {
        if (!image.complete) {
          image.addEventListener('load', () => updateSliderGeometry(slider), { once: true });
        }
      });
    });

    window.addEventListener('load', updateAllSliderGeometry);
    window.addEventListener('resize', updateAllSliderGeometry, { passive: true });
    updateAllSliderGeometry();
  }
})();
