/**
 * DARIA Desktop v0.8.6.4
 */

const state = {
    connected: false,
    windows: new Map(),
    activeWindow: null,
    windowZIndex: 10,
    settings: {},
    iconPositions: {},
    hiddenIcons: [],
    isMobile: window.innerWidth < 768,
    plugins: [],
    audio: null,
    audioPlaying: false,
    currentPath: "",
    currentChatId: null,
    attentionEnabled: true,
    currentFileExt: '',
    stickerCatalog: null,
};

const defaultIcons = [
    { id: 'chat', icon: '💬', name: 'Чат', window: 'chat' },
    { id: 'self', icon: '🪞', name: 'Самоосознание', window: 'self' },
    { id: 'todos', icon: '✅', name: 'Списки дел', window: 'todos' },
    { id: 'senses', icon: '👁️', name: 'Сенсоры', window: 'senses' },
    { id: 'wiki', icon: '📚', name: 'Wiki', window: 'wiki' },
    { id: 'updater', icon: '⬆️', name: 'Обновления', window: 'updater' },
    { id: 'files', icon: '📁', name: 'Файлы', window: 'files' },
    { id: 'daria-games', icon: '🎮', name: 'Игры Даши', window: 'daria-games' },
    { id: 'terminal', icon: '💻', name: 'Терминал', window: 'terminal' },
    { id: 'browser', icon: '🌐', name: 'Браузер', window: 'browser' },
    { id: 'player', icon: '🎵', name: 'Плеер', window: 'player' },
    { id: 'store', icon: '🛒', name: 'Магазин', window: 'store' },
    { id: 'memory', icon: '🧠', name: 'Память', window: 'memory' },
    { id: 'settings', icon: '⚙️', name: 'Настройки', window: 'settings' },
    { id: 'support', icon: '☕', name: 'Поддержать', window: 'support' },
];

const windowConfigs = {
    chat: { icon: '💬', title: 'Чат с Дарьей', width: 600, height: 500 },
    self: { icon: '🪞', title: 'Самоосознание Даши', width: 520, height: 520 },
    todos: { icon: '✅', title: 'Списки дел', width: 560, height: 560 },
    senses: { icon: '👁️', title: 'Сенсоры', width: 560, height: 560 },
    wiki: { icon: '📚', title: 'Wiki', width: 760, height: 560 },
    updater: { icon: '⬆️', title: 'Обновления', width: 560, height: 540 },
    files: { icon: '📁', title: 'Файлы', width: 550, height: 400 },
    'daria-games': { icon: '🎮', title: 'Игры Даши', width: 620, height: 430 },
    terminal: { icon: '💻', title: 'Терминал', width: 600, height: 400 },
    browser: { icon: '🌐', title: 'Браузер', width: 800, height: 600 },
    player: { icon: '🎵', title: 'Плеер', width: 320, height: 420 },
    logs: { icon: '📋', title: 'Логи', width: 600, height: 400 },
    store: { icon: '🛒', title: 'Магазин', width: 500, height: 450 },
    memory: { icon: '🧠', title: 'Память', width: 380, height: 400 },
    settings: { icon: '⚙️', title: 'Настройки', width: 400, height: 480 },
    support: { icon: '☕', title: 'Поддержать', width: 380, height: 400 },
    about: { icon: '💕', title: 'О Дарье', width: 350, height: 380 },
};

// ═══════════════════════════════════════════════════════════════
//  Init
// ═══════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
    state.isMobile = window.innerWidth < 768;
    await loadSettings();
    await loadPlugins();
    initDesktopIcons();
    initClock();
    initAvatar();
    await initConnection();
    initNotifications();
    initProactivePolling();
    initMoodBehavior();
    checkFirstVisit();
    applyStartupDeepLink();
    window.addEventListener('resize', () => { state.isMobile = window.innerWidth < 768; });
});

function applyStartupDeepLink() {
    try {
        const params = new URLSearchParams(window.location.search || '');
        const open = (params.get('open') || '').toLowerCase();
        if (open === 'logs') {
            openWindow('logs');
        } else if (open && windowConfigs[open]) {
            openWindow(open);
        }
    } catch (e) {}
}

async function initConnection() {
    try {
        const r = await fetch('/api/status');
        const s = await r.json();
        state.connected = s.brain && s.memory;
        document.getElementById('status-indicator')?.classList.toggle('online', state.connected);
        document.querySelector('.avatar-status')?.classList.toggle('online', state.connected);
    } catch (e) {}
}

async function loadPlugins() {
    try {
        const r = await fetch('/api/plugins/desktop');
        state.plugins = await r.json();
    } catch (e) { state.plugins = []; }
}

async function loadSettings() {
    try {
        const r = await fetch('/api/settings');
        state.settings = await r.json();
        applyTheme(state.settings.theme || 'pink');
        applyCursor(state.settings.cursor || 'default');
        state.attentionEnabled = state.settings.attention_enabled !== false;
        if (state.settings.wallpaper) {
            document.getElementById('desktop').style.backgroundImage = `url(${state.settings.wallpaper})`;
        }
        const r2 = await fetch('/api/desktop/icons');
        state.iconPositions = await r2.json() || {};
        const r3 = await fetch('/api/desktop/hidden-icons');
        state.hiddenIcons = await r3.json() || [];
    } catch (e) {}
}

// ═══════════════════════════════════════════════════════════════
//  Desktop Icons
// ═══════════════════════════════════════════════════════════════

function initDesktopIcons() {
    const container = document.getElementById('desktop-icons');
    if (!container) return;
    container.innerHTML = '';
    
    defaultIcons.forEach((ic, i) => {
        if (!state.hiddenIcons.includes(ic.id)) {
            createDesktopIcon(container, ic, i);
        }
    });
    
    state.plugins.forEach((p, i) => {
        if (p.has_window && !state.hiddenIcons.includes(`plugin-${p.id}`)) {
            createDesktopIcon(container, {
                id: `plugin-${p.id}`, icon: p.icon, name: p.title,
                window: `plugin:${p.id}`, isPlugin: true
            }, defaultIcons.length + i);
        }
    });
}

function createDesktopIcon(container, data, index) {
    const icon = document.createElement('div');
    icon.className = 'desktop-icon';
    icon.dataset.iconId = data.id;
    icon.innerHTML = `<div class="icon">${data.icon}</div><span>${data.name}</span>`;
    
    icon.addEventListener('dblclick', (e) => {
        e.preventDefault();
        if (data.window.startsWith('plugin:')) openPluginWindow(data.window.replace('plugin:', ''));
        else openWindow(data.window);
    });
    
    icon.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showIconContextMenu(e, data.id);
    });
    
    const saved = state.iconPositions[data.id];
    if (saved && saved.x !== undefined && !state.isMobile) {
        icon.style.position = 'absolute';
        icon.style.left = saved.x + 'px';
        icon.style.top = saved.y + 'px';
    }
    
    if (!state.isMobile) initIconDrag(icon);
    container.appendChild(icon);
}

function showIconContextMenu(e, iconId) {
    const existing = document.querySelector('.context-menu');
    if (existing) existing.remove();
    
    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.style.left = e.clientX + 'px';
    menu.style.top = e.clientY + 'px';
    menu.innerHTML = `
        <div class="context-item" onclick="hideIcon('${iconId}')">🙈 Скрыть</div>
        <div class="context-item" onclick="resetIconPosition('${iconId}')">📍 Сбросить позицию</div>
    `;
    document.body.appendChild(menu);
    
    setTimeout(() => {
        document.addEventListener('click', () => menu.remove(), {once: true});
    }, 10);
}

function hideIcon(iconId) {
    state.hiddenIcons.push(iconId);
    fetch('/api/desktop/hidden-icons', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(state.hiddenIcons)
    });
    initDesktopIcons();
}

function resetIconPosition(iconId) {
    delete state.iconPositions[iconId];
    fetch('/api/desktop/icons', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(state.iconPositions)
    });
    initDesktopIcons();
}

