const GOOGLE_SCOPE = 'https://www.googleapis.com/auth/drive.readonly';
const STORAGE_KEY = 'bounce-drive-media-studio-config';
const OUTPUT_WIDTH = 1080;
const OUTPUT_HEIGHT = 1920;
const MOBILE_BREAKPOINT = 920;

const state = {
  accessToken: '',
  googleReady: false,
  tokenClient: null,
  files: [],
  filteredFiles: [],
  rootFolder: null,
  folderCount: 0,
  selectedFileId: '',
  currentPreviewUrl: '',
  currentPreviewBlob: null,
  currentPreviewFileId: '',
  currentPreviewToken: 0,
  rouletteTimer: null,
  serverConfig: {},
  isMobileMode: false,
  mobilePanel: 'setup',
  tiktokStatus: null,
  currentPublishing: false,
};

const elements = {
  rendererChip: document.getElementById('rendererChip'),
  authPill: document.getElementById('authPill'),
  statusMessage: document.getElementById('statusMessage'),
  clientIdInput: document.getElementById('clientIdInput'),
  folderInput: document.getElementById('folderInput'),
  teamNameInput: document.getElementById('teamNameInput'),
  publicBaseUrlInput: document.getElementById('publicBaseUrlInput'),
  tiktokRedirectPreview: document.getElementById('tiktokRedirectPreview'),
  saveConfigButton: document.getElementById('saveConfigButton'),
  connectButton: document.getElementById('connectButton'),
  loadLibraryButton: document.getElementById('loadLibraryButton'),
  signOutButton: document.getElementById('signOutButton'),
  statAssets: document.getElementById('statAssets'),
  statVideos: document.getElementById('statVideos'),
  statImages: document.getElementById('statImages'),
  statFolders: document.getElementById('statFolders'),
  searchInput: document.getElementById('searchInput'),
  typeFilter: document.getElementById('typeFilter'),
  sortSelect: document.getElementById('sortSelect'),
  rouletteButton: document.getElementById('rouletteButton'),
  reloadLibraryButton: document.getElementById('reloadLibraryButton'),
  libraryCounter: document.getElementById('libraryCounter'),
  pathBadge: document.getElementById('pathBadge'),
  libraryGrid: document.getElementById('libraryGrid'),
  previewBadge: document.getElementById('previewBadge'),
  previewPlaceholder: document.getElementById('previewPlaceholder'),
  previewImage: document.getElementById('previewImage'),
  previewVideo: document.getElementById('previewVideo'),
  overlayPreview: document.getElementById('overlayPreview'),
  overlayPreviewText: document.getElementById('overlayPreviewText'),
  reloadPreviewButton: document.getElementById('reloadPreviewButton'),
  openInDriveLink: document.getElementById('openInDriveLink'),
  metaName: document.getElementById('metaName'),
  metaPath: document.getElementById('metaPath'),
  metaType: document.getElementById('metaType'),
  metaDimensions: document.getElementById('metaDimensions'),
  metaSize: document.getElementById('metaSize'),
  metaDuration: document.getElementById('metaDuration'),
  overlayTextInput: document.getElementById('overlayTextInput'),
  fontSizeInput: document.getElementById('fontSizeInput'),
  fontSizeValue: document.getElementById('fontSizeValue'),
  lineSpacingInput: document.getElementById('lineSpacingInput'),
  lineSpacingValue: document.getElementById('lineSpacingValue'),
  topOffsetInput: document.getElementById('topOffsetInput'),
  topOffsetValue: document.getElementById('topOffsetValue'),
  maxWidthInput: document.getElementById('maxWidthInput'),
  maxWidthValue: document.getElementById('maxWidthValue'),
  boxOpacityInput: document.getElementById('boxOpacityInput'),
  boxOpacityValue: document.getElementById('boxOpacityValue'),
  fitModeInput: document.getElementById('fitModeInput'),
  exportButton: document.getElementById('exportButton'),
  tiktokStatusBadge: document.getElementById('tiktokStatusBadge'),
  tiktokAccountLabel: document.getElementById('tiktokAccountLabel'),
  tiktokModeBadge: document.getElementById('tiktokModeBadge'),
  tiktokChecklist: document.getElementById('tiktokChecklist'),
  connectTikTokButton: document.getElementById('connectTikTokButton'),
  refreshTikTokButton: document.getElementById('refreshTikTokButton'),
  disconnectTikTokButton: document.getElementById('disconnectTikTokButton'),
  tiktokCaptionInput: document.getElementById('tiktokCaptionInput'),
  tiktokHashtagsInput: document.getElementById('tiktokHashtagsInput'),
  tiktokMentionsInput: document.getElementById('tiktokMentionsInput'),
  tiktokPostModeInput: document.getElementById('tiktokPostModeInput'),
  tiktokPrivacyInput: document.getElementById('tiktokPrivacyInput'),
  tiktokCoverTimestampInput: document.getElementById('tiktokCoverTimestampInput'),
  allowCommentCheckbox: document.getElementById('allowCommentCheckbox'),
  allowDuetCheckbox: document.getElementById('allowDuetCheckbox'),
  allowStitchCheckbox: document.getElementById('allowStitchCheckbox'),
  brandOrganicCheckbox: document.getElementById('brandOrganicCheckbox'),
  brandContentCheckbox: document.getElementById('brandContentCheckbox'),
  musicConsentCheckbox: document.getElementById('musicConsentCheckbox'),
  tiktokModeHint: document.getElementById('tiktokModeHint'),
  publishTikTokButton: document.getElementById('publishTikTokButton'),
  tiktokPublishResult: document.getElementById('tiktokPublishResult'),
  mobileNav: document.getElementById('mobileNav'),
  mobileNavButtons: [...document.querySelectorAll('[data-mobile-target]')],
  mobilePanels: [...document.querySelectorAll('[data-mobile-panel]')],
};

window.addEventListener('load', () => {
  void initApp();
});

async function initApp() {
  bindEvents();
  applyResponsiveMode();
  window.addEventListener('resize', applyResponsiveMode);
  await hydrateConfig();
  pollForGoogle();
  await checkServerHealth();
  syncOverlayControls();
  renderAuthState();
  renderSelectionState();
  renderTikTokModeHint();
  await loadTikTokStatus();
  applyTikTokQueryState();
  switchMobilePanel(state.mobilePanel, { scroll: false });
  // Auto-load shared library — no user auth needed
  void loadLibrary();
}

