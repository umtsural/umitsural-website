(function () {
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  if (!finePointer.matches || reducedMotion.matches) {
    return;
  }

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
})();