function initIconDrag(icon) {
    let dragging = false, hasMoved = false, startX, startY, iconX, iconY;
    const GRID_SIZE = 100; // Размер ячейки сетки
    
    icon.addEventListener('mousedown', (e) => {
        if (e.detail >= 2) return;
        dragging = true; hasMoved = false;
        const rect = icon.getBoundingClientRect();
        const containerRect = icon.parentElement.getBoundingClientRect();
        startX = e.clientX; startY = e.clientY;
        iconX = rect.left - containerRect.left;
        iconY = rect.top - containerRect.top;
        icon.classList.add('dragging');
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!dragging) return;
        const dx = e.clientX - startX, dy = e.clientY - startY;
        if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
            hasMoved = true;
            icon.style.position = 'absolute';
            icon.style.left = Math.max(0, iconX + dx) + 'px';
            icon.style.top = Math.max(0, iconY + dy) + 'px';
        }
    });
    
    document.addEventListener('mouseup', () => {
        if (!dragging) return;
        dragging = false;
        icon.classList.remove('dragging');
        
        if (hasMoved) {
            // Привязка к сетке
            let x = parseInt(icon.style.left) || 0;
            let y = parseInt(icon.style.top) || 0;
            
            x = Math.round(x / GRID_SIZE) * GRID_SIZE;
            y = Math.round(y / GRID_SIZE) * GRID_SIZE;
            
            // Проверяем что позиция не занята другой иконкой
            const iconId = icon.dataset.iconId;
            let collision = false;
            
            for (const [id, pos] of Object.entries(state.iconPositions)) {
                if (id !== iconId && pos.x === x && pos.y === y) {
                    collision = true;
                    break;
                }
            }
            
            // Если коллизия, ищем свободную ячейку
            if (collision) {
                for (let tryY = 0; tryY < 600; tryY += GRID_SIZE) {
                    for (let tryX = 0; tryX < 600; tryX += GRID_SIZE) {
                        let free = true;
                        for (const [id, pos] of Object.entries(state.iconPositions)) {
                            if (id !== iconId && pos.x === tryX && pos.y === tryY) {
                                free = false;
                                break;
                            }
                        }
                        if (free) {
                            x = tryX;
                            y = tryY;
                            collision = false;
                            break;
                        }
                    }
                    if (!collision) break;
                }
            }
            
            icon.style.left = x + 'px';
            icon.style.top = y + 'px';
            
            state.iconPositions[iconId] = {x, y};
            fetch('/api/desktop/icons', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(state.iconPositions)
            });
        }
    });
}

// ═══════════════════════════════════════════════════════════════
//  Clock, Avatar, Notifications
// ═══════════════════════════════════════════════════════════════

function initClock() {
    const update = () => {
        const el = document.getElementById('clock');
        if (el) el.textContent = new Date().toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'});
    };
    update(); setInterval(update, 1000);
}

function initAvatar() {
    document.getElementById('daria-avatar')?.addEventListener('click', toggleQuickChat);
    
    // Запускаем обновление состояния
    updateDariaState();
    setInterval(updateDariaState, 30000); // Каждые 30 сек
}

async function updateDariaState() {
    try {
        const r = await fetch('/api/state');
        const state = await r.json();
        
        // Обновляем аватар
        const avatar = document.querySelector('.avatar-image');
        if (avatar && state.mood_emoji) {
            avatar.textContent = state.mood_emoji;
            avatar.title = state.mood_label;
        }
        
        // Обновляем индикатор в настройках если открыт
        const indicator = document.getElementById('mood-indicator');
        if (indicator) {
            indicator.innerHTML = `
                <span style="font-size:24px">${state.mood_emoji}</span>
                <span>${state.mood_label}</span>
                <div class="energy-bar" style="width:${state.energy * 100}%;background:${state.mood_color}"></div>
            `;
        }
    } catch (e) {}
}

function toggleQuickChat() {
    const qc = document.getElementById('quick-chat');
    if (qc) {
        qc.classList.toggle('hidden');
        if (!qc.classList.contains('hidden')) document.getElementById('quick-input')?.focus();
    }
}

function initNotifications() {
    // Request permission for system notifications
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    let reconnectMs = 1000;
    const connect = () => {
        let es;
        try {
            es = new EventSource('/api/notifications/stream');
        } catch (e) {
            setTimeout(connect, reconnectMs);
            reconnectMs = Math.min(15000, reconnectMs * 2);
            return;
        }
        es.onmessage = (e) => {
            reconnectMs = 1000;
            try { showNotification(JSON.parse(e.data)); } catch (_) {}
        };
        es.onerror = () => {
            try { es.close(); } catch (_) {}
            setTimeout(connect, reconnectMs);
            reconnectMs = Math.min(15000, reconnectMs * 2);
        };
    };
    connect();
}

function showNotification(notif) {
    const performAction = () => {
        if (!notif?.action) return;
        if (notif.action === 'open_chat') {
            openWindow('chat');
            return;
        }
        if (notif.action.startsWith('open_window:')) {
            const winId = notif.action.split(':')[1];
            if (winId) openWindow(winId);
            return;
        }
        if (notif.action.startsWith('open_file:')) {
            const relPath = notif.action.slice('open_file:'.length);
            openWindow('files');
            setTimeout(() => openFile(relPath), 120);
        }
    };
    // Show in-app notification
    const container = document.getElementById('notifications-container');
    if (container) {
        const el = document.createElement('div');
        el.className = `notification ${notif.type || 'info'}`;
        el.innerHTML = `<span>${notif.icon || '💬'}</span><div><b>${notif.title}</b><p>${notif.message}</p></div><button onclick="this.parentElement.remove()">×</button>`;
        el.onclick = () => performAction();
        container.appendChild(el);
        setTimeout(() => el.remove(), notif.duration || 5000);
    }
    
    // Browser notification duplicate (if permission granted)
    const shouldNative = ('Notification' in window && Notification.permission === 'granted' && notif.type !== 'mood_action');
    if (shouldNative) {
        const sysNotif = new Notification(notif.title, {
            body: notif.message,
            icon: '/static/favicon.svg',
            tag: 'daria-' + notif.id,
            requireInteraction: Boolean(notif.system),
        });
        
        sysNotif.onclick = () => {
            window.focus();
            performAction();
            sysNotif.close();
        };
        
        // Auto close after duration
        setTimeout(() => sysNotif.close(), notif.duration || 10000);
    }
}

function toggleAttention() {
    state.attentionEnabled = !state.attentionEnabled;
    fetch('/api/attention/toggle', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enabled: state.attentionEnabled})
    });
    document.getElementById('attention-toggle').style.opacity = state.attentionEnabled ? '1' : '0.5';
}

// ═══════════════════════════════════════════════════════════════
//  Settings
// ═══════════════════════════════════════════════════════════════

async function saveSettings() {
    const settings = {
        name: document.getElementById('setting-name')?.value || '',
        gender: document.getElementById('setting-gender')?.value || '',
        mode: document.getElementById('setting-mode')?.value || 'adaptive',
        theme: document.getElementById('setting-theme')?.value || 'pink',
        attention_enabled: document.getElementById('setting-attention')?.checked ?? true,
    };
    try {
        await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(settings)});
        state.settings = {...state.settings, ...settings};
        applyTheme(settings.theme);
        showNotification({title: 'Настройки', message: 'Сохранено!', type: 'success', icon: '✅', duration: 3000});
    } catch (e) {}
}

function applyTheme(theme) { document.body.setAttribute('data-theme', theme); }
function applyCursor(cursor) { document.body.setAttribute('data-cursor', cursor); }

async function uploadAvatar(file) {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    try {
        const r = await fetch('/api/upload/avatar', {method: 'POST', body: fd});
        const data = await r.json();
        if (data.url) showNotification({title: 'Аватар', message: 'Загружен!', type: 'success', icon: '👤'});
    } catch (e) {}
}

async function uploadWallpaper(file) {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    try {
        const r = await fetch('/api/upload/wallpaper', {method: 'POST', body: fd});
        const data = await r.json();
        if (data.url) document.getElementById('desktop').style.backgroundImage = `url(${data.url})`;
    } catch (e) {}
}

// ═══════════════════════════════════════════════════════════════
//  Windows
// ═══════════════════════════════════════════════════════════════

function openWindow(windowId) {
    if (state.windows.has(windowId)) {
        state.windows.get(windowId).element.classList.remove('minimized');
        focusWindow(windowId);
        return;
    }
    const config = windowConfigs[windowId];
    if (!config) return;
    const loadPromise = createWindow(windowId, config, () => {
        const tpl = document.getElementById(windowId + '-content');
        return tpl ? tpl.content.cloneNode(true) : null;
    });
    Promise.resolve(loadPromise).then(() => initWindowContent(windowId));
}

async function openPluginWindow(pluginId) {
    const windowId = `plugin:${pluginId}`;
    if (state.windows.has(windowId)) {
        state.windows.get(windowId).element.classList.remove('minimized');
        focusWindow(windowId);
        return;
    }
    try {
        const r = await fetch(`/api/plugins/${pluginId}/window`);
        const data = await r.json();
        const m = data.manifest || {};
        createWindow(windowId, {
            icon: m.icon || '🧩', title: m.window_title || m.name || 'Плагин',
            width: m.window_size?.width || 400, height: m.window_size?.height || 300,
        }, async () => {
            try {
                const tr = await fetch(`/plugins/${pluginId}/template/window.html`);
                let html = await tr.text();
                if (data.data) Object.keys(data.data).forEach(k => {
                    html = html.replace(new RegExp(`{{\\s*${k}\\s*}}`, 'g'), data.data[k] || '');
                });
                const container = document.createElement('div');
                container.innerHTML = html;
                return container;
            } catch (e) { return null; }
        });
    } catch (e) {}
}

