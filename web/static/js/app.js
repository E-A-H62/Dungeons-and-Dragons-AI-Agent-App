// D&D Dungeon Manager - JavaScript Application

const API_BASE = '/api';

// State management
let currentDungeon = null;
let currentRoom = null;
let currentCategory = null;
let currentItemData = null; // Store current item data for editing

// Utility Functions
function showLoading() {
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    toast.innerHTML = `
        <span style="flex: 1;">${message}</span>
        <button class="toast-close" aria-label="Close" style="background: none; border: none; color: var(--text-secondary); cursor: pointer; font-size: 18px; padding: 0; margin-left: 12px; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 4px; transition: all 0.2s ease;">&times;</button>
    `;
    
    // Add click handler to close button
    const closeButton = toast.querySelector('.toast-close');
    closeButton.addEventListener('click', () => {
        toast.style.animation = 'toastSlideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    });
    
    // Add hover effect to close button
    closeButton.addEventListener('mouseenter', () => {
        closeButton.style.background = 'var(--bg-secondary)';
        closeButton.style.color = 'var(--text-primary)';
    });
    closeButton.addEventListener('mouseleave', () => {
        closeButton.style.background = 'none';
        closeButton.style.color = 'var(--text-secondary)';
    });
    
    container.appendChild(toast);
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('active');
    });
}

// Authentication Functions
let isAuthenticated = false;
let currentUsername = null;

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/auth/check`, {
            credentials: 'include'
        });
        const data = await response.json();
        if (data.authenticated) {
            isAuthenticated = true;
            currentUsername = data.username;
            updateAuthUI();
            return true;
        } else {
            isAuthenticated = false;
            currentUsername = null;
            updateAuthUI();
            // Redirect to login page instead of showing modal
            window.location.href = '/login';
            return false;
        }
    } catch (error) {
        console.error('Auth check error:', error);
        // Redirect to login page instead of showing modal
        window.location.href = '/login';
        return false;
    }
}

function updateAuthUI() {
    const userInfo = document.getElementById('user-info');
    const usernameDisplay = document.getElementById('username-display');
    
    if (isAuthenticated && currentUsername) {
        userInfo.style.display = 'flex';
        usernameDisplay.textContent = `Welcome, ${currentUsername}`;
    } else {
        userInfo.style.display = 'none';
    }
}

async function login(username, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            isAuthenticated = true;
            currentUsername = data.username;
            updateAuthUI();
            // Redirect to main page (this function is only used if login modal is still present)
            window.location.href = '/';
            return true;
        } else {
            showToast(data.message || 'Login failed', 'error');
            return false;
        }
    } catch (error) {
        showToast('Login failed: ' + error.message, 'error');
        return false;
    }
}

async function register(username, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            isAuthenticated = true;
            currentUsername = data.username;
            updateAuthUI();
            // Redirect to main page (this function is only used if register modal is still present)
            window.location.href = '/';
            return true;
        } else {
            showToast(data.message || 'Registration failed', 'error');
            return false;
        }
    } catch (error) {
        showToast('Registration failed: ' + error.message, 'error');
        return false;
    }
}

async function logout() {
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
        isAuthenticated = false;
        currentUsername = null;
        updateAuthUI();
        // Redirect to login page
        window.location.href = '/login';
    } catch (error) {
        showToast('Logout failed: ' + error.message, 'error');
        // Still redirect to login page
        window.location.href = '/login';
    }
}

// API Functions
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            credentials: 'include',
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            if (response.status === 401) {
                // Not authenticated, redirect to login page
                isAuthenticated = false;
                updateAuthUI();
                window.location.href = '/login';
            }
            throw new Error(data.message || 'An error occurred');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Dungeon Functions
async function loadDungeons() {
    try {
        showLoading();
        const data = await apiCall('/dungeons');
        renderDungeons(data.dungeons);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderDungeons(dungeons) {
    const container = document.getElementById('dungeons-list');
    
    // Update title and show create button
    updateDungeonsViewTitle(null);
    
    if (dungeons.length === 0) {
        container.innerHTML = `
            <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <p style="font-size: 1.2em; color: var(--secondary-brown);">
                    No dungeons yet. Create your first dungeon to get started!
                </p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = dungeons.map(dungeon => `
        <div class="card" data-dungeon="${dungeon.name}">
            <div class="card-header">
                <div>
                    <div class="card-title">${escapeHtml(dungeon.name)}</div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-small btn-secondary" onclick="editDungeon('${escapeHtml(dungeon.name)}', ${dungeon.summary ? `'${escapeHtml(dungeon.summary)}'` : 'null'})" title="Edit">
                        ✎
                    </button>
                    <button class="btn btn-small btn-danger" onclick="deleteDungeonConfirm('${escapeHtml(dungeon.name)}')" title="Delete">
                        ×
                    </button>
                </div>
            </div>
            <div class="card-body">
                ${dungeon.summary && dungeon.summary.trim() ? `<p style="color: var(--text-secondary);">${escapeHtml(dungeon.summary)}</p>` : ''}
            </div>
            <div class="card-footer">
                <button class="btn btn-primary btn-small" onclick="loadDungeonDetails('${escapeHtml(dungeon.name)}')">
                    View Details
                </button>
                <button class="btn btn-secondary btn-small" onclick="createRoom('${escapeHtml(dungeon.name)}')">
                    Add Room
                </button>
            </div>
        </div>
    `).join('');
}