function bindEvents() {
  elements.saveConfigButton.addEventListener('click', () => {
    void saveConfig();
  });
  elements.connectButton.addEventListener('click', () => {
    void connectGoogleDrive();
  });
  elements.loadLibraryButton.addEventListener('click', () => {
    void loadLibrary();
  });
  elements.signOutButton.addEventListener('click', signOutGoogle);
  elements.searchInput.addEventListener('input', applyFiltersAndRender);
  elements.typeFilter.addEventListener('change', applyFiltersAndRender);
  elements.sortSelect.addEventListener('change', applyFiltersAndRender);
  elements.rouletteButton.addEventListener('click', () => {
    void runRoulette();
  });
  elements.reloadLibraryButton.addEventListener('click', () => {
    void loadLibrary(true);
  });
  elements.reloadPreviewButton.addEventListener('click', () => {
    const file = getSelectedFile();
    if (file) {
      void loadPreview(file, { force: true });
    }
  });
  elements.exportButton.addEventListener('click', () => {
    void exportCurrentSelection();
  });

  [
    elements.clientIdInput,
    elements.folderInput,
    elements.teamNameInput,
    elements.publicBaseUrlInput,
  ].forEach((control) => {
    control.addEventListener('input', () => {
      syncComputedFields();
      maybeRefreshTokenClient();
    });
    control.addEventListener('change', () => {
      syncComputedFields();
      maybeRefreshTokenClient();
    });
  });

  [
    elements.overlayTextInput,
    elements.fontSizeInput,
    elements.lineSpacingInput,
    elements.topOffsetInput,
    elements.maxWidthInput,
    elements.boxOpacityInput,
    elements.fitModeInput,
  ].forEach((control) => {
    control.addEventListener('input', syncOverlayControls);
    control.addEventListener('change', syncOverlayControls);
  });

  elements.connectTikTokButton.addEventListener('click', connectTikTok);
  elements.refreshTikTokButton.addEventListener('click', () => {
    void loadTikTokStatus(true);
  });
  elements.disconnectTikTokButton.addEventListener('click', () => {
    void disconnectTikTok();
  });
  elements.publishTikTokButton.addEventListener('click', () => {
    void publishToTikTok();
  });
  elements.tiktokPostModeInput.addEventListener('change', () => {
    renderTikTokModeHint();
    renderTikTokStatus();
  });
  elements.tiktokPrivacyInput.addEventListener('change', renderSelectionState);
  elements.tiktokCaptionInput.addEventListener('input', renderSelectionState);
  elements.tiktokHashtagsInput.addEventListener('input', renderSelectionState);
  elements.tiktokMentionsInput.addEventListener('input', renderSelectionState);
  elements.tiktokCoverTimestampInput.addEventListener('input', renderSelectionState);
  elements.allowCommentCheckbox.addEventListener('change', renderSelectionState);
  elements.allowDuetCheckbox.addEventListener('change', renderSelectionState);
  elements.allowStitchCheckbox.addEventListener('change', renderSelectionState);
  elements.brandOrganicCheckbox.addEventListener('change', renderSelectionState);
  elements.brandContentCheckbox.addEventListener('change', renderSelectionState);
  elements.musicConsentCheckbox.addEventListener('change', renderSelectionState);

  elements.mobileNavButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const target = button.dataset.mobileTarget || 'setup';
      switchMobilePanel(target);
    });
  });
}

async function hydrateConfig() {
  const local = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  let server = {};

  try {
    const response = await fetch('/api/config');
    if (response.ok) {
      const payload = await response.json();
      server = payload.publicConfig || {};
      state.serverConfig = server;
    }
  } catch (error) {
    server = {};
  }

  const merged = {
    teamName: server.teamName || local.teamName || 'Bounce',
    googleClientId: server.googleClientId || local.googleClientId || '',
    driveFolder: server.driveFolder || local.driveFolder || '',
    publicBaseUrl: server.publicBaseUrl || local.publicBaseUrl || '',
  };

  elements.teamNameInput.value = merged.teamName;
  elements.clientIdInput.value = merged.googleClientId;
  elements.folderInput.value = merged.driveFolder;
  elements.publicBaseUrlInput.value = merged.publicBaseUrl;
  syncComputedFields();
  maybeRefreshTokenClient();
}

async function saveConfig() {
  const payload = {
    teamName: elements.teamNameInput.value.trim() || 'Bounce',
    googleClientId: elements.clientIdInput.value.trim(),
    driveFolder: elements.folderInput.value.trim(),
    publicBaseUrl: elements.publicBaseUrlInput.value.trim().replace(/\/$/, ''),
  };

  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  state.serverConfig = { ...payload };
  syncComputedFields();

  try {
    const response = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`config-${response.status}`);
    }

    const saved = await response.json();
    state.serverConfig = saved.publicConfig || payload;
    setStatus('Configuración guardada para todo el equipo.', 'success');
  } catch (error) {
    setStatus('Guardé la config solo en este navegador. El guardado compartido no respondió.', 'warn');
  }
}

function syncComputedFields() {
  const base = elements.publicBaseUrlInput.value.trim().replace(/\/$/, '') || window.location.origin;
  const redirect = `${base}/api/tiktok/callback`;
  const isHttps = redirect.startsWith('https://');
  elements.tiktokRedirectPreview.textContent = isHttps
    ? redirect
    : `${redirect} (TikTok web exige HTTPS para OAuth)`;
}

function pollForGoogle() {
  if (window.google?.accounts?.oauth2) {
    state.googleReady = true;
    maybeRefreshTokenClient();
    return;
  }

  window.setTimeout(pollForGoogle, 250);
}

function maybeRefreshTokenClient() {
  if (!state.googleReady) {
    return;
  }

  const clientId = elements.clientIdInput.value.trim();
  if (!clientId) {
    state.tokenClient = null;
    renderAuthState();
    return;
  }

  state.tokenClient = google.accounts.oauth2.initTokenClient({
    client_id: clientId,
    scope: GOOGLE_SCOPE,
    callback: () => {},
  });
  renderAuthState();
}

async function checkServerHealth() {
  try {
    const response = await fetch('/api/health');
    if (!response.ok) {
      throw new Error('health-unavailable');
    }

    const payload = await response.json();
    elements.rendererChip.textContent = payload.tiktokConfigured
      ? 'Servidor local: listo + TikTok configurado'
      : 'Servidor local: listo';
    elements.rendererChip.className = 'status-chip ok';
  } catch (error) {
    elements.rendererChip.textContent = 'Servidor local: sin respuesta';
    elements.rendererChip.className = 'status-chip error';
    setStatus('No pude hablar con el servidor local. Abrí la app con `python server.py`.', 'warn');
  }
}

function renderAuthState() {
  const hasClientId = Boolean(elements.clientIdInput.value.trim());
  // Library button always enabled — loads from server, no user token needed
  elements.loadLibraryButton.disabled = false;

  if (state.accessToken) {
    elements.authPill.textContent = 'Google Drive conectado';
    elements.authPill.className = 'auth-pill ok';
    return;
  }

  if (hasClientId && state.googleReady) {
    elements.authPill.textContent = 'Listo para conectar';
    elements.authPill.className = 'auth-pill warn';
    return;
  }

  elements.authPill.textContent = 'Sin conectar';
  elements.authPill.className = 'auth-pill';
}

function setStatus(message, tone = 'info') {
  elements.statusMessage.textContent = message;
  elements.statusMessage.className = `status-message ${tone}`;
}

function setTikTokResult(message, tone = 'info') {
  elements.tiktokPublishResult.textContent = message;
  elements.tiktokPublishResult.className = `status-message ${tone}`;
}

function applyResponsiveMode() {
  state.isMobileMode = window.innerWidth <= MOBILE_BREAKPOINT;
  document.body.classList.toggle('mobile-mode', state.isMobileMode);

  if (!state.isMobileMode) {
    elements.mobilePanels.forEach((panel) => panel.classList.remove('mobile-panel-hidden'));
    elements.mobileNavButtons.forEach((button) => button.classList.remove('active'));
    return;
  }

  switchMobilePanel(state.mobilePanel, { scroll: false });
}

