(function () {
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  const editorialIntro = document.querySelector('.editorial-intro');
  const editorialIntroLogo = document.querySelector('.nav > .nav-logo');

  if (editorialIntro && editorialIntroLogo && !reducedMotion.matches) {
    let introSeen = false;

    try {
      introSeen = window.sessionStorage.getItem('umit-sural-intro-seen') === 'true';
      if (!introSeen) window.sessionStorage.setItem('umit-sural-intro-seen', 'true');
    } catch (error) {
      introSeen = true;
    }

    if (!introSeen) {
      const introSiblings = Array.from(document.body.children).filter((element) => element !== editorialIntro);
      const logoParent = editorialIntroLogo.parentNode;
      const logoNextSibling = editorialIntroLogo.nextSibling;
      const lockedScrollKeys = new Set(['ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowUp', 'End', 'Home', 'PageDown', 'PageUp', ' ']);
      let introFinished = false;

      const preventIntroScroll = (event) => {
        event.preventDefault();
      };

      const preventIntroScrollKeys = (event) => {
        if (lockedScrollKeys.has(event.key)) event.preventDefault();
      };

      editorialIntro.hidden = false;
      editorialIntro.appendChild(editorialIntroLogo);
      document.body.classList.add('is-intro-playing');
      introSiblings.forEach((element) => {
        element.inert = true;
      });
      window.addEventListener('wheel', preventIntroScroll, { passive: false });
      window.addEventListener('touchmove', preventIntroScroll, { passive: false });
      window.addEventListener('keydown', preventIntroScrollKeys);

      const finishEditorialIntro = () => {
        if (introFinished) return;
        introFinished = true;

        logoParent.insertBefore(editorialIntroLogo, logoNextSibling);
        editorialIntro.remove();
        document.body.classList.remove('is-intro-playing');
        introSiblings.forEach((element) => {
          element.inert = false;
        });
        window.removeEventListener('wheel', preventIntroScroll);
        window.removeEventListener('touchmove', preventIntroScroll);
        window.removeEventListener('keydown', preventIntroScrollKeys);
      };

      editorialIntro.addEventListener('animationend', finishEditorialIntro, { once: true });
      window.setTimeout(finishEditorialIntro, 1400);
    }
  }

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

  const mobileArchiveComposition = archiveSection
    && archiveItems.length
    && window.matchMedia('(max-width: 600px)').matches;

  if (mobileArchiveComposition) {
    archiveSection.classList.add('is-mobile-composition');

    archiveItems.forEach((item, index) => {
      item.style.zIndex = String(index + 1);
    });

    if (!reducedMotion.matches) {
      archiveSection.classList.add('is-mobile-animated');
      let mobileArchiveActive = false;
      let mobileArchiveTicking = false;

      function mobileClamp(value, minimum = 0, maximum = 1) {
        return Math.min(maximum, Math.max(minimum, value));
      }

      function mobileSmoothstep(edgeStart, edgeEnd, value) {
        const progress = mobileClamp((value - edgeStart) / Math.max(0.001, edgeEnd - edgeStart));
        return progress * progress * (3 - 2 * progress);
      }

      function renderMobileArchive() {
        const rect = archiveSection.getBoundingClientRect();
        const scrollDistance = Math.max(1, archiveSection.offsetHeight - window.innerHeight);
        const progress = mobileClamp(-rect.top / scrollDistance);

        archiveItems.forEach((item, index) => {
          const start = 0.03 + index * 0.055;
          const entrance = mobileSmoothstep(start, start + 0.18, progress);
          const departure = mobileSmoothstep(0.84 + index * 0.006, 0.98, progress);
          const direction = index % 2 === 0 ? -1 : 1;
          const translateX = direction * (14 * (1 - entrance) + 8 * departure);
          const translateY = 44 * (1 - entrance) - 18 * departure;
          const scale = 0.98 + entrance * 0.02 - departure * 0.01;
          const opacity = entrance * (1 - departure * 0.78);

          item.style.setProperty('opacity', opacity.toFixed(3), 'important');
          item.style.setProperty('transform', `translate3d(${translateX.toFixed(2)}px, ${translateY.toFixed(2)}px, 0) scale(${scale.toFixed(3)})`, 'important');
          item.style.pointerEvents = opacity > 0.22 ? 'auto' : 'none';
          item.tabIndex = opacity > 0.22 ? 0 : -1;
        });

        mobileArchiveTicking = false;
      }

      function requestMobileArchiveRender() {
        if (!mobileArchiveActive || mobileArchiveTicking) return;

        mobileArchiveTicking = true;
        window.requestAnimationFrame(renderMobileArchive);
      }

      const mobileArchiveSectionObserver = new IntersectionObserver((entries) => {
        mobileArchiveActive = entries[0].isIntersecting;
        if (mobileArchiveActive) requestMobileArchiveRender();
      }, { rootMargin: '20% 0px' });

      mobileArchiveSectionObserver.observe(archiveSection);
      window.addEventListener('scroll', requestMobileArchiveRender, { passive: true });
      window.addEventListener('resize', requestMobileArchiveRender, { passive: true });
    }
  }

  const selectedWorkTracks = document.querySelectorAll('[data-work-track]');

  selectedWorkTracks.forEach((track) => {
    const indicator = track.parentElement.querySelector('.work-scroll-indicator');
    if (!indicator) return;

    let indicatorFrame = 0;
    let userInteracted = false;

    const updateIndicator = () => {
      const scrollRange = track.scrollHeight - track.clientHeight;
      const progress = scrollRange > 0 ? track.scrollTop / scrollRange : 0;
      indicator.style.setProperty('--work-scroll-progress', String(Math.min(1, Math.max(0, progress))));
      indicatorFrame = 0;
    };

    const requestIndicatorUpdate = () => {
      if (!indicatorFrame) indicatorFrame = window.requestAnimationFrame(updateIndicator);
    };

    const stopIndicatorHint = () => {
      if (userInteracted) return;
      userInteracted = true;
      indicator.classList.remove('is-hinting');
      requestIndicatorUpdate();
    };

    track.addEventListener('scroll', requestIndicatorUpdate, { passive: true });
    track.addEventListener('wheel', stopIndicatorHint, { passive: true });
    track.addEventListener('touchstart', stopIndicatorHint, { passive: true });
    track.addEventListener('keydown', stopIndicatorHint);

    updateIndicator();

    if (!reducedMotion.matches && finePointer.matches && window.matchMedia('(min-width: 901px)').matches) {
      const hintDelay = document.body.classList.contains('is-intro-playing') ? 1450 : 150;
      window.setTimeout(() => {
        if (!userInteracted) indicator.classList.add('is-hinting');
      }, hintDelay);
      indicator.addEventListener('animationend', () => indicator.classList.remove('is-hinting'), { once: true });
    }
  });

  const collectionGrids = document.querySelectorAll('.collection-grid');

  if (collectionGrids.length) {
    function updateCollectionGrid(grid) {
      const verticalGap = parseFloat(window.getComputedStyle(grid).getPropertyValue('--collection-row-gap')) || 0;
      const items = Array.from(grid.querySelectorAll('.collection-work'));

      grid.classList.remove('is-masonry');
      items.forEach((item) => {
        item.style.gridRowEnd = 'auto';
      });

      const itemHeights = items.map((item) => item.getBoundingClientRect().height);
      grid.classList.add('is-masonry');

      items.forEach((item, index) => {
        item.style.gridRowEnd = `span ${Math.ceil(itemHeights[index] + verticalGap)}`;
      });
    }

    function updateAllCollectionGrids() {
      window.requestAnimationFrame(() => {
        collectionGrids.forEach(updateCollectionGrid);
      });
    }

    collectionGrids.forEach((grid) => {
      grid.querySelectorAll('img').forEach((image) => {
        if (!image.complete) image.addEventListener('load', updateAllCollectionGrids, { once: true });
      });
    });

    window.addEventListener('load', updateAllCollectionGrids);
    window.addEventListener('resize', updateAllCollectionGrids, { passive: true });
    updateAllCollectionGrids();
  }

  const artworkMedia = document.querySelectorAll('.artwork-slider, .artwork-single');

  if (artworkMedia.length) {
    const viewer = document.createElement('div');
    viewer.className = 'artwork-viewer';
    viewer.hidden = true;
    viewer.setAttribute('role', 'dialog');
    viewer.setAttribute('aria-modal', 'true');
    viewer.setAttribute('aria-label', 'Artwork detail viewer');
    viewer.innerHTML = `
      <div class="artwork-viewer-bar">
        <button type="button" data-viewer-action="out" aria-label="Zoom out">−</button>
        <button type="button" data-viewer-action="reset" aria-label="Reset zoom">100%</button>
        <button type="button" data-viewer-action="in" aria-label="Zoom in">+</button>
        <button type="button" class="artwork-viewer-close" data-viewer-action="close" aria-label="Close artwork detail viewer">Close ×</button>
      </div>
      <div class="artwork-viewer-stage">
        <img class="artwork-viewer-image" alt="" draggable="false">
      </div>`;
    document.body.appendChild(viewer);

    const viewerStage = viewer.querySelector('.artwork-viewer-stage');
    const viewerImage = viewer.querySelector('.artwork-viewer-image');
    const viewerReset = viewer.querySelector('[data-viewer-action="reset"]');
    const viewerClose = viewer.querySelector('[data-viewer-action="close"]');
    const activePointers = new Map();
    let viewerScale = 1;
    let viewerX = 0;
    let viewerY = 0;
    let dragStartX = 0;
    let dragStartY = 0;
    let dragOriginX = 0;
    let dragOriginY = 0;
    let pinchStartDistance = 0;
    let pinchStartScale = 1;
    let pointerMoved = false;
    let viewerTrigger = null;

    function clampViewerPan() {
      if (viewerScale <= 1) {
        viewerX = 0;
        viewerY = 0;
        return;
      }

      const maximumX = Math.max(0, (viewerImage.offsetWidth * viewerScale - viewerStage.clientWidth) / 2);
      const maximumY = Math.max(0, (viewerImage.offsetHeight * viewerScale - viewerStage.clientHeight) / 2);
      viewerX = Math.min(maximumX, Math.max(-maximumX, viewerX));
      viewerY = Math.min(maximumY, Math.max(-maximumY, viewerY));
    }

    function renderViewerTransform() {
      clampViewerPan();
      viewerImage.style.transform = `translate3d(${viewerX}px, ${viewerY}px, 0) scale(${viewerScale})`;
      viewerReset.textContent = `${Math.round(viewerScale * 100)}%`;
      viewerStage.classList.toggle('is-pannable', viewerScale > 1);
    }

    function setViewerScale(nextScale) {
      viewerScale = Math.min(4, Math.max(1, nextScale));
      renderViewerTransform();
    }

    function resetViewerTransform() {
      viewerScale = 1;
      viewerX = 0;
      viewerY = 0;
      renderViewerTransform();
    }

    function openArtworkViewer(image) {
      viewerTrigger = image;
      viewerImage.src = image.currentSrc || image.src;
      viewerImage.alt = image.alt;
      resetViewerTransform();
      viewer.hidden = false;
      document.body.classList.add('artwork-viewer-open');
      viewerClose.focus();
    }

    function closeArtworkViewer() {
      if (viewer.hidden) return;
      viewer.hidden = true;
      viewerImage.removeAttribute('src');
      document.body.classList.remove('artwork-viewer-open');
      activePointers.clear();
      if (viewerTrigger) viewerTrigger.focus();
      viewerTrigger = null;
    }

    function updateZoomableImages(container) {
      const images = container.querySelectorAll('img');
      images.forEach((image) => {
        const isAvailable = container.classList.contains('artwork-single') || image.classList.contains('active');
        image.tabIndex = isAvailable ? 0 : -1;
        if (isAvailable) {
          image.setAttribute('role', 'button');
          image.setAttribute('aria-label', `${image.alt}. View detail`);
        } else {
          image.removeAttribute('role');
          image.removeAttribute('aria-label');
        }
      });
    }

    artworkMedia.forEach((container) => {
      container.classList.add('is-zoomable');
      const hint = document.createElement('span');
      hint.className = 'artwork-zoom-hint';
      hint.setAttribute('aria-hidden', 'true');
      hint.textContent = 'View detail +';
      container.appendChild(hint);
      updateZoomableImages(container);

      container.addEventListener('click', (event) => {
        const image = event.target.closest('img');
        if (!image || image.tabIndex !== 0) return;
        openArtworkViewer(image);
      });

      container.addEventListener('keydown', (event) => {
        if (!event.target.matches('img[role="button"]')) return;
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openArtworkViewer(event.target);
        }
      });

      if (container.classList.contains('artwork-slider')) {
        const observer = new MutationObserver(() => updateZoomableImages(container));
        observer.observe(container, { attributes: true, subtree: true, attributeFilter: ['class'] });
      }
    });

    viewer.addEventListener('click', (event) => {
      const action = event.target.closest('[data-viewer-action]')?.dataset.viewerAction;
      if (action === 'close') closeArtworkViewer();
      if (action === 'in') setViewerScale(viewerScale + 0.5);
      if (action === 'out') setViewerScale(viewerScale - 0.5);
      if (action === 'reset') resetViewerTransform();
      if (event.target === viewerStage && !pointerMoved) closeArtworkViewer();
    });

    viewerStage.addEventListener('wheel', (event) => {
      event.preventDefault();
      setViewerScale(viewerScale + (event.deltaY < 0 ? 0.25 : -0.25));
    }, { passive: false });

    viewerStage.addEventListener('pointerdown', (event) => {
      pointerMoved = false;
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      viewerStage.setPointerCapture(event.pointerId);

      if (activePointers.size === 1) {
        dragStartX = event.clientX;
        dragStartY = event.clientY;
        dragOriginX = viewerX;
        dragOriginY = viewerY;
        viewerStage.classList.toggle('is-dragging', viewerScale > 1);
      } else if (activePointers.size === 2) {
        const points = Array.from(activePointers.values());
        pinchStartDistance = Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y);
        pinchStartScale = viewerScale;
      }
    });

    viewerStage.addEventListener('pointermove', (event) => {
      if (!activePointers.has(event.pointerId)) return;
      activePointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

      if (activePointers.size === 2) {
        const points = Array.from(activePointers.values());
        const distance = Math.hypot(points[1].x - points[0].x, points[1].y - points[0].y);
        if (Math.abs(distance - pinchStartDistance) > 2) pointerMoved = true;
        setViewerScale(pinchStartScale * distance / Math.max(1, pinchStartDistance));
      } else if (viewerScale > 1) {
        if (Math.abs(event.clientX - dragStartX) > 2 || Math.abs(event.clientY - dragStartY) > 2) pointerMoved = true;
        viewerX = dragOriginX + event.clientX - dragStartX;
        viewerY = dragOriginY + event.clientY - dragStartY;
        renderViewerTransform();
      }
    });

    function releaseViewerPointer(event) {
      activePointers.delete(event.pointerId);
      viewerStage.classList.remove('is-dragging');
      if (activePointers.size === 1) {
        const point = Array.from(activePointers.values())[0];
        dragStartX = point.x;
        dragStartY = point.y;
        dragOriginX = viewerX;
        dragOriginY = viewerY;
      }
    }

    viewerStage.addEventListener('pointerup', releaseViewerPointer);
    viewerStage.addEventListener('pointercancel', releaseViewerPointer);
    window.addEventListener('resize', renderViewerTransform, { passive: true });

    document.addEventListener('keydown', (event) => {
      if (viewer.hidden) return;
      if (event.key === 'Escape') closeArtworkViewer();
      if (event.key === '+' || event.key === '=') setViewerScale(viewerScale + 0.5);
      if (event.key === '-') setViewerScale(viewerScale - 0.5);
      if (event.key === '0') resetViewerTransform();
      if (event.key === 'Tab') {
        const controls = Array.from(viewer.querySelectorAll('button'));
        const firstControl = controls[0];
        const lastControl = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === firstControl) {
          event.preventDefault();
          lastControl.focus();
        } else if (!event.shiftKey && document.activeElement === lastControl) {
          event.preventDefault();
          firstControl.focus();
        }
      }
    });
  }

  const collectionRails = document.querySelectorAll('.blog-collections');

  if (collectionRails.length) {
    const railObserver = 'IntersectionObserver' in window
      ? new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            entry.target.classList.toggle('is-offscreen', !entry.isIntersecting);
          });
        }, { rootMargin: '20% 0px' })
      : null;

    collectionRails.forEach((rail) => {
      const viewport = rail.querySelector('.blog-collections-viewport');
      let resumeTimer;

      function pauseRail() {
        window.clearTimeout(resumeTimer);
        rail.classList.add('is-interacting');
      }

      function resumeRailLater() {
        window.clearTimeout(resumeTimer);
        resumeTimer = window.setTimeout(() => {
          rail.classList.remove('is-interacting');
        }, 1400);
      }

      viewport.addEventListener('pointerdown', pauseRail, { passive: true });
      viewport.addEventListener('pointerup', resumeRailLater, { passive: true });
      viewport.addEventListener('pointercancel', resumeRailLater, { passive: true });
      viewport.addEventListener('scroll', () => {
        pauseRail();
        resumeRailLater();
      }, { passive: true });

      if (railObserver) railObserver.observe(rail);
    });
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
