(function () {
  'use strict';

  var DEFAULT_ROBOT_NAME = 'LimX';
  var activeRobotName = DEFAULT_ROBOT_NAME;
  var activeRobotAccid = '';
  var LANG_KEY = 'tw:language';

  function normalizeLanguage(value) {
    var text = String(value || '').toLowerCase().replace('_', '-');
    if (text.indexOf('zh') === 0 || text === 'chinese') return 'zh-cn';
    if (text.indexOf('en') === 0 || text === 'english') return 'en';
    return '';
  }

  function urlLanguage() {
    try {
      var params = new URLSearchParams(window.location.search);
      return normalizeLanguage(params.get('language') || params.get('lang') || params.get('locale'));
    } catch (_) {
      return '';
    }
  }

  function currentLanguage() {
    var fromUrl = urlLanguage();
    if (fromUrl) return fromUrl;
    try {
      var stored = localStorage.getItem(LANG_KEY);
      if (stored) return normalizeLanguage(stored);
    } catch (_) {}
    return normalizeLanguage(navigator.language) || 'zh-cn';
  }

  function syncLangCookie() {
    var lang = currentLanguage() || 'zh-cn';
    try { localStorage.setItem(LANG_KEY, lang); } catch (_) {}
    document.cookie = 'limx_lang=' + lang + '; path=/; max-age=31536000; SameSite=Lax';
  }

  function toggleLanguage(e) {
    if (e) { e.stopPropagation(); e.preventDefault(); }
    var next = currentLanguage() === 'zh-cn' ? 'en' : 'zh-cn';
    try { localStorage.setItem(LANG_KEY, next); } catch (_) {}
    document.cookie = 'limx_lang=' + next + '; path=/; max-age=31536000; SameSite=Lax';
    var params = new URLSearchParams(window.location.search);
    params.set('language', next);
    window.location.replace(window.location.pathname + '?' + params.toString() + window.location.hash);
  }

  function hijackLanguageItem() {
    var items = document.querySelectorAll(
      '[class*="settings-menu"] [class*="submenu-label"],' +
      '[class*="settings-menu"] [class*="submenuLabel"]'
    );
    for (var i = 0; i < items.length; i++) {
      var label = items[i];
      if (label.getAttribute('data-lang-hijacked')) continue;
      var text = (label.textContent || '').trim();
      if (text !== 'Language' && text !== '语言') continue;

      label.setAttribute('data-lang-hijacked', '1');
      var parent = label.closest('[class*="option"]') || label.parentElement;
      if (!parent) continue;

      var isZh = currentLanguage() === 'zh-cn';
      label.textContent = isZh ? 'English' : '中文';
      parent.setAttribute('data-lang-toggle', '1');

      var caret = parent.querySelector('[class*="expand-caret"], [class*="expandCaret"]');
      if (caret) caret.style.display = 'none';

      var submenu = parent.querySelector('[class*="language-submenu"], [class*="languageSubmenu"]');
      if (submenu) submenu.style.display = 'none';
      var nextSib = parent.nextElementSibling;
      if (nextSib && nextSib.matches &&
          nextSib.matches('[class*="language-submenu"], [class*="languageSubmenu"]')) {
        nextSib.style.display = 'none';
      }

      parent.style.cursor = 'pointer';
      parent.addEventListener('click', toggleLanguage, true);
    }
  }

  function hideOriginalLanguageMenu() {
    var submenus = document.querySelectorAll(
      '[class*="language-submenu"], [class*="languageSubmenu"], [class*="language-menu-item"], [class*="languageMenuItem"]'
    );
    for (var i = 0; i < submenus.length; i++) {
      if (!submenus[i].closest('[data-lang-toggle]')) {
        submenus[i].style.setProperty('display', 'none', 'important');
      }
    }

    var restored = document.querySelectorAll('div, li, span');
    for (var j = 0; j < restored.length; j++) {
      var node = restored[j];
      if (node.closest('[class*="language-submenu"], [class*="languageSubmenu"], [class*="language-menu-item"], [class*="languageMenuItem"]')) {
        continue;
      }
      var text = (node.textContent || '').trim();
      if (/^Switch\s+To\b/i.test(text) || /^Switch\s+to\b/i.test(text)) {
        node.style.removeProperty('display');
      }
    }
  }

  function fixSettingsMenuPosition() {
    var toggle = document.querySelector('[data-lang-toggle]');
    if (!toggle) return;
    var node = toggle.parentElement;
    var best = null;
    while (node && node !== document.body) {
      var text = node.textContent || '';
      var rect = node.getBoundingClientRect();
      if ((text.indexOf('Settings') !== -1 || text.indexOf('设置') !== -1) &&
          rect.width >= 110 && rect.width <= 360 &&
          rect.height >= 60 && rect.height <= 420) {
        best = node;
      }
      node = node.parentElement;
    }
    if (!best) return;

    var menuRect = best.getBoundingClientRect();
    var overflow = menuRect.right - window.innerWidth + 12;
    if (overflow > 0) {
      best.style.setProperty('transform', 'translateX(-' + Math.ceil(overflow) + 'px)', 'important');
      best.style.setProperty('max-width', 'calc(100vw - 24px)', 'important');
    }
  }

  function injectStyles() {
    if (document.getElementById('limx-bootstrap-css')) return;
    if (!document.head) return;
    var style = document.createElement('style');
    style.id = 'limx-bootstrap-css';
    style.textContent = [
      '[class*="settings-menu"] [class*="language-submenu"],',
      '[class*="settings-menu"] [class*="languageSubmenu"] {',
      '  display: none !important;',
      '}',
      '[class*="language-menu-item"], [class*="languageMenuItem"] {',
      '  display: none !important;',
      '}',
      '[data-lang-toggle] {',
      '  min-width: 120px !important;',
      '}',
      '[data-lang-toggle] [class*="submenu-label"],',
      '[data-lang-toggle] [class*="submenuLabel"] {',
      '  white-space: nowrap !important;',
      '  overflow: visible !important;',
      '}',
      '[data-lang-toggle], [data-lang-toggle] * {',
      '  max-width: none !important;',
      '}',
      '[class*="stage-size-row"], [class*="stageSizeRow"],',
      '[class*="stage-size-toggle-group"], [class*="stageSizeToggleGroup"],',
      '[class*="fullscreen-buttons-row"], [class*="fullscreenButtonsRow"] {',
      '  display: none !important;',
      '}',
      '.stage-header_stage-header-wrapper_1F4gT {',
      '  position: relative !important;',
      '  top: auto !important;',
      '  right: auto !important;',
      '  left: auto !important;',
      '  width: 100% !important;',
      '}',
      '.stage-wrapper_stage-canvas-wrapper_3ewpr,',
      '[class*="stage-canvas-wrapper"], [class*="stageCanvasWrapper"] {',
      '  display: none !important;',
      '  height: 0 !important;',
      '  padding: 0 !important;',
      '}',
      '.gui_target-wrapper_36Gbz {',
      '  display: none !important;',
      '}',
      '[class*="stage-and-target-wrapper"], [class*="stageAndTargetWrapper"] {',
      '  flex-basis: 334px !important;',
      '  width: 334px !important;',
      '}',
      '[class*="controls-container"], [class*="controlsContainer"] {',
      '  flex-direction: row !important;',
      '  align-items: center !important;',
      '  gap: 8px !important;',
      '  min-width: 0 !important;',
      '}',
      '.limx-run-controls-row {',
      '  display: flex;',
      '  align-items: center;',
      '  gap: 8px;',
      '}',
      '.limx-run-separator {',
      '  height: 1px;',
      '  flex: 0 0 auto;',
      '  background: var(--ui-black-transparent, rgba(0,0,0,0.14));',
      '  margin: 10px 0 8px;',
      '  cursor: default;',
      '  user-select: none;',
      '  pointer-events: none;',
      '}',
      '.limx-project-panel {',
      '  position: relative;',
      '  width: 100%;',
      '  max-height: 260px;',
      '  overflow: hidden;',
      '  border: 1px solid var(--ui-black-transparent, rgba(0,0,0,0.12));',
      '  border-radius: 12px;',
      '  background: var(--ui-modal-background, rgba(255,255,255,0.96));',
      '  color: var(--ui-modal-foreground, var(--text-primary, #333));',
      '  box-shadow: 0 4px 16px rgba(0,0,0,0.10);',
      '  font-size: 12px;',
      '}',
      '.limx-project-panel-header {',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: space-between;',
      '  padding: 7px 9px;',
      '  font-weight: 700;',
      '  color: var(--ui-modal-foreground, var(--text-primary, #333));',
      '}',
      '.limx-project-panel-tools {',
      '  display: flex;',
      '  gap: 5px;',
      '}',
      '.limx-project-list {',
      '  max-height: 92px;',
      '  overflow: auto;',
      '  border-top: 1px solid var(--ui-black-transparent, rgba(0,0,0,0.08));',
      '  border-bottom: 1px solid var(--ui-black-transparent, rgba(0,0,0,0.08));',
      '}',
      '.limx-project-item {',
      '  padding: 6px 9px;',
      '  cursor: pointer;',
      '  white-space: nowrap;',
      '  overflow: hidden;',
      '  text-overflow: ellipsis;',
      '}',
      '.limx-project-item:hover { background: var(--ui-secondary, #eef5ff); }',
      '.limx-project-item.selected { background: #1677ff; color: white; }',
      '.limx-project-actions {',
      '  display: grid;',
      '  grid-template-columns: repeat(2, 1fr);',
      '  gap: 5px;',
      '  padding: 7px;',
      '}',
      '.limx-project-actions button, .limx-project-panel-header button {',
      '  border: 1px solid var(--ui-black-transparent, rgba(0,0,0,0.16));',
      '  border-radius: 7px;',
      '  background: var(--ui-white, #fff);',
      '  color: var(--text-primary, #333);',
      '  padding: 4px 6px;',
      '  cursor: pointer;',
      '}',
      '.limx-project-actions button:hover, .limx-project-panel-header button:hover {',
      '  background: var(--ui-secondary, #f1f7ff);',
      '}',
      '.limx-project-actions button:disabled, .limx-project-panel-header button:disabled {',
      '  opacity: 0.45;',
      '  cursor: not-allowed;',
      '  background: var(--ui-tertiary, #f3f3f3);',
      '}',
      '.limx-empty-project-prompt {',
      '  position: absolute;',
      '  inset: 0;',
      '  z-index: 20;',
      '  display: flex;',
      '  align-items: center;',
      '  justify-content: center;',
      '  background: color-mix(in srgb, var(--ui-modal-background, #fff) 92%, transparent);',
      '  color: var(--ui-modal-foreground, var(--text-primary, #333));',
      '  text-align: center;',
      '  padding: 24px;',
      '}',
      '.limx-empty-project-card {',
      '  max-width: 360px;',
      '  padding: 22px;',
      '  border: 1px solid var(--ui-black-transparent, rgba(0,0,0,0.12));',
      '  border-radius: 16px;',
      '  background: var(--ui-modal-background, white);',
      '  box-shadow: 0 8px 24px rgba(0,0,0,0.12);',
      '}',
      '.limx-empty-project-card h3 {',
      '  margin: 0 0 10px;',
      '  font-size: 18px;',
      '}',
      '.limx-empty-project-card p {',
      '  margin: 0 0 16px;',
      '  color: var(--text-primary, #666);',
      '}',
      '.limx-empty-project-card button {',
      '  margin: 0 5px;',
      '  border: 1px solid var(--ui-black-transparent, rgba(0,0,0,0.16));',
      '  border-radius: 8px;',
      '  background: #1677ff;',
      '  color: white;',
      '  padding: 7px 12px;',
      '  cursor: pointer;',
      '}',
      '.limx-readonly-overlay {',
      '  position: absolute;',
      '  inset: 0;',
      '  z-index: 18;',
      '  display: block;',
      '  background: color-mix(in srgb, var(--ui-modal-background, #fff) 58%, transparent);',
      '  color: var(--ui-modal-foreground, #334155);',
      '  font-size: 14px;',
      '  font-weight: 600;',
      '  pointer-events: auto;',
      '  cursor: not-allowed;',
      '  user-select: none;',
      '}',
      '.limx-readonly-overlay span {',
      '  position: absolute;',
      '  top: 14px;',
      '  left: var(--limx-readonly-left, 14px);',
      '  padding: 8px 14px;',
      '  border-radius: 999px;',
      '  background: var(--ui-modal-background, rgba(255,255,255,0.92));',
      '  border: 1px solid var(--ui-black-transparent, rgba(0,0,0,0.12));',
      '  box-shadow: 0 4px 14px rgba(0,0,0,0.12);',
      '}'
    ].join('\n');
    document.head.appendChild(style);
  }

  function titleFor(robotName, accid) {
    var title = (robotName || DEFAULT_ROBOT_NAME) + ' Robot Programming';
    var serial = String(accid || '').trim();
    return serial ? title + ' - ' + serial : title;
  }

  function applyRobotName(robotName, accid) {
    var name = robotName || DEFAULT_ROBOT_NAME;
    var serial = String(accid || '').trim();
    activeRobotName = name;
    activeRobotAccid = serial;
    document.title = titleFor(name, serial);
    document.documentElement.setAttribute('data-robot-name', name);
    if (serial) {
      document.documentElement.setAttribute('data-robot-accid', serial);
    } else {
      document.documentElement.removeAttribute('data-robot-accid');
    }
    enforceBranding();
  }

  function replaceBrandText(text) {
    var title = titleFor(activeRobotName, activeRobotAccid);
    return String(text)
      .replace(/LIMX\s*(LimX|Oli|Luna) Robot Program(?:m)?ing(?:\s*-\s*[^\n\r]*)?/g, 'LIMX ' + title)
      .replace(/\b(LimX|Oli|Luna) Robot Program(?:m)?ing(?:\s*-\s*[^\n\r]*)?/g, title);
  }

  function rewriteBrandText(root) {
    var walker = document.createTreeWalker(
      root || document.body,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: function (node) {
          var parent = node.parentElement;
          if (!parent || /^(SCRIPT|STYLE|TEXTAREA|INPUT)$/i.test(parent.tagName)) {
            return NodeFilter.FILTER_REJECT;
          }
          return /Robot Program(?:m)?ing/.test(node.nodeValue) ?
            NodeFilter.FILTER_ACCEPT :
            NodeFilter.FILTER_REJECT;
        }
      }
    );
    var node;
    while ((node = walker.nextNode())) {
      var next = replaceBrandText(node.nodeValue);
      if (node.nodeValue !== next) {
        node.nodeValue = next;
      }
    }
  }

  function enforceBranding() {
    var expected = titleFor(activeRobotName, activeRobotAccid);
    if (document.title !== expected) {
      document.title = expected;
    }
    if (document.body) {
      rewriteBrandText(document.body);
    }
  }

  function fetchRobotInfo() {
    fetch('/robot-info', {cache: 'no-store'})
      .then(function (response) {
        return response.ok ? response.json() : {};
      })
      .then(function (data) {
        applyRobotName(data.robot_name || DEFAULT_ROBOT_NAME, data.accid || '');
      })
      .catch(function () {
        applyRobotName(DEFAULT_ROBOT_NAME, '');
      });
  }

  // ── Background runner integration ──

  var bgRunnerHooked = false;
  var bgStatusPoller = null;
  var bgSyncing = false;
  var projectPanelReady = false;
  var bgStatusChecked = false;
  var initialProjectLoaded = false;
  var selectedProject = '';
  var currentProjectName = '';
  var projectsCache = [];
  var projectDirty = false;
  var saveInFlight = false;
  var loadingProjectName = '';
  var runningProjectName = '';
  var browserProjectRunning = false;
  var browserRunningProjectName = '';
  var browserRunStartedAt = 0;
  var lastBrowserGreenFlagRunAt = 0;
  var suppressProjectChangedUntil = 0;
  var loadProjectToken = 0;
  var projectEditEnabled = false;
  var lastLocalizedLanguage = '';
  var defaultBlocksCategorySelected = false;
  var defaultBlocksCategoryDeadline = Date.now() + 8000;
  var defaultBlocksCategoryScrollPending = false;
  var lastBgStopAt = 0;

  function isChinese() {
    return currentLanguage().indexOf('zh') === 0;
  }

  function bgMsg(zh, en) {
    return isChinese() ? zh : en;
  }

  function visibleElement(node) {
    if (!node || !node.getBoundingClientRect) return false;
    var rect = node.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function chooseDefaultBlocksCategory() {
    if (defaultBlocksCategorySelected || Date.now() > defaultBlocksCategoryDeadline) return;
    var toolbox = document.querySelector('.blocklyToolboxDiv');
    if (!toolbox) return;
    if (!defaultBlocksCategoryScrollPending &&
        window.Scratch && window.Scratch.gui && typeof window.Scratch.gui.getBlockly === 'function') {
      defaultBlocksCategoryScrollPending = true;
      window.Scratch.gui.getBlockly().then(function (Blockly) {
        [0, 80, 200, 500, 1000].forEach(function (delay, index, delays) {
          window.setTimeout(function () {
            if (scrollBlocklyFlyoutToTop(Blockly) && index === delays.length - 1) {
              defaultBlocksCategorySelected = true;
            }
          }, delay);
        });
        defaultBlocksCategoryScrollPending = false;
      }).catch(function () {
        defaultBlocksCategoryScrollPending = false;
      });
    }
    var flyout = document.querySelector('.blocklyFlyout');
    [toolbox, flyout].forEach(function (node) {
      if (!node) return;
      node.scrollTop = 0;
      node.scrollLeft = 0;
      Array.prototype.forEach.call(node.querySelectorAll('*'), function (child) {
        child.scrollTop = 0;
        child.scrollLeft = 0;
      });
    });
    var firstCategory = Array.prototype.slice.call(document.querySelectorAll(
      '.scratchCategoryMenuItem, .blocklyTreeRow, .blocklyToolboxCategory, [role="treeitem"]'
    )).filter(visibleElement)[0];
    try {
      if (firstCategory) firstCategory.scrollIntoView({block: 'start'});
    } catch (_) {}
  }

  function scrollBlocklyFlyoutToTop(Blockly) {
    var workspace = Blockly && (Blockly.getMainWorkspace ? Blockly.getMainWorkspace() : Blockly.mainWorkspace);
    var flyout = workspace && workspace.getFlyout && workspace.getFlyout();
    if (!flyout) return false;
    try {
      if (typeof flyout.scrollToStart === 'function') flyout.scrollToStart();
      if (typeof flyout.setScrollPos === 'function') flyout.setScrollPos(0);
      if (flyout.scrollbar_ && typeof flyout.scrollbar_.set === 'function') flyout.scrollbar_.set(0);
      if (flyout.workspace_) {
        flyout.workspace_.scrollY = 0;
        if (typeof flyout.workspace_.translate === 'function') {
          var metrics = flyout.workspace_.getMetrics && flyout.workspace_.getMetrics();
          var absoluteLeft = metrics && metrics.absoluteLeft || 0;
          var absoluteTop = metrics && metrics.absoluteTop || 0;
          flyout.workspace_.translate((flyout.workspace_.scrollX || 0) + absoluteLeft, absoluteTop);
        }
      }
      return true;
    } catch (err) {
      console.warn('[bootstrap] failed to reset flyout scroll:', err);
      return false;
    }
  }

  function getVM() {
    return window.__scratch_vm || null;
  }

  function postJson(url, data) {
    return fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data || {})
    }).then(function (r) { return r.json(); });
  }

  function postBlob(url, blob) {
    return fetch(url, {
      method: 'POST',
      body: blob
    }).then(function (r) { return r.json(); });
  }

  function formatProjectTime(value) {
    if (!value) return '';
    try {
      var d = new Date(value * 1000);
      return d.getFullYear().toString() + '-' +
        (d.getMonth() + 1).toString().padStart(2, '0') + '-' +
        d.getDate().toString().padStart(2, '0') + ' ' +
        d.getHours().toString().padStart(2, '0') + ':' +
        d.getMinutes().toString().padStart(2, '0');
    } catch (_) {
      return '';
    }
  }

  function escapeHtml(text) {
    return String(text || '').replace(/[&<>"']/g, function (ch) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[ch];
    });
  }

  function conflictMessage() {
    return bgMsg('项目名称已存在，请重新取名。', 'Project name already exists. Please choose another name.');
  }

  function getBlocksWorkspace() {
    return document.querySelector('[class*="blocks-wrapper"], [class*="blocksWrapper"]');
  }

  function setProjectEditing(enabled) {
    projectEditEnabled = Boolean(enabled);
    updateReadonlyOverlay();
    updateProjectButtons();
  }

  function updateReadonlyOverlay() {
    var workspace = getBlocksWorkspace();
    if (!workspace) return;
    var existing = document.getElementById('limx-readonly-overlay');
    var shouldShow = Boolean(currentProjectName && projectsCache.length && !projectEditEnabled);
    if (!shouldShow) {
      if (existing) existing.remove();
      return;
    }
    if (!existing) {
      existing = document.createElement('div');
      existing.id = 'limx-readonly-overlay';
      existing.className = 'limx-readonly-overlay';
      existing.innerHTML = '<span></span>';
      workspace.appendChild(existing);
    }
    var label = existing.querySelector('span');
    if (label) {
      var readonlyText = bgMsg('点击“编辑”后修改项目', 'Click "Edit" to modify this project');
      if (label.textContent !== readonlyText) label.textContent = readonlyText;
    }
    var left = 14;
    var workspaceRect = workspace.getBoundingClientRect();
    var blocklyArea = workspace.querySelector('.injectionDiv, .blocklySvg, .blocklyWorkspace');
    if (blocklyArea) {
      var blocklyRect = blocklyArea.getBoundingClientRect();
      existing.style.left = Math.max(0, blocklyRect.left - workspaceRect.left) + 'px';
      existing.style.top = Math.max(0, blocklyRect.top - workspaceRect.top) + 'px';
      existing.style.width = Math.max(0, blocklyRect.width) + 'px';
      existing.style.height = Math.max(0, blocklyRect.height) + 'px';
    } else {
      existing.style.left = '0';
      existing.style.top = '0';
      existing.style.width = '100%';
      existing.style.height = '100%';
    }
    var toolbox = workspace.querySelector('.blocklyToolboxDiv');
    var flyout = workspace.querySelector('.blocklyFlyout');
    [toolbox, flyout].forEach(function (node) {
      if (!node) return;
      var rect = node.getBoundingClientRect();
      if (rect.width > 0 && rect.right > workspaceRect.left && rect.left < workspaceRect.right) {
        left = Math.max(left, rect.right - workspaceRect.left + 14);
      }
    });
    existing.style.setProperty('--limx-readonly-left', Math.round(left) + 'px');
  }

  function updateEmptyProjectPrompt() {
    var workspace = getBlocksWorkspace();
    if (!workspace) return;
    var existing = document.getElementById('limx-empty-project-prompt');
    if (projectsCache.length) {
      if (existing) existing.remove();
      return;
    }
    var promptEl = existing;
    if (!promptEl) {
      promptEl = document.createElement('div');
      promptEl.id = 'limx-empty-project-prompt';
      promptEl.className = 'limx-empty-project-prompt';
      promptEl.addEventListener('click', function (e) {
        var action = e.target.getAttribute && e.target.getAttribute('data-empty-action');
        if (action === 'create') createEmptyProject();
        if (action === 'import') {
          ensureProjectPanel();
          var input = document.getElementById('limx-project-import-input');
          if (input) input.click();
        }
      });
      workspace.appendChild(promptEl);
    }
    var nextHtml = [
      '<div class="limx-empty-project-card">',
      '  <h3>' + bgMsg('还没有项目', 'No projects yet') + '</h3>',
      '  <p>' + bgMsg('请先新建一个项目，或导入已有 .sb3 项目。', 'Create a project or import an existing .sb3 file.') + '</p>',
      '  <button type="button" data-empty-action="create">' + bgMsg('新建项目', 'New Project') + '</button>',
      '  <button type="button" data-empty-action="import">' + bgMsg('导入项目', 'Import Project') + '</button>',
      '</div>'
    ].join('');
    if (promptEl.innerHTML !== nextHtml) promptEl.innerHTML = nextHtml;
    updateReadonlyOverlay();
  }

  function autoLoadInitialProject() {
    if (initialProjectLoaded || !bgStatusChecked || window.__LIMX_BG_ACTIVE__) return;
    if (!selectedProject || !projectsCache.length) return;
    if (loadBgProject(selectedProject, false)) initialProjectLoaded = true;
  }

  function markProjectDirty() {
    if (!projectEditEnabled || bgSyncing || Date.now() < suppressProjectChangedUntil || !currentProjectName) return;
    projectDirty = true;
    updateProjectButtons();
  }

  function hasUnsavedCurrentProject() {
    return Boolean(currentProjectName && projectDirty);
  }

  function isProjectRunning(name) {
    return Boolean(name && (
      runningProjectName === name ||
      browserRunningProjectName === name
    ));
  }

  function saveCurrentProject() {
    var vm = getVM();
    if (!vm || !currentProjectName || bgSyncing || !projectDirty || saveInFlight) return;
    if (!confirm(bgMsg('确认保存当前修改到后台项目文件？', 'Save current changes to the background project file?'))) {
      return;
    }
    saveInFlight = true;
    updateProjectButtons();
    vm.saveProjectSb3().then(function (blob) {
      return postBlob('/project/save?name=' + encodeURIComponent(currentProjectName), blob);
    }).then(function (data) {
      if (data.result !== 'success') {
        alert(data.message || bgMsg('保存失败，请确认后台服务已更新并运行。', 'Save failed. Please confirm the bridge service is updated and running.'));
      } else {
        projectDirty = false;
        projectEditEnabled = false;
        updateReadonlyOverlay();
        refreshProjectList();
      }
    }).catch(function (err) {
      alert('Error: ' + err.message);
    }).then(function () {
      saveInFlight = false;
      updateProjectButtons();
    });
  }

  function setButtonText(root, selector, zh, en) {
    var node = root && root.querySelector(selector);
    if (node) {
      var text = bgMsg(zh, en);
      if (node.textContent !== text) node.textContent = text;
    }
  }

  function updateProjectPanelText() {
    var panel = document.getElementById('limx-project-panel');
    if (!panel) return;
    setButtonText(panel, '[data-project-action="create"]', '新建', 'New');
    setButtonText(panel, '[data-project-action="import"]', '导入', 'Import');
    setButtonText(panel, '[data-project-action="run"]', '后台运行', 'Run in Background');
    setButtonText(panel, '[data-project-action="persist"]', '保存', 'Save');
    setButtonText(panel, '[data-project-action="download"]', '下载', 'Download');
    setButtonText(panel, '[data-project-action="edit"]', '编辑', 'Edit');
    setButtonText(panel, '[data-project-action="rename"]', '重命名', 'Rename');
    setButtonText(panel, '[data-project-action="delete"]', '删除', 'Delete');
  }

  function updateLocalizedUi() {
    updateProjectPanelText();
    updateProjectTitle();
    updateReadonlyOverlay();
    updateEmptyProjectPrompt();
    var lang = currentLanguage();
    if (lang !== lastLocalizedLanguage) {
      lastLocalizedLanguage = lang;
      renderProjectList();
    }
  }

  function ensureProjectPanel() {
    var controls = document.querySelector('[class*="controls-container"], [class*="controlsContainer"]');
    if (!controls) return;
    var host = document.querySelector('[class*="stage-and-target-wrapper"], [class*="stageAndTargetWrapper"]') ||
      controls.parentElement;
    if (!host) return;

    if (!host.querySelector('.limx-run-separator')) {
      var separator = document.createElement('div');
      separator.className = 'limx-run-separator';
      host.appendChild(separator);
    }

    var panel = document.getElementById('limx-project-panel');
    if (!panel) {
      var panel = document.createElement('div');
      panel.id = 'limx-project-panel';
      panel.className = 'limx-project-panel';
      panel.innerHTML = [
        '<div class="limx-project-panel-header">',
        '  <span id="limx-project-title"></span>',
        '  <span class="limx-project-panel-tools">',
        '    <button type="button" data-project-action="create"></button>',
        '    <button type="button" data-project-action="import"></button>',
        '  </span>',
        '</div>',
        '<input id="limx-project-import-input" type="file" accept=".sb3" style="display:none" />',
        '<div class="limx-project-list" id="limx-project-list"></div>',
        '<div class="limx-project-actions">',
        '  <button type="button" data-project-action="run"></button>',
        '  <button type="button" data-project-action="persist"></button>',
        '  <button type="button" data-project-action="download"></button>',
        '  <button type="button" data-project-action="edit"></button>',
        '  <button type="button" data-project-action="rename"></button>',
        '  <button type="button" data-project-action="delete"></button>',
        '</div>'
      ].join('');
      host.appendChild(panel);

      panel.addEventListener('click', function (e) {
        var item = e.target.closest && e.target.closest('.limx-project-item');
        if (item) {
          if (!item.hasAttribute('data-name')) return;
          if (hasUnsavedCurrentProject()) {
            alert(bgMsg('当前项目有未保存修改，请先保存。', 'Please save current changes first.'));
            return;
          }
          selectedProject = item.getAttribute('data-name') || '';
          renderProjectList();
          loadBgProject(selectedProject, false);
          return;
        }
        var action = e.target.getAttribute && e.target.getAttribute('data-project-action');
        if (action && !e.target.disabled) handleProjectAction(action);
      });
      var input = panel.querySelector('#limx-project-import-input');
      if (input) {
        input.addEventListener('change', function () {
          importProjectFile(input.files && input.files[0]);
          input.value = '';
        });
      }
      projectPanelReady = true;
      refreshProjectList();
    } else if (panel.parentElement !== host) {
      host.appendChild(panel);
    }

    updateProjectPanelText();
    updateProjectTitle();
    updateProjectButtons();
  }

  function updateProjectTitle() {
    var title = document.getElementById('limx-project-title');
    if (!title) return;
    var text = bgMsg('项目库', 'Projects');
    if (hasUnsavedCurrentProject()) text += bgMsg('（未保存）', ' (Unsaved)');
    if (title.textContent !== text) title.textContent = text;
  }

  function updateProjectButtons() {
    updateProjectTitle();
    var panel = document.getElementById('limx-project-panel');
    if (!panel) return;
    var hasCurrent = Boolean(currentProjectName);
    var hasSelected = Boolean(selectedProject);
    var unsaved = hasUnsavedCurrentProject();
    var selectedRunning = isProjectRunning(selectedProject);
    var buttons = panel.querySelectorAll('[data-project-action]');
    for (var i = 0; i < buttons.length; i++) {
      var button = buttons[i];
      var action = button.getAttribute('data-project-action');
      var disabled = false;
      if (selectedRunning) {
        disabled = true;
      } else if (action === 'persist') {
        disabled = !hasCurrent || !unsaved || saveInFlight;
      } else if (unsaved) {
        disabled = true;
      } else if (action === 'delete') {
        disabled = !hasSelected || selectedRunning;
      } else if (['run', 'download', 'edit', 'rename', 'delete'].indexOf(action) !== -1) {
        disabled = !hasSelected;
      }
      button.disabled = disabled;
    }
  }

  function refreshProjectList() {
    fetch('/project/list', {cache: 'no-store'}).then(function (r) { return r.json(); })
      .then(function (data) {
        projectsCache = Array.isArray(data.projects) ? data.projects : [];
        if (!selectedProject && projectsCache.length) selectedProject = projectsCache[0].name;
        if (selectedProject && !projectsCache.some(function (p) { return p.name === selectedProject; })) {
          selectedProject = projectsCache.length ? projectsCache[0].name : '';
        }
        renderProjectList();
        updateEmptyProjectPrompt();
        autoLoadInitialProject();
      }).catch(function () {
        projectsCache = [];
        renderProjectList();
        updateEmptyProjectPrompt();
      });
  }

  function renderProjectList() {
    var list = document.getElementById('limx-project-list');
    if (!list) return;
    if (!projectsCache.length) {
      list.innerHTML = '<div class="limx-project-empty">' + bgMsg('暂无后台项目', 'No projects') + '</div>';
      updateProjectButtons();
      return;
    }
    list.innerHTML = projectsCache.map(function (p) {
      var selected = p.name === selectedProject ? ' selected' : '';
      var running = isProjectRunning(p.name);
      return '<div class="limx-project-item' + selected + '" data-name="' +
        encodeURIComponent(p.name) + '" title="' + escapeHtml(p.name) + '">' +
        escapeHtml(p.name) +
        (running ? ' · ' + bgMsg('运行中', 'Running') : '') +
        (p.modified ? ' · ' + formatProjectTime(p.modified) : '') +
        '</div>';
    }).join('');
    var items = list.querySelectorAll('.limx-project-item');
    for (var i = 0; i < items.length; i++) {
      var encoded = items[i].getAttribute('data-name');
      if (encoded) items[i].setAttribute('data-name', decodeURIComponent(encoded));
    }
    updateProjectButtons();
  }

  function requireSelectedProject() {
    if (selectedProject) return selectedProject;
    alert(bgMsg('请先选择一个项目', 'Select a project first'));
    return '';
  }

  function normalizeProjectName(name) {
    var value = String(name || '').trim();
    if (!value) return '';
    return /\.sb3$/i.test(value) ? value : value + '.sb3';
  }

  function createEmptyProject() {
    var name = prompt(bgMsg('请输入新项目名称', 'Enter new project name'));
    name = normalizeProjectName(name);
    if (!name) return;
    postJson('/project/create_empty', {name: name}).then(function (data) {
      if (data.result === 'success') {
        selectedProject = data.name;
        currentProjectName = data.name;
        projectDirty = false;
        refreshProjectList();
        loadBgProject(data.name, false);
      } else {
        alert(/already exists/i.test(data.message || '') ? conflictMessage() : (data.message || bgMsg('新建失败', 'Create failed')));
      }
    });
  }

  function importProjectFile(file) {
    if (!file) return;
    var defaultName = file.name || 'project.sb3';
    var name = prompt(bgMsg('请输入导入后的项目名称', 'Project name after import'), defaultName);
    name = normalizeProjectName(name);
    if (!name) return;
    fetch('/project/upload?name=' + encodeURIComponent(name), {
      method: 'POST',
      body: file
    }).then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.result === 'success') {
          selectedProject = name;
          currentProjectName = name;
          projectDirty = false;
          refreshProjectList();
          loadBgProject(name, false);
        } else {
          alert(/already exists/i.test(data.message || '') ? conflictMessage() : (data.message || bgMsg('导入失败', 'Import failed')));
        }
      });
  }

  function handleProjectAction(action) {
    if (action === 'create') {
      if (hasUnsavedCurrentProject()) {
        alert(bgMsg('当前项目有未保存修改，请先保存。', 'Please save current changes first.'));
        return;
      }
      createEmptyProject();
      return;
    }
    if (action === 'import') {
      if (hasUnsavedCurrentProject()) {
        alert(bgMsg('当前项目有未保存修改，请先保存。', 'Please save current changes first.'));
        return;
      }
      var input = document.getElementById('limx-project-import-input');
      if (input) input.click();
      return;
    }
    var name = action === 'persist' ? currentProjectName : requireSelectedProject();
    if (!name) return;
    if (action !== 'persist' && hasUnsavedCurrentProject()) {
      alert(bgMsg('当前项目有未保存修改，请先保存。', 'Please save current changes first.'));
      return;
    }
    if (action === 'run') {
      postJson('/project/stop', {}).then(function () {
        return new Promise(function (resolve) { setTimeout(resolve, 300); });
      }).then(function () {
        return postJson('/project/start', {name: name});
      }).then(function (data) {
        if (data.result === 'success') {
          window.__LIMX_BG_ACTIVE__ = true;
          runningProjectName = name;
          showBgIndicator(true);
          renderProjectList();
          startBgStatusPoll();
        } else {
          alert(data.message || bgMsg('启动失败', 'Start failed'));
        }
      });
    } else if (action === 'persist') {
      saveCurrentProject();
    } else if (action === 'download') {
      window.location.href = '/project/download?name=' + encodeURIComponent(name);
    } else if (action === 'edit') {
      loadBgProject(name, true);
    } else if (action === 'rename') {
      var next = prompt(bgMsg('输入新的项目名称', 'New project name'), name);
      if (!next || next === name) return;
      postJson('/project/rename', {old_name: name, new_name: next}).then(function (data) {
        if (data.result === 'success') {
          selectedProject = data.name;
          if (currentProjectName === name) currentProjectName = data.name;
          refreshProjectList();
        } else {
          alert(/already exists/i.test(data.message || '') ? conflictMessage() : (data.message || bgMsg('重命名失败', 'Rename failed')));
        }
      });
    } else if (action === 'delete') {
      if (isProjectRunning(name)) {
        alert(bgMsg('正在运行的项目不能删除。', 'A running project cannot be deleted.'));
        updateProjectButtons();
        return;
      }
      if (!confirm(bgMsg('确定删除该项目？', 'Delete this project?'))) return;
      var remainingProjects = projectsCache
        .map(function (p) { return p.name; })
        .filter(function (projectName) { return projectName !== name; });
      var nextProject = remainingProjects.length ? remainingProjects[0] : '';
      postJson('/project/delete', {name: name}).then(function (data) {
        if (data.result === 'success') {
          if (currentProjectName === name) {
            currentProjectName = '';
            projectDirty = false;
        projectEditEnabled = false;
          }
          selectedProject = nextProject;
          refreshProjectList();
          if (nextProject) {
            loadBgProject(nextProject, false);
          } else {
            updateEmptyProjectPrompt();
            updateProjectButtons();
          }
        } else {
          alert(data.message || bgMsg('删除失败', 'Delete failed'));
        }
      });
    }
  }

  function bgStop() {
    var now = Date.now();
    if (now - lastBgStopAt < 100) return;
    lastBgStopAt = now;
    window.__LIMX_BG_ACTIVE__ = false;
    runningProjectName = '';
    showBgIndicator(false);
    stopBgStatusPoll();
    renderProjectList();
    updateProjectButtons();
    try {
      new Image().src = '/project/stop-now?t=' + now;
    } catch (_) {}
    fetch('/project/stop', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: '{}',
      keepalive: true
    }).catch(function () {
      try {
        if (navigator.sendBeacon) {
          navigator.sendBeacon('/project/stop', new Blob(['{}'], {type: 'application/json'}));
        }
      } catch (_) {}
    });
  }

  window.__LIMX_REQUEST_ROBOT_STOP__ = bgStop;

  function startBgStatusPoll() {
    stopBgStatusPoll();
    bgStatusPoller = setInterval(function () {
      fetch('/project/status').then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.state !== 'running') {
            window.__LIMX_BG_ACTIVE__ = false;
            runningProjectName = '';
            showBgIndicator(false);
            stopBgStatusPoll();
          } else {
            runningProjectName = data.project || '';
          }
          renderProjectList();
        }).catch(function () {});
    }, 3000);
  }

  function stopBgStatusPoll() {
    if (bgStatusPoller) {
      clearInterval(bgStatusPoller);
      bgStatusPoller = null;
    }
  }

  function findStopAllButton() {
    var buttons = document.querySelectorAll('img[title], img[aria-label]');
    for (var i = 0; i < buttons.length; i++) {
      var button = buttons[i];
      var text = [
        button.getAttribute('title') || '',
        button.getAttribute('aria-label') || ''
      ].join(' ').toLowerCase();
      if (/\bstop\b/.test(text) || text.indexOf('停止') !== -1) {
        return button;
      }
    }
    return null;
  }

  function placeBgIndicator(el) {
    var stopButton = findStopAllButton();
    if (stopButton && stopButton.parentElement) {
      el.style.cssText =
        'position:static;z-index:auto;background:rgba(22,119,255,0.92);color:#fff;' +
        'height:22px;padding:0 10px;border-radius:12px;font-size:12px;font-weight:500;' +
        'box-shadow:0 1px 4px rgba(0,0,0,0.16);pointer-events:auto;cursor:pointer;' +
        'display:inline-flex;align-items:center;gap:6px;line-height:1;margin-left:6px;' +
        'align-self:center;white-space:nowrap;vertical-align:middle;';
      if (el.parentElement !== stopButton.parentElement || el.previousElementSibling !== stopButton) {
        stopButton.parentElement.insertBefore(el, stopButton.nextSibling);
      }
      return;
    }
    el.style.cssText = 'position:fixed;top:60px;right:12px;z-index:99999;' +
      'background:rgba(22,119,255,0.92);color:#fff;padding:5px 14px;border-radius:16px;' +
      'font-size:13px;font-weight:500;box-shadow:0 2px 8px rgba(0,0,0,0.18);' +
      'pointer-events:auto;cursor:pointer;display:flex;align-items:center;gap:6px;';
    if (el.parentElement !== document.body) document.body.appendChild(el);
  }

  function showBgIndicator(active) {
    var el = document.getElementById('limx-bg-indicator');
    if (active) {
      if (!el) {
        el = document.createElement('div');
        el.id = 'limx-bg-indicator';
        el.innerHTML = '<span style="display:inline-block;width:8px;height:8px;' +
          'border-radius:50%;background:#52c41a;animation:limxBgPulse 1.5s infinite"></span>' +
          '<span id="limx-bg-text"></span>';
        var pulseStyle = document.createElement('style');
        pulseStyle.textContent = '@keyframes limxBgPulse{0%,100%{opacity:1}50%{opacity:0.3}}';
        document.head.appendChild(pulseStyle);
        el.addEventListener('click', function () {
          if (confirm(bgMsg('停止后台运行？', 'Stop background execution?'))) {
            bgStop();
          }
        });
      }
      placeBgIndicator(el);
      var textEl = document.getElementById('limx-bg-text');
      if (textEl) textEl.textContent = bgMsg('后台运行中', 'Running');
    } else if (el) {
      el.remove();
    }
  }

  function setBrowserProjectRunning(running) {
    browserProjectRunning = Boolean(running);
    browserRunningProjectName = running ? (currentProjectName || selectedProject || '') : '';
    if (running) browserRunStartedAt = Date.now();
    updateProjectButtons();
    renderProjectList();
  }

  function countBrowserThreads(vm) {
    if (!vm || !vm.runtime || !Array.isArray(vm.runtime.threads)) return 0;
    var count = 0;
    for (var i = 0; i < vm.runtime.threads.length; i++) {
      if (!vm.runtime.threads[i].updateMonitor) count++;
    }
    return count;
  }

  function finishBrowserProjectIfStopped(vm) {
    window.setTimeout(function () {
      if (countBrowserThreads(vm) === 0) {
        setBrowserProjectRunning(false);
      }
    }, 200);
  }

  function startBrowserTopLevelScripts(vm) {
    if (!vm || !vm.runtime || !Array.isArray(vm.runtime.targets)) return 0;
    var started = 0;
    for (var i = 0; i < vm.runtime.targets.length; i++) {
      var target = vm.runtime.targets[i];
      if (!target || !target.blocks) continue;
      var allBlocks = target.blocks._blocks || {};
      Object.keys(allBlocks).forEach(function (id) {
        var block = allBlocks[id];
        if (!block || !block.topLevel || block.parent) return;
        var opcode = block.opcode || '';
        var isHat = opcode.indexOf('event_') === 0 || opcode.indexOf('procedures_definition') === 0;
        if (isHat) return;
        try {
          vm.runtime._pushThread(id, target, {stackClick: true});
          started++;
          console.log('[bootstrap] pushed thread for top-level script:', opcode, id);
        } catch (err) {
          console.warn('[bootstrap] failed to push thread:', err);
        }
      });
    }
    return started;
  }

  function isGreenFlagControl(node) {
    if (!node || !node.closest) return false;
    var el = node.closest('img, button, [role="button"]');
    if (!el) return false;
    var text = [
      el.getAttribute('class') || '',
      el.getAttribute('src') || '',
      el.getAttribute('title') || '',
      el.getAttribute('aria-label') || ''
    ].join(' ').toLowerCase();
    return text.indexOf('green-flag') !== -1 ||
      text.indexOf('greenflag') !== -1 ||
      text.indexOf('icon--green-flag') !== -1 ||
      text === 'go' ||
      text.indexOf(' go') !== -1;
  }

  function isStopAllControl(node) {
    if (!node || !node.closest) return false;
    var el = node.closest('img, button, [role="button"]');
    if (!el) return false;
    var text = [
      el.getAttribute('class') || '',
      el.getAttribute('src') || '',
      el.getAttribute('title') || '',
      el.getAttribute('aria-label') || ''
    ].join(' ').toLowerCase();
    return text.indexOf('stop-all') !== -1 ||
      text.indexOf('icon--stop-all') !== -1 ||
      text.indexOf('pause') !== -1 ||
      text === 'stop' ||
      text.indexOf(' stop') !== -1 ||
      text.indexOf('停止') !== -1 ||
      text.indexOf('暂停') !== -1;
  }

  function hookControlDomClicks() {
    if (document.__limxControlDomHooked) return;
    document.__limxControlDomHooked = true;
    ['pointerdown', 'mousedown', 'touchstart', 'click', 'contextmenu'].forEach(function (eventName) {
      document.addEventListener(eventName, function (event) {
        if (isStopAllControl(event.target)) {
          bgStop();
          return;
        }
        if (!isGreenFlagControl(event.target)) return;
        var vm = getVM();
        if (vm) {
          window.setTimeout(function () {
            var count = startBrowserTopLevelScripts(vm);
            if (count > 0) setBrowserProjectRunning(true);
          }, 50);
        }
      }, true);
    });
  }

  function hookVM() {
    if (bgRunnerHooked) return;
    var vm = getVM();
    if (!vm || !vm.runtime) return;
    bgRunnerHooked = true;
    console.log('[bootstrap] VM hooked; browser green flag runs locally');
    vm.on('PROJECT_CHANGED', markProjectDirty);
    if (!vm.__limxStopAllPatched && typeof vm.stopAll === 'function') {
      var origStopAll = vm.stopAll.bind(vm);
      vm.stopAll = function () {
        bgStop();
        return origStopAll.apply(vm, arguments);
      };
      vm.__limxStopAllPatched = true;
    }
    if (!vm.__limxGreenFlagPatched && typeof vm.greenFlag === 'function') {
      var origGF = vm.greenFlag.bind(vm);
      vm.greenFlag = function () {
        var now = Date.now();
        if (now - lastBrowserGreenFlagRunAt < 300) {
          return;
        }
        lastBrowserGreenFlagRunAt = now;
        origGF.apply(vm, arguments);
        var count = startBrowserTopLevelScripts(vm);
        console.log('[bootstrap] greenFlag patched: started', count, 'orphan scripts');
        if (count > 0) setBrowserProjectRunning(true);
      };
      vm.__limxGreenFlagPatched = true;
    }
    vm.on('PROJECT_START', function () {
      setBrowserProjectRunning(true);
    });
    vm.on('PROJECT_STOP_ALL', function () {
      setBrowserProjectRunning(false);
      bgStop();
    });
    vm.on('PROJECT_RUN_STOP', function () {
      setBrowserProjectRunning(false);
      bgStop();
    });
    vm.on('RUNTIME_STOPPED', function () {
      setBrowserProjectRunning(false);
      bgStop();
    });
    if (vm.runtime && typeof vm.runtime.on === 'function') {
      vm.runtime.on('RUNTIME_PAUSED', function () {
        setBrowserProjectRunning(false);
        bgStop();
      });
    }
    vm.on('RUNTIME_PAUSED', function () {
      setBrowserProjectRunning(false);
      bgStop();
    });
    checkBgStatus();
  }

  function checkBgStatus() {
    fetch('/project/status').then(function (r) { return r.json(); })
      .then(function (data) {
        console.log('[bootstrap] checkBgStatus:', JSON.stringify(data));
        if (data.state === 'running' && data.project) {
          selectedProject = data.project;
          runningProjectName = data.project;
          initialProjectLoaded = true;
          bgStatusChecked = true;
          refreshProjectList();
          window.__LIMX_BG_ACTIVE__ = true;
          showBgIndicator(true);
          startBgStatusPoll();
          loadBgProject(data.project, false);
        } else {
          window.__LIMX_BG_ACTIVE__ = false;
          runningProjectName = '';
          bgStatusChecked = true;
          refreshProjectList();
        }
      }).catch(function () {
        bgStatusChecked = true;
        refreshProjectList();
      });
  }

  function loadBgProject(projectName, enableEditing) {
    var vm = getVM();
    if (!projectName) return false;
    if (!vm) {
      window.setTimeout(function () { loadBgProject(projectName, enableEditing); }, 300);
      return false;
    }
    if (loadingProjectName === projectName) return true;
    var token = ++loadProjectToken;
    loadingProjectName = projectName;
    bgSyncing = true;
    suppressProjectChangedUntil = Date.now() + 3000;
    selectedProject = projectName;
    currentProjectName = projectName;
    projectDirty = false;
    projectEditEnabled = Boolean(enableEditing);
    updateProjectButtons();
    updateReadonlyOverlay();
    fetch('/project/download?name=' + encodeURIComponent(projectName))
      .then(function (r) {
        if (!r.ok) throw new Error('download failed');
        return r.arrayBuffer();
      })
      .then(function (buffer) {
        return vm.loadProject(buffer);
      })
      .then(function () {
        if (token !== loadProjectToken) return;
        currentProjectName = projectName;
        projectDirty = false;
        projectEditEnabled = Boolean(enableEditing);
        initialProjectLoaded = true;
        console.log('[bootstrap] loaded bg project:', projectName);
        window.setTimeout(function () {
          if (token !== loadProjectToken) return;
          bgSyncing = false;
          loadingProjectName = '';
          suppressProjectChangedUntil = Date.now() + 1000;
          projectDirty = false;
          defaultBlocksCategorySelected = false;
          defaultBlocksCategoryScrollPending = false;
          defaultBlocksCategoryDeadline = Date.now() + 8000;
          chooseDefaultBlocksCategory();
          updateProjectButtons();
          updateReadonlyOverlay();
        }, 300);
      })
      .catch(function (err) {
        if (token !== loadProjectToken) return;
        bgSyncing = false;
        loadingProjectName = '';
        suppressProjectChangedUntil = Date.now() + 1000;
        updateReadonlyOverlay();
        console.warn('[bootstrap] load bg project error:', err);
      });
    return true;
  }

  // ── Main bootstrap ──

  function tick() {
    hijackLanguageItem();
    hideOriginalLanguageMenu();
    fixSettingsMenuPosition();
    enforceBranding();
    hookControlDomClicks();
    hookVM();
    ensureProjectPanel();
    chooseDefaultBlocksCategory();
    updateLocalizedUi();
    updateReadonlyOverlay();
  }

  var tickScheduled = false;
  function scheduleTick() {
    if (tickScheduled) return;
    tickScheduled = true;
    setTimeout(function () {
      tickScheduled = false;
      tick();
    }, 100);
  }

  syncLangCookie();
  applyRobotName(DEFAULT_ROBOT_NAME, '');
  document.addEventListener('DOMContentLoaded', injectStyles);
  window.addEventListener('limx-projects-changed', function (event) {
    if (event.detail && event.detail.name) {
      selectedProject = event.detail.name;
      currentProjectName = event.detail.name;
      projectDirty = false;
      projectEditEnabled = false;
    }
    refreshProjectList();
  });
  setInterval(tick, 500);
  setInterval(function () {
    if (projectPanelReady) refreshProjectList();
  }, 5000);
  new MutationObserver(scheduleTick).observe(
    document.documentElement,
    {childList: true, subtree: true}
  );
  fetchRobotInfo();
})();