function switchMobilePanel(panelName, { scroll = true } = {}) {
  state.mobilePanel = panelName || 'setup';

  elements.mobileNavButtons.forEach((button) => {
    button.classList.toggle('active', button.dataset.mobileTarget === state.mobilePanel);
  });

  if (!state.isMobileMode) {
    return;
  }

  elements.mobilePanels.forEach((panel) => {
    panel.classList.toggle('mobile-panel-hidden', panel.dataset.mobilePanel !== state.mobilePanel);
  });

  if (scroll) {
    const targetPanel = elements.mobilePanels.find((panel) => panel.dataset.mobilePanel === state.mobilePanel);
    if (targetPanel) {
      targetPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}

async function connectGoogleDrive() {
  const clientId = elements.clientIdInput.value.trim();
  if (!clientId) {
    setStatus('Antes de conectar necesitás pegar tu Google OAuth Client ID.', 'warn');
    elements.clientIdInput.focus();
    return;
  }

  if (!state.tokenClient) {
    maybeRefreshTokenClient();
  }

  if (!state.tokenClient) {
    setStatus('Google todavía no terminó de cargar. Probá otra vez en un segundo.', 'warn');
    return;
  }

  try {
    await requestAccessToken({ prompt: state.accessToken ? '' : 'consent' });
    renderAuthState();
    setStatus('Conexión con Google Drive lista. Ya podés cargar la carpeta.', 'success');
  } catch (error) {
    setStatus(`No pude conectar con Google Drive: ${humanizeError(error)}`, 'error');
  }
}

function requestAccessToken({ prompt = 'consent' } = {}) {
  return new Promise((resolve, reject) => {
    state.tokenClient.callback = (response) => {
      if (response?.error) {
        reject(response);
        return;
      }

      state.accessToken = response.access_token || '';
      renderAuthState();
      resolve(response);
    };

    try {
      state.tokenClient.requestAccessToken({ prompt });
    } catch (error) {
      reject(error);
    }
  });
}

function signOutGoogle() {
  if (state.accessToken && window.google?.accounts?.oauth2?.revoke) {
    google.accounts.oauth2.revoke(state.accessToken, () => {});
  }

  state.accessToken = '';
  renderAuthState();
  setStatus('Sesión de Google cerrada en este navegador.', 'info');
}

async function loadLibrary(force = false) {
  clearRoulette();
  clearCurrentPreview();
  state.files = [];
  state.filteredFiles = [];
  state.rootFolder = { id: 'server', name: 'Biblioteca compartida' };
  state.folderCount = 0;
  state.selectedFileId = '';
  renderStats();
  renderLibrary();
  renderSelectedFileMeta(null);
  renderSelectionState();
  setStatus('Cargando biblioteca compartida desde el servidor...', 'info');

  try {
    const url = force ? '/api/drive/library?refresh=1' : '/api/drive/library';
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    if (data.error && !data.files?.length) {
      setStatus(`Error al cargar la biblioteca: ${data.error}`, 'error');
      return;
    }

    // Normalize server file format to match existing app format
    state.files = (data.files || []).map((f) => ({
      id: f.id,
      name: f.name,
      mimeType: f.mimeType,
      size: f.size || 0,
      modifiedTime: f.modifiedTime || '',
      createdTime: f.modifiedTime || '',
      resourceKey: '',
      webViewLink: `https://drive.google.com/file/d/${f.id}/view`,
      width: Number(f.videoMeta?.width || f.imageMeta?.width || 0),
      height: Number(f.videoMeta?.height || f.imageMeta?.height || 0),
      durationMs: Number(f.videoMeta?.durationMillis || 0),
      path: 'Bounce',
      kind: f.type === 'vid' ? 'video' : 'image',
    }));

    state.files.forEach((file) => {
      file.searchText = `${file.name} ${file.path} ${file.kind}`.toLowerCase();
    });

    state.folderCount = new Set(state.files.map((f) => f.path)).size;
    renderStats();
    applyFiltersAndRender();

    const cached = data.cached ? ' (caché)' : '';
    const warn = data.error ? ` · ⚠️ ${data.error}` : '';
    setStatus(
      `Biblioteca cargada${cached}: ${state.files.length} assets · ${state.files.filter((f) => f.kind === 'video').length} videos · ${state.files.filter((f) => f.kind === 'image').length} imágenes.${warn}`,
      data.error ? 'warn' : 'success'
    );

    if (state.isMobileMode) {
      switchMobilePanel('library');
    }
  } catch (error) {
    setStatus(`No pude cargar la biblioteca: ${humanizeError(error)}`, 'error');
  }
}

async function fetchFolderName(parsedFolder) {
  const folder = await fetchDriveJson(
    `https://www.googleapis.com/drive/v3/files/${parsedFolder.id}?fields=id,name,resourceKey&supportsAllDrives=true`,
    {
      headers: buildResourceKeyHeader(parsedFolder.id, parsedFolder.resourceKey),
    }
  );

  if (folder.resourceKey && !parsedFolder.resourceKey) {
    parsedFolder.resourceKey = folder.resourceKey;
  }

  return folder.name || 'Carpeta raíz';
}

async function crawlDriveTree(parsedFolder, rootName) {
  const queue = [{ id: parsedFolder.id, path: rootName, resourceKey: parsedFolder.resourceKey || '' }];
  const media = [];
  let visitedFolders = 0;

  while (queue.length) {
    const current = queue.shift();
    visitedFolders += 1;
    state.folderCount = visitedFolders - 1;
    setStatus(
      `Leyendo Drive... ${media.length} assets detectados · ${visitedFolders} carpetas revisadas`,
      'info'
    );

    let pageToken = '';
    do {
      const params = new URLSearchParams({
        q: `'${current.id}' in parents and trashed = false`,
        pageSize: '1000',
        fields: 'nextPageToken,files(id,name,mimeType,size,createdTime,modifiedTime,resourceKey,webViewLink,videoMediaMetadata(durationMillis,width,height),imageMediaMetadata(width,height))',
        includeItemsFromAllDrives: 'true',
        supportsAllDrives: 'true',
      });

      if (pageToken) {
        params.set('pageToken', pageToken);
      }

      const listing = await fetchDriveJson(
        `https://www.googleapis.com/drive/v3/files?${params.toString()}`,
        {
          headers: buildResourceKeyHeader(current.id, current.resourceKey),
        }
      );

      for (const item of listing.files || []) {
        if (item.mimeType === 'application/vnd.google-apps.folder') {
          queue.push({
            id: item.id,
            path: `${current.path} / ${item.name}`,
            resourceKey: item.resourceKey || '',
          });
          continue;
        }

        const kind = inferFileKind(item.mimeType);
        if (!kind) {
          continue;
        }

        media.push({
          id: item.id,
          name: item.name,
          mimeType: item.mimeType,
          size: Number(item.size || 0),
          createdTime: item.createdTime || '',
          modifiedTime: item.modifiedTime || '',
          resourceKey: item.resourceKey || '',
          webViewLink: item.webViewLink || '',
          width: Number(item.videoMediaMetadata?.width || item.imageMediaMetadata?.width || 0),
          height: Number(item.videoMediaMetadata?.height || item.imageMediaMetadata?.height || 0),
          durationMs: Number(item.videoMediaMetadata?.durationMillis || 0),
          path: current.path,
          kind,
        });
      }

      pageToken = listing.nextPageToken || '';
    } while (pageToken);
  }

  return media;
}

function applyFiltersAndRender() {
  const query = elements.searchInput.value.trim().toLowerCase();
  const typeFilter = elements.typeFilter.value;
  const sortMode = elements.sortSelect.value;

  state.filteredFiles = state.files
    .filter((file) => {
      if (typeFilter !== 'all' && file.kind !== typeFilter) {
        return false;
      }

      if (!query) {
        return true;
      }

      return file.searchText.includes(query);
    })
    .sort((left, right) => sortFiles(left, right, sortMode));

  renderLibrary();
}

function renderLibrary() {
  elements.libraryCounter.textContent = `${state.filteredFiles.length} resultados`;
  elements.pathBadge.textContent = state.rootFolder?.id
    ? `${state.rootFolder.name || state.rootFolder.id} · ${state.folderCount} subcarpetas`
    : 'Sin carpeta cargada';

  if (!state.filteredFiles.length) {
    elements.libraryGrid.className = 'library-grid empty-grid';
    elements.libraryGrid.innerHTML = `
      <div class="empty-card">
        <strong>No hay assets para mostrar.</strong>
        <p>Probá con otra carpeta, quitá filtros o revisá que la cuenta tenga acceso a los archivos.</p>
      </div>
    `;
    return;
  }

  elements.libraryGrid.className = 'library-grid';
  elements.libraryGrid.innerHTML = '';
  const fragment = document.createDocumentFragment();

  for (const file of state.filteredFiles) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = `media-card ${file.kind}${file.id === state.selectedFileId ? ' active' : ''}`;
    card.dataset.fileId = file.id;
    card.innerHTML = `
      <div class="card-topline">
        <span class="media-kind">${file.kind === 'video' ? 'VIDEO' : 'IMAGEN'}</span>
        <span class="media-size">${formatSize(file.size)}</span>
      </div>
      <h3>${escapeHtml(file.name)}</h3>
      <p>${escapeHtml(trimMiddle(file.path, 42))}</p>
      <div class="card-meta">
        <span>${file.width && file.height ? `${file.width}×${file.height}` : 'Sin dimensiones'}</span>
        <span>${file.kind === 'video' ? formatDuration(file.durationMs) : 'Foto'}</span>
      </div>
    `;
    card.addEventListener('click', () => {
      void selectFile(file);
    });
    fragment.appendChild(card);
  }

  elements.libraryGrid.appendChild(fragment);
}

function renderStats() {
  const videos = state.files.filter((file) => file.kind === 'video').length;
  const images = state.files.filter((file) => file.kind === 'image').length;

  elements.statAssets.textContent = String(state.files.length);
  elements.statVideos.textContent = String(videos);
  elements.statImages.textContent = String(images);
  elements.statFolders.textContent = String(state.folderCount);
}

async function selectFile(file) {
  state.selectedFileId = file.id;
  renderLibrary();
  renderSelectedFileMeta(file);
  renderSelectionState();
  elements.previewBadge.textContent = file.kind === 'video' ? 'Video seleccionado' : 'Imagen seleccionada';
  elements.previewBadge.className = 'preview-badge';
  elements.openInDriveLink.href = file.webViewLink || '#';
  elements.openInDriveLink.className = file.webViewLink ? 'button linkish' : 'button linkish disabled-link';
  await loadPreview(file);

  if (state.isMobileMode) {
    switchMobilePanel('editor');
  }
}

function getSelectedFile() {
  return state.files.find((file) => file.id === state.selectedFileId) || null;
}

function renderSelectedFileMeta(file) {
  elements.metaName.textContent = file?.name || '-';
  elements.metaPath.textContent = file?.path || '-';
  elements.metaType.textContent = file ? `${file.kind} · ${file.mimeType}` : '-';
  elements.metaDimensions.textContent = file?.width && file?.height ? `${file.width} × ${file.height}` : '-';
  elements.metaSize.textContent = file ? formatSize(file.size) : '-';
  elements.metaDuration.textContent = file?.kind === 'video' ? formatDuration(file.durationMs) : '-';
}

function renderSelectionState() {
  const file = getSelectedFile();
  elements.exportButton.disabled = !file;
  elements.exportButton.textContent = file?.kind === 'video' ? 'Exportar WEBM' : file ? 'Exportar PNG' : 'Exportar';
  elements.tiktokModeBadge.textContent = file ? (file.kind === 'video' ? 'Video listo' : 'Imagen elegida') : 'Video only';
  syncTikTokPublishAvailability();
  syncOverlayControls();
}

async function loadPreview(file, { force = false } = {}) {
  const token = ++state.currentPreviewToken;

  // For videos: reuse if same file and not forced
  if (!force && state.currentPreviewFileId === file.id && state.currentPreviewUrl) {
    showPreview(file);
    return;
  }

  setStatus(`Cargando preview de "${file.name}"...`, 'info');
  elements.previewPlaceholder.hidden = false;
  elements.previewPlaceholder.textContent = 'Cargando...';

  if (token !== state.currentPreviewToken) return;

  // Revoke previous object URL if it was a blob URL (images)
  if (state.currentPreviewUrl && state.currentPreviewUrl.startsWith('blob:')) {
    URL.revokeObjectURL(state.currentPreviewUrl);
  }

  if (file.kind === 'video') {
    state.currentPreviewUrl = `/api/drive/proxy/${file.id}`;
    state.currentPreviewFileId = file.id;
    state.currentPreviewBlob = null;
    showPreview(file, token);
    setStatus(`Preview listo para "${file.name}".`, 'success');
  } else {
    // Images: download as blob (small files, no streaming needed)
    try {
      const blob = await fetchDriveBlob(file);
      if (token !== state.currentPreviewToken) return;
      state.currentPreviewUrl = URL.createObjectURL(blob);
      state.currentPreviewBlob = blob;
      state.currentPreviewFileId = file.id;
      showPreview(file);
      setStatus(`Preview listo para "${file.name}".`, 'success');
    } catch (error) {
      if (token !== state.currentPreviewToken) return;
      clearCurrentPreview();
      elements.previewPlaceholder.hidden = false;
      elements.previewPlaceholder.textContent = 'No pude cargar el preview.';
      setStatus(`No pude cargar el preview: ${humanizeError(error)}`, 'error');
    }
  }
}

async function fetchDriveBlob(file) {
  const response = await fetch(`/api/drive/proxy/${file.id}`);
  if (!response.ok) throw new Error(`drive-preview-${response.status}`);
  return response.blob();
}

function showPreview(file, previewToken) {
  elements.previewPlaceholder.hidden = true;

  if (file.kind === 'image') {
    elements.previewVideo.pause();
    elements.previewVideo.hidden = true;
    elements.previewVideo.removeAttribute('src');
    elements.previewImage.src = state.currentPreviewUrl;
    elements.previewImage.hidden = false;
  } else {
    elements.previewImage.hidden = true;
    elements.previewImage.removeAttribute('src');

    // Remove old error listener if any
    if (elements.previewVideo._errorHandler) {
      elements.previewVideo.removeEventListener('error', elements.previewVideo._errorHandler);
    }

    // Listen for load errors (e.g. ffmpeg missing, unsupported format)
    elements.previewVideo._errorHandler = async () => {
      if (previewToken !== undefined && previewToken !== state.currentPreviewToken) return;
      // Try to get the actual error from the proxy
      try {
        const resp = await fetch(`/api/drive/proxy/${file.id}`);
        if (!resp.ok) {
          const data = await resp.json().catch(() => ({}));
          const msg = data.error || `Error ${resp.status}`;
          elements.previewPlaceholder.textContent = msg;
          elements.previewPlaceholder.hidden = false;
          elements.previewVideo.hidden = true;
          setStatus(`No se puede reproducir: ${msg}`, 'error');
          return;
        }
      } catch (_) {}
      elements.previewPlaceholder.textContent = 'Este formato de video no es compatible con el navegador.';
      elements.previewPlaceholder.hidden = false;
      elements.previewVideo.hidden = true;
      setStatus(`No se puede reproducir "${file.name}". Formato no soportado.`, 'error');
    };
    elements.previewVideo.addEventListener('error', elements.previewVideo._errorHandler, { once: true });

    elements.previewVideo.src = state.currentPreviewUrl;
    elements.previewVideo.hidden = false;
    elements.previewVideo.load();
  }

  syncOverlayControls();
}

function clearCurrentPreview() {
  if (state.currentPreviewUrl) {
    URL.revokeObjectURL(state.currentPreviewUrl);
  }

  state.currentPreviewUrl = '';
  state.currentPreviewBlob = null;
  state.currentPreviewFileId = '';
  elements.previewImage.hidden = true;
  elements.previewImage.removeAttribute('src');
  elements.previewVideo.pause();
  elements.previewVideo.hidden = true;
  elements.previewVideo.removeAttribute('src');
  elements.overlayPreview.hidden = true;
}

function syncOverlayControls() {
  const fontSize = Number(elements.fontSizeInput.value);
  const lineSpacing = Number(elements.lineSpacingInput.value);
  const topOffset = Number(elements.topOffsetInput.value);
  const maxWidth = Number(elements.maxWidthInput.value);
  const boxOpacity = Number(elements.boxOpacityInput.value);
  const overlayText = elements.overlayTextInput.value.trim();

  elements.fontSizeValue.textContent = String(fontSize);
  elements.lineSpacingValue.textContent = String(lineSpacing);
  elements.topOffsetValue.textContent = `${topOffset}%`;
  elements.maxWidthValue.textContent = `${maxWidth}%`;
  elements.boxOpacityValue.textContent = boxOpacity.toFixed(2);
  elements.overlayPreviewText.textContent = wrapTextForDisplay(overlayText || '');
  elements.overlayPreview.style.setProperty('--overlay-size', `${Math.max(28, fontSize * 0.34)}px`);
  elements.overlayPreview.style.setProperty('--overlay-top', `${topOffset}%`);
  elements.overlayPreview.style.setProperty('--overlay-width', `${maxWidth}%`);
  elements.overlayPreview.style.setProperty('--overlay-box-opacity', String(boxOpacity));
  elements.overlayPreview.hidden = !getSelectedFile() || !overlayText;
}

function wrapTextForDisplay(text) {
  return text.replace(/\s+/g, ' ').trim();
}

async function exportCurrentSelection() {
  const file = getSelectedFile();
  if (!file) {
    setStatus('Elegí un archivo antes de exportar.', 'warn');
    return;
  }

  elements.exportButton.disabled = true;
  elements.exportButton.textContent = file.kind === 'video' ? 'Exportando WEBM...' : 'Exportando PNG...';
  setStatus(`Procesando "${file.name}" desde el navegador...`, 'info');

  try {
    const exportAsset = await buildExportBlobForCurrentSelection(file);
    downloadBlob(exportAsset.blob, exportAsset.filename);
    setStatus(`Exportación lista: ${exportAsset.filename}`, 'success');
  } catch (error) {
    setStatus(`Falló la exportación: ${humanizeError(error)}`, 'error');
  } finally {
    renderSelectionState();
  }
}

async function buildExportBlobForCurrentSelection(file) {
  // For videos we stream via proxy — no blob needed. For images we need the blob.
  if (file.kind === 'image') {
    if (!state.currentPreviewBlob || state.currentPreviewFileId !== file.id) {
      await loadPreview(file);
    }
    if (!state.currentPreviewBlob) {
      throw new Error('No pude conseguir la imagen para exportar.');
    }
  } else {
    // Video: make sure preview URL is set
    if (!state.currentPreviewUrl || state.currentPreviewFileId !== file.id) {
      await loadPreview(file);
    }
  }

  const options = buildRenderOptions(file, elements.overlayTextInput.value.trim());
  const blob = file.kind === 'image'
    ? await exportImageClientSide(options)
    : await exportVideoClientSide(options, file);

  return {
    blob,
    filename: buildExportName(file),
    mimeType: file.kind === 'video' ? 'video/webm' : 'image/png',
  };
}

function buildRenderOptions(file, overlayText) {
  const fontSize = Number(elements.fontSizeInput.value);
  const topPercent = Number(elements.topOffsetInput.value);
  const maxWidthPercent = Number(elements.maxWidthInput.value);
  const lineSpacing = Number(elements.lineSpacingInput.value);
  const boxOpacity = Number(elements.boxOpacityInput.value);
  const fitMode = elements.fitModeInput.value;
  const wrappedText = overlayText
    ? wrapTextForRender(overlayText, fontSize, maxWidthPercent)
    : '';

  return {
    teamName: elements.teamNameInput.value.trim() || 'Bounce',
    fitMode,
    outputWidth: OUTPUT_WIDTH,
    outputHeight: OUTPUT_HEIGHT,
    fontSize,
    topPercent,
    maxWidthPercent,
    lineSpacing,
    boxOpacity,
    wrappedText,
    assetKind: file.kind,
  };
}

function wrapTextForRender(text, fontSize, maxWidthPercent) {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  context.font = `700 ${fontSize}px Arial`;

  const maxWidth = OUTPUT_WIDTH * (maxWidthPercent / 100);
  const paragraphs = text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  const lines = [];
  for (const paragraph of paragraphs.length ? paragraphs : [text.trim()]) {
    const words = paragraph.split(/\s+/);
    let currentLine = '';

    for (const word of words) {
      const candidate = currentLine ? `${currentLine} ${word}` : word;
      if (context.measureText(candidate).width > maxWidth && currentLine) {
        lines.push(currentLine);
        currentLine = word;
      } else {
        currentLine = candidate;
      }
    }

    if (currentLine) {
      lines.push(currentLine);
    }
  }

  return lines.join('\n');
}

function buildExportName(file) {
  const stem = file.name
    .replace(/\.[^.]+$/, '')
    .replace(/[^\w\-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
  return `${stem || 'bounce-export'}${file.kind === 'video' ? '.webm' : '.png'}`;
}

async function exportImageClientSide(options) {
  const imageBitmap = await createImageBitmap(state.currentPreviewBlob);
  const canvas = document.createElement('canvas');
  canvas.width = OUTPUT_WIDTH;
  canvas.height = OUTPUT_HEIGHT;
  const context = canvas.getContext('2d');

  drawSceneToCanvas(context, imageBitmap, options);
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('No pude generar el PNG.'));
        return;
      }
      resolve(blob);
    }, 'image/png');
  });
}