function createWindow(windowId, config, contentFactory) {
    const template = document.getElementById('window-template');
    const windowEl = template.content.cloneNode(true).querySelector('.window');
    windowEl.dataset.windowId = windowId;
    windowEl.querySelector('.window-icon').textContent = config.icon;
    windowEl.querySelector('.window-name').textContent = config.title;
    
    if (state.isMobile) windowEl.classList.add('maximized');
    else {
        windowEl.style.width = config.width + 'px';
        windowEl.style.height = config.height + 'px';
        windowEl.style.left = (80 + state.windows.size * 20) + 'px';
        windowEl.style.top = (40 + state.windows.size * 20) + 'px';
    }
    
    const loadContent = async () => {
        const content = await contentFactory();
        if (content) {
            windowEl.querySelector('.window-content').appendChild(content);
            const scripts = windowEl.querySelectorAll('script');
            scripts.forEach(s => {
                const ns = document.createElement('script');
                ns.textContent = s.textContent;
                s.parentNode.replaceChild(ns, s);
            });
        }
    };
    const loadPromise = loadContent();
    
    initWindowEvents(windowEl, windowId);
    document.getElementById('windows-container').appendChild(windowEl);
    state.windows.set(windowId, {element: windowEl, config, loadPromise});
    addTaskbarItem(windowId, config);
    focusWindow(windowId);
    return loadPromise;
}

function initWindowEvents(windowEl, windowId) {
    windowEl.querySelector('.win-btn.minimize')?.addEventListener('click', () => minimizeWindow(windowId));
    windowEl.querySelector('.win-btn.maximize')?.addEventListener('click', () => maximizeWindow(windowId));
    windowEl.querySelector('.win-btn.close')?.addEventListener('click', () => closeWindow(windowId));
    windowEl.addEventListener('mousedown', () => focusWindow(windowId));
    
    if (state.isMobile) return;
    
    const header = windowEl.querySelector('.window-header');
    let dragging = false, startX, startY, startLeft, startTop;
    header.addEventListener('mousedown', (e) => {
        if (e.target.closest('.win-btn') || windowEl.classList.contains('maximized')) return;
        dragging = true; startX = e.clientX; startY = e.clientY;
        startLeft = windowEl.offsetLeft; startTop = windowEl.offsetTop;
    });
    document.addEventListener('mousemove', (e) => {
        if (!dragging) return;
        windowEl.style.left = Math.max(0, startLeft + e.clientX - startX) + 'px';
        windowEl.style.top = Math.max(0, startTop + e.clientY - startY) + 'px';
    });
    document.addEventListener('mouseup', () => { dragging = false; });
    
    const resize = windowEl.querySelector('.window-resize-handle');
    let resizing = false, rX, rY, rW, rH;
    resize?.addEventListener('mousedown', (e) => {
        if (windowEl.classList.contains('maximized')) return;
        e.stopPropagation(); resizing = true;
        rX = e.clientX; rY = e.clientY; rW = windowEl.offsetWidth; rH = windowEl.offsetHeight;
    });
    document.addEventListener('mousemove', (e) => {
        if (!resizing) return;
        windowEl.style.width = Math.max(300, rW + e.clientX - rX) + 'px';
        windowEl.style.height = Math.max(200, rH + e.clientY - rY) + 'px';
    });
    document.addEventListener('mouseup', () => { resizing = false; });
}

function focusWindow(windowId) {
    state.windows.forEach((win, id) => {
        win.element.classList.remove('focused');
        document.querySelector(`.taskbar-item[data-window="${id}"]`)?.classList.remove('active');
    });
    const win = state.windows.get(windowId);
    if (win) {
        win.element.classList.add('focused');
        win.element.style.zIndex = ++state.windowZIndex;
        state.activeWindow = windowId;
        document.querySelector(`.taskbar-item[data-window="${windowId}"]`)?.classList.add('active');
    }
}

function minimizeWindow(windowId) { state.windows.get(windowId)?.element.classList.add('minimized'); }
function maximizeWindow(windowId) { state.windows.get(windowId)?.element.classList.toggle('maximized'); }
function closeWindow(windowId) {
    const win = state.windows.get(windowId);
    if (win) {
        if (windowId === 'daria-games' && dariaGamePollTimer) {
            clearInterval(dariaGamePollTimer);
            dariaGamePollTimer = null;
        }
        win.element.remove();
        state.windows.delete(windowId);
        document.querySelector(`.taskbar-item[data-window="${windowId}"]`)?.remove();
    }
}

function addTaskbarItem(windowId, config) {
    const item = document.createElement('button');
    item.className = 'taskbar-item active';
    item.dataset.window = windowId;
    item.innerHTML = `<span>${config.icon}</span><span>${config.title}</span>`;
    item.onclick = () => {
        const win = state.windows.get(windowId);
        if (win) {
            if (win.element.classList.contains('minimized')) { win.element.classList.remove('minimized'); focusWindow(windowId); }
            else if (state.activeWindow === windowId) minimizeWindow(windowId);
            else focusWindow(windowId);
        }
    };
    document.getElementById('taskbar-windows').appendChild(item);
}

function initWindowContent(windowId) {
    if (windowId === 'chat') loadChatHistory();
    else if (windowId === 'self') loadSelfPerception();
    else if (windowId === 'todos') loadTodoLists();
    else if (windowId === 'senses') initSensesWindow();
    else if (windowId === 'wiki') initWikiWindow();
    else if (windowId === 'updater') initUpdaterWindow();
    else if (windowId === 'settings') initSettingsWindow();
    else if (windowId === 'memory') loadMemoryStats();
    else if (windowId === 'store') loadStore();
    else if (windowId === 'logs') initLogs();
    else if (windowId === 'player') initPlayer();
    else if (windowId === 'files') loadFiles();
    else if (windowId === 'daria-games') initDariaGamesWindow();
}

// ═══════════════════════════════════════════════════════════════
//  Chat with History
// ═══════════════════════════════════════════════════════════════

async function loadChatHistory() {
    try {
        const r = await fetch('/api/chats');
        const chats = await r.json();
        const container = document.getElementById('chat-history');
        if (!container) return;
        
        const localChats = chats.filter(c => (c.source || 'local') !== 'telegram');
        const tgChats = chats.filter(c => (c.source || '') === 'telegram');
        const renderItems = (items) => items.map(c => `
            <div class="chat-history-item ${c.id === state.currentChatId ? 'active' : ''}" 
                 onclick="loadChat('${c.id}')">
                <span class="chat-preview">${c.title ? `[${c.title}] ` : ''}${c.last_author ? `${c.last_author}: ` : ''}${c.preview || 'Новый чат'}</span>
                <span class="chat-date">${new Date(c.created).toLocaleDateString('ru')}</span>
                <button class="chat-delete" onclick="deleteChat('${c.id}', event)">×</button>
            </div>
        `).join('');

        let html = '';
        if (localChats.length) {
            html += `<div class="chat-group-title">💬 Личные чаты</div>${renderItems(localChats)}`;
        }
        if (tgChats.length) {
            html += `<div class="chat-group-title">📨 Telegram</div>${renderItems(tgChats)}`;
        }
        container.innerHTML = html || '<p class="empty">Нет истории</p>';
    } catch (e) {}
}

async function loadChat(chatId) {
    state.currentChatId = chatId;
    try {
        const r = await fetch(`/api/chats/${chatId}`);
        const chat = await r.json();
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        container.innerHTML = '';
        (chat.messages || []).forEach(m => addMessage(m.content, m.role, 'chat-messages'));
        loadChatHistory();
    } catch (e) {}
}

async function newChat() {
    try {
        const r = await fetch('/api/chats/new', {method: 'POST'});
        const data = await r.json();
        state.currentChatId = data.chat_id;
        document.getElementById('chat-messages').innerHTML = '';
        loadChatHistory();
    } catch (e) {}
}

async function deleteChat(chatId, e) {
    e?.stopPropagation();
    if (!confirm('Удалить чат?')) return;
    await fetch(`/api/chats/${chatId}`, {method: 'DELETE'});
    if (state.currentChatId === chatId) {
        state.currentChatId = null;
        document.getElementById('chat-messages').innerHTML = '';
    }
    loadChatHistory();
}

function sendChatMessage() {
    const input = document.getElementById('chat-input');
    if (!input) return;
    const content = input.value.trim();
    if (!content) return;
    
    addMessage(content, 'user', 'chat-messages');
    input.value = '';
    document.getElementById('chat-typing')?.classList.remove('hidden');
    
    let payloadContent = content;
    const chatContainer = document.getElementById('chat-messages');
    const lastAssistant = chatContainer?.querySelector('.message.assistant:last-child');
    const shortReply = content.length < 40;
    if (shortReply && lastAssistant?.dataset?.proactive === '1') {
        payloadContent = `Контекст: ты недавно предложила активность: "${lastAssistant.textContent}".\nОтвет пользователя: ${content}`;
    }

    fetch('/api/chat', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content: payloadContent, chat_id: state.currentChatId})
    }).then(r => r.json()).then(data => {
        document.getElementById('chat-typing')?.classList.add('hidden');
        if (data.chat_id) state.currentChatId = data.chat_id;
        
        // Multi-message support (Point #12)
        const messages = data.messages || [data.response];
        displaySequentialMessages(messages, 'chat-messages');
        
        loadChatHistory();
        closeStickerPicker();
    }).catch(() => {
        document.getElementById('chat-typing')?.classList.add('hidden');
        addMessage('Ошибка соединения... 💔', 'assistant', 'chat-messages');
    });
}

