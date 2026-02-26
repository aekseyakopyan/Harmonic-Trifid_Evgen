// API Base URL
const API_URL = '/api';

// API fetch wrapper for consistent endpoint handling 
async function apiFetch(endpoint, options = {}) {
    const url = `${API_URL}${endpoint}`;
    return fetch(url, options);
}

// Current view state
let currentView = 'dashboard';
let allLeads = [];
let dashboardRefreshInterval = null;
let systemStatusInterval = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeNavigation();
    checkAPIStatus();
    loadDashboard();
    // Start system status polling every 15 seconds
    loadSystemStatus();
    systemStatusInterval = setInterval(loadSystemStatus, 15000);
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
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === view);
    });

    // Update active view
    document.querySelectorAll('.view').forEach(viewEl => {
        viewEl.classList.toggle('active', viewEl.id === `${view}-view`);
    });

    currentView = view;

    // Load view data
    switch (view) {
        case 'dashboard':
            loadDashboard();
            // Auto-refresh dashboard every 30 seconds when active
            if (dashboardRefreshInterval) clearInterval(dashboardRefreshInterval);
            dashboardRefreshInterval = setInterval(() => {
                if (currentView === 'dashboard') loadDashboard();
            }, 30000);
            break;
        case 'leads':
            loadLeads();
            break;
        case 'cases':
            loadCases();
            break;
        case 'services':
            loadServices();
            break;
        case 'parser':
            loadParser();
            break;
        case 'settings':
            loadSettings();
            break;
    }
}

// API Status Check
async function checkAPIStatus() {
    try {
        const response = await apiFetch('/health');
        const data = await response.json();
        document.getElementById('api-status').textContent = data.status === 'ok' ? 'Онлайн' : 'Оффлайн';
    } catch (error) {
        document.getElementById('api-status').textContent = 'Оффлайн';
        console.error('API connection error:', error);
    }
}