async function exportVideoClientSide(options, file) {
  if (!window.MediaRecorder) {
    throw new Error('Este navegador no soporta MediaRecorder para exportar videos.');
  }

  const mimeType = pickRecorderMimeType();
  if (!mimeType) {
    throw new Error('Este navegador no soporta exportación de video en WEBM.');
  }

  const video = document.createElement('video');
  video.src = state.currentPreviewUrl || URL.createObjectURL(state.currentPreviewBlob);
  video.preload = 'auto';
  video.playsInline = true;
  video.muted = true;

  await waitForVideo(video);

  const canvas = document.createElement('canvas');
  canvas.width = OUTPUT_WIDTH;
  canvas.height = OUTPUT_HEIGHT;
  const context = canvas.getContext('2d');

  const canvasStream = canvas.captureStream(30);
  const sourceStream = typeof video.captureStream === 'function' ? video.captureStream() : null;
  const composedStream = new MediaStream([
    ...canvasStream.getVideoTracks(),
    ...(sourceStream ? sourceStream.getAudioTracks() : []),
  ]);

  const recorder = new MediaRecorder(composedStream, { mimeType });
  const chunks = [];
  const stopPromise = new Promise((resolve, reject) => {
    recorder.addEventListener('dataavailable', (event) => {
      if (event.data?.size) {
        chunks.push(event.data);
      }
    });
    recorder.addEventListener('stop', () => {
      resolve(new Blob(chunks, { type: mimeType }));
    });
    recorder.addEventListener('error', (event) => {
      reject(event.error || new Error('MediaRecorder falló.'));
    });
  });

  let rafId = 0;
  let lastPercent = -1;

  const drawFrame = () => {
    drawSceneToCanvas(context, video, options);

    if (video.duration) {
      const percent = Math.min(100, Math.round((video.currentTime / video.duration) * 100));
      if (percent !== lastPercent) {
        lastPercent = percent;
        setStatus(`Exportando "${file.name}"... ${percent}%`, 'info');
      }
    }

    if (!video.paused && !video.ended) {
      rafId = requestAnimationFrame(drawFrame);
    }
  };

  recorder.start(250);
  drawSceneToCanvas(context, video, options);
  video.currentTime = 0;
  await video.play();
  rafId = requestAnimationFrame(drawFrame);

  await new Promise((resolve) => {
    video.addEventListener('ended', resolve, { once: true });
  });

  cancelAnimationFrame(rafId);
  drawSceneToCanvas(context, video, options);
  if (recorder.state !== 'inactive') {
    recorder.stop();
  }

  return stopPromise;
}