async function loadStickerCatalog() {
    if (state.stickerCatalog) return state.stickerCatalog;
    try {
        const r = await fetch('/api/stickers/catalog');
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        state.stickerCatalog = await r.json();
        return state.stickerCatalog;
    } catch (e) {
        return {emoji_stickers: []};
    }
}

function closeStickerPicker() {
    const picker = document.getElementById('chat-sticker-picker');
    if (picker) picker.classList.add('hidden');
}

async function toggleStickerPicker(ev) {
    if (ev) {
        ev.preventDefault();
        ev.stopPropagation();
    }
    const picker = document.getElementById('chat-sticker-picker');
    if (!picker) return;
    if (!picker.classList.contains('hidden')) {
        picker.classList.add('hidden');
        return;
    }
    const data = await loadStickerCatalog();
    const stickers = data.emoji_stickers || [];
    picker.innerHTML = stickers.length
        ? stickers.map(s => `<button type="button" class="chat-sticker-item" onclick="sendSticker('${s.replace(/'/g, "\\'")}')">${s}</button>`).join('')
        : '<div class="empty">Стикеры недоступны</div>';
    picker.classList.remove('hidden');
}

function sendSticker(sticker) {
    if (!sticker) return;
    const input = document.getElementById('chat-input');
    if (!input) return;
    input.value = sticker;
    closeStickerPicker();
    sendChatMessage();
}

function displaySequentialMessages(messages, containerId, options = {}) {
    if (!messages || messages.length === 0) return;
    
    // First message immediately
    addMessage(messages[0], 'assistant', containerId, options);
    
    // Subsequent messages with delay (simulates typing)
    for (let i = 1; i < messages.length; i++) {
        ((msg, delay) => {
            setTimeout(() => addMessage(msg, 'assistant', containerId, options), delay);
        })(messages[i], i * (800 + messages[i].length * 15));
    }
}

// Proactive messaging - Daria initiates chats (Point #6)
function initProactivePolling() {
    setInterval(async () => {
        try {
            const r = await fetch('/api/proactive');
            const data = await r.json();
            if (data.messages && data.messages.length > 0) {
                for (const proactive of data.messages) {
                    handleProactiveMessage(proactive);
                }
            }
        } catch (e) {}
    }, 30000); // Check every 30 seconds
}

function handleProactiveMessage(proactive) {
    const msgs = proactive.messages || [];
    if (!msgs.length) return;
    
    // Show notification
    showNotification({
        title: '🌸 Дарья',
        message: msgs[0],
        type: 'proactive',
        icon: '💬',
        duration: 15000,
        action: 'open_chat',
        system: true,
    });
    
    // If chat window is open, inject messages
    const chatContainer = document.getElementById('chat-messages');
    if (chatContainer) {
        displaySequentialMessages(msgs, 'chat-messages', {proactive: true});
    }
    
    // If it's a game suggestion, also hint on desktop
    if (proactive.type === 'game_suggest') {
        const avatar = document.querySelector('.avatar-image');
        if (avatar) {
            avatar.classList.add('wants-play');
            setTimeout(() => avatar.classList.remove('wants-play'), 10000);
        }
    }
}

// Mood-driven desktop behavior (Point #7)
function initMoodBehavior() {
    setInterval(async () => {
        try {
            const r = await fetch('/api/behavior');
            const data = await r.json();
            const behavior = data.behavior || {};
            
            if (behavior.desktop_mischief) {
                performDesktopMischief(data.state?.mood);
            }
        } catch (e) {}
    }, 60000); // Check every minute
}

function performDesktopMischief(mood) {
    if (mood === 'angry' || mood === 'offended' || mood === 'playful') {
        // Move random desktop icons
        const icons = document.querySelectorAll('.desktop-icon');
        if (icons.length > 0 && !state.isMobile) {
            const randomIcon = icons[Math.floor(Math.random() * icons.length)];
            const newX = Math.random() * (window.innerWidth - 200);
            const newY = Math.random() * (window.innerHeight - 200);
            randomIcon.style.position = 'absolute';
            randomIcon.style.left = newX + 'px';
            randomIcon.style.top = newY + 'px';
            randomIcon.style.transition = 'all 0.5s ease';
            setTimeout(() => randomIcon.style.transition = '', 600);
        }
    }
}

function sendQuickMessage() {
    const input = document.getElementById('quick-input');
    if (!input) return;
    const content = input.value.trim();
    if (!content) return;
    addMessage(content, 'user', 'quick-messages');
    input.value = '';
    fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({content})})
        .then(r => r.json())
        .then(data => addMessage(data.response, 'assistant', 'quick-messages'));
}

function addMessage(content, role, containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    const text = String(content || '');
    msg.textContent = text;
    const emojiOnly = /^(?:[\p{Emoji}\uFE0F\u200D]\s*){1,3}$/u.test(text.trim());
    if (emojiOnly) msg.classList.add('sticker');
    if (options.proactive) msg.dataset.proactive = '1';
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

// ═══════════════════════════════════════════════════════════════
//  Files, Terminal, Browser, Player, etc.
// ═══════════════════════════════════════════════════════════════

async function loadFiles(path = "") {
    state.currentPath = path;
    const list = document.getElementById('files-list');
    const pathEl = document.getElementById('files-path');
    if (!list || !pathEl) return;
    pathEl.textContent = '/' + path;
    list.innerHTML = '<div class="loading">Загрузка...</div>';
    
    try {
        const r = await fetch(`/api/files?path=${encodeURIComponent(path)}`);
        const data = await r.json();
        let html = path ? `<div class="file-item" ondblclick="goParentDirectory()"><span>📁</span>..</div>` : '';
        data.items.forEach(item => {
            const icon = item.is_dir ? '📁' : '📄';
            const encodedPath = encodeURIComponent(item.path || '');
            html += `<div class="file-item" ondblclick="${item.is_dir ? `loadFiles(decodeURIComponent('${encodedPath}'))` : `openFile(decodeURIComponent('${encodedPath}'))`}">
                <span>${icon}</span><span class="name">${item.name}</span>
                <button onclick="deleteFile(decodeURIComponent('${encodedPath}'),event)">🗑️</button>
            </div>`;
        });
        list.innerHTML = html || '<div class="empty">Пусто</div>';
    } catch (e) { list.innerHTML = '<div class="empty">Ошибка</div>'; }
}

function goParentDirectory() {
    const p = (state.currentPath || '').replace(/\/+$/, '');
    if (!p) {
        loadFiles('');
        return;
    }
    const parent = p.includes('/') ? p.split('/').slice(0, -1).join('/') : '';
    loadFiles(parent);
}

async function openFile(path) {
    try {
        const r = await fetch(`/api/files/read?path=${encodeURIComponent(path)}`);
        const data = await r.json();
        document.getElementById('file-editor-path').value = path;
        document.getElementById('file-editor-content').value = data.content || '';
        state.currentFileExt = data.ext || '';
        const kind = document.getElementById('file-editor-kind');
        if (kind) kind.textContent = `Формат: ${state.currentFileExt || 'text'}`;
        const promptEl = document.getElementById('file-assist-prompt');
        if (promptEl) promptEl.value = '';
        const log = document.getElementById('file-assist-log');
        if (log) log.innerHTML = '<div class="empty">Панель помощника готова. Выдели фрагмент или опиши задачу.</div>';
        const panel = document.getElementById('file-assist-panel');
        const body = document.querySelector('#file-editor .editor-body');
        if (panel) {
            panel.classList.add('hidden');
            panel.classList.remove('open');
        }
        body?.classList.remove('assist-open');
        document.getElementById('file-editor').classList.remove('hidden');
    } catch (e) {}
}

async function saveFile() {
    const path = document.getElementById('file-editor-path').value;
    const content = document.getElementById('file-editor-content').value;
    await fetch('/api/files/write', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path, content})});
    closeEditor();
    loadFiles(state.currentPath);
}

function closeEditor() {
    const editor = document.getElementById('file-editor');
    const panel = document.getElementById('file-assist-panel');
    const body = editor?.querySelector('.editor-body');
    panel?.classList.add('hidden');
    panel?.classList.remove('open');
    body?.classList.remove('assist-open');
    editor?.classList.add('hidden');
}

function toggleFileAssistPanel() {
    const panel = document.getElementById('file-assist-panel');
    const editor = document.getElementById('file-editor');
    if (!panel || !editor) return;
    const wnd = editor.closest('.window');
    const isOpen = panel.classList.contains('open');

    if (isOpen) {
        panel.classList.remove('open');
        panel.classList.add('hidden');
        editor.querySelector('.editor-body')?.classList.remove('assist-open');
        return;
    }

    panel.classList.remove('hidden');
    panel.classList.add('open');
    editor.querySelector('.editor-body')?.classList.add('assist-open');
    if (wnd && !state.isMobile) {
        const baseWidth = parseInt(String(wnd.offsetWidth), 10);
        const extra = 330;
        const maxW = Math.max(520, window.innerWidth - (wnd.offsetLeft || 0) - 20);
        const nextW = Math.min(baseWidth + extra, maxW);
        if (nextW > baseWidth) wnd.style.width = nextW + 'px';
    }
}