// Dashboard
async function loadDashboard() {
    try {
        // Load metrics
        const metricsResponse = await apiFetch('/dashboard/metrics');
        const metrics = await metricsResponse.json();

        document.getElementById('total-leads').textContent = metrics.total_leads;
        document.getElementById('active-dialogues').textContent = metrics.active_dialogues;
        document.getElementById('total-messages').textContent = metrics.total_messages;
        document.getElementById('messages-today').textContent = metrics.messages_today;

        // Load recent activity
        const activityResponse = await apiFetch('/dashboard/recent-activity');
        const activity = await activityResponse.json();

        const activityContainer = document.getElementById('recent-activity');
        activityContainer.innerHTML = activity.map(msg => `
            <div class="activity-item ${msg.direction}">
                <div class="activity-header">
                    <span class="activity-direction">${msg.direction === 'incoming' ? '📥 Входящее' : '📤 Исходящее'}</span>
                    <span class="activity-time">${formatDate(msg.created_at)}</span>
                </div>
                <div class="activity-content">${msg.content}</div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Leads
async function loadLeads(search = '') {
    try {
        const response = await apiFetch(`/leads/?search=${search}`);
        allLeads = await response.json();

        const leadsTable = document.getElementById('leads-table');
        leadsTable.innerHTML = `
            <div class="table-row header">
                <div>Telegram ID</div>
                <div>Имя / Username</div>
                <div>Lead Score</div>
                <div>Последнее взаимодействие</div>
            </div>
            ${allLeads.map(lead => `
                <div class="table-row" onclick="viewLeadHistory(${lead.id})">
                    <div>${lead.telegram_id}</div>
                    <div>
                        <strong>${lead.full_name || 'N/A'}</strong><br>
                        <span style="color: var(--text-muted)">@${lead.username || 'unknown'}</span>
                    </div>
                    <div>${lead.lead_score || 0}</div>
                    <div>${formatDate(lead.last_interaction)}</div>
                </div>
            `).join('')}
        `;

        // Search input
        document.getElementById('leads-search').addEventListener('input', (e) => {
            loadLeads(e.target.value);
        });
    } catch (error) {
        console.error('Error loading leads:', error);
    }
}

async function viewLeadHistory(leadId) {
    try {
        const response = await apiFetch(`/leads/${leadId}/history`);
        const data = await response.json();

        const modal = document.getElementById('lead-modal');
        document.getElementById('modal-lead-name').textContent = `${data.lead.full_name} (@${data.lead.username})`;

        const messagesContainer = document.getElementById('modal-messages');
        messagesContainer.innerHTML = data.messages.map(msg => `
            <div class="message-item ${msg.direction}">
                <div class="message-header">
                    <span class="message-direction">${msg.direction === 'incoming' ? '📥 Клиент' : '📤 Алексей'}</span>
                    <span class="message-time">${formatDate(msg.created_at)}</span>
                </div>
                <div class="message-content">${msg.content}</div>
                ${msg.intent ? `<div style="margin-top: 0.5rem; color: var(--text-muted); font-size: 0.75rem;">Intent: ${msg.intent} | Category: ${msg.category || 'N/A'}</div>` : ''}
            </div>
        `).join('');

        modal.classList.add('active');
    } catch (error) {
        console.error('Error loading lead history:', error);
    }
}

// Modal close
document.querySelector('.modal-close').addEventListener('click', () => {
    document.getElementById('lead-modal').classList.remove('active');
});

document.getElementById('lead-modal').addEventListener('click', (e) => {
    if (e.target.id === 'lead-modal') {
        e.target.classList.remove('active');
    }
});

// Cases
async function loadCases() {
    try {
        const response = await apiFetch('/cases/');
        const cases = await response.json();

        const casesGrid = document.getElementById('cases-grid');
        casesGrid.innerHTML = cases.map(c => `
            <div class="case-card">
                ${c.image_url ? `<img src="${c.image_url}" class="case-image" alt="${c.title}">` : '<div class="case-image"></div>'}
                <div class="case-content">
                    <span class="case-category">${c.category}</span>
                    <h4 class="case-title">${c.title}</h4>
                    <p class="case-description">${c.description.substring(0, 120)}...</p>
                    <div style="color: var(--success); font-size: 0.875rem; margin-bottom: 1rem;">
                        ✅ ${c.results}
                    </div>
                    <div class="case-actions">
                        <button class="btn-secondary" onclick="editCase(${c.id})">✏️ Изменить</button>
                        <button class="btn-danger" onclick="deleteCase(${c.id})">🗑️ Удалить</button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading cases:', error);
    }
}

function editCase(id) {
    alert('Функция редактирования в разработке. ID: ' + id);
}

async function deleteCase(id) {
    if (!confirm('Вы уверены, что хотите деактивировать этот кейс?')) return;

    try {
        await apiFetch(`/cases/${id}`, { method: 'DELETE' });
        loadCases();
    } catch (error) {
        console.error('Error deleting case:', error);
    }
}

document.getElementById('add-case-btn').addEventListener('click', () => {
    alert('Функция добавления кейса в разработке');
});

// Services
async function loadServices() {
    try {
        const [servicesResponse, casesResponse] = await Promise.all([
            apiFetch('/services/'),
            apiFetch('/cases/')
        ]);

        const services = await servicesResponse.json();
        const allCases = await casesResponse.json();

        const servicesAccordion = document.getElementById('services-accordion');
        servicesAccordion.innerHTML = services.map(service => {
            const serviceCases = allCases.filter(c =>
                c.category.toLowerCase().includes(service.name.toLowerCase()) ||
                service.name.toLowerCase().includes(c.category.toLowerCase())
            );

            return `
                <div class="service-item" data-service-id="${service.id}">
                    <div class="service-header" onclick="toggleService(${service.id})">
                        <h3>${service.name}</h3>
                        <span class="service-toggle">▼</span>
                    </div>
                    <div class="service-content">
                        <div class="service-details">
                            <div class="service-description">
                                <label><strong>Описание услуги</strong> (используется AI для ответов)</label>
                                <textarea id="service-desc-${service.id}">${service.description}</textarea>
                            </div>
                            
                            <div class="service-meta">
                                <div class="service-meta-item">
                                    <label>Примерная стоимость</label>
                                    <input type="text" id="service-price-${service.id}" value="${service.price_range}">
                                </div>
                                <div class="service-meta-item">
                                    <label>Сроки выполнения</label>
                                    <input type="text" id="service-timeline-${service.id}" value="${service.timeline}">
                                </div>
                            </div>
                            
                            <div class="service-actions">
                                <button class="btn-primary" onclick="saveService(${service.id})">💾 Сохранить изменения</button>
                            </div>
                            
                            <div class="service-cases">
                                <h4>📊 Кейсы по направлению "${service.name}" (${serviceCases.length})</h4>
                                <div class="service-cases-grid">
                                    ${serviceCases.map(c => `
                                        <div class="case-card">
                                            ${c.image_url ? `<img src="${c.image_url}" class="case-image" alt="${c.title}" style="height: 120px;">` : '<div class="case-image" style="height: 120px;"></div>'}
                                            <div class="case-content">
                                                <h4 class="case-title" style="font-size: 1rem;">${c.title}</h4>
                                                <p class="case-description" style="font-size: 0.75rem;">${c.description.substring(0, 80)}...</p>
                                                <div style="color: var(--success); font-size: 0.75rem;">
                                                    ✅ ${c.results.substring(0, 60)}...
                                                </div>
                                            </div>
                                        </div>
                                    `).join('') || '<p style="color: var(--text-muted)">Нет кейсов для этого направления</p>'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading services:', error);
    }
}

function toggleService(serviceId) {
    const serviceItem = document.querySelector(`[data-service-id\="${serviceId}"]`);
    serviceItem.classList.toggle('expanded');
}

async function saveService(serviceId) {
    try {
        const description = document.getElementById(`service-desc-${serviceId}`).value;
        const price_range = document.getElementById(`service-price-${serviceId}`).value;
        const timeline = document.getElementById(`service-timeline-${serviceId}`).value;

        await apiFetch(`/services/${serviceId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description, price_range, timeline })
        });

        alert('✅ Изменения сохранены!');
    } catch (error) {
        console.error('Error saving service:', error);
        alert('❌ Ошибка при сохранении');
    }
}