async function waitForVideo(video) {
  if (video.readyState >= 1) {
    return;
  }

  await new Promise((resolve, reject) => {
    video.addEventListener('loadedmetadata', resolve, { once: true });
    video.addEventListener('error', () => reject(new Error('No pude leer los metadatos del video.')), { once: true });
  });
}

function pickRecorderMimeType() {
  const candidates = [
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
  ];

  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || '';
}

function drawSceneToCanvas(context, source, options) {
  context.clearRect(0, 0, OUTPUT_WIDTH, OUTPUT_HEIGHT);
  context.fillStyle = '#000000';
  context.fillRect(0, 0, OUTPUT_WIDTH, OUTPUT_HEIGHT);
  drawMediaLayer(context, source, options.fitMode);
  drawOverlayLayer(context, options);
}

function drawMediaLayer(context, source, fitMode) {
  const sourceWidth = source.videoWidth || source.width;
  const sourceHeight = source.videoHeight || source.height;
  if (!sourceWidth || !sourceHeight) {
    return;
  }

  const scale = fitMode === 'contain'
    ? Math.min(OUTPUT_WIDTH / sourceWidth, OUTPUT_HEIGHT / sourceHeight)
    : Math.max(OUTPUT_WIDTH / sourceWidth, OUTPUT_HEIGHT / sourceHeight);

  const drawWidth = sourceWidth * scale;
  const drawHeight = sourceHeight * scale;
  const offsetX = (OUTPUT_WIDTH - drawWidth) / 2;
  const offsetY = (OUTPUT_HEIGHT - drawHeight) / 2;
  context.drawImage(source, offsetX, offsetY, drawWidth, drawHeight);
}