async function assistFileWithDaria() {
    const path = document.getElementById('file-editor-path')?.value;
    const instruction = document.getElementById('file-assist-prompt')?.value?.trim();
    if (!path || !instruction) return;
    const contentEl = document.getElementById('file-editor-content');
    const applyBtn = document.getElementById('file-assist-apply-btn');
    const log = document.getElementById('file-assist-log');
    try {
        if (applyBtn) applyBtn.disabled = true;
        const selStart = contentEl?.selectionStart ?? 0;
        const selEnd = contentEl?.selectionEnd ?? 0;
        const selectedText = (contentEl && selEnd > selStart) ? contentEl.value.slice(selStart, selEnd) : '';
        if (log) {
            const row = document.createElement('div');
            row.className = 'assist-line user';
            row.textContent = instruction;
            log.appendChild(row);
            log.scrollTop = log.scrollHeight;
        }
        const r = await fetch('/api/chat/file-assist', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                path, instruction,
                selected_text: selectedText,
                selection_start: selStart,
                selection_end: selEnd,
            }),
        });
        const data = await r.json();
        if (data.error) throw new Error(data.error);
        if (contentEl) contentEl.value = data.content || '';
        const promptEl = document.getElementById('file-assist-prompt');
        if (promptEl) promptEl.value = '';
        if (log) {
            const row = document.createElement('div');
            row.className = 'assist-line dasha';
            row.textContent = data.selection_applied === false
                ? 'Не нашла выбранный фрагмент, оставила текст как есть.'
                : 'Готово, внесла изменения.';
            log.appendChild(row);
            log.scrollTop = log.scrollHeight;
        }
        showNotification({title: 'Файл', message: 'Даша подготовила правки', type: 'success', icon: '🌸', duration: 3500});
    } catch (e) {
        if (log) {
            const row = document.createElement('div');
            row.className = 'assist-line dasha';
            row.textContent = `Ошибка: ${e.message || e}`;
            log.appendChild(row);
            log.scrollTop = log.scrollHeight;
        }
        showNotification({title: 'Файл', message: `Ошибка: ${e.message || e}`, type: 'error', icon: '⚠️', duration: 4500});
    } finally {
        if (applyBtn) applyBtn.disabled = false;
    }
}

async function createNewFile() {
    const name = prompt('Имя файла:');
    if (!name) return;
    const path = state.currentPath ? `${state.currentPath}/${name}` : name;
    await fetch('/api/files/write', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path, content: ''})});
    loadFiles(state.currentPath);
}

async function createNewFolder() {
    const name = prompt('Имя папки:');
    if (!name) return;
    const path = state.currentPath ? `${state.currentPath}/${name}` : name;
    await fetch('/api/files/mkdir', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path})});
    loadFiles(state.currentPath);
}

async function deleteFile(path, e) {
    e?.stopPropagation();
    if (!confirm('Удалить?')) return;
    await fetch('/api/files/delete', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path})});
    loadFiles(state.currentPath);
}

async function uploadFile(input) {
    if (!input?.files?.[0]) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    fd.append('path', state.currentPath);
    await fetch('/api/files/upload', {method: 'POST', body: fd});
    loadFiles(state.currentPath);
    input.value = '';
}

function executeTerminal() {
    const input = document.getElementById('terminal-input');
    const output = document.getElementById('terminal-output');
    const cmd = input.value.trim();
    if (!cmd) return;
    input.value = '';
    output.innerHTML += `<div class="term-line cmd">$ ${cmd}</div>`;
    
    const [command, ...args] = cmd.split(' ');
    let result = '';
    
    switch(command) {
        case 'help': result = 'Команды: help, clear, date, ask, ls, cat'; break;
        case 'clear': output.innerHTML = ''; return;
        case 'date': result = new Date().toLocaleString('ru'); break;
        case 'ls': fetch(`/api/files?path=${args[0]||''}`).then(r=>r.json()).then(d=>{output.innerHTML+=`<div class="term-line">${d.items.map(f=>f.name).join('  ')}</div>`;output.scrollTop=output.scrollHeight;}); return;
        case 'ask': if(args.length){fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:args.join(' ')})}).then(r=>r.json()).then(d=>{output.innerHTML+=`<div class="term-line daria">🌸 ${d.response}</div>`;output.scrollTop=output.scrollHeight;});}else{result='ask <вопрос>';} return;
        default: result = `Неизвестно: ${command}`;
    }
    output.innerHTML += `<div class="term-line">${result}</div>`;
    output.scrollTop = output.scrollHeight;
}

function browserGo() {
    const input = document.getElementById('browser-url');
    const frame = document.getElementById('browser-frame');
    if (!input || !frame) return;
    let url = (input.value || '').trim();
    if (!url) return;
    if (!/^https?:\/\//i.test(url)) url = 'https://' + url;
    input.value = url;
    frame.src = `/api/browser/proxy?url=${encodeURIComponent(url)}`;
}
function browserBack() { document.getElementById('browser-frame')?.contentWindow?.history.back(); }
function browserForward() { document.getElementById('browser-frame')?.contentWindow?.history.forward(); }

let dariaGamePollTimer = null;
function initDariaGamesWindow() {
    if (dariaGamePollTimer) clearInterval(dariaGamePollTimer);
    loadDariaGameState();
    dariaGamePollTimer = setInterval(loadDariaGameState, 1500);
}

async function startDariaGame() {
    const mode = document.getElementById('daria-game-mode')?.value || 'associations';
    const opponent = document.getElementById('daria-game-opponent')?.value || 'bot';
    try {
        await fetch('/api/daria-games/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({reason: 'manual_ui', mode, opponent}),
        });
    } catch (e) {}
    loadDariaGameState();
}

async function stopDariaGame() {
    try {
        await fetch('/api/daria-games/stop', {method: 'POST'});
    } catch (e) {}
    loadDariaGameState();
}

async function loadDariaGameState() {
    const log = document.getElementById('daria-game-log');
    const status = document.getElementById('daria-game-status');
    const score = document.getElementById('daria-game-score');
    const board = document.getElementById('daria-game-board');
    if (!log || !status || !score || !board) return;
    try {
        const r = await fetch('/api/daria-games/state');
        const s = await r.json();
        status.textContent = s.running ? `Статус: игра идёт (${s.game})` : `Статус: ожидание (${s.game})`;
        score.textContent = `Счёт: ${s.score_dasha || 0} - ${s.score_shadow || 0}`;
        board.innerHTML = renderGameBoard(s);
        const lines = (s.moves || []).map(m => {
            const role = String(m.role || '').toLowerCase();
            const c = role.includes('system') ? 'system' : (role.includes('dasha') ? 'dasha' : 'user');
            return `<div class="daria-games-line ${c}"><b>${m.author}:</b> ${m.text}</div>`;
        }).join('');
        log.innerHTML = lines || '<div class="empty">Пока ходов нет</div>';
        log.scrollTop = log.scrollHeight;
    } catch (e) {
        status.textContent = 'Статус: ошибка соединения';
    }
}

function renderGameBoard(s) {
    if (s.mode === 'battleship' && s.battleship) {
        const enemy = s.battleship.dasha_shots || [];
        const own = s.battleship.dasha_board_public || [];
        const renderGrid = (grid, type, isEnemy) => {
            let html = `<div class="battle-grid-wrap"><div class="battle-grid-title">${type}</div><div class="battle-grid">`;
            for (let r = 0; r < 10; r++) {
                for (let c = 0; c < 10; c++) {
                    const v = grid?.[r]?.[c] ?? 0;
                    let cls = 'cell-water';
                    if (isEnemy) {
                        cls = v === 2 ? 'cell-hit' : v === 1 ? 'cell-miss' : 'cell-unknown';
                    } else {
                        cls = v === 3 ? 'cell-hit' : v === 1 ? 'cell-miss' : v === 2 ? 'cell-ship' : 'cell-water';
                    }
                    html += `<div class="battle-cell ${cls}" title="${String.fromCharCode(65 + c)}${r + 1}"></div>`;
                }
            }
            html += `</div></div>`;
            return html;
        };
        let out = `<div class="battle-boards">${renderGrid(enemy, 'Поле соперника', true)}${renderGrid(own, 'Поле Даши', false)}</div>`;
        out += `<div class="battle-meta">Ход: ${s.battleship.turn_owner || '—'}</div>`;
        if (s.winner) out += `<div class="battle-meta">Победитель: ${s.winner}</div>`;
        if (s.reward) out += `<div class="battle-meta">Награда: ${s.reward}</div>`;
        return out;
    }
    if (s.mode === 'maze2d' && s.maze?.grid) {
        const g = s.maze.grid;
        const p = s.maze.pos || [0, 0];
        const goal = s.maze.goal || [g.length - 1, g.length - 1];
        let out = '2D Лабиринт\n';
        for (let r = 0; r < g.length; r++) {
            let line = '';
            for (let c = 0; c < g[r].length; c++) {
                if (r === p[0] && c === p[1]) line += '🩷';
                else if (r === goal[0] && c === goal[1]) line += '🏁';
                else line += g[r][c] ? '⬛' : '⬜';
            }
            out += line + '\n';
        }
        if (s.reward) out += `Награда: ${s.reward}\n`;
        return `<pre>${out}</pre>`;
    }
    return '<pre>Ассоциации: здесь идёт ролевая игра ходов.\nСледи за мини-чатом ниже.</pre>';
}

