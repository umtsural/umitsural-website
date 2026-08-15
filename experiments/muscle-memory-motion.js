(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (reducedMotion.matches) return;

  const artworks = [
    { title: 'Factory-Farmed Consciousness', source: '../assets/images/muscle-memory/factory-farmed-consciousness-main.webp' },
    { title: 'Fear Pushes Hope', source: '../assets/images/muscle-memory/fear-pushes-hope-main.webp' },
    { title: 'Insensitivity to Smell', source: '../assets/images/muscle-memory/insensitivity-to-smell-main.webp' },
    { title: 'Internalized Oppression', source: '../assets/images/muscle-memory/internalized-oppression-main.webp' },
    { title: 'Ruthless Conformity', source: '../assets/images/muscle-memory/ruthless-conformity-main.webp' }
  ];
  const study = document.querySelector('.motion-study');
  const canvas = document.querySelector('.motion-canvas');
  const controls = document.querySelector('.study-controls');
  const performanceReadout = document.querySelector('.performance-readout');
  const currentOutput = document.querySelector('[data-scene="current"]');
  const nextOutput = document.querySelector('[data-scene="next"]');
  const gl = canvas.getContext('webgl', {
    alpha: false,
    antialias: false,
    depth: false,
    powerPreference: 'high-performance',
    preserveDrawingBuffer: false
  });

  if (!gl) {
    performanceReadout.textContent = 'WebGL unavailable · static artwork shown';
    canvas.hidden = true;
    return;
  }

  const vertexSource = `
    attribute vec2 a_position;
    varying vec2 v_uv;

    void main() {
      v_uv = a_position * 0.5 + 0.5;
      gl_Position = vec4(a_position, 0.0, 1.0);
    }
  `;

  const fragmentSource = `
    precision highp float;

    varying vec2 v_uv;
    uniform sampler2D u_texture0;
    uniform sampler2D u_texture1;
    uniform sampler2D u_texture2;
    uniform sampler2D u_texture3;
    uniform sampler2D u_texture4;
    uniform vec2 u_grid;
    uniform float u_localProgress;
    uniform float u_stillnessEnd;
    uniform float u_transitionStart;
    uniform float u_currentArtwork;
    uniform float u_nextArtwork;
    uniform float u_intensity;
    uniform float u_displacement;
    uniform float u_stretch;
    uniform float u_softness;
    uniform float u_horizontal;
    uniform float u_showGrid;
    uniform float u_time;

    const vec3 BACKGROUND = vec3(0.075, 0.068, 0.061);
    const float STAGE_ASPECT = 1.7777778;

    float hash21(vec2 point) {
      point = fract(point * vec2(123.34, 456.21));
      point += dot(point, point + 45.32);
      return fract(point.x * point.y);
    }

    vec4 regionValue(vec2 cell) {
      return vec4(
        hash21(cell + 1.13),
        hash21(cell + 7.71),
        hash21(cell + 14.37),
        hash21(cell + 23.91)
      );
    }

    vec4 blendedRegion(vec2 gridPosition) {
      vec2 cell = floor(gridPosition);
      vec2 local = fract(gridPosition);
      vec2 blend = smoothstep(vec2(0.14), vec2(0.86), local);
      vec4 bottom = mix(regionValue(cell), regionValue(cell + vec2(1.0, 0.0)), blend.x);
      vec4 top = mix(regionValue(cell + vec2(0.0, 1.0)), regionValue(cell + vec2(1.0)), blend.x);
      return mix(bottom, top, blend.y);
    }

    vec3 fittedArtworkUv(vec2 screenUv, float sourceAspect) {
      float presentedAspect = mix(sourceAspect, 1.0 / sourceAspect, u_horizontal);
      vec2 contentSize = vec2(1.0);
      if (presentedAspect > STAGE_ASPECT) {
        contentSize.y = STAGE_ASPECT / presentedAspect;
      } else {
        contentSize.x = presentedAspect / STAGE_ASPECT;
      }
      vec2 localUv = (screenUv - 0.5) / contentSize + 0.5;
      float mask = step(0.0, localUv.x) * step(localUv.x, 1.0) * step(0.0, localUv.y) * step(localUv.y, 1.0);
      vec2 sourceUv = mix(localUv, vec2(localUv.y, 1.0 - localUv.x), u_horizontal);
      return vec3(clamp(sourceUv, vec2(0.001), vec2(0.999)), mask);
    }

    vec4 sampleArtwork(float artworkIndex, vec2 screenUv) {
      vec3 fitted;
      vec3 color;
      if (artworkIndex < 0.5) {
        fitted = fittedArtworkUv(screenUv, 0.6684);
        color = texture2D(u_texture0, fitted.xy).rgb;
      } else if (artworkIndex < 1.5) {
        fitted = fittedArtworkUv(screenUv, 0.6680);
        color = texture2D(u_texture1, fitted.xy).rgb;
      } else if (artworkIndex < 2.5) {
        fitted = fittedArtworkUv(screenUv, 0.6658);
        color = texture2D(u_texture2, fitted.xy).rgb;
      } else if (artworkIndex < 3.5) {
        fitted = fittedArtworkUv(screenUv, 0.7102);
        color = texture2D(u_texture3, fitted.xy).rgb;
      } else {
        fitted = fittedArtworkUv(screenUv, 0.6671);
        color = texture2D(u_texture4, fitted.xy).rgb;
      }
      return vec4(mix(BACKGROUND, color, fitted.z), 1.0);
    }

    vec2 mappedUv(vec2 screenUv, vec4 region, float movement, float seed) {
      vec2 gridPosition = screenUv * u_grid;
      vec2 cellOrigin = floor(gridPosition) / u_grid;
      vec2 cellCenter = cellOrigin + 0.5 / u_grid;
      float activation = smoothstep(0.18, 0.82, fract(region.w + seed));
      float amount = movement * activation * u_intensity;
      vec2 stretch = vec2(
        1.0 + (region.z - 0.5) * u_stretch,
        1.0 + (region.x - 0.5) * u_stretch
      );
      vec2 mapped = cellCenter + (screenUv - cellCenter) / mix(vec2(1.0), stretch, amount);
      mapped += (region.xy - 0.5) * 2.0 * u_displacement * amount;
      vec2 fluid = vec2(
        sin((screenUv.y * 3.4 + u_time * 0.045 + seed * 4.0) * 3.14159265),
        cos((screenUv.x * 3.1 - u_time * 0.038 + seed * 3.0) * 3.14159265)
      );
      mapped += fluid * 0.008 * amount;

      float repeatRegion = step(0.88, region.z) * smoothstep(0.48, 0.85, movement);
      vec2 repeated = cellOrigin + fract((mapped - cellOrigin) * u_grid * 1.12) / u_grid;
      mapped = mix(mapped, repeated, repeatRegion * 0.18);
      return mix(screenUv, mapped, clamp(amount, 0.0, 1.0));
    }

    void main() {
      vec2 screenUv = v_uv;
      vec4 region = blendedRegion(screenUv * u_grid);
      float movementIn = smoothstep(u_stillnessEnd, u_stillnessEnd + 0.18, u_localProgress);
      float reconstruction = 1.0 - smoothstep(u_transitionStart + 0.48 * (1.0 - u_transitionStart), 0.99, u_localProgress);
      float movement = movementIn * reconstruction;
      vec2 currentUv = mappedUv(screenUv, region, movement, 0.17);
      vec2 nextUv = mappedUv(screenUv, region.yzwx, movement, 0.63);

      float transitionProgress = smoothstep(u_transitionStart, 1.0, u_localProgress);
      float threshold = 0.06 + region.w * 0.88;
      float localTransition = smoothstep(threshold - u_softness, threshold + u_softness, transitionProgress);
      localTransition *= smoothstep(0.0, 0.035, transitionProgress);
      localTransition = mix(localTransition, 1.0, smoothstep(0.965, 1.0, transitionProgress));

      vec3 currentColor = sampleArtwork(u_currentArtwork, currentUv).rgb;
      vec3 nextColor = sampleArtwork(u_nextArtwork, nextUv).rgb;
      vec3 color = mix(currentColor, nextColor, localTransition);

      if (u_showGrid > 0.5) {
        vec2 gridPosition = screenUv * u_grid;
        vec2 edgeDistance = min(fract(gridPosition), 1.0 - fract(gridPosition));
        float gridLine = 1.0 - smoothstep(0.0, 0.025, min(edgeDistance.x, edgeDistance.y));
        color = mix(color, vec3(0.35, 0.95, 0.67), gridLine * 0.72);
      }

      gl_FragColor = vec4(color, 1.0);
    }
  `;

  const settings = {
    sceneDuration: 8.5,
    stillness: 1.6,
    intensity: 0.78,
    displacement: 0.075,
    stretch: 0.38,
    regions: 8,
    transitionDuration: 2.6,
    softness: 0.18,
    horizontal: true
  };
  let startTime = performance.now();
  let pausedAt = 0;
  let paused = false;
  let showGrid = false;
  let animationFrame = 0;
  let lastFrameTime = startTime;
  let frameSamples = [];
  let displayedScene = -1;

  function compileShader(type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
    return shader;
  }

  function createProgram() {
    const program = gl.createProgram();
    gl.attachShader(program, compileShader(gl.VERTEX_SHADER, vertexSource));
    gl.attachShader(program, compileShader(gl.FRAGMENT_SHADER, fragmentSource));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    return program;
  }

  const program = createProgram();
  const uniformNames = [
    'grid', 'localProgress', 'stillnessEnd', 'transitionStart', 'currentArtwork',
    'nextArtwork', 'intensity', 'displacement', 'stretch', 'softness',
    'horizontal', 'showGrid', 'time'
  ];
  const uniforms = Object.fromEntries(uniformNames.map((name) => [name, gl.getUniformLocation(program, `u_${name}`)]));
  const positionBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
  gl.useProgram(program);
  const positionLocation = gl.getAttribLocation(program, 'a_position');
  gl.enableVertexAttribArray(positionLocation);
  gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

  function resize() {
    const bounds = study.getBoundingClientRect();
    const maximumScale = Math.min(1920 / bounds.width, 1080 / bounds.height);
    const renderScale = Math.min(window.devicePixelRatio || 1, maximumScale);
    const width = Math.max(1, Math.round(bounds.width * renderScale));
    const height = Math.max(1, Math.round(bounds.height * renderScale));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      gl.viewport(0, 0, width, height);
    }
  }

  function updateSceneLabels(sceneIndex, nextIndex) {
    if (displayedScene === sceneIndex) return;
    displayedScene = sceneIndex;
    currentOutput.value = artworks[sceneIndex].title;
    nextOutput.value = artworks[nextIndex].title;
  }

  function render(time) {
    resize();
    const elapsed = paused ? pausedAt : time - startTime;
    const sceneMilliseconds = settings.sceneDuration * 1000;
    const sceneIndex = Math.floor(elapsed / sceneMilliseconds) % artworks.length;
    const nextIndex = (sceneIndex + 1) % artworks.length;
    const localProgress = (elapsed % sceneMilliseconds) / sceneMilliseconds;
    const rowCount = Math.max(3, Math.round(settings.regions * 0.875));
    updateSceneLabels(sceneIndex, nextIndex);

    gl.useProgram(program);
    gl.uniform2f(uniforms.grid, settings.regions, rowCount);
    gl.uniform1f(uniforms.localProgress, localProgress);
    gl.uniform1f(uniforms.stillnessEnd, settings.stillness / settings.sceneDuration);
    gl.uniform1f(uniforms.transitionStart, 1 - settings.transitionDuration / settings.sceneDuration);
    gl.uniform1f(uniforms.currentArtwork, sceneIndex);
    gl.uniform1f(uniforms.nextArtwork, nextIndex);
    gl.uniform1f(uniforms.intensity, settings.intensity);
    gl.uniform1f(uniforms.displacement, settings.displacement);
    gl.uniform1f(uniforms.stretch, settings.stretch);
    gl.uniform1f(uniforms.softness, settings.softness);
    gl.uniform1f(uniforms.horizontal, settings.horizontal ? 1 : 0);
    gl.uniform1f(uniforms.showGrid, showGrid ? 1 : 0);
    gl.uniform1f(uniforms.time, elapsed / 1000);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    study.classList.add('is-ready');

    const frameDuration = time - lastFrameTime;
    lastFrameTime = time;
    if (frameDuration > 0 && frameDuration < 100) frameSamples.push(1000 / frameDuration);
    if (frameSamples.length >= 60) {
      const average = frameSamples.reduce((sum, value) => sum + value, 0) / frameSamples.length;
      performanceReadout.textContent = `${average.toFixed(0)} fps · ${canvas.width} × ${canvas.height} · scene ${sceneIndex + 1}/5`;
      frameSamples = [];
    }
    if (!paused) animationFrame = window.requestAnimationFrame(render);
  }

  function jumpToScene(sceneIndex) {
    const normalizedIndex = (sceneIndex + artworks.length) % artworks.length;
    const now = performance.now();
    const targetElapsed = normalizedIndex * settings.sceneDuration * 1000;
    displayedScene = -1;
    if (paused) {
      pausedAt = targetElapsed;
      render(now);
    } else {
      startTime = now - targetElapsed;
    }
  }

  function currentSceneIndex() {
    const elapsed = paused ? pausedAt : performance.now() - startTime;
    return Math.floor(elapsed / (settings.sceneDuration * 1000)) % artworks.length;
  }

  function restart() {
    startTime = performance.now();
    pausedAt = 0;
    displayedScene = -1;
    lastFrameTime = startTime;
    frameSamples = [];
    if (paused) render(startTime);
  }

  document.querySelectorAll('.controls-body input[type="range"]').forEach((input) => {
    const output = document.querySelector(`[data-output="${input.name}"]`);
    input.addEventListener('input', () => {
      settings[input.name] = Number(input.value);
      const decimals = input.step.includes('.') ? Math.min(3, input.step.split('.')[1].length) : 0;
      if (input.name === 'regions') output.value = `${input.value} × ${Math.max(3, Math.round(Number(input.value) * 0.875))}`;
      else if (input.name.includes('Duration') || input.name === 'stillness') output.value = `${Number(input.value).toFixed(decimals)}s`;
      else output.value = Number(input.value).toFixed(decimals);
      if (paused) render(performance.now());
    });
  });

  document.querySelector('[name="horizontal"]').addEventListener('change', (event) => {
    settings.horizontal = event.currentTarget.checked;
    if (paused) render(performance.now());
  });

  document.querySelector('.controls-toggle').addEventListener('click', (event) => {
    controls.classList.toggle('is-collapsed');
    event.currentTarget.setAttribute('aria-expanded', String(!controls.classList.contains('is-collapsed')));
  });

  document.querySelector('[data-action="play"]').addEventListener('click', (event) => {
    if (paused) {
      startTime = performance.now() - pausedAt;
      paused = false;
      event.currentTarget.textContent = 'Pause';
      lastFrameTime = performance.now();
      animationFrame = window.requestAnimationFrame(render);
    } else {
      pausedAt = performance.now() - startTime;
      paused = true;
      event.currentTarget.textContent = 'Play';
      window.cancelAnimationFrame(animationFrame);
      render(performance.now());
    }
  });

  document.querySelector('[data-action="previous"]').addEventListener('click', () => jumpToScene(currentSceneIndex() - 1));
  document.querySelector('[data-action="next"]').addEventListener('click', () => jumpToScene(currentSceneIndex() + 1));
  document.querySelector('[data-action="reset"]').addEventListener('click', restart);
  document.querySelector('[data-action="grid"]').addEventListener('click', (event) => {
    showGrid = !showGrid;
    event.currentTarget.setAttribute('aria-pressed', String(showGrid));
    event.currentTarget.textContent = showGrid ? 'Hide UV grid' : 'Show UV grid';
    if (paused) render(performance.now());
  });

  document.addEventListener('visibilitychange', () => {
    window.cancelAnimationFrame(animationFrame);
    if (!document.hidden && !paused) {
      lastFrameTime = performance.now();
      animationFrame = window.requestAnimationFrame(render);
    }
  });
  window.addEventListener('resize', resize, { passive: true });

  function loadTexture(artwork, index) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.addEventListener('load', () => {
        const texture = gl.createTexture();
        gl.activeTexture(gl.TEXTURE0 + index);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
        gl.uniform1i(gl.getUniformLocation(program, `u_texture${index}`), index);
        resolve();
      });
      image.addEventListener('error', reject);
      image.src = artwork.source;
    });
  }

  Promise.all(artworks.map(loadTexture)).then(() => {
    startTime = performance.now();
    lastFrameTime = startTime;
    animationFrame = window.requestAnimationFrame(render);
  }).catch(() => {
    performanceReadout.textContent = 'Texture load failed · static artwork shown';
    canvas.hidden = true;
  });
})();
