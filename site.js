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