async function sendDariaGameMessage() {
    const input = document.getElementById('daria-game-input');
    const text = input?.value?.trim();
    if (!text) return;
    input.value = '';
    try {
        await fetch('/api/daria-games/action', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text}),
        });
    } catch (e) {}
    loadDariaGameState();
}

function initPlayer() {
    state.audio = document.getElementById('player-audio');
    if (state.audio) {
        state.audio.addEventListener('timeupdate', () => {
            const p = document.getElementById('player-progress');
            if (p) p.style.width = (state.audio.currentTime / state.audio.duration * 100) + '%';
            document.getElementById('player-current').textContent = formatTime(state.audio.currentTime);
            document.getElementById('player-duration').textContent = formatTime(state.audio.duration);
        });
        state.audio.addEventListener('ended', () => { state.audioPlaying = false; updatePlayBtn(); });
    }
}

function formatTime(s) { return isNaN(s) ? '0:00' : `${Math.floor(s/60)}:${Math.floor(s%60).toString().padStart(2,'0')}`; }
function playerLoad(files) {
    if(files?.[0]&&state.audio){
        state.audio.src=URL.createObjectURL(files[0]);
        document.querySelector('.player-title').textContent=files[0].name;
        state.audio.load();
        fetch('/api/music/listen', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({title: files[0].name, source: 'local-file'}),
        }).catch(()=>{});
    }
}
async function playerPlay() {
    if (!state.audio) return;
    if (state.audioPlaying) {
        state.audio.pause();
        state.audioPlaying = false;
        updatePlayBtn();
        return;
    }
    try {
        await state.audio.play();
        state.audioPlaying = true;
        updatePlayBtn();
    } catch (e) {
        state.audioPlaying = false;
        updatePlayBtn();
    }
}
function updatePlayBtn() { document.getElementById('player-play-btn').textContent = state.audioPlaying ? '⏸' : '▶'; }
function playerVolume(v) { if(state.audio) state.audio.volume = v/100; }
function playerPrev() { if(state.audio) state.audio.currentTime = 0; }
function playerNext() {}

async function dashaListenTrack() {
    const input = document.getElementById('music-title-input');
    const title = input?.value?.trim();
    if (!title) return;
    try {
        const r = await fetch('/api/music/listen', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, source: title.includes('http') ? 'link' : 'manual'}),
        });
        const data = await r.json();
        if (data.status === 'ok') {
            showNotification({
                title: '🎧 Даша',
                message: `Послушала: ${data.listen.title} (${data.listen.mood})`,
                type: 'success',
                icon: '🎵',
                duration: 5000,
            });
            if (input) input.value = '';
        } else {
            throw new Error(data.error || 'Ошибка');
        }
    } catch (e) {
        showNotification({title: '🎵', message: `Не удалось: ${e.message || e}`, type: 'error', icon: '⚠️', duration: 4500});
    }
}

async function initLogs() {
    await refreshLogs();
    try { const es = new EventSource('/api/logs/stream'); es.onmessage = e => appendLog(JSON.parse(e.data)); } catch(e){}
}
async function refreshLogs() {
    const output = document.getElementById('logs-output'); if(!output) return;
    try { const r = await fetch('/api/logs?limit=100'); const logs = await r.json(); output.innerHTML=''; logs.forEach(appendLog); } catch(e){}
}
function appendLog(log) {
    const output = document.getElementById('logs-output');
    const filter = document.getElementById('logs-filter')?.value;
    if(filter!=='all' && log.level!==filter) return;
    output.innerHTML += `<div class="log ${log.level}">[${log.timestamp?.split('T')[1]?.substring(0,8)}] ${log.level} | ${log.message}</div>`;
    if(document.getElementById('logs-autoscroll')?.checked) output.scrollTop = output.scrollHeight;
}
function filterLogs() { refreshLogs(); }