function drawOverlayLayer(context, options) {
  const lines = options.wrappedText ? options.wrappedText.split('\n').filter(Boolean) : [];
  if (!lines.length) {
    return;
  }

  const fontSize = Number(options.fontSize);
  const lineSpacing = Number(options.lineSpacing);
  const lineHeight = fontSize + lineSpacing;
  const topY = OUTPUT_HEIGHT * (Number(options.topPercent) / 100);
  const centerX = OUTPUT_WIDTH / 2;

  context.save();
  context.font = `700 ${fontSize}px Arial`;
  context.textAlign = 'center';
  context.textBaseline = 'top';

  const widths = lines.map((line) => context.measureText(line).width);
  const textWidth = Math.max(...widths);
  const blockHeight = lines.length * lineHeight - lineSpacing;
  const paddingX = Math.round(fontSize * 0.42);
  const paddingY = Math.round(fontSize * 0.22);
  const left = centerX - (textWidth / 2) - paddingX;
  const top = topY - paddingY;
  const boxWidth = textWidth + paddingX * 2;
  const boxHeight = blockHeight + paddingY * 2;
  const boxOpacity = Number(options.boxOpacity);

  if (boxOpacity > 0) {
    context.fillStyle = `rgba(0, 0, 0, ${boxOpacity})`;
    drawRoundedRect(context, left, top, boxWidth, boxHeight, Math.round(fontSize * 0.24));
    context.fill();
  }

  context.fillStyle = '#ffffff';
  context.shadowColor = 'rgba(0, 0, 0, 0.88)';
  context.shadowBlur = Math.round(fontSize * 0.18);
  context.lineWidth = Math.max(2, Math.round(fontSize * 0.05));
  context.strokeStyle = 'rgba(0, 0, 0, 0.82)';

  lines.forEach((line, index) => {
    const y = topY + index * lineHeight;
    context.strokeText(line, centerX, y);
    context.fillText(line, centerX, y);
  });

  context.restore();
}

function drawRoundedRect(context, x, y, width, height, radius) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.arcTo(x + width, y, x + width, y + height, radius);
  context.arcTo(x + width, y + height, x, y + height, radius);
  context.arcTo(x, y + height, x, y, radius);
  context.arcTo(x, y, x + width, y, radius);
  context.closePath();
}

async function loadTikTokStatus(showBusy = false) {
  if (showBusy) {
    setTikTokResult('Actualizando estado de TikTok...', 'info');
  }

  try {
    const response = await fetch('/api/tiktok/status');
    if (!response.ok) {
      throw new Error(`tiktok-status-${response.status}`);
    }

    state.tiktokStatus = await response.json();
    renderTikTokStatus();
  } catch (error) {
    state.tiktokStatus = {
      configured: false,
      connected: false,
      oauthReady: false,
      missingConfig: [],
      notes: ['No pude leer el estado de TikTok desde el backend.'],
      privacyLevelOptions: [],
    };
    renderTikTokStatus();
  }
}

function renderTikTokStatus() {
  const status = state.tiktokStatus || {
    configured: false,
    connected: false,
    oauthReady: false,
    missingConfig: [],
    notes: [],
    privacyLevelOptions: [],
  };
  const creator = status.creator || {};

  if (!status.configured) {
    elements.tiktokStatusBadge.textContent = 'TikTok: falta configurar';
    elements.tiktokStatusBadge.className = 'status-chip warn';
    elements.tiktokAccountLabel.textContent = 'Sin cuenta conectada';
    elements.tiktokChecklist.innerHTML = `
      Falta completar <code>.studio-secrets.json</code> con:
      ${status.missingConfig.length ? status.missingConfig.map((item) => `<code>${escapeHtml(item)}</code>`).join(', ') : '<code>tiktokClientKey</code>, <code>tiktokClientSecret</code> y redirect URI HTTPS'}
    `;
  } else if (!status.oauthReady) {
    elements.tiktokStatusBadge.textContent = 'TikTok: falta HTTPS';
    elements.tiktokStatusBadge.className = 'status-chip warn';
    elements.tiktokAccountLabel.textContent = 'OAuth listo, pero sin redirect HTTPS';
    elements.tiktokChecklist.innerHTML = `Configurá un <code>Public Base URL</code> con HTTPS o definí <code>tiktokRedirectUri</code> en <code>studio-secrets.json</code>.`;
  } else if (!status.connected) {
    elements.tiktokStatusBadge.textContent = 'TikTok: listo para conectar';
    elements.tiktokStatusBadge.className = 'status-chip';
    elements.tiktokAccountLabel.textContent = 'Cuenta no conectada todavía';
    elements.tiktokChecklist.innerHTML = `
      La app ya tiene el backend preparado. Siguiente paso: conectar la cuenta de Bounce en TikTok.
      <br>${status.notes?.length ? escapeHtml(status.notes.join(' ')) : ''}
    `;
  } else {
    elements.tiktokStatusBadge.textContent = 'TikTok: conectado';
    elements.tiktokStatusBadge.className = 'status-chip ok';
    elements.tiktokAccountLabel.textContent = creator.nickname
      ? `${creator.nickname}${creator.username ? ` · @${creator.username}` : ''}`
      : creator.username
        ? `@${creator.username}`
        : 'Cuenta conectada';
    elements.tiktokChecklist.innerHTML = `
      ${creator.bioDescription ? `${escapeHtml(creator.bioDescription)}<br>` : ''}
      ${status.maxVideoPostDurationSec ? `Duración máxima habilitada: <strong>${status.maxVideoPostDurationSec}s</strong>.` : 'Cuenta lista para publicar videos.'}
      ${status.notes?.length ? `<br>${escapeHtml(status.notes.join(' '))}` : ''}
    `;
  }

  populatePrivacySelect(status.privacyLevelOptions || []);
  syncTikTokToggleAvailability();
  syncTikTokPublishAvailability();
}