// Settings
async function loadSettings() {
    try {
        // Load System Prompt
        const promptResponse = await apiFetch('/settings/prompt');
        const promptData = await promptResponse.json();
        document.getElementById('system-prompt').value = promptData.prompt;

        // Load Outreach Settings
        const outreachResponse = await apiFetch('/settings/outreach');
        const outreachData = await outreachResponse.json();

        document.getElementById('outreach-enabled').checked = outreachData.enabled;
        document.getElementById('outreach-test-mode').checked = outreachData.test_mode;
        document.getElementById('outreach-test-chat-id').value = outreachData.test_chat_id || '';

        // Add save listener
        const saveBtn = document.getElementById('save-outreach-settings');
        // Remove existing listener if any
        const newSaveBtn = saveBtn.cloneNode(true);
        saveBtn.parentNode.replaceChild(newSaveBtn, saveBtn);

        newSaveBtn.addEventListener('click', saveOutreachSettings);

    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveOutreachSettings() {
    const statusEl = document.getElementById('outreach-save-status');
    const enabled = document.getElementById('outreach-enabled').checked;
    const testMode = document.getElementById('outreach-test-mode').checked;
    const testChatId = document.getElementById('outreach-test-chat-id').value;

    statusEl.textContent = 'Сохранение...';
    statusEl.className = 'save-status';

    try {
        const response = await apiFetch('/settings/outreach', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                enabled: enabled,
                test_mode: testMode,
                test_chat_id: testChatId ? parseInt(testChatId) : null
            })
        });

        if (response.ok) {
            statusEl.textContent = '✅ Настройки сохранены! Перезапустите бота в терминале для применения.';
            statusEl.classList.add('success');
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        statusEl.textContent = '❌ Ошибка при сохранении';
        statusEl.classList.add('error');
        console.error('Error saving outreach settings:', error);
    }
}