async function initSettingsWindow() {
    // Загружаем настройки с сервера
    try {
        const r = await fetch('/api/settings');
        const settings = await r.json();
        
        // Заполняем поля
        if (document.getElementById('setting-name')) {
            document.getElementById('setting-name').value = settings.name || '';
        }
        if (document.getElementById('setting-gender')) {
            document.getElementById('setting-gender').value = settings.gender || '';
        }
        if (document.getElementById('setting-mode')) {
            document.getElementById('setting-mode').value = settings.mode || 'adaptive';
        }
        if (document.getElementById('setting-theme')) {
            document.getElementById('setting-theme').value = settings.theme || 'pink';
        }
        if (document.getElementById('setting-attention')) {
            document.getElementById('setting-attention').checked = settings.attention_enabled !== false;
        }
        
        // Обновляем локальный state
        state.settings = settings;
        state.attentionEnabled = settings.attention_enabled !== false;
        
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
    
    // Проверяем LLM статус
    try {
        const r = await fetch('/api/status');
        const s = await r.json();
        const llmEl = document.getElementById('llm-status');
        if (llmEl) {
            llmEl.textContent = s.llm?.available ? '✅ Доступен' : '❌ Недоступен';
        }
    } catch (e) {}
}

async function loadMemoryStats() {
    try {
        const [sr, fr] = await Promise.all([fetch('/api/memory/stats'), fetch('/api/memory/facts')]);
        const stats = await sr.json(), facts = await fr.json();
        document.getElementById('stat-conversations').textContent = stats.conversations || 0;
        document.getElementById('stat-facts').textContent = stats.facts || 0;
        const fc = document.getElementById('memory-facts');
        fc.innerHTML = Object.keys(facts).length ? Object.entries(facts).map(([k,v])=>`<div class="fact"><b>${k}</b>: ${v}</div>`).join('') : '<p class="empty">Пока ничего 💕</p>';
    } catch(e){}
}

async function clearMemory() { if(confirm('Очистить?')) { await fetch('/api/memory/clear',{method:'POST'}); loadMemoryStats(); }}

async function loadStore() {
    const container = document.getElementById('store-plugins'); if(!container) return;
    try {
        const r = await fetch('/api/plugins/catalog');
        const plugins = await r.json();
        container.innerHTML = plugins.map(p => `
            <div class="plugin-card" onclick="showPluginDetails('${p.id}')">
                <span class="plugin-icon">${p.icon}</span>
                <div class="plugin-info"><b>${p.name}</b><span>v${p.version}</span></div>
                <span class="plugin-status ${p.installed?'installed':''}">${p.installed?'✓':''}</span>
            </div>
        `).join('') || '<p class="empty">Пусто</p>';
    } catch(e) { container.innerHTML = '<p class="empty">Ошибка</p>'; }
}

async function showPluginDetails(id) {
    try {
        const r = await fetch(`/api/plugins/${id}`);
        const p = await r.json();
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content"><div class="modal-header"><h2>${p.icon} ${p.name}</h2></div>
            <div class="modal-body"><p>${p.description}</p><p><small>v${p.version} • ${p.author}</small></p>
            ${p.update_available ? `<p><small>Доступно обновление: v${p.latest_version}</small></p>` : ''}</div>
            <div class="modal-footer">
                ${p.installed && p.update_available ? `<button class="btn-primary" onclick="updatePlugin('${id}',this)">Обновить</button>` : ''}
                ${p.installed?`<button class="btn-danger" onclick="uninstallPlugin('${id}',this)">Удалить</button>`:`<button class="btn-primary" onclick="installPlugin('${id}',this)">Установить</button>`}
                <button onclick="this.closest('.modal').remove()">Закрыть</button>
            </div></div>`;
        modal.onclick = e => { if(e.target===modal) modal.remove(); };
        document.body.appendChild(modal);
    } catch(e){}
}

async function installPlugin(id, btn) { btn.disabled=true; await fetch(`/api/plugins/${id}/install`,{method:'POST'}); btn.closest('.modal')?.remove(); await loadPlugins(); initDesktopIcons(); loadStore(); }
async function uninstallPlugin(id, btn) { if(!confirm('Удалить?'))return; await fetch(`/api/plugins/${id}/uninstall`,{method:'POST'}); btn.closest('.modal')?.remove(); await loadPlugins(); initDesktopIcons(); loadStore(); }
async function updatePlugin(id, btn) { btn.disabled=true; await fetch(`/api/plugins/${id}/update`,{method:'POST'}); btn.closest('.modal')?.remove(); await loadPlugins(); initDesktopIcons(); loadStore(); }
function refreshStore() { loadStore(); }

// ═══════════════════════════════════════════════════════════════
//  Updater
// ═══════════════════════════════════════════════════════════════

async function initUpdaterWindow() {
    await updaterLoadState();
    await updaterCheck();
    await updaterLoadPluginUpdates();
}

async function updaterLoadState() {
    try {
        const autoResp = await fetch('/api/update/auto');
        const autoData = await autoResp.json();
        const autoEl = document.getElementById('updater-auto');
        if (autoEl) autoEl.checked = !!autoData.auto_update;

        const r = await fetch('/api/update/state');
        const s = await r.json();
        const el = document.getElementById('updater-state');
        if (el) {
            el.textContent = s.running ? 'Обновление выполняется...' : `Текущая версия: v${s.version || '—'}`;
        }
    } catch (e) {}
}

async function updaterToggleAuto(input) {
    try {
        await fetch('/api/update/auto', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({auto_update: !!input?.checked}),
        });
    } catch (e) {}
}

async function updaterCheck() {
    const repo = document.getElementById('updater-repo')?.value || 'dariumi/Daria';
    const ref = document.getElementById('updater-ref')?.value || 'main';
    const out = document.getElementById('updater-core-info');
    if (out) out.textContent = 'Проверка...';
    try {
        const r = await fetch(`/api/update/check?source=github&repo=${encodeURIComponent(repo)}&ref=${encodeURIComponent(ref)}`);
        const data = await r.json();
        if (!out) return;
        out.textContent = `Текущая: v${data.current} • Доступно: v${data.latest}${data.update_available ? ' (есть обновление)' : ''}`;
    } catch (e) {
        if (out) out.textContent = 'Ошибка проверки';
    }
}

async function updaterRunGithub() {
    const repo = document.getElementById('updater-repo')?.value || 'dariumi/Daria';
    const ref = document.getElementById('updater-ref')?.value || 'main';
    const out = document.getElementById('updater-core-info');
    if (out) out.textContent = 'Обновляю из GitHub...';
    try {
        const r = await fetch('/api/update/from-github', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({repo, ref}),
        });
        const data = await r.json();
        if (data.status === 'ok') out.textContent = `Готово. Версия: v${data.version}. Нужен перезапуск.`;
        else out.textContent = `Ошибка: ${data.error || 'неизвестно'}`;
    } catch (e) {
        if (out) out.textContent = 'Ошибка обновления';
    }
}

async function updaterRunArchive() {
    const archivePath = document.getElementById('updater-archive-path')?.value?.trim();
    const out = document.getElementById('updater-core-info');
    if (!archivePath) {
        if (out) out.textContent = 'Укажи путь к архиву';
        return;
    }
    if (out) out.textContent = 'Обновляю из архива...';
    try {
        const r = await fetch('/api/update/from-archive', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({archive_path: archivePath}),
        });
        const data = await r.json();
        if (data.status === 'ok') out.textContent = `Готово. Версия: v${data.version}. Нужен перезапуск.`;
        else out.textContent = `Ошибка: ${data.error || 'неизвестно'}`;
    } catch (e) {
        if (out) out.textContent = 'Ошибка обновления';
    }
}

async function updaterLoadPluginUpdates() {
    const el = document.getElementById('updater-plugin-updates');
    if (!el) return;
    el.innerHTML = '<div class="loading">Проверка...</div>';
    try {
        const r = await fetch('/api/plugins/updates');
        const updates = await r.json();
        if (!Array.isArray(updates) || updates.length === 0) {
            el.innerHTML = '<div class="empty">Плагины обновлены</div>';
            return;
        }
        el.innerHTML = updates.map(u => `
            <div class="plugin-card">
                <span class="plugin-icon">🧩</span>
                <div class="plugin-info"><b>${u.name || u.id}</b><span>v${u.current_version} → v${u.latest_version}</span></div>
                <button onclick="updaterUpdatePlugin('${u.id}', this)">Обновить</button>
            </div>
        `).join('');
    } catch (e) {
        el.innerHTML = '<div class="empty">Ошибка загрузки</div>';
    }
}

async function updaterUpdatePlugin(id, btn) {
    btn.disabled = true;
    await fetch(`/api/plugins/${id}/update`, {method: 'POST'});
    await loadPlugins();
    initDesktopIcons();
    updaterLoadPluginUpdates();
}

async function updaterUpdateAllPlugins() {
    await fetch('/api/plugins/update-all', {method: 'POST'});
    await loadPlugins();
    initDesktopIcons();
    updaterLoadPluginUpdates();
}

// ═══════════════════════════════════════════════════════════════
//  Self / Senses / Wiki
// ═══════════════════════════════════════════════════════════════

async function loadSelfPerception() {
    const box = document.getElementById('self-perception-content');
    if (!box) return;
    box.innerHTML = '<div class="loading">Загрузка...</div>';
    try {
        const r = await fetch('/api/self/perception');
        const data = await r.json();
        const state = data.state || {};
        const traits = data.traits || [];
        const followups = data.followups || [];
        box.innerHTML = `
            <div class="self-grid">
                <section class="self-card">
                    <h3>${state.mood_emoji || '🌸'} ${data.self_name || 'Даша'}</h3>
                    <p>Состояние: ${state.mood_label || 'Спокойна'}</p>
                    <p>Энергия: ${Math.round((state.energy || 0.7) * 100)}%</p>
                    <p>Социальная потребность: ${Math.round((state.social_need || 0.5) * 100)}%</p>
                </section>
                <section class="self-card">
                    <h3>Кто я сейчас</h3>
                    <ul>${traits.map(t => `<li>${t}</li>`).join('')}</ul>
                </section>
                <section class="self-card self-instruction-card">
                    <h3>Базовая инструкция самосознания</h3>
                    <p class="self-note">Этот текст формирует самоощущение Даши. Его можно менять под ваш стиль.</p>
                    <textarea id="self-instruction-input" class="self-instruction-input" placeholder="Опиши характер Даши..."></textarea>
                    <div class="self-actions">
                        <button class="btn-primary" onclick="saveSelfInstruction()">💾 Сохранить</button>
                        <button onclick="loadSelfInstruction()">↻ Обновить</button>
                    </div>
                    <div id="self-instruction-info" class="self-note"></div>
                </section>
                <section class="self-card">
                    <h3>Запланированные напоминания</h3>
                    ${followups.length ? followups.map(f => `<p>• ${f.time}: ${f.message}</p>`).join('') : '<p>Пока нет.</p>'}
                </section>
            </div>
        `;
        const input = document.getElementById('self-instruction-input');
        if (input) input.value = data.instruction || '';
    } catch (e) {
        box.innerHTML = '<div class="empty">Ошибка загрузки</div>';
    }
}

async function loadSelfInstruction() {
    const input = document.getElementById('self-instruction-input');
    if (!input) return;
    try {
        const r = await fetch('/api/self/instruction');
        const data = await r.json();
        input.value = data.instruction || '';
    } catch (e) {}
}

async function saveSelfInstruction() {
    const input = document.getElementById('self-instruction-input');
    const info = document.getElementById('self-instruction-info');
    if (!input) return;
    if (info) info.textContent = 'Сохраняю...';
    try {
        const r = await fetch('/api/self/instruction', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({instruction: input.value}),
        });
        const data = await r.json();
        if (info) info.textContent = data.status === 'ok' ? 'Сохранено.' : (data.error || 'Ошибка');
    } catch (e) {
        if (info) info.textContent = 'Ошибка соединения';
    }
}

function mdToHtml(md) {
    const safeHref = (url) => {
        const u = String(url || '').trim();
        if (!u) return '#';
        if (u.startsWith('/')) return u;
        if (/^https?:\/\//i.test(u)) return u;
        return '#';
    };
    const esc = (s) => String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    const inline = (s) => esc(s)
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, link) => `<a href="${safeHref(link)}" target="_blank" rel="noopener">${label}</a>`);

    const lines = String(md || '').replace(/\r\n/g, '\n').split('\n');
    let html = '';
    let inCode = false;
    let inUl = false;
    let inOl = false;

    const closeLists = () => {
        if (inUl) { html += '</ul>'; inUl = false; }
        if (inOl) { html += '</ol>'; inOl = false; }
    };

    for (const line of lines) {
        if (line.startsWith('```')) {
            closeLists();
            html += inCode ? '</code></pre>' : '<pre><code>';
            inCode = !inCode;
            continue;
        }
        if (inCode) {
            html += `${esc(line)}\n`;
            continue;
        }
        if (/^\s*$/.test(line)) {
            closeLists();
            html += '<br>';
            continue;
        }
        if (/^#{1,6}\s+/.test(line)) {
            closeLists();
            const level = line.match(/^#+/)[0].length;
            html += `<h${level}>${inline(line.replace(/^#{1,6}\s+/, ''))}</h${level}>`;
            continue;
        }
        if (/^>\s?/.test(line)) {
            closeLists();
            html += `<blockquote>${inline(line.replace(/^>\s?/, ''))}</blockquote>`;
            continue;
        }
        if (/^\d+\.\s+/.test(line)) {
            if (!inOl) { closeLists(); html += '<ol>'; inOl = true; }
            html += `<li>${inline(line.replace(/^\d+\.\s+/, ''))}</li>`;
            continue;
        }
        if (/^[-*]\s+/.test(line)) {
            if (!inUl) { closeLists(); html += '<ul>'; inUl = true; }
            html += `<li>${inline(line.replace(/^[-*]\s+/, ''))}</li>`;
            continue;
        }
        closeLists();
        if (/^---+$/.test(line.trim())) {
            html += '<hr>';
            continue;
        }
        html += `<p>${inline(line)}</p>`;
    }
    if (inCode) html += '</code></pre>';
    if (inUl) html += '</ul>';
    if (inOl) html += '</ol>';
    return html;
}

async function sensesSee() {
    const input = document.getElementById('senses-see-input');
    const file = document.getElementById('senses-see-file')?.files?.[0];
    const out = document.getElementById('senses-output');
    if ((!input?.value?.trim() && !file) || !out) return;
    out.textContent = 'Думаю...';
    try {
        const fd = new FormData();
        if (input?.value?.trim()) fd.append('description', input.value.trim());
        if (file) fd.append('image', file);
        const r = await fetch('/api/senses/see', {
            method: 'POST',
            body: fd,
        });
        const data = await r.json();
        out.textContent = data.result || data.error || 'Нет ответа';
    } catch (e) {
        out.textContent = 'Ошибка анализа';
    }
}

async function sensesHear() {
    const input = document.getElementById('senses-hear-input');
    const file = document.getElementById('senses-hear-file')?.files?.[0];
    const out = document.getElementById('senses-output');
    if ((!input?.value?.trim() && !file) || !out) return;
    out.textContent = 'Слушаю...';
    try {
        const fd = new FormData();
        if (input?.value?.trim()) fd.append('transcript', input.value.trim());
        if (file) fd.append('audio', file);
        const r = await fetch('/api/senses/hear', {
            method: 'POST',
            body: fd,
        });
        const data = await r.json();
        out.textContent = data.result || data.error || 'Нет ответа';
    } catch (e) {
        out.textContent = 'Ошибка анализа';
    }
}

function initSensesWindow() {
    const out = document.getElementById('senses-output');
    if (out) out.textContent = 'Опиши, что ты видишь или слышишь — Даша разберёт смысл.';
}

async function loadTodoLists() {
    const userList = document.getElementById('todo-user-list');
    const dashaList = document.getElementById('todo-dasha-list');
    const dateEl = document.getElementById('todo-date');
    if (!userList || !dashaList) return;
    userList.innerHTML = '<div class="loading">Загрузка...</div>';
    dashaList.innerHTML = '<div class="loading">Загрузка...</div>';
    try {
        const r = await fetch('/api/tasks');
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        if (dateEl) dateEl.textContent = data.date || '—';
        userList.innerHTML = renderTodoItems(data.user_tasks || []);
        dashaList.innerHTML = renderDashaTodoItems(data.dasha_tasks || []);
        const planEl = document.getElementById('todo-plan-summary');
        if (planEl) {
            const current = data.current_task?.title ? `Сейчас: ${data.current_task.title}` : 'Сейчас: свободна';
            const recent = (data.activity_log || []).slice(-3).map(a => `• ${a.title}`).join('<br>');
            planEl.innerHTML = `${current}<br>${recent || '• Активность появится после первых задач'}`;
        }
    } catch (e) {
        userList.innerHTML = '<div class="empty">Ошибка загрузки</div>';
        dashaList.innerHTML = '<div class="empty">Ошибка загрузки</div>';
    }
}

async function askDashaPlans() {
    try {
        const r = await fetch('/api/tasks/plans');
        const data = await r.json();
        openWindow('chat');
        if (data?.summary) {
            addMessage(data.summary, 'assistant', 'chat-messages');
        }
    } catch (e) {}
}

function renderTodoItems(items) {
    if (!items.length) return '<div class="empty">Пока пусто</div>';
    return items.map(t => `
        <div class="todo-item ${t.done ? 'done' : ''}">
            <label><input type="checkbox" ${t.done ? 'checked' : ''} onchange="toggleTask('${t.id}', this.checked)"> ${t.done ? '✅' : '📝'} ${t.title}</label>
            <button onclick="deleteTask('${t.id}')">🗑️</button>
        </div>
    `).join('');
}

function renderDashaTodoItems(items) {
    if (!items.length) return '<div class="empty">Пока пусто</div>';
    const open = items.filter(t => !t.done);
    const done = items.filter(t => t.done);
    const doneAgg = {};
    for (const t of done) {
        const key = t.title || 'Без названия';
        doneAgg[key] = (doneAgg[key] || 0) + 1;
    }
    const openHtml = open.map(t => `
        <div class="todo-item">
            <label><input type="checkbox" onchange="toggleTask('${t.id}', true)"> 📝 ${t.title}</label>
            <button onclick="deleteTask('${t.id}')">🗑️</button>
        </div>
    `).join('');
    const doneRows = Object.entries(doneAgg).map(([title, count]) => `
        <div class="todo-item done aggregate">
            <label>✅ ${title} <span class="todo-count">×${count}</span></label>
        </div>
    `).join('');
    return (openHtml || '<div class="empty">Нет активных дел</div>') + (doneRows ? `<div class="todo-group-title">Сделано</div>${doneRows}` : '');
}

async function addUserTask() {
    const input = document.getElementById('todo-user-input');
    const title = input?.value?.trim();
    if (!title) return;
    const r = await fetch('/api/tasks/user/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title}),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    input.value = '';
    loadTodoLists();
}

async function generateDashaTasks() {
    const r = await fetch('/api/tasks/generate-dasha-day', {method: 'POST'});
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    loadTodoLists();
}

async function toggleTask(id, done) {
    await fetch('/api/tasks/toggle', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id, done}),
    });
    loadTodoLists();
}