async function createDungeon(name, summary, existsOk) {
    try {
        showLoading();
        await apiCall('/dungeons', {
            method: 'POST',
            body: JSON.stringify({ name, summary, exists_ok: existsOk })
        });
        showToast('Dungeon created successfully!', 'success');
        hideModal('create-dungeon-modal');
        document.getElementById('create-dungeon-form').reset();
        await loadDungeons();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function editDungeon(oldName, currentSummary) {
    document.getElementById('edit-dungeon-old-name').value = oldName;
    document.getElementById('edit-dungeon-name').value = oldName;
    const summaryField = document.getElementById('edit-dungeon-summary');
    summaryField.value = currentSummary || '';
    summaryField.setAttribute('data-original', currentSummary || '');
    showModal('edit-dungeon-modal');
}

async function updateDungeonSubmit() {
    const oldName = document.getElementById('edit-dungeon-old-name').value;
    const newName = document.getElementById('edit-dungeon-name').value.trim();
    const summaryField = document.getElementById('edit-dungeon-summary');
    const summary = summaryField.value.trim();
    const originalSummary = summaryField.getAttribute('data-original') || '';
    
    const patch = {};
    let hasChanges = false;
    
    if (newName && newName !== oldName) {
        patch.name = newName;
        hasChanges = true;
    }
    
    if (summary !== originalSummary) {
        patch.summary = summary || null;
        hasChanges = true;
    }
    
    if (!hasChanges) {
        showToast('At least one field must be updated. No changes detected.', 'error');
        return;
    }
    
    try {
        showLoading();
        await apiCall(`/dungeons/${encodeURIComponent(oldName)}`, {
            method: 'PATCH',
            body: JSON.stringify({ patch })
        });
        showToast('Dungeon updated successfully!', 'success');
        hideModal('edit-dungeon-modal');
        document.getElementById('edit-dungeon-form').reset();
        await loadDungeons();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function deleteDungeonConfirm(name) {
    // Show confirmation modal
    document.getElementById('confirm-title').textContent = 'Delete Dungeon';
    document.getElementById('confirm-message').textContent = `Are you sure you want to delete the dungeon "${name}"?`;
    document.getElementById('confirm-token').value = '';
    document.getElementById('confirm-token').focus();
    
    // Store the delete function to call on confirmation
    const confirmModal = document.getElementById('confirm-modal');
    const confirmYesBtn = document.getElementById('confirm-yes');
    const confirmTokenInput = document.getElementById('confirm-token');
    
    // Remove any existing event listeners by cloning and replacing
    const newConfirmYesBtn = confirmYesBtn.cloneNode(true);
    confirmYesBtn.parentNode.replaceChild(newConfirmYesBtn, confirmYesBtn);
    
    newConfirmYesBtn.addEventListener('click', async () => {
        const token = confirmTokenInput.value.trim();
        if (token !== 'DELETE') {
            showToast('Please type "DELETE" to confirm deletion', 'error');
            confirmTokenInput.focus();
            return;
        }
        
        const confirmToken = `DELETE:/${name}`;
        hideModal('confirm-modal');
        
        try {
            showLoading();
            await apiCall(`/dungeons/${encodeURIComponent(name)}?token=${encodeURIComponent(confirmToken)}`, {
                method: 'DELETE'
            });
            showToast('Dungeon deleted successfully!', 'success');
            await loadDungeons();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    });
    
    // Handle Enter key in token input
    confirmTokenInput.onkeypress = (e) => {
        if (e.key === 'Enter') {
            newConfirmYesBtn.click();
        }
    };
    
    showModal('confirm-modal');
}

async function loadDungeonDetails(dungeonName) {
    currentDungeon = dungeonName;
    currentRoom = null;
    currentCategory = null;
    
    try {
        showLoading();
        const [roomsData, statData] = await Promise.all([
            apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms`),
            apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/stat`)
        ]);
        
        renderDungeonDetails(dungeonName, roomsData.rooms, statData.stat);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderDungeonDetails(dungeonName, rooms, stat) {
    const container = document.getElementById('dungeons-list');
    
    // Update title and hide create button
    updateDungeonsViewTitle(dungeonName);
    
    container.innerHTML = `
        <div class="card" style="grid-column: 1 / -1; margin-bottom: 20px;">
            <div class="card-header">
                <div>
                    <div class="card-title">${escapeHtml(dungeonName)}</div>
                    <div style="margin-top: 10px;">
                        <button class="btn btn-secondary btn-small" onclick="loadDungeons()">
                            ← Back to Dungeons
                        </button>
                    </div>
                </div>
            </div>
        </div>
        ${rooms.length === 0 ? `
            <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <p style="font-size: 1.2em; color: var(--secondary-brown);">
                    No rooms in this dungeon yet. Create your first room!
                </p>
                <button class="btn btn-primary" onclick="createRoom('${escapeHtml(dungeonName)}')" style="margin-top: 20px;">
                    Create Room
                </button>
            </div>
        ` : rooms.map(room => `
            <div class="card" data-room="${room.name}">
                <div class="card-header">
                    <div>
                        <div class="card-title">${escapeHtml(room.name)}</div>
                    </div>
                    <div class="card-actions">
                        <button class="btn btn-small btn-secondary" onclick="editRoom('${escapeHtml(dungeonName)}', '${escapeHtml(room.name)}', ${room.summary ? `'${escapeHtml(room.summary)}'` : 'null'})" title="Edit">
                            ✎
                        </button>
                        <button class="btn btn-small btn-danger" onclick="deleteRoomConfirm('${escapeHtml(dungeonName)}', '${escapeHtml(room.name)}')" title="Delete">
                            ×
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    ${room.summary && room.summary.trim() ? `<p style="color: var(--text-secondary);">${escapeHtml(room.summary)}</p>` : ''}
                </div>
                <div class="card-footer">
                    <button class="btn btn-primary btn-small" onclick="loadRoomDetails('${escapeHtml(dungeonName)}', '${escapeHtml(room.name)}')">
                        View Details
                    </button>
                    <button class="btn btn-secondary btn-small" onclick="createItem('${escapeHtml(dungeonName)}', '${escapeHtml(room.name)}')">
                        Add Item
                    </button>
                </div>
            </div>
        `).join('')}
    `;
}

// Room Functions
function createRoom(dungeonName) {
    document.getElementById('room-dungeon-name').value = dungeonName;
    showModal('create-room-modal');
}

async function createRoomSubmit(dungeonName, name, summary) {
    try {
        showLoading();
        await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms`, {
            method: 'POST',
            body: JSON.stringify({ name, summary })
        });
        showToast('Room created successfully!', 'success');
        hideModal('create-room-modal');
        document.getElementById('create-room-form').reset();
        await loadDungeonDetails(dungeonName);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function editRoom(dungeonName, oldName, currentSummary) {
    document.getElementById('edit-room-dungeon-name').value = dungeonName;
    document.getElementById('edit-room-old-name').value = oldName;
    document.getElementById('edit-room-name').value = oldName;
    const summaryField = document.getElementById('edit-room-summary');
    summaryField.value = currentSummary || '';
    summaryField.setAttribute('data-original', currentSummary || '');
    showModal('edit-room-modal');
}

async function updateRoomSubmit() {
    const dungeonName = document.getElementById('edit-room-dungeon-name').value;
    const oldName = document.getElementById('edit-room-old-name').value;
    const newName = document.getElementById('edit-room-name').value.trim();
    const summaryField = document.getElementById('edit-room-summary');
    const summary = summaryField.value.trim();
    const originalSummary = summaryField.getAttribute('data-original') || '';
    
    const patch = {};
    let hasChanges = false;
    
    if (newName && newName !== oldName) {
        patch.name = newName;
        hasChanges = true;
    }
    
    if (summary !== originalSummary) {
        patch.summary = summary || null;
        hasChanges = true;
    }
    
    if (!hasChanges) {
        showToast('At least one field must be updated. No changes detected.', 'error');
        return;
    }
    
    try {
        showLoading();
        await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(oldName)}`, {
            method: 'PATCH',
            body: JSON.stringify({ patch })
        });
        showToast('Room updated successfully!', 'success');
        hideModal('edit-room-modal');
        document.getElementById('edit-room-form').reset();
        await loadDungeonDetails(dungeonName);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function deleteRoomConfirm(dungeonName, roomName) {
    // Show confirmation modal
    document.getElementById('confirm-title').textContent = 'Delete Room';
    document.getElementById('confirm-message').textContent = `Are you sure you want to delete the room "${roomName}" from "${dungeonName}"?`;
    document.getElementById('confirm-token').value = '';
    document.getElementById('confirm-token').focus();
    
    // Store the delete function to call on confirmation
    const confirmModal = document.getElementById('confirm-modal');
    const confirmYesBtn = document.getElementById('confirm-yes');
    const confirmTokenInput = document.getElementById('confirm-token');
    
    // Remove any existing event listeners by cloning and replacing
    const newConfirmYesBtn = confirmYesBtn.cloneNode(true);
    confirmYesBtn.parentNode.replaceChild(newConfirmYesBtn, confirmYesBtn);
    
    newConfirmYesBtn.addEventListener('click', async () => {
        const token = confirmTokenInput.value.trim();
        if (token !== 'DELETE') {
            showToast('Please type "DELETE" to confirm deletion', 'error');
            confirmTokenInput.focus();
            return;
        }
        
        const confirmToken = `DELETE:/${dungeonName}/${roomName}`;
        hideModal('confirm-modal');
        
        try {
            showLoading();
            await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(roomName)}?token=${encodeURIComponent(confirmToken)}`, {
                method: 'DELETE'
            });
            showToast('Room deleted successfully!', 'success');
            await loadDungeonDetails(dungeonName);
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    });
    
    // Handle Enter key in token input
    confirmTokenInput.onkeypress = (e) => {
        if (e.key === 'Enter') {
            newConfirmYesBtn.click();
        }
    };
    
    showModal('confirm-modal');
}

async function loadRoomDetails(dungeonName, roomName) {
    currentDungeon = dungeonName;
    currentRoom = roomName;
    currentCategory = null;
    
    try {
        showLoading();
        
        // Ensure all categories exist
        const categories = ['puzzles', 'traps', 'treasures', 'enemies'];
        await Promise.all(categories.map(cat => 
            apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(roomName)}/categories/${cat}`, {
                method: 'POST'
            }).catch(() => {}) // Ignore errors if category already exists
        ));
        
        // Load items for each category
        const itemsPromises = categories.map(cat =>
            apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(roomName)}/categories/${cat}`)
                .then(data => ({ category: cat, items: data.items }))
                .catch(() => ({ category: cat, items: [] }))
        );
        
        const categoryItems = await Promise.all(itemsPromises);
        
        renderRoomDetails(dungeonName, roomName, categoryItems);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderRoomDetails(dungeonName, roomName, categoryItems) {
    const container = document.getElementById('dungeons-list');
    
    const categoryNames = {
        puzzles: 'Puzzles',
        traps: 'Traps',
        treasures: 'Treasures',
        enemies: 'Enemies'
    };
    
    // Update title to show dungeon name
    updateDungeonsViewTitle(dungeonName);
    
    container.innerHTML = `
        <div class="card" style="grid-column: 1 / -1; margin-bottom: 20px;">
            <div class="card-header">
                <div>
                    <div class="card-title">${escapeHtml(roomName)}</div>
                    <div style="margin-top: 10px;">
                        <button class="btn btn-secondary btn-small" onclick="loadDungeonDetails('${escapeHtml(dungeonName)}')">
                            ← Back to Rooms
                        </button>
                    </div>
                </div>
            </div>
        </div>
        ${categoryItems.map(({ category, items }) => `
            <div class="card" data-category="${category}">
                <div class="card-header">
                    <div>
                        <div class="card-title">${categoryNames[category]}</div>
                        <div class="card-badge">${items.length} items</div>
                    </div>
                </div>
                <div class="card-body">
                    ${items.length === 0 ? '<p style="color: var(--secondary-brown);">No items yet</p>' : 
                        items.map(item => `
                            <div style="margin-bottom: 10px; padding: 10px; background: var(--primary-brown); border-radius: 5px; border-left: 3px solid var(--accent-gold);">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <span style="font-weight: 600; color: var(--text-light);">${escapeHtml(item.name)}</span>
                                    <div>
                                        <button class="btn btn-small btn-secondary" onclick="viewItem('${escapeHtml(dungeonName)}', '${escapeHtml(roomName)}', '${category}', '${escapeHtml(item.name)}')" title="View">
                                            ⊙
                                        </button>
                                        <button class="btn btn-small btn-primary" onclick="editItem('${escapeHtml(dungeonName)}', '${escapeHtml(roomName)}', '${category}', '${escapeHtml(item.name)}')" title="Edit">
                                            ✎
                                        </button>
                                        <button class="btn btn-small btn-danger" onclick="deleteItemConfirm('${escapeHtml(dungeonName)}', '${escapeHtml(roomName)}', '${category}', '${escapeHtml(item.name)}')" title="Delete">
                                            ×
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `).join('')
                    }
                </div>
                <div class="card-footer">
                    <button class="btn btn-primary btn-small" onclick="createItem('${escapeHtml(dungeonName)}', '${escapeHtml(roomName)}', '${category}')">
                        Add Item
                    </button>
                </div>
            </div>
        `).join('')}
    `;
}

// Item Functions
function createItem(dungeonName, roomName, category = null) {
    document.getElementById('item-dungeon-name').value = dungeonName;
    document.getElementById('item-room-name').value = roomName;
    if (category) {
        document.getElementById('item-category').value = category;
    }
    showModal('create-item-modal');
}

async function createItemSubmit(dungeonName, roomName, category, payload) {
    try {
        showLoading();
        await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(roomName)}/categories/${category}/items`, {
            method: 'POST',
            body: JSON.stringify({ payload })
        });
        showToast('Item created successfully!', 'success');
        hideModal('create-item-modal');
        document.getElementById('create-item-form').reset();
        await loadRoomDetails(dungeonName, roomName);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function viewItem(dungeonName, roomName, category, itemName) {
    try {
        showLoading();
        const data = await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(roomName)}/categories/${category}/items/${encodeURIComponent(itemName)}`);
        
        const item = data.item;
        currentItemData = { dungeonName, roomName, category, itemName, item };
        
        const details = document.getElementById('item-details');
        details.innerHTML = `
            <div class="item-detail">
                <div class="item-detail-label">Name</div>
                <div class="item-detail-value">${escapeHtml(item.name)}</div>
            </div>
            ${item.summary ? `
                <div class="item-detail">
                    <div class="item-detail-label">Summary</div>
                    <div class="item-detail-value">${escapeHtml(item.summary)}</div>
                </div>
            ` : ''}
            ${item.notes_md ? `
                <div class="item-detail">
                    <div class="item-detail-label">Notes</div>
                    <div class="item-detail-value">${escapeHtml(item.notes_md).replace(/\n/g, '<br>')}</div>
                </div>
            ` : ''}
            ${item.tags && item.tags.length > 0 ? `
                <div class="item-detail">
                    <div class="item-detail-label">Tags</div>
                    <div class="item-tags">
                        ${item.tags.map(tag => `<span class="item-tag">${escapeHtml(tag)}</span>`).join('')}
                    </div>
                </div>
            ` : ''}
            ${item.metadata && Object.keys(item.metadata).length > 0 ? `
                <div class="item-detail">
                    <div class="item-detail-label">Metadata</div>
                    <div class="item-detail-value">
                        ${Object.entries(item.metadata).map(([key, value]) => 
                            `<strong>${escapeHtml(key)}</strong>: ${escapeHtml(value)}`
                        ).join('<br>')}
                    </div>
                </div>
            ` : ''}
        `;
        
        document.getElementById('view-item-title').textContent = itemName;
        showModal('view-item-modal');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function editItem(dungeonName, roomName, category, itemName) {
    // If we have current item data, use it; otherwise fetch it
    if (currentItemData && 
        currentItemData.dungeonName === dungeonName &&
        currentItemData.roomName === roomName &&
        currentItemData.category === category &&
        currentItemData.itemName === itemName) {
        populateEditForm(currentItemData);
    } else {
        // Fetch item data first
        try {
            showLoading();
            const data = await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(roomName)}/categories/${category}/items/${encodeURIComponent(itemName)}`);
            currentItemData = { dungeonName, roomName, category, itemName, item: data.item };
            populateEditForm(currentItemData);
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    }
}

function populateEditForm(itemData) {
    if (!itemData || !itemData.item) return;
    
    const item = itemData.item;
    
    // Set hidden fields
    document.getElementById('edit-item-dungeon-name').value = itemData.dungeonName;
    document.getElementById('edit-item-room-name').value = itemData.roomName;
    document.getElementById('edit-item-category').value = itemData.category;
    document.getElementById('edit-item-name').value = itemData.itemName;
    
    // Populate form fields with current values (as placeholders/hints)
    document.getElementById('edit-item-summary').value = item.summary || '';
    document.getElementById('edit-item-notes').value = item.notes_md || '';
    document.getElementById('edit-item-tags').value = item.tags ? item.tags.join(', ') : '';
    document.getElementById('edit-item-metadata').value = item.metadata ? 
        Object.entries(item.metadata).map(([k, v]) => `${k}=${v}`).join(', ') : '';
    
    // Close view modal and open edit modal
    hideModal('view-item-modal');
    showModal('edit-item-modal');
}

async function updateItemSubmit(dungeonName, roomName, category, itemName, patch) {
    try {
        showLoading();
        await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(roomName)}/categories/${category}/items/${encodeURIComponent(itemName)}`, {
            method: 'PATCH',
            body: JSON.stringify({ patch })
        });
        showToast('Item updated successfully!', 'success');
        hideModal('edit-item-modal');
        document.getElementById('edit-item-form').reset();
        // Refresh the room view to show updated item
        await loadRoomDetails(dungeonName, roomName);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function deleteItemConfirm(dungeonName, roomName, category, itemName) {
    // Show confirmation modal
    document.getElementById('confirm-title').textContent = 'Delete Item';
    document.getElementById('confirm-message').textContent = `Are you sure you want to delete the item "${itemName}" from ${category}?`;
    document.getElementById('confirm-token').value = '';
    document.getElementById('confirm-token').focus();
    
    // Store the delete function to call on confirmation
    const confirmModal = document.getElementById('confirm-modal');
    const confirmYesBtn = document.getElementById('confirm-yes');
    const confirmTokenInput = document.getElementById('confirm-token');
    
    // Remove any existing event listeners by cloning and replacing
    const newConfirmYesBtn = confirmYesBtn.cloneNode(true);
    confirmYesBtn.parentNode.replaceChild(newConfirmYesBtn, confirmYesBtn);
    
    newConfirmYesBtn.addEventListener('click', async () => {
        const token = confirmTokenInput.value.trim();
        if (token !== 'DELETE') {
            showToast('Please type "DELETE" to confirm deletion', 'error');
            confirmTokenInput.focus();
            return;
        }
        
        const confirmToken = `DELETE:/${dungeonName}/${roomName}/${category}/${itemName}`;
        hideModal('confirm-modal');
        
        try {
            showLoading();
            await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/rooms/${encodeURIComponent(roomName)}/categories/${category}/items/${encodeURIComponent(itemName)}?token=${encodeURIComponent(confirmToken)}`, {
                method: 'DELETE'
            });
            showToast('Item deleted successfully!', 'success');
            await loadRoomDetails(dungeonName, roomName);
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    });
    
    // Handle Enter key in token input
    confirmTokenInput.onkeypress = (e) => {
        if (e.key === 'Enter') {
            newConfirmYesBtn.click();
        }
    };
    
    showModal('confirm-modal');
}

// Search Functions
async function performSearch() {
    const query = document.getElementById('search-query').value;
    const dungeon = document.getElementById('search-dungeon').value;
    const tags = document.getElementById('search-tags').value;
    
    if (!query.trim()) {
        showToast('Please enter a search query', 'error');
        return;
    }
    
    try {
        showLoading();
        const params = new URLSearchParams({ query });
        if (dungeon) params.append('dungeon', dungeon);
        if (tags) params.append('tags', tags);
        
        const data = await apiCall(`/search?${params.toString()}`);
        renderSearchResults(data.results);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderSearchResults(results) {
    const container = document.getElementById('search-results');
    
    if (results.length === 0) {
        container.innerHTML = `
            <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <p style="font-size: 1.2em; color: var(--secondary-brown);">
                    No items found matching your search.
                </p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = results.map(item => `
        <div class="card">
            <div class="card-header">
                <div>
                    <div class="card-title">${escapeHtml(item.name)}</div>
                    <div class="card-badge">${escapeHtml(item.dungeon)}</div>
                    <div class="card-badge">${escapeHtml(item.room)}</div>
                    <div class="card-badge">${escapeHtml(item.category)}</div>
                </div>
            </div>
            <div class="card-footer">
                <button class="btn btn-primary btn-small" onclick="viewItem('${escapeHtml(item.dungeon)}', '${escapeHtml(item.room)}', '${escapeHtml(item.category)}', '${escapeHtml(item.name)}')">
                    View Details
                </button>
            </div>
        </div>
    `).join('');
}

async function loadDungeonsForSearch() {
    try {
        const data = await apiCall('/dungeons');
        const select = document.getElementById('search-dungeon');
        select.innerHTML = '<option value="">All Dungeons</option>' +
            data.dungeons.map(d => `<option value="${escapeHtml(d.name)}">${escapeHtml(d.name)}</option>`).join('');
    } catch (error) {
        console.error('Error loading dungeons for search:', error);
    }
}

// Export/Import Functions
async function exportDungeon() {
    const dungeonName = document.getElementById('export-dungeon-select').value;
    if (!dungeonName) {
        showToast('Please select a dungeon to export', 'error');
        return;
    }
    
    try {
        showLoading();
        const data = await apiCall(`/dungeons/${encodeURIComponent(dungeonName)}/export`);
        const output = document.getElementById('export-output');
        output.textContent = JSON.stringify(data.dungeon, null, 2);
        showToast('Dungeon exported successfully!', 'success');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function importDungeon() {
    const jsonText = document.getElementById('import-data').value.trim();
    if (!jsonText) {
        showToast('Please paste dungeon JSON data', 'error');
        return;
    }
    
    try {
        const dungeonData = JSON.parse(jsonText);
        const strategy = document.getElementById('import-strategy').value;
        const originalName = dungeonData.name;
        
        showLoading();
        const response = await apiCall('/dungeons/import', {
            method: 'POST',
            body: JSON.stringify({ dungeon: dungeonData, strategy })
        });
        
        // Show different messages based on import action
        const importAction = response.dungeon?.import_action || 'imported';
        const finalName = response.dungeon?.name || originalName;
        
        if (importAction === 'skipped') {
            showToast(`Import skipped: A dungeon named "${originalName}" already exists.`, 'info');
        } else if (importAction === 'renamed') {
            showToast(`Dungeon imported as "${finalName}" (renamed from "${originalName}")`, 'success');
        } else {
            showToast(`Dungeon "${finalName}" imported successfully!`, 'success');
        }
        
        document.getElementById('import-data').value = '';
        await loadDungeons();
    } catch (error) {
        showToast(error.message || 'Invalid JSON data', 'error');
    } finally {
        hideLoading();
    }
}

async function loadDungeonsForExport() {
    try {
        const data = await apiCall('/dungeons');
        const select = document.getElementById('export-dungeon-select');
        select.innerHTML = '<option value="">Select a dungeon...</option>' +
            data.dungeons.map(d => `<option value="${escapeHtml(d.name)}">${escapeHtml(d.name)}</option>`).join('');
    } catch (error) {
        console.error('Error loading dungeons for export:', error);
    }
}

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Update dungeons view title and create button visibility
function updateDungeonsViewTitle(dungeonName) {
    const titleElement = document.getElementById('dungeons-view-title');
    const createButton = document.getElementById('create-dungeon-btn');
    
    if (dungeonName) {
        // Viewing a specific dungeon - show dungeon name
        titleElement.textContent = dungeonName;
        createButton.style.display = 'none';
    } else {
        // Viewing all dungeons - show "Your Dungeons"
        titleElement.textContent = 'Your Dungeons';
        createButton.style.display = 'inline-flex';
    }
}

// Theme Management
function initTheme() {
    // Check for saved theme preference or default to light
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
}

function setTheme(theme) {
    const root = document.documentElement;
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle.querySelector('.theme-toggle-icon');
    const themeText = document.getElementById('theme-toggle-text');
    
    if (theme === 'dark') {
        root.setAttribute('data-theme', 'dark');
        themeIcon.textContent = '○';
        themeText.textContent = 'Dark';
        localStorage.setItem('theme', 'dark');
    } else {
        root.removeAttribute('data-theme');
        themeIcon.textContent = '●';
        themeText.textContent = 'Light';
        localStorage.setItem('theme', 'light');
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    setTheme(currentTheme === 'dark' ? 'light' : 'dark');
}

// Event Listeners
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize theme
    initTheme();
    
    // Theme toggle
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    
    // Check authentication status
    const authenticated = await checkAuth();
    if (authenticated) {
        // Load dungeons if authenticated
        loadDungeons();
    }
    
    // Navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            
            // Update active nav button
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Show corresponding view
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById(`${view}-view`).classList.add('active');
            
            // Load data for the view
            if (view === 'dungeons') {
                loadDungeons();
            } else if (view === 'search') {
                loadDungeonsForSearch();
            } else if (view === 'export') {
                loadDungeonsForExport();
                loadDungeonsForSearch(); // Also for import dropdown
            } else if (view === 'characters') {
                loadCharacters();
            }
        });
    });
    
    // Create dungeon form
    document.getElementById('create-dungeon-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const name = document.getElementById('dungeon-name').value.trim();
        const summary = document.getElementById('dungeon-summary').value.trim();
        const existsOk = document.getElementById('dungeon-exists-ok').checked;
        if (name) {
            createDungeon(name, summary || null, existsOk);
        }
    });
    
    // Create room form
    document.getElementById('create-room-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const dungeonName = document.getElementById('room-dungeon-name').value;
        const name = document.getElementById('room-name').value.trim();
        const summary = document.getElementById('room-summary').value.trim();
        if (name) {
            createRoomSubmit(dungeonName, name, summary || null);
        }
    });
    
    // Create item form
    document.getElementById('create-item-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const dungeonName = document.getElementById('item-dungeon-name').value;
        const roomName = document.getElementById('item-room-name').value;
        const category = document.getElementById('item-category').value;
        const name = document.getElementById('item-name').value.trim();
        const summary = document.getElementById('item-summary').value.trim();
        const notes = document.getElementById('item-notes').value.trim();
        const tagsInput = document.getElementById('item-tags').value.trim();
        const metadataInput = document.getElementById('item-metadata').value.trim();
        
        if (!name || !category) {
            showToast('Name and category are required', 'error');
            return;
        }
        
        const payload = { name };
        if (summary) payload.summary = summary;
        if (notes) payload.notes_md = notes;
        if (tagsInput) {
            payload.tags = tagsInput.split(',').map(t => t.trim()).filter(t => t);
        }
        if (metadataInput) {
            const metadata = {};
            metadataInput.split(',').forEach(pair => {
                if (pair.includes('=')) {
                    const [key, value] = pair.split('=', 2);
                    metadata[key.trim()] = value.trim();
                }
            });
            if (Object.keys(metadata).length > 0) {
                payload.metadata = metadata;
            }
        }
        
        createItemSubmit(dungeonName, roomName, category, payload);
    });
    
    // Edit item form
    document.getElementById('edit-item-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const dungeonName = document.getElementById('edit-item-dungeon-name').value;
        const roomName = document.getElementById('edit-item-room-name').value;
        const category = document.getElementById('edit-item-category').value;
        const itemName = document.getElementById('edit-item-name').value;
        
        const summary = document.getElementById('edit-item-summary').value.trim();
        const notes = document.getElementById('edit-item-notes').value.trim();
        const tagsInput = document.getElementById('edit-item-tags').value.trim();
        const metadataInput = document.getElementById('edit-item-metadata').value.trim();
        
        const patch = {};
        
        // Include fields that have values (empty strings are valid for clearing)
        // We check if the field was modified by comparing to original value
        const originalItem = currentItemData?.item;
        
        // Summary: include if provided (even if empty, to clear it)
        if (summary !== undefined && summary !== (originalItem?.summary || '')) {
            patch.summary = summary;
        }
        
        // Notes: include if provided (even if empty, to clear it)
        if (notes !== undefined && notes !== (originalItem?.notes_md || '')) {
            patch.notes_md = notes;
        }
        
        // Tags: parse and include if provided
        if (tagsInput !== undefined) {
            const newTags = tagsInput.split(',').map(t => t.trim()).filter(t => t);
            const oldTags = originalItem?.tags || [];
            // Compare arrays
            if (JSON.stringify(newTags.sort()) !== JSON.stringify(oldTags.sort())) {
                patch.tags = newTags;
            }
        }
        
        // Metadata: parse and include if provided
        if (metadataInput !== undefined) {
            const metadata = {};
            if (metadataInput.trim()) {
                metadataInput.split(',').forEach(pair => {
                    if (pair.includes('=')) {
                        const [key, value] = pair.split('=', 2);
                        metadata[key.trim()] = value.trim();
                    }
                });
            }
            const oldMetadata = originalItem?.metadata || {};
            // Compare objects
            if (JSON.stringify(metadata) !== JSON.stringify(oldMetadata)) {
                patch.metadata = metadata;
            }
        }
        
        // Validate that at least one field is provided and changed
        if (Object.keys(patch).length === 0) {
            showToast('At least one field must be updated. No changes detected.', 'error');
            return;
        }
        
        updateItemSubmit(dungeonName, roomName, category, itemName, patch);
    });
    
    // Edit button in view modal
    document.getElementById('edit-item-btn').addEventListener('click', () => {
        if (currentItemData) {
            populateEditForm(currentItemData);
        }
    });
    
    // Search
    document.getElementById('search-btn').addEventListener('click', performSearch);
    document.getElementById('search-query').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch();
    });
    
    // Export/Import
    document.getElementById('export-btn').addEventListener('click', exportDungeon);
    document.getElementById('import-btn').addEventListener('click', importDungeon);
    
    // Modal close buttons
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal').classList.remove('active');
        });
    });
    
    // Close modals on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
    
    // Authentication
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;
        await login(username, password);
    });
    
    document.getElementById('register-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('register-username').value;
        const password = document.getElementById('register-password').value;
        await register(username, password);
    });
    
    document.getElementById('show-register-btn').addEventListener('click', () => {
        hideModal('login-modal');
        showModal('register-modal');
    });
    
    document.getElementById('show-login-btn').addEventListener('click', () => {
        hideModal('register-modal');
        showModal('login-modal');
    });
    
    document.getElementById('logout-btn').addEventListener('click', logout);
    
    // Create dungeon button
    document.getElementById('create-dungeon-btn').addEventListener('click', () => {
        showModal('create-dungeon-modal');
    });
    
    // Edit dungeon form
    document.getElementById('edit-dungeon-form').addEventListener('submit', (e) => {
        e.preventDefault();
        updateDungeonSubmit();
    });
    
    // Edit room form
    document.getElementById('edit-room-form').addEventListener('submit', (e) => {
        e.preventDefault();
        updateRoomSubmit();
    });
    
    // Load initial data
    loadDungeons();
    
    // Character management
    document.getElementById('create-character-btn').addEventListener('click', startCharacterCreation);
    document.getElementById('character-chat-send').addEventListener('click', sendCharacterMessage);
    document.getElementById('character-chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendCharacterMessage();
        }
    });
    document.getElementById('character-save-btn').addEventListener('click', saveCurrentCharacter);
    
    // Reset character session when modal closes
    document.getElementById('create-character-modal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal') || e.target.classList.contains('modal-close')) {
            currentCharacterSessionId = null;
        }
    });
    
    // Character editing event listeners
    document.getElementById('edit-character-btn').addEventListener('click', () => {
        if (currentViewingCharacterId) {
            openEditCharacter(currentViewingCharacterId);
        }
    });
    
    // Edit tab switching
    document.querySelectorAll('.edit-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchEditTab(tab.dataset.tab);
        });
    });
    
    // Manual edit form
    document.getElementById('manual-edit-character-form').addEventListener('submit', (e) => {
        e.preventDefault();
        submitManualEdit();
    });
    
    // Agent edit chat
    document.getElementById('edit-character-chat-send').addEventListener('click', sendEditCharacterMessage);
    document.getElementById('edit-character-chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendEditCharacterMessage();
        }
    });
    document.getElementById('edit-character-save-btn').addEventListener('click', saveEditCharacter);
    
    // Reset edit session when modal closes
    document.getElementById('edit-character-modal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal') || e.target.classList.contains('modal-close')) {
            currentEditCharacterSessionId = null;
            currentEditCharacterId = null;
        }
    });
});

// Character Management Functions
let currentCharacterSessionId = null;

async function loadCharacters() {
    try {
        showLoading();
        const data = await apiCall('/characters');
        renderCharacters(data.characters);
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function renderCharacters(characters) {
    const container = document.getElementById('characters-list');
    
    if (characters.length === 0) {
        container.innerHTML = `
            <div class="card" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <p style="font-size: 1.2em; color: var(--secondary-brown);">
                    No characters yet. Create your first character to get started!
                </p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = characters.map(char => `
        <div class="card" data-character-id="${char._id}">
            <div class="card-header">
                <div>
                    <div class="card-title">${escapeHtml(char.name || 'Unnamed Character')}</div>
                    ${char.character_data && char.character_data.class ? 
                        `<div class="card-badge">${escapeHtml(char.character_data.class)} ${char.character_data.level || 1}</div>` : ''}
                    ${char.character_data && char.character_data.species ? 
                        `<div class="card-badge">${escapeHtml(char.character_data.subspecies ? char.character_data.subspecies + ' ' : '')}${escapeHtml(char.character_data.species)}</div>` : ''}
                </div>
                <div class="card-actions">
                    <button class="btn btn-small btn-danger" onclick="deleteCharacterConfirm('${char._id}', '${escapeHtml(char.name || 'Unnamed')}')" title="Delete">
                        ×
                    </button>
                </div>
            </div>
            <div class="card-body">
                ${char.character_data && char.character_data.background ? 
                    `<p style="color: var(--text-secondary);">Background: ${escapeHtml(char.character_data.background)}</p>` : ''}
                ${char.character_data && char.character_data.alignment ? 
                    `<p style="color: var(--text-secondary);">Alignment: ${escapeHtml(char.character_data.alignment)}</p>` : ''}
            </div>
            <div class="card-footer">
                <button class="btn btn-primary btn-small" onclick="viewCharacter('${char._id}')">
                    View Character Sheet
                </button>
            </div>
        </div>
    `).join('');
}

async function startCharacterCreation() {
    try {
        showLoading();
        const data = await apiCall('/characters', {
            method: 'POST'
        });
        currentCharacterSessionId = data.session_id;
        
        // Clear chat messages
        const chatMessages = document.getElementById('chat-messages');
        chatMessages.innerHTML = `
            <div style="padding: 10px; color: var(--text-secondary);">
                <p><strong>Character Creation Assistant</strong></p>
                <p>I'll help you create a complete D&D 5e character following PHB rules!</p>
                <p>Tell me what you'd like to create, or ask me to guide you through the process.</p>
            </div>
        `;
        
        // Hide save button initially
        document.getElementById('character-save-btn').style.display = 'none';
        
        // Clear input
        document.getElementById('character-chat-input').value = '';
        
        showModal('create-character-modal');
        document.getElementById('character-chat-input').focus();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function sendCharacterMessage() {
    const input = document.getElementById('character-chat-input');
    const message = input.value.trim();
    
    if (!message || !currentCharacterSessionId) {
        return;
    }
    
    // Ensure full-page loading overlay is hidden (shouldn't be visible, but just in case)
    hideLoading();
    
    // Clear input immediately for better UX
    input.value = '';
    
    // Disable input and send button while sending
    input.disabled = true;
    document.getElementById('character-chat-send').disabled = true;
    
    // Add user message to chat with "sending" state
    const messageId = addChatMessage('user', message, true);
    
    // Add a slight delay to simulate sending effect (like messaging apps)
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Update message to show it's been sent
    updateMessageStatus(messageId, 'sent');
    
    // Show loading indicator in chat (three dots) for assistant response
    const loadingId = showChatLoading();
    
    try {
        const data = await apiCall('/characters/agent/chat', {
            method: 'POST',
            body: JSON.stringify({
                session_id: currentCharacterSessionId,
                message: message
            })
        });
        
        // Remove loading indicator
        removeChatLoading(loadingId);
        
        // Add assistant response to chat
        addChatMessage('assistant', data.response);
        
        // Show save button if character has a name
        if (data.character_data && data.character_data.name) {
            document.getElementById('character-save-btn').style.display = 'inline-flex';
        }
        
        // Scroll to bottom
        const chatContainer = document.getElementById('character-creation-chat');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    } catch (error) {
        removeChatLoading(loadingId);
        // Update message to show error state
        updateMessageStatus(messageId, 'error');
        showToast(error.message, 'error');
        addChatMessage('error', `Error: ${error.message}`);
    } finally {
        // Re-enable input and send button
        input.disabled = false;
        document.getElementById('character-chat-send').disabled = false;
        input.focus();
    }
}

function addChatMessage(role, message, isSending = false) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    messageDiv.id = messageId;
    messageDiv.style.cssText = 'padding: 10px; margin-bottom: 10px; border-radius: 5px;';
    
    if (role === 'user') {
        // Match the send button background color (var(--accent-gold))
        messageDiv.style.cssText += 'background: var(--accent-gold); color: var(--text-inverse); text-align: right; margin-left: 20%;';
        
        if (isSending) {
            // Show sending indicator
            messageDiv.innerHTML = `
                <strong>You:</strong> ${escapeHtml(message)}
                <span class="message-status sending" style="margin-left: 8px; opacity: 0.7; font-size: 0.85em;">
                    <span class="sending-dot"></span><span class="sending-dot"></span><span class="sending-dot"></span>
                </span>
            `;
        } else {
            messageDiv.innerHTML = `<strong>You:</strong> ${escapeHtml(message)}`;
        }
    } else if (role === 'assistant') {
        messageDiv.style.cssText += 'background: var(--bg-secondary); margin-right: 20%;';
        // Convert markdown-style formatting to HTML
        let formattedMessage = escapeHtml(message);
        // Simple markdown conversion for bold
        formattedMessage = formattedMessage.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formattedMessage = formattedMessage.replace(/\n/g, '<br>');
        messageDiv.innerHTML = `<strong>Assistant:</strong><br>${formattedMessage}`;
    } else if (role === 'error') {
        messageDiv.style.cssText += 'background: var(--error); color: white;';
        messageDiv.innerHTML = escapeHtml(message);
    }
    
    // Add CSS for sending dots if not already added
    if (isSending && !document.getElementById('sending-dots-style')) {
        const style = document.createElement('style');
        style.id = 'sending-dots-style';
        style.textContent = `
            .sending-dot {
                display: inline-block;
                width: 4px;
                height: 4px;
                border-radius: 50%;
                background-color: currentColor;
                margin: 0 1px;
                animation: sending-pulse 1.4s infinite ease-in-out both;
            }
            .sending-dot:nth-child(1) {
                animation-delay: 0s;
            }
            .sending-dot:nth-child(2) {
                animation-delay: 0.2s;
            }
            .sending-dot:nth-child(3) {
                animation-delay: 0.4s;
            }
            @keyframes sending-pulse {
                0%, 80%, 100% {
                    opacity: 0.3;
                    transform: scale(0.8);
                }
                40% {
                    opacity: 1;
                    transform: scale(1);
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    const chatContainer = document.getElementById('character-creation-chat');
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return messageId;
}

function updateMessageStatus(messageId, status) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;
    
    const statusSpan = messageDiv.querySelector('.message-status');
    
    if (status === 'sent') {
        // Remove sending indicator (message is sent)
        if (statusSpan) {
            statusSpan.remove();
        }
    } else if (status === 'error') {
        // Show error indicator
        if (statusSpan) {
            statusSpan.className = 'message-status error';
            statusSpan.innerHTML = '⚠';
            statusSpan.style.opacity = '1';
        }
    }
}

function showChatLoading() {
    const chatMessages = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    const loadingId = 'chat-loading-' + Date.now();
    loadingDiv.id = loadingId;
    loadingDiv.style.cssText = 'padding: 10px; margin-bottom: 10px; border-radius: 5px; background: var(--bg-secondary); margin-right: 20%;';
    loadingDiv.innerHTML = `
        <strong>Assistant:</strong><br>
        <span class="chat-loading-dots">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </span>
    `;
    
    // Add CSS for animated dots if not already added
    if (!document.getElementById('chat-loading-style')) {
        const style = document.createElement('style');
        style.id = 'chat-loading-style';
        style.textContent = `
            .chat-loading-dots {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 4px 0;
            }
            .chat-loading-dots .dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: var(--text-secondary);
                animation: chat-dot-pulse 1.4s infinite ease-in-out both;
                display: inline-block;
            }
            .chat-loading-dots .dot:nth-child(1) {
                animation-delay: 0s;
            }
            .chat-loading-dots .dot:nth-child(2) {
                animation-delay: 0.2s;
            }
            .chat-loading-dots .dot:nth-child(3) {
                animation-delay: 0.4s;
            }
            @keyframes chat-dot-pulse {
                0%, 80%, 100% {
                    transform: scale(0.8);
                    opacity: 0.5;
                }
                40% {
                    transform: scale(1);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    chatMessages.appendChild(loadingDiv);
    
    // Scroll to bottom
    const chatContainer = document.getElementById('character-creation-chat');
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return loadingId;
}

function removeChatLoading(loadingId) {
    const loadingDiv = document.getElementById(loadingId);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

async function saveCurrentCharacter() {
    if (!currentCharacterSessionId) {
        showToast('No active character session', 'error');
        return;
    }
    
    try {
        showLoading();
        const data = await apiCall('/characters/agent/save', {
            method: 'POST',
            body: JSON.stringify({
                session_id: currentCharacterSessionId
            })
        });
        
        showToast('Character saved successfully!', 'success');
        hideModal('create-character-modal');
        currentCharacterSessionId = null;
        await loadCharacters();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

let currentViewingCharacterId = null;

async function viewCharacter(characterId) {
    try {
        showLoading();
        const data = await apiCall(`/characters/${characterId}`);
        
        const character = data.character;
        currentViewingCharacterId = characterId;
        document.getElementById('view-character-title').textContent = character.name || 'Character Details';
        
        // Display character sheet if available, otherwise show character data
        const detailsDiv = document.getElementById('character-details');
        if (character.character_sheet) {
            // Convert markdown to HTML
            let sheet = escapeHtml(character.character_sheet);
            sheet = sheet.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            sheet = sheet.replace(/\n/g, '<br>');
            detailsDiv.innerHTML = sheet;
        } else {
            // Fallback to JSON display
            detailsDiv.textContent = JSON.stringify(character.character_data, null, 2);
        }
        
        showModal('view-character-modal');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function deleteCharacterConfirm(characterId, characterName) {
    // Show confirmation modal
    document.getElementById('confirm-title').textContent = 'Delete Character';
    document.getElementById('confirm-message').textContent = `Are you sure you want to delete the character "${characterName}"?`;
    document.getElementById('confirm-token').value = '';
    document.getElementById('confirm-token').focus();
    
    // Store the delete function to call on confirmation
    const confirmModal = document.getElementById('confirm-modal');
    const confirmYesBtn = document.getElementById('confirm-yes');
    const confirmTokenInput = document.getElementById('confirm-token');
    
    // Remove any existing event listeners by cloning and replacing
    const newConfirmYesBtn = confirmYesBtn.cloneNode(true);
    confirmYesBtn.parentNode.replaceChild(newConfirmYesBtn, confirmYesBtn);
    
    newConfirmYesBtn.addEventListener('click', async () => {
        const token = confirmTokenInput.value.trim();
        if (token !== 'DELETE') {
            showToast('Please type "DELETE" to confirm deletion', 'error');
            confirmTokenInput.focus();
            return;
        }
        
        hideModal('confirm-modal');
        
        try {
            showLoading();
            await apiCall(`/characters/${characterId}`, {
                method: 'DELETE'
            });
            showToast('Character deleted successfully!', 'success');
            await loadCharacters();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    });
    
    // Handle Enter key in token input
    confirmTokenInput.onkeypress = (e) => {
        if (e.key === 'Enter') {
            newConfirmYesBtn.click();
        }
    };
    
    showModal('confirm-modal');
}

// Character Editing Functions
let currentEditCharacterId = null;
let currentEditCharacterSessionId = null;

async function openEditCharacter(characterId) {
    currentEditCharacterId = characterId;
    
    try {
        showLoading();
        const data = await apiCall(`/characters/${characterId}`);
        const character = data.character;
        const charData = character.character_data || {};
        
        // Populate manual edit form
        document.getElementById('edit-character-id').value = characterId;
        document.getElementById('edit-char-name').value = charData.name || '';
        document.getElementById('edit-char-class').value = charData.class || '';
        document.getElementById('edit-char-level').value = charData.level || 1;
        document.getElementById('edit-char-species').value = charData.species || '';
        document.getElementById('edit-char-subspecies').value = charData.subspecies || '';
        document.getElementById('edit-char-background').value = charData.background || '';
        document.getElementById('edit-char-alignment').value = charData.alignment || '';
        document.getElementById('edit-char-str').value = charData.ability_scores?.Strength || '';
        document.getElementById('edit-char-dex').value = charData.ability_scores?.Dexterity || '';
        document.getElementById('edit-char-con').value = charData.ability_scores?.Constitution || '';
        document.getElementById('edit-char-int').value = charData.ability_scores?.Intelligence || '';
        document.getElementById('edit-char-wis').value = charData.ability_scores?.Wisdom || '';
        document.getElementById('edit-char-cha').value = charData.ability_scores?.Charisma || '';
        document.getElementById('edit-char-hit-points').value = charData.hit_points || '';
        document.getElementById('edit-char-armor-class').value = charData.armor_class || '';
        document.getElementById('edit-char-speed').value = charData.speed || '';
        document.getElementById('edit-char-backstory').value = charData.backstory || '';
        
        // Reset agent chat tab
        currentEditCharacterSessionId = null;
        const editChatMessages = document.getElementById('edit-chat-messages');
        editChatMessages.innerHTML = `
            <div style="padding: 10px; color: var(--text-secondary);">
                <p><strong>Character Editing Assistant</strong></p>
                <p>I'll help you edit your character! You can ask me to change any field, or I can suggest improvements.</p>
                <p>What would you like to change?</p>
            </div>
        `;
        document.getElementById('edit-character-save-btn').style.display = 'none';
        document.getElementById('edit-character-chat-input').value = '';
        
        // Switch to manual edit tab by default
        switchEditTab('manual');
        
        // Close view modal and open edit modal
        hideModal('view-character-modal');
        showModal('edit-character-modal');
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

function switchEditTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.edit-tab').forEach(tab => {
        if (tab.dataset.tab === tabName) {
            tab.classList.add('active');
            tab.style.borderBottomColor = 'var(--accent-gold)';
            tab.style.color = 'var(--text-primary)';
        } else {
            tab.classList.remove('active');
            tab.style.borderBottomColor = 'transparent';
            tab.style.color = 'var(--text-secondary)';
        }
    });
    
    // Update tab content
    document.getElementById('manual-edit-tab').style.display = tabName === 'manual' ? 'block' : 'none';
    document.getElementById('agent-edit-tab').style.display = tabName === 'agent' ? 'block' : 'none';
    
    // Initialize agent session if switching to agent tab
    if (tabName === 'agent' && !currentEditCharacterSessionId && currentEditCharacterId) {
        startAgentEditSession(currentEditCharacterId);
    }
}

async function startAgentEditSession(characterId) {
    try {
        showLoading();
        const data = await apiCall(`/characters/${characterId}/agent/edit`, {
            method: 'POST'
        });
        currentEditCharacterSessionId = data.session_id;
        
        // Display the initial context message from the agent
        // This message contains all the character information so the agent knows what it's editing
        if (data.initial_message) {
            addEditChatMessage('assistant', data.initial_message);
        } else {
            // Fallback if initial message not provided
            const charData = data.character_data;
            if (charData && charData.name) {
                addEditChatMessage('assistant', `I'm ready to help you edit ${charData.name}! What would you like to change?`);
            }
        }
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function submitManualEdit() {
    const characterId = document.getElementById('edit-character-id').value;
    if (!characterId) {
        showToast('Character ID is missing', 'error');
        return;
    }
    
    const patch = {};
    
    // Collect all form values
    const name = document.getElementById('edit-char-name').value.trim();
    if (name) patch.name = name;
    
    const classVal = document.getElementById('edit-char-class').value.trim();
    if (classVal) patch.class = classVal;
    
    const level = document.getElementById('edit-char-level').value;
    if (level) patch.level = parseInt(level);
    
    const species = document.getElementById('edit-char-species').value.trim();
    if (species) patch.species = species;
    
    const subspecies = document.getElementById('edit-char-subspecies').value.trim();
    if (subspecies) patch.subspecies = subspecies;
    
    const background = document.getElementById('edit-char-background').value.trim();
    if (background) patch.background = background;
    
    const alignment = document.getElementById('edit-char-alignment').value.trim();
    if (alignment) patch.alignment = alignment;
    
    // Ability scores
    const str = document.getElementById('edit-char-str').value;
    const dex = document.getElementById('edit-char-dex').value;
    const con = document.getElementById('edit-char-con').value;
    const int = document.getElementById('edit-char-int').value;
    const wis = document.getElementById('edit-char-wis').value;
    const cha = document.getElementById('edit-char-cha').value;
    
    if (str || dex || con || int || wis || cha) {
        patch.ability_scores = {};
        if (str) patch.ability_scores.Strength = parseInt(str);
        if (dex) patch.ability_scores.Dexterity = parseInt(dex);
        if (con) patch.ability_scores.Constitution = parseInt(con);
        if (int) patch.ability_scores.Intelligence = parseInt(int);
        if (wis) patch.ability_scores.Wisdom = parseInt(wis);
        if (cha) patch.ability_scores.Charisma = parseInt(cha);
    }
    
    const hitPoints = document.getElementById('edit-char-hit-points').value;
    if (hitPoints) patch.hit_points = parseInt(hitPoints);
    
    const armorClass = document.getElementById('edit-char-armor-class').value;
    if (armorClass) patch.armor_class = parseInt(armorClass);
    
    const speed = document.getElementById('edit-char-speed').value;
    if (speed) patch.speed = parseInt(speed);
    
    const backstory = document.getElementById('edit-char-backstory').value.trim();
    if (backstory) patch.backstory = backstory;
    
    if (Object.keys(patch).length === 0) {
        showToast('No changes to save', 'error');
        return;
    }
    
    try {
        showLoading();
        await apiCall(`/characters/${characterId}`, {
            method: 'PATCH',
            body: JSON.stringify({ patch })
        });
        showToast('Character updated successfully!', 'success');
        hideModal('edit-character-modal');
        await loadCharacters();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function sendEditCharacterMessage() {
    const input = document.getElementById('edit-character-chat-input');
    const message = input.value.trim();
    
    if (!message || !currentEditCharacterSessionId) {
        return;
    }
    
    input.value = '';
    input.disabled = true;
    document.getElementById('edit-character-chat-send').disabled = true;
    
    const messageId = addEditChatMessage('user', message, true);
    await new Promise(resolve => setTimeout(resolve, 300));
    updateEditMessageStatus(messageId, 'sent');
    
    const loadingId = showEditChatLoading();
    
    try {
        const data = await apiCall('/characters/agent/chat', {
            method: 'POST',
            body: JSON.stringify({
                session_id: currentEditCharacterSessionId,
                message: message
            })
        });
        
        removeEditChatLoading(loadingId);
        addEditChatMessage('assistant', data.response);
        
        if (data.character_data && data.character_data.name) {
            document.getElementById('edit-character-save-btn').style.display = 'inline-flex';
        }
        
        const chatContainer = document.getElementById('edit-character-creation-chat');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    } catch (error) {
        removeEditChatLoading(loadingId);
        updateEditMessageStatus(messageId, 'error');
        showToast(error.message, 'error');
        addEditChatMessage('error', `Error: ${error.message}`);
    } finally {
        input.disabled = false;
        document.getElementById('edit-character-chat-send').disabled = false;
        input.focus();
    }
}

function addEditChatMessage(role, message, isSending = false) {
    const chatMessages = document.getElementById('edit-chat-messages');
    const messageDiv = document.createElement('div');
    const messageId = 'edit-msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    messageDiv.id = messageId;
    messageDiv.style.cssText = 'padding: 10px; margin-bottom: 10px; border-radius: 5px;';
    
    if (role === 'user') {
        messageDiv.style.cssText += 'background: var(--accent-gold); color: var(--text-inverse); text-align: right; margin-left: 20%;';
        if (isSending) {
            messageDiv.innerHTML = `
                <strong>You:</strong> ${escapeHtml(message)}
                <span class="message-status sending" style="margin-left: 8px; opacity: 0.7; font-size: 0.85em;">
                    <span class="sending-dot"></span><span class="sending-dot"></span><span class="sending-dot"></span>
                </span>
            `;
        } else {
            messageDiv.innerHTML = `<strong>You:</strong> ${escapeHtml(message)}`;
        }
    } else if (role === 'assistant') {
        messageDiv.style.cssText += 'background: var(--bg-secondary); margin-right: 20%;';
        let formattedMessage = escapeHtml(message);
        formattedMessage = formattedMessage.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formattedMessage = formattedMessage.replace(/\n/g, '<br>');
        messageDiv.innerHTML = `<strong>Assistant:</strong><br>${formattedMessage}`;
    } else if (role === 'error') {
        messageDiv.style.cssText += 'background: var(--error); color: white;';
        messageDiv.innerHTML = escapeHtml(message);
    }
    
    chatMessages.appendChild(messageDiv);
    const chatContainer = document.getElementById('edit-character-creation-chat');
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return messageId;
}

function updateEditMessageStatus(messageId, status) {
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) return;
    
    const statusSpan = messageDiv.querySelector('.message-status');
    
    if (status === 'sent') {
        if (statusSpan) {
            statusSpan.remove();
        }
    } else if (status === 'error') {
        if (statusSpan) {
            statusSpan.className = 'message-status error';
            statusSpan.innerHTML = '⚠';
            statusSpan.style.opacity = '1';
        }
    }
}

function showEditChatLoading() {
    const chatMessages = document.getElementById('edit-chat-messages');
    const loadingDiv = document.createElement('div');
    const loadingId = 'edit-chat-loading-' + Date.now();
    loadingDiv.id = loadingId;
    loadingDiv.style.cssText = 'padding: 10px; margin-bottom: 10px; border-radius: 5px; background: var(--bg-secondary); margin-right: 20%;';
    loadingDiv.innerHTML = `
        <strong>Assistant:</strong><br>
        <span class="chat-loading-dots">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </span>
    `;
    
    // Add CSS for animated dots if not already added
    if (!document.getElementById('chat-loading-style')) {
        const style = document.createElement('style');
        style.id = 'chat-loading-style';
        style.textContent = `
            .chat-loading-dots {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                padding: 4px 0;
            }
            .chat-loading-dots .dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: var(--text-secondary);
                animation: chat-dot-pulse 1.4s infinite ease-in-out both;
                display: inline-block;
            }
            .chat-loading-dots .dot:nth-child(1) {
                animation-delay: 0s;
            }
            .chat-loading-dots .dot:nth-child(2) {
                animation-delay: 0.2s;
            }
            .chat-loading-dots .dot:nth-child(3) {
                animation-delay: 0.4s;
            }
            @keyframes chat-dot-pulse {
                0%, 80%, 100% {
                    transform: scale(0.8);
                    opacity: 0.5;
                }
                40% {
                    transform: scale(1);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    chatMessages.appendChild(loadingDiv);
    const chatContainer = document.getElementById('edit-character-creation-chat');
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return loadingId;
}

function removeEditChatLoading(loadingId) {
    const loadingDiv = document.getElementById(loadingId);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

async function saveEditCharacter() {
    if (!currentEditCharacterSessionId) {
        showToast('No active edit session', 'error');
        return;
    }
    
    try {
        showLoading();
        const data = await apiCall('/characters/agent/save', {
            method: 'POST',
            body: JSON.stringify({
                session_id: currentEditCharacterSessionId
            })
        });
        
        showToast('Character updated successfully!', 'success');
        hideModal('edit-character-modal');
        currentEditCharacterSessionId = null;
        currentEditCharacterId = null;
        await loadCharacters();
    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        hideLoading();
    }
}

