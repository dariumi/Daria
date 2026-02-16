/**
 * DARIA Desktop v0.9.1
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
    currentFileReadOnly: false,
    stickerCatalog: null,
    stickerPickerOpen: false,
    calendarMonthShift: 0,
    knowledgeResults: [],
    chatHistoryFilter: 'all',
    chatReplyTo: null,
    chatAttachedImage: null,
    imageGenJobs: new Map(),
};

function escapeHtml(s) {
    return String(s ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const defaultIcons = [
    { id: 'chat', icon: '💬', name: 'Разговор с Дашей', window: 'chat' },
    { id: 'self', icon: '🪞', name: 'Состояние Даши', window: 'self' },
    { id: 'todos', icon: '✅', name: 'Списки дел', window: 'todos' },
    { id: 'senses', icon: '👁️', name: 'Чувства и восприятие', window: 'senses' },
    { id: 'wiki', icon: '📚', name: 'База знаний', window: 'wiki' },
    { id: 'calendar', icon: '📅', name: 'Календарь', window: 'calendar' },
    { id: 'updater', icon: '⬆️', name: 'Обновления', window: 'updater' },
    { id: 'files', icon: '📁', name: 'Файлы', window: 'files' },
    { id: 'diary', icon: '📝', name: 'Дневник Даши', window: 'diary' },
    { id: 'knowledge', icon: '📖', name: 'Инспектор знаний', window: 'knowledge' },
    { id: 'daria-games', icon: '🎮', name: 'Игровой центр', window: 'daria-games' },
    { id: 'terminal', icon: '💻', name: 'Консоль', window: 'terminal' },
    { id: 'monitor', icon: '📈', name: 'Монитор Даши', window: 'monitor' },
    { id: 'browser', icon: '🌐', name: 'Браузер', window: 'browser' },
    { id: 'player', icon: '🎵', name: 'Музыка', window: 'player' },
    { id: 'store', icon: '🛒', name: 'Магазин', window: 'store' },
    { id: 'memory', icon: '🧠', name: 'Память', window: 'memory' },
    { id: 'settings', icon: '⚙️', name: 'Настройки', window: 'settings' },
    { id: 'support', icon: '☕', name: 'Поддержать', window: 'support' },
];

const iconPacks = {
    default: {},
    soft: {
        chat: '🩷', self: '🪞', todos: '🗒️', senses: '👀', wiki: '📖', calendar: '🗓️',
        updater: '🔼', files: '🗂️', diary: '📝', knowledge: '📖', 'daria-games': '🧸', terminal: '⌨️', browser: '🧭',
        player: '🎶', store: '🧺', memory: '💭', settings: '🔧', support: '☕'
    },
    line: {
        chat: '💬', self: '🧠', todos: '✅', senses: '🎧', wiki: '📚', calendar: '📅',
        updater: '⬆️', files: '📁', diary: '📝', knowledge: '📖', 'daria-games': '🎮', terminal: '💻', browser: '🌐',
        player: '🎵', store: '🛒', memory: '🧠', settings: '⚙️', support: '🤍'
    },
    bootstrap: {
        chat: 'bi:bi-chat-dots-fill',
        self: 'bi:bi-person-heart',
        todos: 'bi:bi-check2-square',
        senses: 'bi:bi-binoculars-fill',
        wiki: 'bi:bi-journal-richtext',
        calendar: 'bi:bi-calendar3',
        updater: 'bi:bi-arrow-up-circle-fill',
        files: 'bi:bi-folder2-open',
        diary: 'bi:bi-journal-heart',
        knowledge: 'bi:bi-lightbulb-fill',
        'daria-games': 'bi:bi-controller',
        terminal: 'bi:bi-terminal-fill',
        monitor: 'bi:bi-activity',
        browser: 'bi:bi-globe2',
        player: 'bi:bi-music-note-list',
        store: 'bi:bi-shop',
        memory: 'bi:bi-database-fill',
        settings: 'bi:bi-sliders2-vertical',
        support: 'bi:bi-cup-hot-fill',
    },
};

const windowConfigs = {
    chat: { icon: '💬', title: 'Разговор с Дарьей', width: 620, height: 520 },
    self: { icon: '🪞', title: 'Состояние Даши', width: 640, height: 560 },
    todos: { icon: '✅', title: 'Списки дел', width: 560, height: 560 },
    senses: { icon: '👁️', title: 'Чувства и восприятие', width: 620, height: 560 },
    wiki: { icon: '📚', title: 'База знаний', width: 760, height: 560 },
    calendar: { icon: '📅', title: 'Календарь', width: 560, height: 520 },
    updater: { icon: '⬆️', title: 'Обновления', width: 560, height: 540 },
    files: { icon: '📁', title: 'Файлы', width: 550, height: 400 },
    diary: { icon: '📝', title: 'Личный дневник Даши', width: 760, height: 560 },
    knowledge: { icon: '📖', title: 'Инспектор знаний', width: 760, height: 560 },
    'daria-games': { icon: '🎮', title: 'Игровой центр', width: 660, height: 460 },
    terminal: { icon: '💻', title: 'Консоль', width: 600, height: 400 },
    monitor: { icon: '📈', title: 'Монитор Даши', width: 420, height: 360 },
    browser: { icon: '🌐', title: 'Браузер', width: 800, height: 600 },
    player: { icon: '🎵', title: 'Музыка Даши', width: 860, height: 520 },
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
    initDesktopContextMenu();
    initClock();
    initAvatar();
    await initConnection();
    initNotifications();
    initProactivePolling();
    initMoodBehavior();
    checkFirstVisit();
    applyStartupDeepLink();
    initWallpaperRoutine();
    window.addEventListener('resize', () => { state.isMobile = window.innerWidth < 768; });
});

function applyStartupDeepLink() {
    try {
        const params = new URLSearchParams(window.location.search || '');
        const open = (params.get('open') || '').toLowerCase();
        if (open === 'logs' || open === 'debug') {
            openWindow('terminal');
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
        applyIconPack(state.settings.icon_pack || 'default');
        state.attentionEnabled = state.settings.attention_enabled !== false;
        if (state.settings.wallpaper) {
            document.getElementById('desktop').style.backgroundImage = `url(${state.settings.wallpaper})`;
        }
        const startAvatar = document.getElementById('start-user-avatar');
        if (startAvatar) {
            if (state.settings.avatar) {
                startAvatar.src = state.settings.avatar;
                startAvatar.classList.remove('hidden');
            } else {
                startAvatar.classList.add('hidden');
            }
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
            createDesktopIcon(container, {...ic, icon: resolveIcon(ic.id, ic.icon)}, i);
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

function resolveIcon(id, fallback) {
    const pack = state.settings?.icon_pack || 'default';
    return (iconPacks[pack] && iconPacks[pack][id]) || fallback;
}

function renderIcon(iconValue) {
    const v = String(iconValue || '');
    if (v.startsWith('bi:')) {
        const cls = v.slice(3);
        return `<i class="${cls}"></i>`;
    }
    return v;
}

function createDesktopIcon(container, data, index) {
    const icon = document.createElement('div');
    icon.className = 'desktop-icon';
    icon.dataset.iconId = data.id;
    icon.innerHTML = `<div class="icon">${renderIcon(data.icon)}</div><span>${data.name}</span>`;
    
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

function saveIconPositions() {
    fetch('/api/desktop/icons', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(state.iconPositions || {}),
    }).catch(() => {});
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
            const cid = String(notif?.action_data?.chat_id || '').trim();
            if (cid) {
                setTimeout(() => {
                    loadChat(cid).catch(() => {});
                }, 140);
            }
            return;
        }
        if (notif.action === 'open_calendar') {
            openWindow('calendar');
            return;
        }
        if (notif.action.startsWith('open_window:')) {
            const winId = notif.action.split(':')[1];
            if (winId) {
                openWindow(winId);
                setTimeout(() => applyWindowOps(winId, notif?.action_data?.window_ops || {}), 100);
                if (winId === 'browser' && notif?.action_data?.url) {
                    setTimeout(() => {
                        const u = document.getElementById('browser-url');
                        if (u) {
                            u.value = String(notif.action_data.url);
                            browserGo();
                        }
                    }, 120);
                }
            }
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
    if (notif?.action_data?.auto_open) {
        setTimeout(() => performAction(), 120);
    }
    if (notif?.action_data?.desktop_action === 'tidy') {
        setTimeout(() => dariaTidyDesktop(), 150);
    }
    if (notif?.action_data?.wallpaper) {
        applyWallpaper(notif.action_data.wallpaper);
    }
    if (notif?.action_data?.wallpaper_url) {
        applyWallpaper(`url(${notif.action_data.wallpaper_url})`);
        fetch('/api/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({wallpaper: notif.action_data.wallpaper_url}),
        }).catch(()=>{});
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

function applyWallpaper(value) {
    const desktop = document.getElementById('desktop');
    if (!desktop) return;
    if (!value) return;
    desktop.style.backgroundImage = String(value);
}

function randomGradientWallpaper() {
    const palettes = [
        ['#1f2937', '#334155', '#0ea5e9'],
        ['#0f172a', '#1d4ed8', '#60a5fa'],
        ['#3f1d2e', '#7e22ce', '#f472b6'],
        ['#1b4332', '#2d6a4f', '#95d5b2'],
        ['#2d1b3d', '#6d28d9', '#f9a8d4'],
    ];
    const p = palettes[Math.floor(Math.random() * palettes.length)];
    return `linear-gradient(135deg, ${p[0]} 0%, ${p[1]} 55%, ${p[2]} 100%)`;
}

function initWallpaperRoutine() {
    setInterval(() => {
        if (!state.settings?.auto_wallpaper_change) return;
        const w = randomGradientWallpaper();
        applyWallpaper(w);
    }, 1000 * 60 * 90);
}

function applyWindowOps(windowId, ops = {}) {
    const win = state.windows.get(windowId);
    const el = win?.element;
    if (!el || !ops) return;
    if (typeof ops.width === 'number') el.style.width = Math.max(320, ops.width) + 'px';
    if (typeof ops.height === 'number') el.style.height = Math.max(220, ops.height) + 'px';
    if (typeof ops.left === 'number') el.style.left = Math.max(0, ops.left) + 'px';
    if (typeof ops.top === 'number') el.style.top = Math.max(0, ops.top) + 'px';
    if (ops.maximize === true) el.classList.add('maximized');
    if (ops.minimize === true) el.classList.add('minimized');
    if (typeof ops.close_after_ms === 'number' && ops.close_after_ms > 0) {
        setTimeout(() => {
            if (state.windows.has(windowId)) closeWindow(windowId);
        }, ops.close_after_ms);
    }
}

function initDesktopContextMenu() {
    const desktop = document.getElementById('desktop');
    if (!desktop) return;
    desktop.addEventListener('contextmenu', (e) => {
        if (e.target.closest('.desktop-icon') || e.target.closest('.window') || e.target.closest('#taskbar')) return;
        e.preventDefault();
        const existing = document.querySelector('.context-menu');
        if (existing) existing.remove();
        const menu = document.createElement('div');
        menu.className = 'context-menu';
        menu.style.left = e.clientX + 'px';
        menu.style.top = e.clientY + 'px';
        menu.innerHTML = `
            <div class="context-item" onclick="arrangeDesktopIcons();this.parentElement.remove()">🧩 Упорядочить иконки</div>
            <div class="context-item" onclick="dariaTidyDesktop();this.parentElement.remove()">🧹 Навести порядок</div>
            <div class="context-item" onclick="toggleStartMenu();this.parentElement.remove()">🌸 Пуск</div>
            <div class="context-item" onclick="location.reload()">🔄 Обновить рабочий стол</div>
        `;
        document.body.appendChild(menu);
        setTimeout(() => {
            document.addEventListener('click', () => menu.remove(), {once: true});
        }, 10);
    });
}

function arrangeDesktopIcons() {
    const container = document.getElementById('desktop-icons');
    if (!container) return;
    const icons = [...container.querySelectorAll('.desktop-icon')];
    const maxRows = Math.max(4, Math.floor((window.innerHeight - 180) / 108));
    const cols = Math.max(1, Math.ceil(icons.length / maxRows));
    icons.forEach((el, i) => {
        const col = Math.floor(i / maxRows);
        const row = i % maxRows;
        const left = 22 + col * 104;
        const top = 20 + row * 110;
        el.style.position = 'absolute';
        el.style.left = left + 'px';
        el.style.top = top + 'px';
        state.iconPositions[el.dataset.iconId] = {x: left, y: top};
    });
    saveIconPositions();
}

function dariaTidyDesktop() {
    const groups = [
        ['chat', 'self', 'senses', 'knowledge', 'wiki'],
        ['todos', 'calendar', 'files', 'diary', 'memory'],
        ['player', 'daria-games', 'browser'],
        ['settings', 'monitor', 'updater', 'store', 'terminal', 'support'],
    ];
    const elById = {};
    document.querySelectorAll('.desktop-icon').forEach(el => {
        elById[el.dataset.iconId] = el;
    });
    let col = 0;
    groups.forEach((g) => {
        let row = 0;
        g.forEach((id) => {
            const el = elById[id];
            if (!el) return;
            const left = 22 + col * 104;
            const top = 20 + row * 110;
            el.style.position = 'absolute';
            el.style.left = left + 'px';
            el.style.top = top + 'px';
            state.iconPositions[id] = {x: left, y: top};
            row += 1;
        });
        col += 1;
    });
    // Остальные иконки (например, плагины) укладываем после групп.
    let extraCol = col;
    let extraRow = 0;
    Object.values(elById).forEach((el) => {
        const id = el.dataset.iconId;
        if (state.iconPositions[id]) return;
        const left = 22 + extraCol * 104;
        const top = 20 + extraRow * 110;
        el.style.position = 'absolute';
        el.style.left = left + 'px';
        el.style.top = top + 'px';
        state.iconPositions[id] = {x: left, y: top};
        extraRow += 1;
        if (extraRow > 6) {
            extraRow = 0;
            extraCol += 1;
        }
    });
    const now = Date.now();
    state.windows.forEach((win, id) => {
        const ts = Number(win.lastFocusAt || 0);
        if (state.activeWindow !== id && ts && (now - ts > 20 * 60 * 1000) && id !== 'chat') {
            win.element.classList.add('minimized');
        }
    });
    saveIconPositions();
    showNotification({title: '🌸 Даша', message: 'Навела порядок на рабочем столе', type: 'info', icon: '🧹', duration: 3500});
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
        day_routine_mode: document.getElementById('setting-day-routine')?.value || 'realistic',
        icon_pack: document.getElementById('setting-icon-pack')?.value || 'default',
        auto_wallpaper_change: document.getElementById('setting-auto-wallpaper')?.checked ?? false,
        attention_enabled: document.getElementById('setting-attention')?.checked ?? true,
        unrestricted_topics: document.getElementById('setting-unrestricted-topics')?.checked ?? true,
        senses_vision_provider: document.getElementById('setting-vision-provider')?.value || 'auto',
        senses_audio_provider: document.getElementById('setting-audio-provider')?.value || 'auto',
    };
    try {
        await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(settings)});
        state.settings = {...state.settings, ...settings};
        applyTheme(settings.theme);
        applyIconPack(settings.icon_pack || 'default');
        showNotification({title: 'Настройки', message: 'Сохранено!', type: 'success', icon: '✅', duration: 3000});
    } catch (e) {}
}

function applyTheme(theme) { document.body.setAttribute('data-theme', theme); }
function applyCursor(cursor) { document.body.setAttribute('data-cursor', cursor); }
function applyIconPack(pack) {
    state.settings.icon_pack = pack || 'default';
    initDesktopIcons();
}

async function uploadAvatar(file) {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    try {
        const r = await fetch('/api/upload/avatar', {method: 'POST', body: fd});
        const data = await r.json();
        if (data.url) {
            state.settings.avatar = data.url;
            const startAvatar = document.getElementById('start-user-avatar');
            if (startAvatar) {
                startAvatar.src = data.url;
                startAvatar.classList.remove('hidden');
            }
            showNotification({title: 'Аватар', message: 'Загружен!', type: 'success', icon: '👤'});
        }
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

async function loadBuiltinWallpapers() {
    const sel = document.getElementById('setting-wallpaper-builtin');
    if (!sel) return;
    try {
        const r = await fetch('/api/wallpapers/list');
        const data = await r.json();
        const items = data.items || [];
        sel.innerHTML = items.map(i => `<option value="${i.url}">${i.name}</option>`).join('') || '<option value="">(нет)</option>';
    } catch (e) {
        sel.innerHTML = '<option value="">(ошибка)</option>';
    }
}

async function applyBuiltinWallpaper() {
    const sel = document.getElementById('setting-wallpaper-builtin');
    if (!sel || !sel.value) return;
    document.getElementById('desktop').style.backgroundImage = `url(${sel.value})`;
    await fetch('/api/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({wallpaper: sel.value}),
    });
}

async function generateWallpaper() {
    const input = document.getElementById('setting-wallpaper-prompt');
    const prompt = input?.value?.trim() || 'нежные абстрактные обои';
    try {
        const r = await fetch('/api/wallpapers/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({prompt, mode: 'abstract'}),
        });
        const data = await r.json();
        if (data.status === 'ok' && data.url) {
            document.getElementById('desktop').style.backgroundImage = `url(${data.url})`;
            showNotification({title:'Обои', message:'Новые обои созданы', type:'success', icon:'🖼️', duration:2800});
        } else {
            showNotification({title:'Обои', message:data.error || 'Не удалось создать', type:'error', icon:'⚠️', duration:3000});
        }
    } catch (e) {
        showNotification({title:'Обои', message:'Ошибка рисования', type:'error', icon:'⚠️', duration:3000});
    }
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
    const baseConfig = windowConfigs[windowId];
    if (!baseConfig) return;
    const config = {...baseConfig};
    const defaultEntry = defaultIcons.find(x => x.window === windowId);
    if (defaultEntry) config.icon = resolveIcon(defaultEntry.id, config.icon);
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
    windowEl.querySelector('.window-icon').innerHTML = renderIcon(config.icon);
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
        win.lastFocusAt = Date.now();
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
        if (windowId === 'monitor' && dariaMonitorTimer) {
            clearInterval(dariaMonitorTimer);
            dariaMonitorTimer = null;
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
    item.innerHTML = `<span>${renderIcon(config.icon)}</span><span>${config.title}</span>`;
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
    if (windowId === 'chat') {
        loadChatHistory();
        initChatComposer();
    }
    else if (windowId === 'self') loadSelfPerception();
    else if (windowId === 'todos') loadTodoLists();
    else if (windowId === 'senses') initSensesWindow();
    else if (windowId === 'wiki') initWikiWindow();
    else if (windowId === 'calendar') loadCalendar();
    else if (windowId === 'updater') initUpdaterWindow();
    else if (windowId === 'monitor') initDariaMonitorWindow();
    else if (windowId === 'browser') initBrowserWindow();
    else if (windowId === 'settings') initSettingsWindow();
    else if (windowId === 'memory') loadMemoryStats();
    else if (windowId === 'diary') initDiaryWindow();
    else if (windowId === 'store') loadStore();
    else if (windowId === 'logs') initLogs();
    else if (windowId === 'player') initPlayer();
    else if (windowId === 'files') loadFiles();
    else if (windowId === 'knowledge') initKnowledgeInspector();
    else if (windowId === 'daria-games') initDariaGamesWindow();
}

async function initKnowledgeInspector() {
    const input = document.getElementById('knowledge-query');
    if (!input) return;
    if (!input.value.trim()) input.value = 'что такое градиентный спуск';
    input.onkeypress = (e) => { if (e.key === 'Enter') knowledgeSearch(); };
    await knowledgeSearch();
}

async function knowledgeSearch() {
    const input = document.getElementById('knowledge-query');
    const results = document.getElementById('knowledge-results');
    if (!input || !results) return;
    const q = input.value.trim();
    if (!q) {
        results.innerHTML = '<div class="empty">Введите запрос</div>';
        return;
    }
    results.innerHTML = '<div class="loading">Ищу в базе...</div>';
    try {
        const r = await fetch(`/api/knowledge/search?q=${encodeURIComponent(q)}&limit=8`);
        const data = await r.json();
        const items = data.items || [];
        if (!items.length) {
            results.innerHTML = '<div class="empty">Ничего не найдено</div>';
            return;
        }
        results.innerHTML = items.map((it, idx) => {
            const title = escapeHtml(it.title || `Источник ${idx + 1}`);
            const snippet = escapeHtml(it.snippet || '');
            const path = String(it.path || '');
            const m = path.match(/docs[\\/]+wiki[\\/]+([^\\/]+\.md)$/i);
            const openWiki = m ? `<button onclick="knowledgeOpenWiki('${m[1].replace(/'/g, "\\'")}')">Открыть Wiki</button>` : '';
            return `
                <div class="knowledge-item">
                    <div class="knowledge-head"><b>${title}</b><span class="todo-count">${escapeHtml(path)}</span></div>
                    <div class="knowledge-snippet">${snippet}</div>
                    <div class="knowledge-actions">
                        ${openWiki}
                        <button onclick="knowledgeCopySnippet(${idx})">Копировать</button>
                    </div>
                </div>`;
        }).join('');
        state.knowledgeResults = items;
    } catch (e) {
        results.innerHTML = '<div class="empty">Ошибка поиска</div>';
    }
}

function knowledgeOpenWiki(name) {
    openWindow('wiki');
    setTimeout(() => loadWikiPage(name), 120);
}

async function knowledgeCopySnippet(idx) {
    const item = state.knowledgeResults?.[idx];
    if (!item?.snippet) return;
    try {
        await navigator.clipboard.writeText(item.snippet);
        showNotification({title: 'Knowledge', message: 'Фрагмент скопирован', type: 'success', icon: '📋', duration: 2200});
    } catch (e) {}
}

function knowledgeUseInChat() {
    const input = document.getElementById('knowledge-query');
    if (!input) return;
    openWindow('chat');
    setTimeout(() => {
        const ci = document.getElementById('chat-input');
        if (!ci) return;
        ci.value = input.value.trim();
        ci.focus();
    }, 120);
}

async function loadCalendar() {
    const list = document.getElementById('calendar-list');
    if (!list) return;
    list.innerHTML = '<div class="loading">Загрузка...</div>';
    try {
        const r = await fetch('/api/calendar');
        const data = await r.json();
        const items = data.events || [];
        const now = new Date();
        const view = new Date(now.getFullYear(), now.getMonth() + state.calendarMonthShift, 1);
        const y = view.getFullYear();
        const m = view.getMonth();
        const first = new Date(y, m, 1);
        const startOffset = (first.getDay() + 6) % 7;
        const daysInMonth = new Date(y, m + 1, 0).getDate();
        const evByDay = {};
        items.forEach(e => {
            try {
                const d = new Date(e.date);
                if (d.getFullYear() === y && d.getMonth() === m) {
                    const day = d.getDate();
                    evByDay[day] = evByDay[day] || [];
                    evByDay[day].push(e);
                }
            } catch (x) {}
        });
        const holidays = {
            "1-1": "🎉 Новый год",
            "2-14": "💘 День влюблённых",
            "3-8": "🌷 8 Марта",
            "5-1": "🌼 Праздник весны",
            "5-9": "⭐ День Победы",
            "12-31": "🎄 Канун Нового года",
        };
        let html = `<div class="calendar-head">
            <button onclick="shiftCalendarMonth(-1)">←</button>
            <b>${view.toLocaleDateString('ru-RU', {month: 'long', year: 'numeric'})}</b>
            <button onclick="shiftCalendarMonth(1)">→</button>
        </div>
        <div class="calendar-weekdays"><span>Пн</span><span>Вт</span><span>Ср</span><span>Чт</span><span>Пт</span><span>Сб</span><span>Вс</span></div>
        <div class="calendar-grid">`;
        for (let i = 0; i < startOffset; i++) html += `<div class="calendar-cell muted"></div>`;
        for (let d = 1; d <= daysInMonth; d++) {
            const isToday = y === now.getFullYear() && m === now.getMonth() && d === now.getDate();
            const key = `${m+1}-${d}`;
            const holiday = holidays[key] || "";
            const markers = evByDay[d] || [];
            const mark = markers.length ? `<div class="calendar-marker">${markers.length} событ.</div>` : (holiday ? `<div class="calendar-holiday">${holiday}</div>` : "");
            const tip = [...markers.map(x => x.title), holiday].filter(Boolean).join(" • ");
            html += `<div class="calendar-cell ${isToday ? 'today' : ''}" title="${tip.replace(/"/g,'&quot;')}"><div class="calendar-day">${d}</div>${mark}</div>`;
        }
        html += `</div>`;
        const eventList = items
            .map(e => ({...e, _d: new Date(e.date)}))
            .filter(e => !isNaN(e._d.getTime()))
            .sort((a, b) => a._d - b._d)
            .slice(0, 10)
            .map(e => `<div class="todo-item"><label>📌 ${e.title} <span class="todo-count">${e._d.toLocaleDateString('ru-RU')} ${e._d.toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'})}</span></label><button onclick="deleteCalendarEvent('${e.id}')">🗑️</button></div>`)
            .join('');
        list.innerHTML = html + `<div class="todo-group-title">Ближайшие события</div>` + (eventList || '<div class="empty">Пока без событий</div>');
    } catch (e) {
        list.innerHTML = '<div class="empty">Ошибка загрузки</div>';
    }
}

function shiftCalendarMonth(delta) {
    state.calendarMonthShift += delta;
    loadCalendar();
}

async function addCalendarEvent() {
    const title = document.getElementById('calendar-title')?.value?.trim();
    const date = document.getElementById('calendar-date')?.value;
    if (!title || !date) return;
    const r = await fetch('/api/calendar/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title, date: new Date(date).toISOString(), source: 'user'}),
    });
    if (!r.ok) return;
    document.getElementById('calendar-title').value = '';
    loadCalendar();
}

async function deleteCalendarEvent(id) {
    await fetch('/api/calendar/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id}),
    });
    loadCalendar();
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
        ['all', 'local', 'telegram'].forEach(k => {
            document.getElementById(`chat-filter-${k}`)?.classList.toggle('active', state.chatHistoryFilter === k);
        });
        
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
        if (state.chatHistoryFilter !== 'telegram' && localChats.length) {
            html += `<div class="chat-group-title">💬 Личные чаты</div>${renderItems(localChats)}`;
        }
        if (state.chatHistoryFilter !== 'local' && tgChats.length) {
            html += `<div class="chat-group-title">📨 Telegram</div>${renderItems(tgChats)}`;
        }
        container.innerHTML = html || '<p class="empty">Нет истории</p>';
        updateChatTopbar(chats);
    } catch (e) {}
}

function setChatFilter(filter) {
    state.chatHistoryFilter = filter || 'all';
    loadChatHistory();
}

function extractDrawPrompt(text) {
    const src = String(text || '').trim();
    if (!src) return '';
    const m = src.match(/^\s*(?:даша[,:\s-]*)?(?:можешь\s+нарисовать|нарисуй|сделай\s+картинку|сгенерируй\s+картинку|создай\s+картинку|хочу\s+картинку)\s*(.*)$/i);
    const p = (m?.[1] || '').trim().replace(/[.,!?;:]+$/, '');
    if (p) return p;
    return m ? 'нежный портрет в пастельных тонах' : '';
}

function createChatGenerationBadge(prompt, steps = []) {
    const el = addMessage(
        {
            type: 'image_job',
            progress: 0,
            prompt: prompt || '',
            steps: Array.isArray(steps) ? steps : [],
        },
        'assistant',
        'chat-messages',
        {replyText: 'рисование изображения'}
    );
    if (el) {
        el.dataset.generating = '1';
        el.dataset.progress = '0';
        el.dataset.steps = JSON.stringify(Array.isArray(steps) ? steps : []);
    }
    return el;
}

function pickDrawStep(steps, progress) {
    const arr = Array.isArray(steps) ? steps.filter(Boolean) : [];
    if (!arr.length) {
        if (progress < 25) return 'Думаю над идеей рисунка';
        if (progress < 55) return 'Собираю композицию';
        if (progress < 90) return 'Рисую основные детали';
        return 'Дорабатываю финальные штрихи';
    }
    const idx = Math.max(0, Math.min(arr.length - 1, Math.floor((Math.max(0, Math.min(100, progress)) / 100) * arr.length)));
    return String(arr[idx] || arr[arr.length - 1] || '').trim();
}

async function startImageGenerationJob(prompt, chatId, badgeEl, steps = []) {
    const attempts = 4;
    for (let attempt = 1; attempt <= attempts; attempt++) {
        try {
            if (badgeEl) {
                const line = badgeEl.querySelector('.imgjob-line');
                if (line && attempt > 1) {
                    line.textContent = `🎨 Подключаю кисти... попытка ${attempt}/${attempts}`;
                }
            }
            const r = await fetch('/api/images/jobs', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    prompt,
                    style: 'universal',
                    mode: 'model',
                    allow_fallback: false,
                    chat_id: chatId || null,
                    steps: Array.isArray(steps) ? steps : [],
                }),
            });
            let data = {};
            try { data = await r.json(); } catch (_) { data = {}; }
            if (r.ok && data.job_id) {
                const jobId = data.job_id;
                if (badgeEl) badgeEl.dataset.jobId = jobId;
                pollImageJob(jobId, chatId, badgeEl);
                return;
            }
        } catch (_) {
            // retry silently
        }
        if (attempt < attempts) {
            await new Promise(resolve => setTimeout(resolve, 600 * attempt));
            continue;
        }
        if (badgeEl) {
            const line = badgeEl.querySelector('.imgjob-line');
            if (line) line.textContent = '⚠️ Не получилось начать рисование';
        }
    }
}

function pollImageJob(jobId, chatId, badgeEl) {
    if (!jobId) return;
    if (state.imageGenJobs.get(jobId)) {
        clearInterval(state.imageGenJobs.get(jobId));
        state.imageGenJobs.delete(jobId);
    }
    const timer = setInterval(async () => {
        try {
            const r = await fetch(`/api/images/jobs/${encodeURIComponent(jobId)}`);
            if (!r.ok) throw new Error('status');
            const data = await r.json();
            const job = data.job || {};
            const st = String(job.status || '');
            const pr = Number(job.progress || 0);
            let steps = [];
            try { steps = JSON.parse(String(badgeEl?.dataset?.steps || '[]')); } catch (_) {}
            const phaseText = String(job.message || '').trim() || pickDrawStep(steps, pr);
            if (badgeEl) {
                const pct = Math.max(0, Math.min(100, Math.round(pr)));
                badgeEl.dataset.progress = String(pct);
                const bar = badgeEl.querySelector('.imgjob-progress');
                const line = badgeEl.querySelector('.imgjob-line');
                if (bar) bar.style.width = `${pct}%`;
                if (line) {
                    line.textContent = st === 'error'
                        ? `⚠️ Не дорисовала: ${job.error || 'ошибка'}`
                        : `🎨 ${phaseText} • ${pct}%`;
                }
            }
            if (st === 'done' || st === 'error') {
                clearInterval(timer);
                state.imageGenJobs.delete(jobId);
                if (st === 'done') {
                    const url = String(job?.result?.url || '').trim();
                    if (url && badgeEl) {
                        badgeEl.innerHTML = '';
                        badgeEl.classList.add('message-image');
                        const im = document.createElement('img');
                        im.src = url;
                        im.alt = 'generated image';
                        im.style.maxWidth = '320px';
                        im.style.borderRadius = '10px';
                        im.style.border = '1px solid rgba(255,255,255,.15)';
                        badgeEl.appendChild(im);
                    } else {
                        badgeEl?.remove();
                    }
                    if (chatId && chatId === state.currentChatId) {
                        await loadChat(chatId);
                    }
                    loadChatHistory();
                } else {
                    const dashaErr = String(job?.result?.dasha_message || '').trim();
                    if (badgeEl) {
                        badgeEl.classList.remove('message-image-job');
                        const line = badgeEl.querySelector('.imgjob-line');
                        if (line) line.textContent = dashaErr || `⚠️ Не получилось дорисовать: ${job.error || 'ошибка'}`;
                    }
                    if (chatId && chatId === state.currentChatId) {
                        await loadChat(chatId);
                    } else {
                        loadChatHistory();
                    }
                }
            }
        } catch (_) {
            // keep polling; transient network issues should not kill job tracking
        }
    }, 1200);
    state.imageGenJobs.set(jobId, timer);
}

async function loadChat(chatId) {
    state.currentChatId = chatId;
    clearChatReply();
    clearChatAttachment();
    try {
        const r = await fetch(`/api/chats/${chatId}`);
        const chat = await r.json();
        const container = document.getElementById('chat-messages');
        if (!container) return;
        
        container.innerHTML = '';
        (chat.messages || []).forEach(m => {
            const c = String(m.content || '');
            if (c.startsWith('[image]')) {
                const url = c.replace('[image]', '').trim();
                addMessage({type: 'image', url, alt: 'image'}, m.role, 'chat-messages', {replyText: '[изображение]'});
            } else {
                addMessage(m.content, m.role, 'chat-messages');
            }
        });
        updateChatTopbar();
        loadChatHistory();
    } catch (e) {}
}

async function newChat() {
    try {
        const r = await fetch('/api/chats/new', {method: 'POST'});
        const data = await r.json();
        state.currentChatId = data.chat_id;
        document.getElementById('chat-messages').innerHTML = '';
        updateChatTopbar();
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
        updateChatTopbar();
    }
    loadChatHistory();
}

async function deleteCurrentChat() {
    if (!state.currentChatId) return;
    await deleteChat(state.currentChatId);
}

function updateChatTopbar(chats = null) {
    const titleEl = document.getElementById('chat-current-title');
    const delBtn = document.getElementById('chat-current-delete');
    if (!titleEl || !delBtn) return;
    const list = Array.isArray(chats) ? chats : null;
    let current = null;
    if (list && state.currentChatId) {
        current = list.find(x => x.id === state.currentChatId) || null;
    }
    if (!current && state.currentChatId) {
        titleEl.textContent = `Чат: ${state.currentChatId}`;
        delBtn.disabled = false;
        return;
    }
    if (!state.currentChatId) {
        titleEl.textContent = 'Новый чат';
        delBtn.disabled = true;
        return;
    }
    const prefix = (current?.source || 'local') === 'telegram' ? '📨' : '💬';
    titleEl.textContent = `${prefix} ${current?.title || 'Чат'}`;
    delBtn.disabled = false;
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    if (!input) return;
    const content = input.value.trim();
    const attached = state.chatAttachedImage;
    if (!content && !attached) return;
    
    const shown = content || (attached?.kind === 'image' ? '[изображение]' : '[файл]');
    addMessage(shown, 'user', 'chat-messages');
    if (attached?.kind === 'image' && attached?.previewUrl) {
        addMessage({type: 'image', url: attached.previewUrl, alt: attached.name || 'image'}, 'user', 'chat-messages', {replyText: '[изображение]'});
    }
    input.value = '';
    document.getElementById('chat-typing')?.classList.remove('hidden');
    
    let payloadContent = content;
    const chatContainer = document.getElementById('chat-messages');
    const lastAssistant = chatContainer?.querySelector('.message.assistant:last-child');
    const shortReply = content.length < 40;
    if (shortReply && lastAssistant?.dataset?.proactive === '1') {
        payloadContent = `Контекст: ты недавно предложила активность: "${lastAssistant.textContent}".\nОтвет пользователя: ${content}`;
    }
    if (state.chatReplyTo?.text) {
        payloadContent = `Ответ на сообщение: ${state.chatReplyTo.text}\n${payloadContent}`;
    }
    closeStickerPicker();
    closeChatTools();
    clearChatReply();
    clearChatAttachment();

    let genBadge = null;
    try {
        if (attached?.kind === 'file') {
            const uploaded = await uploadChatFile(attached.file);
            if (uploaded?.path) {
                payloadContent = `${payloadContent ? payloadContent + '\n' : ''}Вложение файла: ${uploaded.path}`;
            } else {
                payloadContent = `${payloadContent ? payloadContent + '\n' : ''}Вложение файла: ${attached.name}`;
            }
        }
        const drawPromptFromUser = extractDrawPrompt(content);
        const drawRequested = !!drawPromptFromUser && attached?.kind !== 'image';
        if (drawRequested) {
            genBadge = createChatGenerationBadge(drawPromptFromUser, []);
        }

        const req = attached?.kind === 'image'
            ? fetch('/api/chat', {
                method: 'POST',
                body: (() => {
                    const fd = new FormData();
                    fd.append('content', payloadContent || '');
                    if (state.currentChatId) fd.append('chat_id', state.currentChatId);
                    fd.append('image', attached.file);
                    return fd;
                })(),
            })
            : fetch('/api/chat', {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: payloadContent, chat_id: state.currentChatId})
            });

        const data = await (await req).json();
        document.getElementById('chat-typing')?.classList.add('hidden');
        if (data.chat_id) state.currentChatId = data.chat_id;
        const messages = data.messages || [data.response];
        if (!drawRequested) {
            displaySequentialMessages(messages, 'chat-messages');
        }
        if (drawRequested && data?.draw_request) {
            const prompt = data?.draw_request?.prompt || drawPromptFromUser || content;
            const steps = Array.isArray(data?.draw_request?.steps) ? data.draw_request.steps : [];
            if (genBadge) genBadge.dataset.steps = JSON.stringify(steps);
            await startImageGenerationJob(prompt, state.currentChatId, genBadge, steps);
        } else if (drawRequested) {
            // draw intent was detected by client, but server did not confirm draw flow.
            genBadge?.remove();
            displaySequentialMessages(messages, 'chat-messages');
        } else {
            genBadge?.remove();
        }
        loadChatHistory();
    } catch (_) {
        genBadge?.remove();
        document.getElementById('chat-typing')?.classList.add('hidden');
        addMessage('Ошибка соединения... 💔', 'assistant', 'chat-messages');
    }
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
    state.stickerPickerOpen = false;
}

function closeChatTools() {
    const menu = document.getElementById('chat-tools-menu');
    if (menu) menu.classList.add('hidden');
}

function toggleChatTools(ev) {
    ev?.preventDefault();
    ev?.stopPropagation();
    const menu = document.getElementById('chat-tools-menu');
    if (!menu) return;
    if (menu.classList.contains('hidden')) menu.classList.remove('hidden');
    else menu.classList.add('hidden');
}

function chatToolOpenStickers() {
    closeChatTools();
    toggleStickerPicker();
}

function chatToolPickImage() {
    closeChatTools();
    document.getElementById('chat-attach-image')?.click();
}

function chatToolPickFile() {
    closeChatTools();
    document.getElementById('chat-attach-file')?.click();
}

function chatToolInsertLink() {
    closeChatTools();
    attachChatLink();
}

async function toggleStickerPicker(ev) {
    if (ev) {
        ev.preventDefault();
        ev.stopPropagation();
    }
    const picker = document.getElementById('chat-sticker-picker');
    if (!picker) return;
    if (state.stickerPickerOpen || !picker.classList.contains('hidden')) {
        picker.classList.add('hidden');
        state.stickerPickerOpen = false;
        return;
    }
    const data = await loadStickerCatalog();
    const stickers = data.emoji_stickers || [];
    picker.innerHTML = stickers.length
        ? stickers.map(s => `<button type="button" class="chat-sticker-item" onclick="sendSticker('${s.replace(/'/g, "\\'")}')">${s}</button>`).join('')
        : '<div class="empty">Стикеры недоступны</div>';
    picker.classList.remove('hidden');
    state.stickerPickerOpen = true;
}

function sendSticker(sticker) {
    if (!sticker) return;
    const input = document.getElementById('chat-input');
    if (!input) return;
    input.value = sticker;
    closeStickerPicker();
    sendChatMessage();
}

function initChatComposer() {
    const main = document.querySelector('.chat-main');
    if (!main || main.dataset.enhanced === '1') return;
    main.dataset.enhanced = '1';
    main.addEventListener('dragover', (e) => {
        e.preventDefault();
        main.classList.add('chat-dragover');
    });
    main.addEventListener('dragleave', () => {
        main.classList.remove('chat-dragover');
    });
    main.addEventListener('drop', (e) => {
        e.preventDefault();
        main.classList.remove('chat-dragover');
        const file = e.dataTransfer?.files?.[0];
        if (!file) return;
        if (file.type?.startsWith('image/')) onChatAttachImage(file);
        else onChatAttachAnyFile(file);
    });
}

function onChatAttachImage(file) {
    if (!file) return;
    if (!file.type || !file.type.startsWith('image/')) {
        showNotification({title: 'Чат', message: 'Сейчас можно прикрепить только изображение', type: 'info', icon: '📎', duration: 2600});
        return;
    }
    const previewUrl = URL.createObjectURL(file);
    state.chatAttachedImage = {
        kind: 'image',
        file,
        name: file.name || 'image',
        previewUrl,
    };
    renderChatAttachment();
}

function onChatAttachAnyFile(file) {
    if (!file) return;
    if (file.type?.startsWith('image/')) {
        onChatAttachImage(file);
        return;
    }
    state.chatAttachedImage = {
        kind: 'file',
        file,
        name: file.name || 'file',
        previewUrl: '',
    };
    renderChatAttachment();
}

function attachChatLink() {
    const u = prompt('Вставь ссылку:');
    if (!u) return;
    const input = document.getElementById('chat-input');
    if (!input) return;
    input.value = `${input.value ? input.value + ' ' : ''}${u.trim()}`.trim();
    input.focus();
}

function renderChatAttachment() {
    const box = document.getElementById('chat-attachment-preview');
    if (!box) return;
    const at = state.chatAttachedImage;
    if (!at) {
        box.classList.add('hidden');
        box.innerHTML = '';
        return;
    }
    const img = at.kind === 'image' && at.previewUrl ? `<img src="${at.previewUrl}" alt="attachment">` : '<span>📎 файл</span>';
    box.innerHTML = `<span>Вложение: ${escapeHtml(at.name || 'file')}</span>${img}<button type="button" onclick="clearChatAttachment()">Убрать</button>`;
    box.classList.remove('hidden');
}

function clearChatAttachment() {
    const at = state.chatAttachedImage;
    if (at?.previewUrl) URL.revokeObjectURL(at.previewUrl);
    state.chatAttachedImage = null;
    const input = document.getElementById('chat-attach-image');
    if (input) input.value = '';
    const file = document.getElementById('chat-attach-file');
    if (file) file.value = '';
    renderChatAttachment();
}

async function uploadChatFile(file) {
    if (!file) return null;
    const fd = new FormData();
    fd.append('file', file);
    fd.append('path', 'chat_uploads');
    try {
        const r = await fetch('/api/files/upload', {method: 'POST', body: fd});
        if (!r.ok) return null;
        return {path: `/api/files/download/chat_uploads/${encodeURIComponent(file.name)}`};
    } catch (_) {
        return null;
    }
}

function setChatReply(text) {
    const val = String(text || '').trim();
    if (!val) return;
    state.chatReplyTo = {text: val.slice(0, 600)};
    const box = document.getElementById('chat-reply-context');
    if (!box) return;
    box.innerHTML = `Ответ на: ${escapeHtml(state.chatReplyTo.text)} <button type="button" onclick="clearChatReply()">✖</button>`;
    box.classList.remove('hidden');
}

function clearChatReply() {
    state.chatReplyTo = null;
    const box = document.getElementById('chat-reply-context');
    if (!box) return;
    box.classList.add('hidden');
    box.innerHTML = '';
}

function displaySequentialMessages(messages, containerId, options = {}) {
    if (!messages || messages.length === 0) return;
    
    // First message immediately
    addMessage(messages[0], 'assistant', containerId, options);
    
    // Subsequent messages with delay (simulates typing)
    for (let i = 1; i < messages.length; i++) {
        ((msg, delay) => {
            setTimeout(() => addMessage(msg, 'assistant', containerId, options), delay);
        })(
            messages[i],
            i * (800 + (typeof messages[i] === 'string' ? messages[i].length : 20) * 15)
        );
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
            
            if (behavior.desktop_mischief || behavior.action_type || data.state?.mood) {
                performDesktopMischief(data.state?.mood, behavior);
            }
        } catch (e) {}
    }, 60000); // Check every minute
}

function performDesktopMischief(mood, behavior = {}) {
    if (!state.isMobile && (mood === 'angry' || mood === 'offended' || mood === 'playful' || behavior.desktop_mischief)) {
        const icons = document.querySelectorAll('.desktop-icon');
        if (icons.length > 0) {
            const randomIcon = icons[Math.floor(Math.random() * icons.length)];
            const newX = Math.random() * Math.max(120, window.innerWidth - 220);
            const newY = Math.random() * Math.max(120, window.innerHeight - 240);
            randomIcon.style.position = 'absolute';
            randomIcon.style.left = newX + 'px';
            randomIcon.style.top = newY + 'px';
            randomIcon.style.transition = 'all 0.5s ease';
            setTimeout(() => { randomIcon.style.transition = ''; }, 600);
        }
    }
    dariaWindowChoreography(mood, behavior);
}

function dariaWindowChoreography(mood, behavior = {}) {
    if (state.isMobile || !state.windows || state.windows.size === 0) return;
    const opened = [...state.windows.entries()]
        .filter(([id]) => id !== 'settings')
        .map(([id, win]) => ({id, ...win}));
    if (!opened.length) return;

    const target = opened[Math.floor(Math.random() * opened.length)];
    const el = target.element;
    if (!el) return;
    const areaW = Math.max(340, window.innerWidth - 30);
    const areaH = Math.max(280, window.innerHeight - 110);

    if (mood === 'angry' || mood === 'offended') {
        focusWindow(target.id);
        el.style.transition = 'transform 0.12s ease';
        el.style.transform = 'translateX(-6px)';
        setTimeout(() => { el.style.transform = 'translateX(6px)'; }, 90);
        setTimeout(() => { el.style.transform = ''; el.style.transition = ''; }, 180);
        if (Math.random() < 0.35) {
            const w = Math.min(areaW, Math.max(360, el.offsetWidth + 40));
            const h = Math.min(areaH, Math.max(260, el.offsetHeight + 20));
            const left = Math.max(0, Math.random() * Math.max(20, areaW - w));
            const top = Math.max(0, Math.random() * Math.max(20, areaH - h));
            applyWindowOps(target.id, {width: w, height: h, left, top});
        }
        if (Math.random() < 0.25) {
            const stale = opened.find((w) => w.id !== target.id && w.id !== 'chat');
            if (stale) stale.element.classList.add('minimized');
        }
        return;
    }

    if (mood === 'playful' || mood === 'excited') {
        focusWindow(target.id);
        const w = Math.min(areaW, Math.max(360, Math.round(el.offsetWidth * (0.92 + Math.random() * 0.2))));
        const h = Math.min(areaH, Math.max(250, Math.round(el.offsetHeight * (0.90 + Math.random() * 0.2))));
        const left = Math.max(0, Math.random() * Math.max(10, areaW - w));
        const top = Math.max(0, Math.random() * Math.max(10, areaH - h));
        applyWindowOps(target.id, {width: w, height: h, left, top});
        if (Math.random() < 0.22 && !state.windows.has('daria-games')) {
            openWindow('daria-games');
            setTimeout(() => applyWindowOps('daria-games', {width: 760, height: 560, left: 80, top: 55}), 130);
        }
        return;
    }

    if (mood === 'cozy' || mood === 'tender' || mood === 'affectionate') {
        const cozyTarget = state.windows.get('chat') ? 'chat' : target.id;
        focusWindow(cozyTarget);
        applyWindowOps(cozyTarget, {
            width: Math.min(areaW, 700),
            height: Math.min(areaH, 540),
            left: Math.max(0, (areaW - Math.min(areaW, 700)) * 0.5),
            top: Math.max(0, (areaH - Math.min(areaH, 540)) * 0.32),
        });
        if (Math.random() < 0.18) {
            const stale = opened.find((w) => w.id !== cozyTarget && w.id !== 'chat');
            if (stale && Number(Date.now() - (stale.lastFocusAt || 0)) > 12 * 60 * 1000) {
                closeWindow(stale.id);
            }
        }
        return;
    }

    if (mood === 'bored' && Math.random() < 0.28) {
        const toOpen = Math.random() < 0.5 ? 'player' : 'browser';
        openWindow(toOpen);
        setTimeout(() => {
            applyWindowOps(toOpen, {
                width: toOpen === 'player' ? 860 : 900,
                height: toOpen === 'player' ? 520 : 620,
                left: 40 + Math.random() * 180,
                top: 45 + Math.random() * 120,
            });
        }, 120);
        return;
    }

    if (Math.random() < 0.18) {
        const left = Math.max(0, Math.random() * Math.max(10, areaW - el.offsetWidth));
        const top = Math.max(0, Math.random() * Math.max(10, areaH - el.offsetHeight));
        applyWindowOps(target.id, {left, top});
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
    const payload = content && typeof content === 'object' ? content : null;
    if (payload && payload.type === 'image' && payload.url) {
        msg.classList.add('message-image');
        const im = document.createElement('img');
        im.src = payload.url;
        im.alt = payload.alt || 'image';
        im.style.maxWidth = '320px';
        im.style.borderRadius = '10px';
        im.style.border = '1px solid rgba(255,255,255,.15)';
        msg.appendChild(im);
    } else if (payload && payload.type === 'image_job') {
        msg.classList.add('message-image', 'message-image-job');
        const seedSteps = Array.isArray(payload.steps) ? payload.steps : [];
        const firstStep = (seedSteps[0] || 'Думаю над идеей рисунка').toString();
        const card = document.createElement('div');
        card.className = 'imgjob-card';
        card.innerHTML = `
            <div class="imgjob-preview" aria-label="Рисование изображения"></div>
            <div class="imgjob-line">🎨 ${escapeHtml(firstStep)} • ${Math.max(0, Math.min(100, Number(payload.progress || 0)))}%</div>
            <div class="imgjob-track"><div class="imgjob-progress" style="width: 0%"></div></div>
            <div class="imgjob-prompt">${escapeHtml(payload.prompt || '')}</div>
        `;
        msg.appendChild(card);
    } else {
        const text = String(payload?.content ?? content ?? '');
        msg.textContent = text;
        const emojiOnly = /^(?:[\p{Emoji}\uFE0F\u200D]\s*){1,3}$/u.test(text.trim());
        if (emojiOnly) msg.classList.add('sticker');
        msg.dataset.replyText = text.slice(0, 500);
    }
    if (options.replyText) msg.dataset.replyText = String(options.replyText);
    if (containerId === 'chat-messages') {
        const act = document.createElement('button');
        act.type = 'button';
        act.className = 'message-reply-btn';
        act.textContent = '↩';
        act.title = 'Ответить';
        act.onclick = (e) => {
            e.stopPropagation();
            setChatReply(msg.dataset.replyText || msg.textContent || '[сообщение]');
        };
        msg.appendChild(act);
    }
    if (options.proactive) msg.dataset.proactive = '1';
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    return msg;
}

// ═══════════════════════════════════════════════════════════════
//  Files, Terminal, Browser, Player, etc.
// ═══════════════════════════════════════════════════════════════

function isDiaryProtectedPath(path = '') {
    const clean = String(path || '').replace(/^\/+/, '');
    return clean === 'dasha_notes' || clean.startsWith('dasha_notes/');
}

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
            const allowDelete = !isDiaryProtectedPath(item.path || '');
            const deleteBtn = allowDelete
                ? `<button onclick="deleteFile(decodeURIComponent('${encodedPath}'),event)">🗑️</button>`
                : '';
            html += `<div class="file-item" ondblclick="${item.is_dir ? `loadFiles(decodeURIComponent('${encodedPath}'))` : `openFile(decodeURIComponent('${encodedPath}'))`}">
                <span>${icon}</span><span class="name">${item.name}</span>
                ${deleteBtn}
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
        if (!r.ok) {
            throw new Error(data.error || 'Ошибка чтения файла');
        }
        const isReadOnly = isDiaryProtectedPath(path);
        state.currentFileReadOnly = isReadOnly;
        const contentEl = document.getElementById('file-editor-content');
        const saveBtn = document.getElementById('file-editor-save-btn');
        const assistToggle = document.getElementById('file-assist-toggle');
        const readonlyNote = document.getElementById('file-editor-readonly-note');
        document.getElementById('file-editor-path').value = path;
        if (contentEl) {
            contentEl.value = data.content || '';
            contentEl.readOnly = isReadOnly;
        }
        if (saveBtn) saveBtn.disabled = isReadOnly;
        if (assistToggle) {
            assistToggle.disabled = isReadOnly;
            assistToggle.style.display = isReadOnly ? 'none' : '';
        }
        if (readonlyNote) readonlyNote.classList.toggle('hidden', !isReadOnly);
        state.currentFileExt = data.ext || '';
        const kind = document.getElementById('file-editor-kind');
        if (kind) {
            kind.textContent = `Формат: ${state.currentFileExt || 'text'}${isReadOnly ? ' · только чтение' : ''}`;
        }
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
    } catch (e) {
        showNotification({title: 'Файлы', message: `Не удалось открыть: ${e.message || e}`, type: 'error', icon: '⚠️', duration: 3200});
    }
}

async function saveFile() {
    if (state.currentFileReadOnly) {
        showNotification({title: 'Файл', message: 'Этот дневник ведёт только Даша (режим чтения)', type: 'info', icon: '🔒', duration: 3500});
        return;
    }
    const path = document.getElementById('file-editor-path').value;
    const content = document.getElementById('file-editor-content').value;
    const r = await fetch('/api/files/write', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path, content})});
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
        showNotification({title: 'Файл', message: data.error || 'Не удалось сохранить', type: 'error', icon: '⚠️', duration: 3500});
        return;
    }
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
    if (state.currentFileReadOnly) {
        showNotification({title: 'Файл', message: 'Редактирование дневника пользователем отключено', type: 'info', icon: '🔒', duration: 3200});
        return;
    }
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
    if (isDiaryProtectedPath(state.currentPath || '')) {
        showNotification({title: 'Файлы', message: 'В папке дневника можно только читать', type: 'info', icon: '🔒', duration: 3200});
        return;
    }
    const name = prompt('Имя файла:');
    if (!name) return;
    const path = state.currentPath ? `${state.currentPath}/${name}` : name;
    const r = await fetch('/api/files/write', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path, content: ''})});
    if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showNotification({title: 'Файлы', message: data.error || 'Не удалось создать файл', type: 'error', icon: '⚠️', duration: 3200});
        return;
    }
    loadFiles(state.currentPath);
}

async function createNewFolder() {
    if (isDiaryProtectedPath(state.currentPath || '')) {
        showNotification({title: 'Файлы', message: 'В папке дневника можно только читать', type: 'info', icon: '🔒', duration: 3200});
        return;
    }
    const name = prompt('Имя папки:');
    if (!name) return;
    const path = state.currentPath ? `${state.currentPath}/${name}` : name;
    const r = await fetch('/api/files/mkdir', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path})});
    if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showNotification({title: 'Файлы', message: data.error || 'Не удалось создать папку', type: 'error', icon: '⚠️', duration: 3200});
        return;
    }
    loadFiles(state.currentPath);
}

async function deleteFile(path, e) {
    e?.stopPropagation();
    if (isDiaryProtectedPath(path)) {
        showNotification({title: 'Файлы', message: 'Дневник защищён от изменений', type: 'info', icon: '🔒', duration: 3200});
        return;
    }
    if (!confirm('Удалить?')) return;
    const r = await fetch('/api/files/delete', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({path})});
    if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showNotification({title: 'Файлы', message: data.error || 'Не удалось удалить', type: 'error', icon: '⚠️', duration: 3200});
        return;
    }
    loadFiles(state.currentPath);
}

async function uploadFile(input) {
    if (!input?.files?.[0]) return;
    if (isDiaryProtectedPath(state.currentPath || '')) {
        showNotification({title: 'Файлы', message: 'В папку дневника загрузка отключена', type: 'info', icon: '🔒', duration: 3200});
        input.value = '';
        return;
    }
    const fd = new FormData();
    fd.append('file', input.files[0]);
    fd.append('path', state.currentPath);
    const r = await fetch('/api/files/upload', {method: 'POST', body: fd});
    if (!r.ok) {
        const data = await r.json().catch(() => ({}));
        showNotification({title: 'Файлы', message: data.error || 'Не удалось загрузить файл', type: 'error', icon: '⚠️', duration: 3200});
        return;
    }
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
    if (!/^https?:\/\//i.test(url)) {
        if (url.includes('.') || url.includes('/')) url = 'https://' + url;
        else url = `https://ya.ru/search/?text=${encodeURIComponent(url)}`;
    }
    input.value = url;
    frame.src = `/api/browser/proxy?url=${encodeURIComponent(url)}`;
}
function browserBack() { document.getElementById('browser-frame')?.contentWindow?.history.back(); }
function browserForward() { document.getElementById('browser-frame')?.contentWindow?.history.forward(); }
function initBrowserWindow() {
    const frame = document.getElementById('browser-frame');
    const input = document.getElementById('browser-url');
    if (!frame || !input) return;
    if (!input.value.trim()) frame.src = '/api/browser/start';
}

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
        out += `
            <div class="battle-legend">
                <span><i class="battle-cell cell-unknown"></i> неизвестно</span>
                <span><i class="battle-cell cell-water"></i> вода</span>
                <span><i class="battle-cell cell-ship"></i> корабль</span>
                <span><i class="battle-cell cell-miss"></i> мимо</span>
                <span><i class="battle-cell cell-hit"></i> попадание</span>
            </div>`;
        out += `<div class="battle-meta">Ход: ${s.battleship.turn_owner || '—'}</div>`;
        if (s.winner) out += `<div class="battle-meta">Победитель: ${s.winner}</div>`;
        if (s.reward) out += `<div class="battle-meta">Награда: ${s.reward}</div>`;
        return out;
    }
    if (s.mode === 'connect4' && s.connect4?.board) {
        const b = s.connect4.board;
        let out = `<div class="connect4-wrap"><div class="connect4-grid">`;
        for (let r = 0; r < b.length; r++) {
            for (let c = 0; c < b[r].length; c++) {
                const v = b[r][c];
                const cls = v === 1 ? 'c4-dasha' : (v === 2 ? 'c4-opponent' : 'c4-empty');
                out += `<div class="connect4-cell ${cls}" title="Колонка ${c + 1}"></div>`;
            }
        }
        out += `</div></div>`;
        out += `<div class="battle-meta">Ход: ${s.connect4.turn_owner || '—'}</div>`;
        out += `<div class="battle-legend"><span><i class="connect4-cell c4-dasha"></i> Даша</span><span><i class="connect4-cell c4-opponent"></i> соперник</span></div>`;
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
    state.playerQueue = state.playerQueue || [];
    state.playerIndex = Number.isInteger(state.playerIndex) ? state.playerIndex : -1;
    loadPlayerQueueFromServer();
    if (state.audio) {
        state.audio.addEventListener('timeupdate', () => {
            const p = document.getElementById('player-progress');
            if (p) p.style.width = (state.audio.currentTime / state.audio.duration * 100) + '%';
            document.getElementById('player-current').textContent = formatTime(state.audio.currentTime);
            document.getElementById('player-duration').textContent = formatTime(state.audio.duration);
        });
        state.audio.addEventListener('loadedmetadata', () => {
            const dur = state.audio.duration;
            if (!isNaN(dur)) {
                document.getElementById('player-duration').textContent = formatTime(dur);
                if (state.playerIndex >= 0 && state.playerQueue?.[state.playerIndex]) {
                    state.playerQueue[state.playerIndex].duration_sec = Math.round(dur);
                    persistPlayerQueue();
                    renderPlayerQueue();
                }
            }
        });
        state.audio.addEventListener('error', () => {
            const cur = (state.playerQueue || [])[state.playerIndex];
            showNotification({
                title: 'Музыка',
                message: `Не удалось воспроизвести: ${cur?.title || 'трек'}`,
                type: 'error',
                icon: '⚠️',
                duration: 4000
            });
        });
        state.audio.addEventListener('ended', () => { state.audioPlaying = false; updatePlayBtn(); playerNext(); });
    }
    renderPlayerQueue();
}

function formatTime(s) { return isNaN(s) ? '0:00' : `${Math.floor(s/60)}:${Math.floor(s%60).toString().padStart(2,'0')}`; }
async function playerLoad(files) {
    if(!files?.[0]) return;
    const file = files[0];
    const fd = new FormData();
    fd.append('file', file);
    try {
        const r = await fetch('/api/music/upload', {method: 'POST', body: fd});
        const data = await r.json();
        if (r.ok && data.status === 'ok') {
            enqueueTrack({
                title: data.title || file.name,
                source: 'local-file',
                play_url: data.play_url || '',
                open_url: '',
                cover: '/static/favicon.svg',
                duration_sec: data.duration_sec || 0,
            }, true);
            return;
        }
    } catch (_) {}
    const url = URL.createObjectURL(file);
    enqueueTrack({
        title: file.name,
        source: 'local-file-temp',
        play_url: url,
        open_url: '',
        cover: '/static/favicon.svg',
    }, true);
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
function playerPrev() {
    if (!state.playerQueue || !state.playerQueue.length) return;
    if (state.audio && state.audio.currentTime > 4) {
        state.audio.currentTime = 0;
        return;
    }
    const next = Math.max(0, state.playerIndex - 1);
    playTrackAt(next);
}
function playerNext() {
    if (!state.playerQueue || !state.playerQueue.length) return;
    const next = state.playerIndex + 1;
    if (next < state.playerQueue.length) playTrackAt(next);
}

function playerSeek(ev) {
    if (!state.audio) return;
    const bar = ev.currentTarget;
    const rect = bar.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (ev.clientX - rect.left) / Math.max(1, rect.width)));
    if (!isNaN(state.audio.duration)) state.audio.currentTime = ratio * state.audio.duration;
}

function enqueueTrack(track, playNow = false) {
    state.playerQueue = state.playerQueue || [];
    state.playerQueue.push(track);
    persistPlayerQueue();
    if (playNow || state.playerIndex < 0) {
        playTrackAt(state.playerQueue.length - 1);
    } else {
        renderPlayerQueue();
    }
}

function renderPlayerQueue() {
    const box = document.getElementById('player-queue');
    if (!box) return;
    const queue = state.playerQueue || [];
    if (!queue.length) {
        box.innerHTML = '<div class="empty">Очередь пуста</div>';
        return;
    }
    box.innerHTML = queue.map((t, i) => `
        <div class="player-track ${i === state.playerIndex ? 'active' : ''}" onclick="playTrackAt(${i})">
            <div class="name">${escapeHtml(t.title || 'Без названия')}</div>
            <div class="meta">${escapeHtml(t.source || '')}${t.duration_sec ? ` · ${formatTime(t.duration_sec)}` : ''}${t.open_url ? ` · <button type="button" onclick="openTrackSource(${i}, event)">открыть</button>` : ''}</div>
        </div>
    `).join('');
}

function openTrackSource(index, ev) {
    ev?.stopPropagation();
    const t = (state.playerQueue || [])[index];
    if (!t?.open_url) return;
    openWindow('browser');
    setTimeout(() => {
        const input = document.getElementById('browser-url');
        if (!input) return;
        input.value = t.open_url;
        browserGo();
    }, 80);
}

async function playTrackAt(index) {
    const queue = state.playerQueue || [];
    if (!queue[index] || !state.audio) return;
    state.playerIndex = index;
    const t = queue[index];
    const titleEl = document.querySelector('.player-title');
    const artistEl = document.querySelector('.player-artist');
    const cover = document.getElementById('player-cover-img');
    if (titleEl) titleEl.textContent = t.title || 'Без названия';
    if (artistEl) artistEl.textContent = t.source || '';
    if (cover) cover.src = t.cover || '/static/favicon.svg';
    document.getElementById('player-current').textContent = '0:00';
    document.getElementById('player-duration').textContent = t.duration_sec ? formatTime(t.duration_sec) : '0:00';
    const prog = document.getElementById('player-progress');
    if (prog) prog.style.width = '0%';
    persistPlayerQueue();

    if (!t.play_url) {
        showNotification({
            title:'Музыка',
            message:'Источник добавлен в очередь. Прямой аудиопоток недоступен для встроенного плеера.',
            type:'info',
            icon:'🎵',
            duration:4200
        });
        renderPlayerQueue();
        return;
    }
    state.audio.src = t.play_url;
    state.audio.load();
    await playerPlay();
    fetch('/api/music/listen', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({title: t.title || 'track', source: t.source || 'queue'}),
    }).catch(()=>{});
    renderPlayerQueue();
}

async function playerAddSource() {
    const input = document.getElementById('music-title-input');
    const value = input?.value?.trim();
    if (!value) return;
    try {
        const r = await fetch('/api/music/resolve', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({value, cache: true}),
        });
        const data = await r.json();
        if (data.status === 'ok') {
            enqueueTrack({
                title: data.title || value,
                source: data.source || 'internet',
                play_url: data.play_url || '',
                open_url: data.open_url || '',
                cover: data.cover || '/static/favicon.svg',
                duration_sec: data.duration_sec || 0,
            }, true);
            input.value = '';
        } else {
            enqueueTrack({
                title: value,
                source: 'external-link',
                play_url: '',
                open_url: data.open_url || value,
                cover: '/static/favicon.svg',
            }, true);
            showNotification({title:'Музыка', message:data.reason || data.error || 'Прямое воспроизведение недоступно', type:'info', icon:'🎵', duration:4200});
        }
    } catch (e) {
        showNotification({title:'Музыка', message:'Не удалось добавить источник', type:'error', icon:'⚠️', duration:3500});
    }
}

async function loadPlayerQueueFromServer() {
    try {
        const r = await fetch('/api/music/queue');
        if (!r.ok) return;
        const data = await r.json();
        state.playerQueue = Array.isArray(data.queue) ? data.queue : [];
        state.playerIndex = Math.min(Math.max(Number(state.playerIndex) || 0, 0), Math.max(0, state.playerQueue.length - 1));
        renderPlayerQueue();
    } catch (_) {}
}

async function persistPlayerQueue() {
    try {
        const queue = (state.playerQueue || []).filter(t => !(String(t.play_url || '').startsWith('blob:')));
        await fetch('/api/music/queue', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({queue}),
        });
    } catch (_) {}
}

async function dashaListenTrack() {
    const current = (state.playerQueue || [])[state.playerIndex];
    const title = current?.title || '';
    if (!title) return;
    try {
        const r = await fetch('/api/music/listen', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title, source: current?.source || 'manual'}),
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
        } else {
            throw new Error(data.error || 'Ошибка');
        }
    } catch (e) {
        showNotification({title: '🎵', message: `Не удалось: ${e.message || e}`, type: 'error', icon: '⚠️', duration: 4500});
    }
}

async function initDiaryWindow() {
    await loadDiaryEntries();
}

async function loadDiaryEntries(fileName = '') {
    const box = document.getElementById('diary-entries');
    const fileLabel = document.getElementById('diary-current-file');
    if (box) box.innerHTML = '<div class="loading">Открываю книжку дневника...</div>';
    try {
        const q = fileName ? `?file=${encodeURIComponent(fileName)}` : '';
        const r = await fetch(`/api/diary${q}`);
        const data = await r.json();
        if (fileLabel) {
            const bookName = String(data.file || '').trim() || 'daria_diary_book.md';
            fileLabel.textContent = `Книга: ${bookName}`;
        }
        const entries = Array.isArray(data.entries) ? data.entries : [];
        if (!box) return;
        box.dataset.path = data.path || '';
        if (!entries.length) {
            box.innerHTML = '<div class="empty">Пока нет записей. Даша добавит их автоматически.</div>';
            return;
        }
        let html = '';
        let currentDate = '';
        entries.forEach((e) => {
            const dateLabel = String(e.date || '').trim();
            if (dateLabel && dateLabel !== currentDate) {
                currentDate = dateLabel;
                html += `<div class="diary-day-divider">${escapeHtml(dateLabel)}</div>`;
            }
            const title = String(e.title || '').trim() || 'Запись';
            const text = escapeHtml(String(e.text || '')).replace(/\n/g, '<br>');
            html += `
                <article class="diary-page-entry">
                    <div class="diary-entry-meta">${escapeHtml(title)}</div>
                    <p class="diary-entry-text">${text}</p>
                </article>
            `;
        });
        box.innerHTML = html;
        box.scrollTop = box.scrollHeight;
    } catch (e) {
        if (fileLabel) fileLabel.textContent = 'Книга: ошибка загрузки';
        if (box) box.innerHTML = '<div class="empty">Не удалось загрузить книгу дневника</div>';
    }
}

async function saveDiaryEntry() {
    showNotification({
        title: 'Дневник',
        message: 'Дневник ведёт только Даша. Для тебя доступно чтение.',
        type: 'info',
        icon: '🔒',
        duration: 3400,
    });
}

function openDiaryFileInFiles() {
    const box = document.getElementById('diary-entries');
    const rel = String(box?.dataset?.path || '').trim();
    if (!rel) return;
    openWindow('files');
    setTimeout(() => openFile(rel), 120);
}

async function initLogs() {
    const output = document.getElementById('logs-output');
    if (output) {
        output.innerHTML = '<div class="empty">Режим отладки перенесён в терминал. Запуск: `python3 main.py --debug --debug-trace`</div>';
    }
}
async function refreshLogs() {
    await initLogs();
}
function renderDebugRuntime(debug, output) {
    if (!debug || debug.status !== 'ok') return;
    const p = debug.process || {};
    const plugins = Array.isArray(debug.plugins) ? debug.plugins : [];
    const threads = Array.isArray(debug.threads) ? debug.threads : [];
    const errs = Array.isArray(debug.errors_last) ? debug.errors_last : [];
    const warns = Array.isArray(debug.warnings_last) ? debug.warnings_last : [];
    const reqs = Array.isArray(debug.requests_last) ? debug.requests_last : [];
    const jobs = Array.isArray(debug.image_jobs_last) ? debug.image_jobs_last : [];
    const models = debug.models || {};
    const pluginLine = plugins.map(x => `${x.name}:${x.loaded ? 'loaded' : 'off'}`).join(' | ') || 'нет';
    const threadLine = threads.slice(0, 8).map(x => `${x.name}${x.alive ? '' : '(dead)'}`).join(', ');
    output.innerHTML += `
        <div class="log INFO">[DBG] PID=${p.pid || '-'} uptime=${Math.floor((p.uptime_sec || 0)/60)}m python=${p.python || '-'}</div>
        <div class="log INFO">[DBG] plugins: ${escapeHtml(pluginLine)}</div>
        <div class="log INFO">[DBG] threads(${threads.length}): ${escapeHtml(threadLine || 'нет')}</div>
        <div class="log INFO">[DBG] models: chat=${escapeHtml(models.chat_llm || '-')} vision=${escapeHtml(models.vision || '-')} asr=${escapeHtml(models.audio_asr || '-')} img=${escapeHtml(models.image_gen || '-')}</div>
        <div class="log INFO">[DBG] image_jobs(${jobs.length}): ${escapeHtml(jobs.slice(0,5).map(j => `${j.id}:${j.status}:${Math.round(j.progress || 0)}%`).join(' | ') || 'нет')}</div>
        <div class="log WARNING">[DBG] warnings=${warns.length} errors=${errs.length}</div>
    `;
    reqs.slice(-15).forEach(r => {
        output.innerHTML += `<div class="log INFO">[TRACE] ${escapeHtml(r.message || '')}</div>`;
    });
    errs.slice(-5).forEach(e => {
        output.innerHTML += `<div class="log ERROR">[ERR] ${escapeHtml(e.message || '')}</div>`;
    });
}
function appendLog(log) {
    const output = document.getElementById('logs-output');
    const filter = document.getElementById('logs-filter')?.value;
    if(filter!=='all' && log.level!==filter) return;
    output.innerHTML += `<div class="log ${log.level}">[${log.timestamp?.split('T')[1]?.substring(0,8)}] ${log.level} | ${log.message}</div>`;
    if(document.getElementById('logs-autoscroll')?.checked) output.scrollTop = output.scrollHeight;
}
function filterLogs() { refreshLogs(); }

let dariaMonitorTimer = null;
async function initDariaMonitorWindow() {
    const out = document.getElementById('daria-monitor-output');
    if (!out) return;
    if (dariaMonitorTimer) clearInterval(dariaMonitorTimer);
    const load = async () => {
        try {
            const r = await fetch('/api/daria/metrics');
            const d = await r.json();
            out.innerHTML = `
                <div class="todo-item"><label>CPU процесса</label><span class="todo-count">${d.cpu_percent ?? 0}%</span></div>
                <div class="todo-item"><label>RAM процесса</label><span class="todo-count">${d.rss_mb ?? 0} MB</span></div>
                <div class="todo-item"><label>Потоков</label><span class="todo-count">${d.threads ?? 0}</span></div>
                <div class="todo-item"><label>Открытых окон</label><span class="todo-count">${state.windows.size}</span></div>
                <div class="todo-item"><label>Открытых файлов</label><span class="todo-count">${d.open_files ?? 0}</span></div>
                <div class="todo-item"><label>Аптайм</label><span class="todo-count">${Math.floor((d.uptime_sec || 0) / 60)} мин</span></div>
            `;
        } catch (e) {
            out.innerHTML = '<div class="empty">Ошибка мониторинга</div>';
        }
    };
    await load();
    dariaMonitorTimer = setInterval(load, 3000);
}

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
        if (document.getElementById('setting-icon-pack')) {
            document.getElementById('setting-icon-pack').value = settings.icon_pack || 'default';
        }
        if (document.getElementById('setting-auto-wallpaper')) {
            document.getElementById('setting-auto-wallpaper').checked = settings.auto_wallpaper_change === true;
        }
        if (document.getElementById('setting-day-routine')) {
            document.getElementById('setting-day-routine').value = settings.day_routine_mode || 'realistic';
        }
        if (document.getElementById('setting-attention')) {
            document.getElementById('setting-attention').checked = settings.attention_enabled !== false;
        }
        if (document.getElementById('setting-unrestricted-topics')) {
            document.getElementById('setting-unrestricted-topics').checked = settings.unrestricted_topics !== false;
        }
        if (document.getElementById('setting-vision-provider')) {
            document.getElementById('setting-vision-provider').value = settings.senses_vision_provider || 'auto';
        }
        if (document.getElementById('setting-audio-provider')) {
            document.getElementById('setting-audio-provider').value = settings.senses_audio_provider || 'auto';
        }
        
        // Обновляем локальный state
        state.settings = settings;
        state.attentionEnabled = settings.attention_enabled !== false;
        
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
    await loadBuiltinWallpapers();
    
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
        const concerns = data.concerns || [];
        const needs = data.needs || [];
        const followups = data.followups || [];
        const moodLine = `${state.mood_emoji || '🌸'} ${state.mood_label || 'спокойна'}`;
        box.innerHTML = `
            <div class="self-grid">
                <section class="self-card">
                    <h3>${data.self_name || 'Даша'} сейчас</h3>
                    <p><b>${moodLine}</b></p>
                    <p>Энергия: ${Math.round((state.energy || 0.7) * 100)}% · Тепло: ${Math.round((state.warmth || 0.5) * 100)}%</p>
                    <p>Нагрузка: ${Math.round((state.stress || 0.2) * 100)}% · Потребность в общении: ${Math.round((state.social_need || 0.5) * 100)}%</p>
                </section>
                <section class="self-card">
                    <h3>Что во мне откликается</h3>
                    <ul>${traits.map(t => `<li>${t}</li>`).join('')}</ul>
                </section>
                <section class="self-card">
                    <h3>Переживания и страхи</h3>
                    <ul>${concerns.length ? concerns.map(t => `<li>${t}</li>`).join('') : '<li>Сейчас всё спокойно</li>'}</ul>
                </section>
                <section class="self-card">
                    <h3>Что мне сейчас нужно</h3>
                    <ul>${needs.length ? needs.map(t => `<li>${t}</li>`).join('') : '<li>Тихий, живой контакт</li>'}</ul>
                </section>
                <section class="self-card self-instruction-card">
                    <h3>Ядро самоощущения</h3>
                    <p class="self-note">Это текст, через который Даша осмысляет себя и своё поведение. Можно мягко настроить под ваш стиль.</p>
                    <textarea id="self-instruction-input" class="self-instruction-input" placeholder="Опиши характер Даши..."></textarea>
                    <div class="self-actions">
                        <button class="btn-primary" onclick="saveSelfInstruction()">💾 Сохранить</button>
                        <button onclick="loadSelfInstruction()">↻ Обновить</button>
                    </div>
                    <div id="self-instruction-info" class="self-note"></div>
                </section>
                <section class="self-card">
                    <h3>О чём я хочу не забыть</h3>
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
    const openHtml = open.map(t => {
        let plan = '';
        if (t.scheduled_for) {
            try { plan = ` • ${new Date(t.scheduled_for).toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'})}`; } catch (e) {}
        }
        const dur = t.duration_min ? ` • ~${t.duration_min} мин` : '';
        const icon = t.status === 'in_progress' ? '⏳' : '📝';
        return `
        <div class="todo-item">
            <label><input type="checkbox" onchange="toggleTask('${t.id}', true)"> ${icon} ${t.title}<span class="todo-count">${plan}${dur}</span></label>
            <button onclick="deleteTask('${t.id}')">🗑️</button>
        </div>
    `;
    }).join('');
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
        state.stickerPickerOpen = false;
    }
    const tools = document.getElementById('chat-tools-menu');
    if (tools && !tools.classList.contains('hidden') && !tools.contains(e.target) && !toggle) {
        tools.classList.add('hidden');
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
