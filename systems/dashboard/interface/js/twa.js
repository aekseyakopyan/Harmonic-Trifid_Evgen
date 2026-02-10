// TWA Dashboard Logic
const API_URL = '/api';
const tg = window.Telegram ? window.Telegram.WebApp : null;

// Global Error Handler for Mobile Debugging
window.onerror = function (msg, url, line) {
    const errorBox = document.createElement('div');
    errorBox.style.cssText = 'position:fixed;top:0;left:0;right:0;background:rgba(200,0,0,0.9);color:white;padding:10px;z-index:9999;font-size:12px;font-family:monospace;pointer-events:none;';
    errorBox.textContent = `JS Error: ${msg} (line ${line})`;
    document.body.appendChild(errorBox);
    return false;
};

// State
let currentView = 'dashboard';
let parserRefreshInterval = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    try {
        if (tg) {
            tg.expand();
            tg.ready();

            // Apply theme colors
            document.body.style.setProperty('--tg-bg-color', tg.backgroundColor || '#0f172a');
            document.body.style.setProperty('--tg-secondary-bg-color', tg.secondaryBackgroundColor || '#1e293b');
            document.body.style.setProperty('--tg-text-color', tg.textColor || '#f1f5f9');
            document.body.style.setProperty('--tg-hint-color', tg.hintColor || '#94a3b8');

            if (tg.colorScheme === 'light') {
                document.body.classList.add('light-theme');
            }
        }

        initializeNavigation();
        loadDashboard(); // Load initial view
        checkAPIStatus();
    } catch (e) {
        console.error("Init error:", e);
        alert("Init Error: " + e.message);
    }
});

// Navigation
function initializeNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const view = item.dataset.view;
            switchView(view);
        });
    });
}

function switchView(view) {
    if (currentView === view) return;

    // Update UI
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === view);
    });

    document.querySelectorAll('.view').forEach(v => {
        v.classList.toggle('active', v.id === `${view}-view`);
    });

    currentView = view;

    // Stop intervals
    if (parserRefreshInterval) {
        clearInterval(parserRefreshInterval);
        parserRefreshInterval = null;
    }

    // Load data
    switch (view) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'leads':
            loadLeads();
            break;
        case 'parser':
            loadParser();
            break;
    }

    // Impact feedback if available
    if (tg && tg.HapticFeedback) {
        tg.HapticFeedback.impactOccurred('light');
    }
}

// API Helpers
async function apiFetch(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, options);
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`Fetch error (${endpoint}):`, error);
        throw error;
    }
}

// Dashboard
async function loadDashboard() {
    try {
        // Load Metrics
        const metrics = await apiFetch('/dashboard/metrics');
        if (metrics) {
            document.getElementById('total-leads').textContent = metrics.total_leads ?? '0';
            document.getElementById('active-dialogues').textContent = metrics.active_dialogues ?? '0';
            document.getElementById('total-messages').textContent = metrics.total_messages ?? '0';
            document.getElementById('messages-today').textContent = metrics.messages_today ?? '0';
        }

        // Load Activity
        const activity = await apiFetch('/dashboard/recent-activity');
        const container = document.getElementById('recent-activity');

        if (Array.isArray(activity) && activity.length > 0) {
            container.innerHTML = activity.slice(0, 5).map(msg => {
                const content = msg.content || '(no text)';
                const directionSymbol = msg.direction === 'incoming' ? '📥' : '📤';
                const directionText = msg.direction === 'incoming' ? 'Клиент' : 'Алексей';

                return `
                <div class="list-item">
                    <div class="item-main">
                        <span class="item-title">${directionSymbol} ${directionText}</span>
                        <span class="item-subtitle">${content.substring(0, 40)}${content.length > 40 ? '...' : ''}</span>
                    </div>
                    <span class="item-subtitle">${formatTime(msg.created_at)}</span>
                </div>
                `;
            }).join('');
        } else {
            container.innerHTML = '<p style="text-align:center; color:var(--tg-hint-color); padding: 10px;">Нет активности</p>';
        }
    } catch (error) {
        console.error('Dash load fail:', error);
        const container = document.getElementById('recent-activity');
        if (container) {
            container.innerHTML = `<p style="color:red; text-align:center;">Ошибка: ${error.message}</p>`;
        }
    }
}

