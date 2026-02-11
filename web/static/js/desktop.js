/**
 * DARIA Desktop v0.7.0
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
};

const defaultIcons = [
    { id: 'chat', icon: '💬', name: 'Чат', window: 'chat' },
    { id: 'files', icon: '📁', name: 'Файлы', window: 'files' },
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
    files: { icon: '📁', title: 'Файлы', width: 550, height: 400 },
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
    checkFirstVisit();
    window.addEventListener('resize', () => { state.isMobile = window.innerWidth < 768; });
});

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
    
    try {
        const es = new EventSource('/api/notifications/stream');
        es.onmessage = (e) => showNotification(JSON.parse(e.data));
    } catch (e) {}
}

function showNotification(notif) {
    // Show in-app notification
    const container = document.getElementById('notifications-container');
    if (container) {
        const el = document.createElement('div');
        el.className = `notification ${notif.type || 'info'}`;
        el.innerHTML = `<span>${notif.icon || '💬'}</span><div><b>${notif.title}</b><p>${notif.message}</p></div><button onclick="this.parentElement.remove()">×</button>`;
        el.onclick = () => { if (notif.action === 'open_chat') openWindow('chat'); };
        container.appendChild(el);
        setTimeout(() => el.remove(), notif.duration || 5000);
    }
    
    // Show system notification if requested and permitted
    if (notif.system && 'Notification' in window && Notification.permission === 'granted') {
        const sysNotif = new Notification(notif.title, {
            body: notif.message,
            icon: '/static/icon.png',
            tag: 'daria-' + notif.id,
            requireInteraction: true,
        });
        
        sysNotif.onclick = () => {
            window.focus();
            if (notif.action === 'open_chat') openWindow('chat');
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
    createWindow(windowId, config, () => {
        const tpl = document.getElementById(windowId + '-content');
        return tpl ? tpl.content.cloneNode(true) : null;
    });
    initWindowContent(windowId);
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
    loadContent();
    
    initWindowEvents(windowEl, windowId);
    document.getElementById('windows-container').appendChild(windowEl);
    state.windows.set(windowId, {element: windowEl, config});
    addTaskbarItem(windowId, config);
    focusWindow(windowId);
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
    else if (windowId === 'settings') initSettingsWindow();
    else if (windowId === 'memory') loadMemoryStats();
    else if (windowId === 'store') loadStore();
    else if (windowId === 'logs') initLogs();
    else if (windowId === 'player') initPlayer();
    else if (windowId === 'files') loadFiles();
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
        
        container.innerHTML = chats.map(c => `
            <div class="chat-history-item ${c.id === state.currentChatId ? 'active' : ''}" 
                 onclick="loadChat('${c.id}')">
                <span class="chat-preview">${c.preview || 'Новый чат'}</span>
                <span class="chat-date">${new Date(c.created).toLocaleDateString('ru')}</span>
                <button class="chat-delete" onclick="deleteChat('${c.id}', event)">×</button>
            </div>
        `).join('') || '<p class="empty">Нет истории</p>';
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
    
    fetch('/api/chat', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content, chat_id: state.currentChatId})
    }).then(r => r.json()).then(data => {
        document.getElementById('chat-typing')?.classList.add('hidden');
        if (data.chat_id) state.currentChatId = data.chat_id;
        addMessage(data.response, 'assistant', 'chat-messages');
        loadChatHistory();
    }).catch(() => {
        document.getElementById('chat-typing')?.classList.add('hidden');
        addMessage('Ошибка соединения... 💔', 'assistant', 'chat-messages');
    });
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

function addMessage(content, role, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const msg = document.createElement('div');
    msg.className = `message ${role}`;
    msg.textContent = content;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

// ═══════════════════════════════════════════════════════════════
//  Files, Terminal, Browser, Player, etc.
// ═══════════════════════════════════════════════════════════════

async function loadFiles(path = "") {
    state.currentPath = path;
    const list = document.getElementById('files-list');
    document.getElementById('files-path').textContent = '/' + path;
    list.innerHTML = '<div class="loading">Загрузка...</div>';
    
    try {
        const r = await fetch(`/api/files?path=${encodeURIComponent(path)}`);
        const data = await r.json();
        let html = path ? `<div class="file-item" ondblclick="loadFiles('${path.split('/').slice(0,-1).join('/')}')"><span>📁</span>..</div>` : '';
        data.items.forEach(item => {
            const icon = item.is_dir ? '📁' : '📄';
            html += `<div class="file-item" ondblclick="${item.is_dir ? `loadFiles('${item.path}')` : `openFile('${item.path}')`}">
                <span>${icon}</span><span class="name">${item.name}</span>
                <button onclick="deleteFile('${item.path}',event)">🗑️</button>
            </div>`;
        });
        list.innerHTML = html || '<div class="empty">Пусто</div>';
    } catch (e) { list.innerHTML = '<div class="empty">Ошибка</div>'; }
}

async function openFile(path) {
    try {
        const r = await fetch(`/api/files/read?path=${encodeURIComponent(path)}`);
        const data = await r.json();
        document.getElementById('file-editor-path').value = path;
        document.getElementById('file-editor-content').value = data.content || '';
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

function closeEditor() { document.getElementById('file-editor')?.classList.add('hidden'); }

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

function browserGo() { const url = document.getElementById('browser-url')?.value; document.getElementById('browser-frame').src = url; }
function browserBack() { document.getElementById('browser-frame')?.contentWindow?.history.back(); }
function browserForward() { document.getElementById('browser-frame')?.contentWindow?.history.forward(); }

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
function playerLoad(files) { if(files?.[0]&&state.audio){state.audio.src=URL.createObjectURL(files[0]);document.querySelector('.player-title').textContent=files[0].name;state.audio.load();}}
function playerPlay() { if(!state.audio)return; state.audioPlaying?state.audio.pause():state.audio.play(); state.audioPlaying=!state.audioPlaying; updatePlayBtn(); }
function updatePlayBtn() { document.getElementById('player-play-btn').textContent = state.audioPlaying ? '⏸' : '▶'; }
function playerVolume(v) { if(state.audio) state.audio.volume = v/100; }
function playerPrev() { if(state.audio) state.audio.currentTime = 0; }
function playerNext() {}

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
            <div class="modal-body"><p>${p.description}</p><p><small>v${p.version} • ${p.author}</small></p></div>
            <div class="modal-footer">
                ${p.installed?`<button class="btn-danger" onclick="uninstallPlugin('${id}',this)">Удалить</button>`:`<button class="btn-primary" onclick="installPlugin('${id}',this)">Установить</button>`}
                <button onclick="this.closest('.modal').remove()">Закрыть</button>
            </div></div>`;
        modal.onclick = e => { if(e.target===modal) modal.remove(); };
        document.body.appendChild(modal);
    } catch(e){}
}

async function installPlugin(id, btn) { btn.disabled=true; await fetch(`/api/plugins/${id}/install`,{method:'POST'}); btn.closest('.modal')?.remove(); await loadPlugins(); initDesktopIcons(); loadStore(); }
async function uninstallPlugin(id, btn) { if(!confirm('Удалить?'))return; await fetch(`/api/plugins/${id}/uninstall`,{method:'POST'}); btn.closest('.modal')?.remove(); await loadPlugins(); initDesktopIcons(); loadStore(); }
function refreshStore() { loadStore(); }

// ═══════════════════════════════════════════════════════════════
//  Start Menu & Welcome
// ═══════════════════════════════════════════════════════════════

function toggleStartMenu() { document.getElementById('start-menu')?.classList.toggle('hidden'); }
document.addEventListener('click', e => {
    const menu = document.getElementById('start-menu'), btn = document.getElementById('start-button');
    if(menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) menu.classList.add('hidden');
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