function populatePrivacySelect(options) {
  const current = elements.tiktokPrivacyInput.value;
  elements.tiktokPrivacyInput.innerHTML = '<option value="">Elegí privacidad</option>';

  for (const option of options) {
    const opt = document.createElement('option');
    opt.value = option;
    opt.textContent = humanizePrivacy(option);
    if (option === current) {
      opt.selected = true;
    }
    elements.tiktokPrivacyInput.appendChild(opt);
  }
}

function syncTikTokToggleAvailability() {
  const status = state.tiktokStatus || {};
  const isDirectMode = elements.tiktokPostModeInput.value === 'DIRECT_POST';

  const toggleRules = [
    [elements.allowCommentCheckbox, Boolean(status.commentDisabled) || !isDirectMode],
    [elements.allowDuetCheckbox, Boolean(status.duetDisabled) || !isDirectMode],
    [elements.allowStitchCheckbox, Boolean(status.stitchDisabled) || !isDirectMode],
  ];

  for (const [checkbox, disabled] of toggleRules) {
    checkbox.disabled = disabled;
    if (disabled) {
      checkbox.checked = false;
    }
  }
}

function renderTikTokModeHint() {
  elements.tiktokModeHint.innerHTML = elements.tiktokPostModeInput.value === 'DIRECT_POST'
    ? 'En <strong>Direct post</strong>, el caption, hashtags y privacidad viajan desde esta web. TikTok puede limitar visibilidad pública hasta que tu app pase la auditoría.'
    : 'En <strong>Inbox draft</strong>, el video se exporta al inbox de TikTok para seguirlo dentro de la app. Este modo no garantiza llevar caption/hashtags desde la web.';
}

function syncTikTokPublishAvailability() {
  const file = getSelectedFile();
  const status = state.tiktokStatus || {};
  const isDirectMode = elements.tiktokPostModeInput.value === 'DIRECT_POST';
  const privacyChosen = Boolean(elements.tiktokPrivacyInput.value);
  const canPublish = Boolean(
    file &&
      file.kind === 'video' &&
      status.connected &&
      !state.currentPublishing &&
      elements.musicConsentCheckbox.checked &&
      (!isDirectMode || privacyChosen)
  );

  elements.connectTikTokButton.disabled = !status.configured || !status.oauthReady;
  elements.disconnectTikTokButton.disabled = !status.connected;
  elements.publishTikTokButton.disabled = !canPublish;

  if (file?.kind === 'image') {
    setTikTokResult('La publicación directa a TikTok desde esta web está enfocada en videos. Para fotos/carruseles hace falta trabajar con URLs verificadas por dominio.', 'warn');
  }
}

function connectTikTok() {
  const status = state.tiktokStatus || {};
  if (!status.configured) {
    setTikTokResult('Antes de conectar TikTok completá studio-secrets.json.', 'warn');
    return;
  }

  if (!status.oauthReady) {
    setTikTokResult('TikTok Login Kit web requiere un redirect URI HTTPS.', 'warn');
    return;
  }

  window.location.href = '/api/tiktok/oauth/start';
}

async function disconnectTikTok() {
  try {
    const response = await fetch('/api/tiktok/disconnect', { method: 'POST' });
    if (!response.ok) {
      throw new Error(`disconnect-${response.status}`);
    }
    await loadTikTokStatus();
    setTikTokResult('Cuenta de TikTok desconectada.', 'success');
  } catch (error) {
    setTikTokResult(`No pude desconectar TikTok: ${humanizeError(error)}`, 'error');
  }
}

async function publishToTikTok() {
  const file = getSelectedFile();
  const status = state.tiktokStatus || {};
  const isDirectMode = elements.tiktokPostModeInput.value === 'DIRECT_POST';

  if (!file || file.kind !== 'video') {
    setTikTokResult('Elegí un video antes de subir a TikTok.', 'warn');
    return;
  }

  if (!status.connected) {
    setTikTokResult('Primero conectá la cuenta de TikTok.', 'warn');
    return;
  }

  if (isDirectMode && !elements.tiktokPrivacyInput.value) {
    setTikTokResult('Para Direct Post tenés que elegir una privacidad.', 'warn');
    return;
  }

  if (!elements.musicConsentCheckbox.checked) {
    setTikTokResult('TikTok exige confirmar “Music Usage Confirmation” antes de publicar.', 'warn');
    return;
  }

  if (status.maxVideoPostDurationSec && file.durationMs) {
    const durationSec = Math.ceil(file.durationMs / 1000);
    if (durationSec > status.maxVideoPostDurationSec) {
      setTikTokResult(`Este video dura ${durationSec}s y la cuenta hoy tiene un máximo de ${status.maxVideoPostDurationSec}s.`, 'warn');
      return;
    }
  }

  state.currentPublishing = true;
  syncTikTokPublishAvailability();
  setTikTokResult(`Procesando "${file.name}" para TikTok...`, 'info');

  try {
    const exportAsset = await buildExportBlobForCurrentSelection(file);
    const payload = {
      postMode: elements.tiktokPostModeInput.value,
      title: composeTikTokTitle(),
      privacyLevel: elements.tiktokPrivacyInput.value,
      allowComment: elements.allowCommentCheckbox.checked,
      allowDuet: elements.allowDuetCheckbox.checked,
      allowStitch: elements.allowStitchCheckbox.checked,
      brandOrganicToggle: elements.brandOrganicCheckbox.checked,
      brandContentToggle: elements.brandContentCheckbox.checked,
      musicConsent: elements.musicConsentCheckbox.checked,
      videoCoverTimestampMs: Math.max(0, Math.round(Number(elements.tiktokCoverTimestampInput.value || 0) * 1000)),
      durationSec: file.durationMs ? Math.ceil(file.durationMs / 1000) : 0,
    };

    const formData = new FormData();
    formData.append('payload', JSON.stringify(payload));
    formData.append('file', exportAsset.blob, exportAsset.filename);

    const response = await fetch('/api/tiktok/post', {
      method: 'POST',
      body: formData,
    });
    const result = await safeReadJson(response);
    if (!response.ok) {
      throw new Error(result?.error || `tiktok-post-${response.status}`);
    }

    const publishId = result?.result?.publishId || 'sin publish id';
    const modeLabel = payload.postMode === 'DIRECT_POST' ? 'Direct post' : 'Inbox draft';
    setTikTokResult(`${modeLabel} enviado a TikTok. Publish ID: ${publishId}`, 'success');

    if (state.isMobileMode) {
      switchMobilePanel('tiktok');
    }
  } catch (error) {
    setTikTokResult(`Falló la subida a TikTok: ${humanizeError(error)}`, 'error');
  } finally {
    state.currentPublishing = false;
    syncTikTokPublishAvailability();
  }
}