// Utility Functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'только что';
    if (diffMins < 60) return `${diffMins} мин назад`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)} ч назад`;

    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ===================================
// SYSTEM STATUS
// ===================================

async function loadSystemStatus() {
    try {
        const response = await apiFetch('/system/status');
        if (!response.ok) return;
        const data = await response.json();

        const processMap = {
            alexey: { dot: 'proc-alexey-dot', text: 'proc-alexey-text' },
            gwen:   { dot: 'proc-gwen-dot',   text: 'proc-gwen-text' },
            parser: { dot: 'proc-parser-dot',  text: 'proc-parser-text' },
            miniapp:{ dot: 'proc-miniapp-dot', text: 'proc-miniapp-text' },
        };

        for (const [name, ids] of Object.entries(processMap)) {
            const running = data[name] === 'running';
            const dotEl = document.getElementById(ids.dot);
            const textEl = document.getElementById(ids.text);
            if (dotEl) dotEl.textContent = running ? '🟢' : '🔴';
            if (textEl) {
                textEl.textContent = running ? 'Запущен' : 'Остановлен';
                textEl.className = 'proc-status ' + (running ? 'running' : 'stopped');
            }
        }
    } catch (error) {
        // Silently ignore — server may be unreachable
    }
}

// ===================================
// PARSER FUNCTIONS
// ===================================

let parserRefreshInterval = null;

async function loadParser() {
    // Clear any existing interval
    if (parserRefreshInterval) {
        clearInterval(parserRefreshInterval);
    }

    // Load initial data
    await updateParserStatus();

    // Setup auto-refresh every 5 seconds
    parserRefreshInterval = setInterval(updateParserStatus, 5000);

    // Setup emergency button listener
    const toggleBtn = document.getElementById('parser-toggle-btn');
    if (toggleBtn && !toggleBtn.hasAttribute('data-listener')) {
        toggleBtn.setAttribute('data-listener', 'true');
        toggleBtn.addEventListener('click', toggleParser);
    }
}

async function updateParserStatus() {
    try {
        const response = await apiFetch('/parser/status');
        const data = await response.json();

        // Update status indicator
        const indicator = document.getElementById('parser-status-indicator');
        indicator.className = '';
        indicator.classList.add(data.status);

        // Update status text
        const statusText = document.getElementById('parser-status-text');
        statusText.textContent = data.enabled ?
            (data.running ? 'Активен' : 'Тестовый режим') :
            'Выключен';

        // Update current activity
        document.getElementById('parser-current-activity').textContent = data.current_activity;

        // Update toggle button
        const toggleBtn = document.getElementById('parser-toggle-btn');
        if (data.enabled) {
            toggleBtn.textContent = 'ОСТАНОВИТЬ';
            toggleBtn.classList.remove('enabled');
        } else {
            toggleBtn.textContent = 'ЗАПУСТИТЬ';
            toggleBtn.classList.add('enabled');
        }

        // Update metrics
        document.getElementById('parser-vacancies-found').textContent = data.stats.vacancies_found_today;
        document.getElementById('parser-responses-sent').textContent = data.stats.responses_sent_today;
        document.getElementById('parser-vacancies-review').textContent = data.stats.vacancies_needs_review;
        document.getElementById('parser-success-rate').textContent = data.stats.success_rate + '%';

        const lastRun = data.stats.last_run ?
            new Date(data.stats.last_run).toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }) :
            'Никогда';
        document.getElementById('parser-last-run').textContent = lastRun;

        // Update tables
        updateVacanciesTable(data.recent_vacancies);
        await updateProcessingTable();

    } catch (error) {
        console.error('Failed to load parser status:', error);
        document.getElementById('parser-status-text').textContent = 'Ошибка загрузки';
    }
}

async function toggleParser() {
    const toggleBtn = document.getElementById('parser-toggle-btn');
    const isEnabled = !toggleBtn.classList.contains('enabled');

    toggleBtn.disabled = true;

    try {
        const response = await apiFetch('/parser/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled: !isEnabled })
        });

        const data = await response.json();

        if (data.success) {
            // Show notification
            showNotification(data.message, 'success');
            // Immediately update status
            await updateParserStatus();
        }

    } catch (error) {
        console.error('Failed to toggle parser:', error);
        showNotification('Ошибка при переключении парсера', 'error');
    } finally {
        toggleBtn.disabled = false;
    }
}

function updateVacanciesTable(vacancies) {
    const container = document.getElementById('recent-vacancies-container');

    if (!vacancies || vacancies.length === 0) {
        container.innerHTML = '<p class="note">📭 Пока нет найденных вакансий</p>';
        return;
    }

    let tableHTML = `
        <table class="vacancy-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Содержимое</th>
                    <th>Категория</th>
                    <th>Время</th>
                </tr>
            </thead>
            <tbody>
    `;

    vacancies.forEach((v, idx) => {
        const timeAgo = getTimeAgo(new Date(v.found_at));
        const badgeClass = v.intent === 'outreach' ? 'outreach' : v.category || 'general';

        tableHTML += `
            <tr>
                <td>${idx + 1}</td>
                <td>${v.content}</td>
                <td><span class="vacancy-badge ${badgeClass}">${v.category || v.intent || 'general'}</span></td>
                <td>${timeAgo}</td>
            </tr>
        `;
    });

    tableHTML += '</tbody></table>';
    container.innerHTML = tableHTML;
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'только что';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} мин назад`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} ч назад`;
    return `${Math.floor(seconds / 86400)} дн назад`;
}

async function updateProcessingTable() {
    const container = document.getElementById('processing-vacancies-container');

    try {
        const response = await apiFetch('/parser/processing');
        const processing = await response.json();

        if (!processing || processing.length === 0) {
            container.innerHTML = '<p class="note">📭 Нет лидов на верификации</p>';
            return;
        }

        let tableHTML = `
            <table class="vacancy-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Направление</th>
                        <th>Содержимое</th>
                        <th>Информативность</th>
                        <th>Время</th>
                        <th>Действие</th>
                    </tr>
                </thead>
                <tbody>
        `;

        processing.forEach((p, idx) => {
            const timeAgo = getTimeAgo(new Date(p.found_at));

            tableHTML += `
                <tr id="vacancy-row-${p.id}">
                    <td>${idx + 1}</td>
                    <td><span class="vacancy-badge general">${p.direction}</span></td>
                    <td>${p.content}</td>
                    <td><strong>${p.informativeness}</strong></td>
                    <td>${timeAgo}</td>
                    <td>
                        <button class="btn-approve" onclick="approveVacancy(${p.id})">✅</button>
                        <button class="btn-reject" onclick="rejectVacancy(${p.id})">❌</button>
                    </td>
                </tr>
            `;
        });

        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;
    } catch (error) {
        console.error('Failed to update processing table:', error);
    }
}

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    alert(message);
}

// ===================================
// VACANCY APPROVE / REJECT
// ===================================

async function approveVacancy(vacancyId) {
    try {
        const response = await apiFetch(`/parser/approve/${vacancyId}`, { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            const row = document.getElementById(`vacancy-row-${vacancyId}`);
            if (row) row.remove();
        }
    } catch (error) {
        console.error('Error approving vacancy:', error);
    }
}

async function rejectVacancy(vacancyId) {
    try {
        const response = await apiFetch(`/parser/reject/${vacancyId}`, { method: 'POST' });
        const data = await response.json();
        if (data.success) {
            const row = document.getElementById(`vacancy-row-${vacancyId}`);
            if (row) row.remove();
        }
    } catch (error) {
        console.error('Error rejecting vacancy:', error);
    }
}

// ===================================
// SYSTEM PROMPT SAVE
// ===================================

document.addEventListener('DOMContentLoaded', () => {
    const savePromptBtn = document.getElementById('save-prompt-btn');
    if (savePromptBtn) {
        savePromptBtn.addEventListener('click', saveSystemPrompt);
    }
});

async function saveSystemPrompt() {
    const statusEl = document.getElementById('prompt-save-status');
    const prompt = document.getElementById('system-prompt').value;

    statusEl.textContent = 'Сохранение...';
    statusEl.className = 'save-status';

    try {
        const response = await apiFetch('/settings/prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        if (response.ok) {
            statusEl.textContent = '✅ Промпт сохранён';
            statusEl.classList.add('success');
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        statusEl.textContent = '❌ Ошибка при сохранении';
        statusEl.classList.add('error');
        console.error('Error saving prompt:', error);
    }
}