async function deleteTask(id) {
    await fetch('/api/tasks/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id}),
    });
    loadTodoLists();
}

async function initWikiWindow() {
    const list = document.getElementById('wiki-pages');
    const content = document.getElementById('wiki-body');
    if (!list || !content) return;
    list.innerHTML = '<div class="loading">Загрузка...</div>';
    try {
        const r = await fetch('/api/wiki/pages');
        const data = await r.json();
        const pages = data.pages || [];
        list.innerHTML = pages.map(p => `<button onclick="loadWikiPage('${p}')">${p}</button>`).join('') || '<div class="empty">Страниц нет</div>';
        if (pages.length) loadWikiPage(pages[0]);
    } catch (e) {
        list.innerHTML = '<div class="empty">Ошибка загрузки</div>';
    }
}

async function loadWikiPage(name) {
    const content = document.getElementById('wiki-body');
    if (!content) return;
    content.innerHTML = '<div class="loading">Загрузка...</div>';
    try {
        const r = await fetch(`/api/wiki/page?name=${encodeURIComponent(name)}`);
        const data = await r.json();
        if (data.content) {
            content.innerHTML = `<article class="wiki-markdown">${mdToHtml(data.content)}</article>`;
        } else {
            content.textContent = data.error || 'Пусто';
        }
    } catch (e) {
        content.textContent = 'Ошибка чтения страницы';
    }
}

// ═══════════════════════════════════════════════════════════════
//  Start Menu & Welcome
// ═══════════════════════════════════════════════════════════════

function toggleStartMenu() { document.getElementById('start-menu')?.classList.toggle('hidden'); }
document.addEventListener('click', e => {
    const menu = document.getElementById('start-menu'), btn = document.getElementById('start-button');
    if(menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) menu.classList.add('hidden');
    const picker = document.getElementById('chat-sticker-picker');
    const toggle = e.target?.closest?.('.chat-sticker-toggle');
    if (picker && !picker.classList.contains('hidden') && !picker.contains(e.target) && !toggle) {
        picker.classList.add('hidden');
    }
});

function checkFirstVisit() { if(!localStorage.getItem('daria_visited')) document.getElementById('welcome-modal')?.classList.remove('hidden'); }

async function closeWelcome() {
    const name = document.getElementById('welcome-name')?.value.trim();
    const gender = document.querySelector('input[name="gender"]:checked')?.value;
    
    // Сохраняем настройки
    const settings = {name: name || '', gender: gender || ''};
    
    if (name || gender) {
        await fetch('/api/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(settings)
        });
        // Обновляем локальный state
        state.settings.name = name;
        state.settings.gender = gender;
    }
    
    localStorage.setItem('daria_visited', 'true');
    document.getElementById('welcome-modal')?.classList.add('hidden');
    openWindow('chat');
    
    setTimeout(() => {
        const greeting = name ? `Привет! Меня зовут ${name}!` : 'Привет!';
        addMessage(greeting, 'user', 'chat-messages');
        fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({content:greeting})})
            .then(r=>r.json()).then(d=>addMessage(d.response,'assistant','chat-messages'));
    }, 500);
}