function composeTikTokTitle() {
  const caption = elements.tiktokCaptionInput.value.trim();
  const hashtags = normalizePrefixedTokens(elements.tiktokHashtagsInput.value, '#');
  const mentions = normalizePrefixedTokens(elements.tiktokMentionsInput.value, '@');
  return [caption, [...mentions, ...hashtags].join(' ')].filter(Boolean).join('\n').trim();
}

function normalizePrefixedTokens(raw, prefix) {
  const seen = new Set();
  return raw
    .split(/[\s,]+/)
    .map((token) => token.trim())
    .filter(Boolean)
    .map((token) => (token.startsWith(prefix) ? token : `${prefix}${token}`))
    .filter((token) => {
      const key = token.toLowerCase();
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
}

function applyTikTokQueryState() {
  const url = new URL(window.location.href);
  const tiktok = url.searchParams.get('tiktok');
  const message = url.searchParams.get('message');
  if (!tiktok) {
    return;
  }

  if (tiktok === 'connected') {
    setTikTokResult('Cuenta de TikTok conectada. Ya podés actualizar el estado y publicar.', 'success');
    void loadTikTokStatus();
    if (state.isMobileMode) {
      switchMobilePanel('tiktok');
    }
  } else if (tiktok === 'missing-config') {
    setTikTokResult('Falta configurar studio-secrets.json antes de conectar TikTok.', 'warn');
  } else if (tiktok === 'https-required') {
    setTikTokResult('TikTok Login Kit web exige un redirect URI HTTPS.', 'warn');
  } else if (tiktok === 'error') {
    setTikTokResult(message || 'TikTok devolvió un error durante OAuth.', 'error');
  }

  url.searchParams.delete('tiktok');
  url.searchParams.delete('message');
  window.history.replaceState({}, '', url.toString());
}

async function runRoulette() {
  clearRoulette();

  if (!state.filteredFiles.length) {
    setStatus('No hay resultados para usar en la ruleta.', 'warn');
    return;
  }

  elements.rouletteButton.disabled = true;
  let ticks = 0;
  let lastId = '';

  state.rouletteTimer = window.setInterval(() => {
    const randomFile = state.filteredFiles[Math.floor(Math.random() * state.filteredFiles.length)];
    lastId = randomFile.id;
    highlightRouletteCard(randomFile.id);
    ticks += 1;

    if (ticks >= 24) {
      clearRoulette();
      const winner = state.filteredFiles.find((entry) => entry.id === lastId) || state.filteredFiles[0];
      void selectFile(winner);
      setStatus(`La ruleta eligió "${winner.name}".`, 'success');
    }
  }, 90);
}

function highlightRouletteCard(fileId) {
  document.querySelectorAll('.media-card.roulette').forEach((card) => {
    card.classList.remove('roulette');
  });
  const card = document.querySelector(`.media-card[data-file-id="${fileId}"]`);
  if (card) {
    card.classList.add('roulette');
  }
}

function clearRoulette() {
  if (state.rouletteTimer) {
    window.clearInterval(state.rouletteTimer);
    state.rouletteTimer = null;
  }

  elements.rouletteButton.disabled = false;
  document.querySelectorAll('.media-card.roulette').forEach((card) => {
    card.classList.remove('roulette');
  });
}

async function fetchDriveJson(url, options = {}) {
  const response = await fetchWithAuth(url, options);
  if (!response.ok) {
    const payload = await safeReadJson(response);
    throw new Error(payload?.error?.message || payload?.error || `drive-${response.status}`);
  }
  return response.json();
}

async function fetchWithAuth(url, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  headers.set('Authorization', `Bearer ${state.accessToken}`);
  const response = await fetch(url, { ...options, headers });

  if (response.status === 401 && retry && state.tokenClient) {
    await requestAccessToken({ prompt: '' });
    return fetchWithAuth(url, options, false);
  }

  return response;
}

async function safeReadJson(response) {
  try {
    return await response.json();
  } catch (error) {
    return null;
  }
}

function buildResourceKeyHeader(fileId, resourceKey) {
  if (!resourceKey) {
    return {};
  }

  return {
    'X-Goog-Drive-Resource-Keys': `${fileId}/${resourceKey}`,
  };
}

function parseDriveFolderInput(input) {
  if (!input) {
    return { id: '', resourceKey: '' };
  }

  const trimmed = input.trim();
  const folderMatch = trimmed.match(/\/folders\/([a-zA-Z0-9_-]+)/);
  if (folderMatch) {
    try {
      const url = new URL(trimmed);
      return {
        id: folderMatch[1],
        resourceKey: url.searchParams.get('resourcekey') || '',
      };
    } catch (error) {
      return { id: folderMatch[1], resourceKey: '' };
    }
  }

  try {
    const url = new URL(trimmed);
    const maybeId = url.searchParams.get('id');
    if (maybeId) {
      return {
        id: maybeId,
        resourceKey: url.searchParams.get('resourcekey') || '',
      };
    }
  } catch (error) {
    // Ignore invalid URL parsing and fall back to raw input below.
  }

  return {
    id: trimmed.replace(/[?#].*$/, ''),
    resourceKey: '',
  };
}

function inferFileKind(mimeType) {
  if (mimeType.startsWith('video/')) {
    return 'video';
  }

  if (mimeType.startsWith('image/')) {
    return 'image';
  }

  return '';
}

function sortFiles(left, right, mode) {
  switch (mode) {
    case 'oldest':
      return new Date(left.createdTime) - new Date(right.createdTime);
    case 'name':
      return left.name.localeCompare(right.name, 'es', { sensitivity: 'base' });
    case 'duration':
      return right.durationMs - left.durationMs;
    case 'newest':
    default:
      return new Date(right.createdTime) - new Date(left.createdTime);
  }
}

function humanizePrivacy(value) {
  const labels = {
    PUBLIC_TO_EVERYONE: 'Público',
    MUTUAL_FOLLOW_FRIENDS: 'Amigos mutuos',
    FOLLOWER_OF_CREATOR: 'Seguidores',
    SELF_ONLY: 'Solo yo',
  };
  return labels[value] || value;
}

function formatSize(bytes) {
  if (!bytes) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes;
  let unit = 0;

  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }

  return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatDuration(durationMs) {
  if (!durationMs) {
    return '0:00';
  }

  const totalSeconds = Math.floor(durationMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  return `${minutes}:${String(seconds).padStart(2, '0')}`;
}

function trimMiddle(value, maxLength) {
  if (value.length <= maxLength) {
    return value;
  }

  const lead = Math.ceil((maxLength - 1) / 2);
  const tail = Math.floor((maxLength - 1) / 2);
  return `${value.slice(0, lead)}…${value.slice(-tail)}`;
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function humanizeError(error) {
  if (!error) {
    return 'error desconocido';
  }

  if (typeof error === 'string') {
    return error;
  }

  if (error.message) {
    return error.message;
  }

  if (error.error) {
    return error.error;
  }

  return 'error desconocido';
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}