// Leads
async function loadLeads(search = '') {
    try {
        const leads = await apiFetch(`/leads/?search=${encodeURIComponent(search)}`);
        const container = document.getElementById('leads-list');

        if (Array.isArray(leads) && leads.length > 0) {
            container.innerHTML = leads.map(lead => `
                <div class="list-item" onclick="viewLeadHistory(${lead.id})">
                    <div class="item-main">
                        <span class="item-title">${lead.full_name || lead.telegram_id}</span>
                        <span class="item-subtitle">@${lead.username || 'unknown'}</span>
                    </div>
                    <div style="text-align: right">
                        <span class="item-badge ${lead.lead_score > 5 ? 'badge-high' : 'badge-low'}">${lead.lead_score || 0} pts</span>
                        <div class="item-subtitle" style="margin-top:4px">${formatTime(lead.last_interaction)}</div>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="text-align:center; color:var(--tg-hint-color); padding: 20px;">Лидов не найдено</p>';
        }

        // Setup search listener once
        const searchInput = document.getElementById('leads-search');
        if (searchInput && !searchInput.dataset.listener) {
            searchInput.dataset.listener = 'true';
            searchInput.addEventListener('input', (e) => {
                loadLeads(e.target.value);
            });
        }
    } catch (error) {
        console.error('Leads load fail:', error);
        document.getElementById('leads-list').innerHTML = `<p style="color:red; text-align:center;">Ошибка: ${error.message}</p>`;
    }
}

async function viewLeadHistory(leadId) {
    try {
        const data = await apiFetch(`/leads/${leadId}/history`);
        const modal = document.getElementById('lead-modal');

        document.getElementById('modal-lead-name').textContent = data.lead.full_name || data.lead.telegram_id;
        document.getElementById('modal-lead-info').textContent = `@${data.lead.username || 'unknown'} | Score: ${data.lead.lead_score}`;

        const container = document.getElementById('modal-messages');
        if (data.messages && data.messages.length > 0) {
            container.innerHTML = data.messages.map(msg => `
                <div class="history-msg ${msg.direction}">
                    <div>${msg.content}</div>
                    <div class="msg-time">${formatTimeShort(msg.created_at)}</div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<p style="text-align:center; padding:20px;">История пуста</p>';
        }

        modal.classList.add('active');

        // Haptic
        if (tg && tg.HapticFeedback) tg.HapticFeedback.selectionChanged();

    } catch (error) {
        console.error('History load fail:', error);
        alert("Не удалось загрузить историю: " + error.message);
    }
}

// Parser
async function loadParser() {
    await updateParserStatus();
    if (!parserRefreshInterval) {
        parserRefreshInterval = setInterval(updateParserStatus, 5000);
    }

    const btn = document.getElementById('parser-toggle-btn');
    if (btn && !btn.dataset.listener) {
        btn.dataset.listener = 'true';
        btn.addEventListener('click', toggleParser);
    }
}

async function updateParserStatus() {
    try {
        const data = await apiFetch('/parser/status');

        // UI Update
        const label = document.getElementById('parser-status-label');
        const pill = document.getElementById('parser-pill');
        const pillText = document.getElementById('parser-pill-text');
        const btn = document.getElementById('parser-toggle-btn');

        if (label) label.textContent = data.enabled ? (data.running ? 'Парсер запущен' : 'Ожидание цикла') : 'Парсер остановлен';
        if (document.getElementById('parser-current-activity'))
            document.getElementById('parser-current-activity').textContent = data.current_activity;

        if (pill) {
            pill.className = 'status-pill ' + (data.enabled ? 'status-online' : 'status-offline');
        }
        if (pillText) pillText.textContent = data.enabled ? 'ACTIVE' : 'OFF';

        if (btn) {
            btn.textContent = data.enabled ? 'ОСТАНОВИТЬ' : 'ЗАПУСТИТЬ';
            btn.className = 'btn ' + (data.enabled ? 'btn-danger' : 'btn-primary');
        }

        if (document.getElementById('parser-vacancies-found'))
            document.getElementById('parser-vacancies-found').textContent = data.stats.vacancies_found_today;
        if (document.getElementById('parser-responses-sent'))
            document.getElementById('parser-responses-sent').textContent = data.stats.responses_sent_today;

        const vacancyContainer = document.getElementById('recent-vacancies');
        if (vacancyContainer) {
            if (data.recent_vacancies && data.recent_vacancies.length > 0) {
                vacancyContainer.innerHTML = data.recent_vacancies.slice(0, 10).map(v => `
                    <div class="list-item">
                        <div class="item-main" style="width: 70%">
                            <span class="item-title" style="font-size:13px">${(v.content || '').substring(0, 60)}...</span>
                            <span class="vacancy-badge badge-${v.intent || 'general'}">${v.category || v.intent || 'Вакансия'}</span>
                        </div>
                        <span class="item-subtitle">${formatTimeShort(v.found_at)}</span>
                    </div>
                `).join('');
            } else {
                vacancyContainer.innerHTML = '<p style="text-align:center; color:var(--tg-hint-color); padding: 10px;">Вакансий пока нет</p>';
            }
        }

    } catch (error) {
        console.error('Parser status fail:', error);
    }
}

async function toggleParser() {
    const btn = document.getElementById('parser-toggle-btn');
    const isEnabled = btn.classList.contains('btn-danger'); // Dangerous means it's running

    btn.disabled = true;
    if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred(isEnabled ? 'warning' : 'success');

    try {
        await apiFetch('/parser/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: !isEnabled })
        });
        await updateParserStatus();
    } catch (error) {
        console.error('Toggle fail:', error);
        alert("Ошибка переключения: " + error.message);
    } finally {
        btn.disabled = false;
    }
}

// Utils
function formatTime(ds) {
    if (!ds) return '--';
    try {
        const d = new Date(ds);
        if (isNaN(d.getTime())) return 'Invalid Date';

        const now = new Date();
        const diff = (now - d) / 1000;

        if (diff < 60) return 'только что';
        if (diff < 3600) return Math.floor(diff / 60) + ' мин назад';
        if (diff < 86400) return Math.floor(diff / 3600) + ' ч назад';
        return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
    } catch (e) {
        return ds;
    }
}

function formatTimeShort(ds) {
    if (!ds) return '--';
    try {
        const d = new Date(ds);
        if (isNaN(d.getTime())) return '--';
        return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return '--';
    }
}

async function checkAPIStatus() {
    try {
        const data = await apiFetch('/health');
        const pill = document.getElementById('api-status-pill');
        const text = document.getElementById('api-status-text');

        if (data.status === 'ok') {
            if (pill) pill.className = 'status-pill status-online';
            if (text) text.textContent = 'ОНЛАЙН';
        } else {
            if (pill) pill.className = 'status-pill status-offline';
            if (text) text.textContent = 'ОШИБКА';
        }
    } catch (e) {
        const pill = document.getElementById('api-status-pill');
        if (pill) pill.className = 'status-pill status-offline';
        const text = document.getElementById('api-status-text');
        if (text) text.textContent = 'ОФФЛАЙН';
    }
}

// Modal Close logic
const modal = document.getElementById('lead-modal');
if (modal) {
    modal.addEventListener('click', (e) => {
        if (e.target.id === 'lead-modal') {
            modal.classList.remove('active');
        }
    });
}

// Telegram Main Button
if (tg) {
    tg.MainButton.setText('ОБНОВИТЬ');
    tg.MainButton.onClick(() => {
        if (currentView === 'dashboard') loadDashboard();
        if (currentView === 'leads') loadLeads();
        if (currentView === 'parser') updateParserStatus();
    });
    tg.MainButton.show();
}
