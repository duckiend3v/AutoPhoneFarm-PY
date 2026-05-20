document.addEventListener('DOMContentLoaded', () => {
    // 1. Clock top bar
    const clockEl = document.getElementById('clock');
    if (clockEl) {
        setInterval(() => {
            const now = new Date();
            clockEl.textContent = now.toLocaleTimeString('vi-VN');
        }, 1000);
    }

    // 2. Set active nav item based on URL
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === path) {
            link.classList.add('active');
            const pageTitle = link.textContent.trim();
            const pageTitleEl = document.getElementById('page-title');
            if (pageTitleEl) pageTitleEl.textContent = pageTitle;
        }
    });

    // 3. Socket.IO Real-time Connection
    const socket = io();
    
    socket.on('stats_update', (data) => {
        const totalEl = document.getElementById('stat-total-devices');
        const onlineEl = document.getElementById('stat-online-devices');
        if (totalEl) totalEl.textContent = data.total_devices;
        if (onlineEl) onlineEl.textContent = data.online_devices;
    });

    socket.on('device_updated', (data) => {
        console.log("Device updated real-time:", data.serial);
        // Refresh appropriate view
        if (path === '/') {
            loadDashboardDevices();
        } else if (path === '/devices') {
            loadDevicesList();
        }
    });

    // 4. Common Scan Button behavior
    const btnScan = document.getElementById('btn-scan');
    if (btnScan) {
        btnScan.addEventListener('click', () => {
            const originalHtml = btnScan.innerHTML;
            btnScan.innerHTML = '<i data-lucide="loader" class="spin"></i> Scanning...';
            lucide.createIcons();
            
            fetch('/api/devices/scan', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    setTimeout(() => {
                        btnScan.innerHTML = originalHtml;
                        lucide.createIcons();
                        if (path === '/') loadDashboardDevices();
                        if (path === '/devices') loadDevicesList();
                    }, 1500);
                });
        });
    }

    // 5. Page Router / Initializer
    if (path === '/') {
        initDashboard();
    } else if (path === '/devices') {
        initDevicesPage();
    } else if (path === '/tasks') {
        initTasksPage();
    } else if (path === '/accounts') {
        initAccountsPage();
    } else if (path === '/proxies') {
        initProxiesPage();
    } else if (path === '/logs') {
        initLogsPage();
    }
});

// ==========================================
// MODAL SYSTEM HELPERS (Global scope)
// ==========================================
window.openModal = function(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('active');
}

window.closeModal = function(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('active');
}

// ==========================================
// DASHBOARD CONTROLLER
// ==========================================
let dashboardInterval;
function initDashboard() {
    loadDashboardDevices();
    dashboardInterval = setInterval(loadDashboardDevices, 5000);
}

function loadDashboardDevices() {
    const container = document.getElementById('device-container');
    if (!container) return;

    fetch('/api/devices')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;
            
            const devices = data.data;
            
            // Render statistics card defaults
            const onlineCount = devices.filter(d => d.status === 'online').length;
            const runningTasksCount = devices.filter(d => d.status === 'busy').length;
            
            const statsOnline = document.getElementById('stat-online-devices');
            if (statsOnline) statsOnline.textContent = onlineCount;
            
            if (devices.length === 0) {
                container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 40px;">Không tìm thấy thiết bị nào. Vui lòng kết nối điện thoại và click nút Scan.</div>';
                return;
            }

            let html = '';
            devices.forEach((d, i) => {
                const badgeClass = d.status === 'online' ? 'badge-online' : 
                                  (d.status === 'busy' ? 'badge-busy' : 'badge-offline');
                const batColor = d.battery > 50 ? 'var(--success)' : (d.battery > 20 ? 'var(--warning)' : 'var(--danger)');
                
                html += `
                <div class="device-card glass-panel fade-in" style="animation-delay: ${i*0.02}s">
                    <div class="device-header">
                        <div class="device-name">${d.name || d.serial}</div>
                        <div class="badge ${badgeClass}">${d.status}</div>
                    </div>
                    <div class="device-thumb">
                        <i data-lucide="smartphone" style="width: 48px; height: 48px; opacity: 0.3;"></i>
                    </div>
                    <div class="device-info">
                        <div><i data-lucide="hash" style="width: 14px; vertical-align: middle;"></i> ${d.serial}</div>
                        <div><i data-lucide="info" style="width: 14px; vertical-align: middle;"></i> Android ${d.android_version || '?'}</div>
                        <div><i data-lucide="battery" style="width: 14px; vertical-align: middle;"></i> <span style="color: ${batColor}">${d.battery || '?'}%</span></div>
                        <div><i data-lucide="wifi" style="width: 14px; vertical-align: middle;"></i> ${d.ip_address || 'Offline'}</div>
                    </div>
                    <div style="margin-top: 16px; display: flex; gap: 8px;">
                        <button class="btn btn-primary" style="flex:1.5; padding: 6px 12px; font-size:12px; display: flex; align-items: center; justify-content: center; gap: 4px; background: linear-gradient(135deg, var(--accent-color), #764ba2);" onclick="mirrorDevice('${d.serial}')">
                            <i data-lucide="tv" style="width: 14px; height: 14px;"></i> Điều khiển
                        </button>
                        <button class="btn btn-ghost" style="flex:1; padding: 6px; font-size:12px;" onclick="deviceCardQuickReboot('${d.serial}')">Reboot</button>
                    </div>
                </div>
                `;
            });
            container.innerHTML = html;
            lucide.createIcons();
        });
}

function deviceCardQuickReboot(serial) {
    if (confirm(`Bạn có chắc muốn reboot thiết bị ${serial}?`)) {
        fetch(`/api/devices/${serial}/reboot`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                alert("Đã gửi lệnh khởi động lại thiết bị!");
                loadDashboardDevices();
            });
    }
}

// ==========================================
// DEVICES PAGE CONTROLLER
// ==========================================
let devicesCache = [];
function initDevicesPage() {
    loadDevicesList();
    
    // Select all checkboxes handler
    const selectAll = document.getElementById('select-all-devices');
    if (selectAll) {
        selectAll.addEventListener('change', () => {
            const checked = selectAll.checked;
            document.querySelectorAll('.device-select').forEach(cb => {
                cb.checked = checked;
            });
            updateSelectedCount();
        });
    }

    // Filter status event
    const filter = document.getElementById('filter-status');
    if (filter) {
        filter.addEventListener('change', () => {
            renderDevicesList(devicesCache);
        });
    }

    // Batch Reboot
    document.getElementById('btn-batch-reboot').addEventListener('click', () => {
        const serials = getSelectedDevices();
        if (confirm(`Reboot ${serials.length} thiết bị đã chọn?`)) {
            serials.forEach(s => {
                fetch(`/api/devices/${s}/reboot`, { method: 'POST' });
            });
            alert("Đã gửi lệnh Reboot hàng loạt!");
        }
    });

    // Batch Shell dialog
    document.getElementById('btn-batch-shell').addEventListener('click', () => {
        openModal('modal-batch-shell');
    });

    document.getElementById('btn-submit-batch-shell').addEventListener('click', () => {
        const cmd = document.getElementById('batch-shell-cmd').value;
        const serials = getSelectedDevices();
        if (!cmd) return alert("Vui lòng nhập lệnh!");
        
        serials.forEach(s => {
            fetch(`/api/devices/${s}/shell`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            });
        });
        alert(`Đã gửi lệnh shell tới ${serials.length} thiết bị.`);
        closeModal('modal-batch-shell');
    });

    // Batch APK dialog
    document.getElementById('btn-batch-apk').addEventListener('click', () => {
        openModal('modal-batch-apk');
    });

    document.getElementById('btn-submit-batch-apk').addEventListener('click', () => {
        const path = document.getElementById('batch-apk-path').value;
        const serials = getSelectedDevices();
        if (!path) return alert("Vui lòng nhập đường dẫn APK!");
        
        // Use task engine to install APK on multiple devices concurrently
        fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: 'Cài đặt APK hàng loạt',
                type: 'INSTALL_APP',
                target_devices: serials,
                script_data: { apk_path: path }
            })
        })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                // Autostart task
                fetch(`/api/tasks/${d.data.id}/start`, { method: 'POST' });
                alert("Đã tạo Tác vụ cài APK hàng loạt thành công! Chuyển sang Tab Tasks để theo dõi tiến độ.");
                closeModal('modal-batch-apk');
            }
        });
    });

    // Device details refresh screencap
    const btnRefScreen = document.getElementById('btn-refresh-screen');
    if (btnRefScreen) {
        btnRefScreen.addEventListener('click', () => {
            const serial = document.getElementById('detail-serial').textContent;
            btnRefScreen.innerHTML = '<i data-lucide="loader" class="spin"></i> Đang chụp...';
            lucide.createIcons();
            
            fetch(`/api/devices/${serial}/screenshot`, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    btnRefScreen.innerHTML = '<i data-lucide="camera"></i> Chụp ảnh màn hình mới';
                    lucide.createIcons();
                    if (data.success) {
                        const img = document.getElementById('detail-screen-img');
                        const placeholder = document.getElementById('screen-placeholder');
                        placeholder.style.display = 'none';
                        img.src = data.data + '?t=' + new Date().getTime();
                        img.style.display = 'block';
                    } else {
                        alert("Không chụp được màn hình: " + data.error);
                    }
                });
        });
    }

    // Shell execute inside detail
    const btnSendDetailShell = document.getElementById('btn-submit-detail-shell');
    if (btnSendDetailShell) {
        btnSendDetailShell.addEventListener('click', () => {
            const serial = document.getElementById('detail-serial').textContent;
            const cmd = document.getElementById('detail-shell-cmd').value;
            const resBox = document.getElementById('detail-shell-res');
            if (!cmd) return;
            
            fetch(`/api/devices/${serial}/shell`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: cmd })
            })
            .then(r => r.json())
            .then(data => {
                resBox.style.display = 'block';
                if (data.success) {
                    resBox.innerHTML = `<span style="color:var(--success)">$ ${cmd}</span><br>${data.data.replace(/\n/g, '<br>')}`;
                } else {
                    resBox.innerHTML = `<span style="color:var(--danger)">$ ${cmd}</span><br>${data.error}`;
                }
            });
        });
    }
}

function loadDevicesList() {
    const list = document.getElementById('devices-list');
    if (!list) return;

    fetch('/api/devices')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;
            devicesCache = data.data;
            renderDevicesList(devicesCache);
        });
}

function renderDevicesList(devices) {
    const list = document.getElementById('devices-list');
    if (!list) return;

    const filterVal = document.getElementById('filter-status').value;
    let filtered = devices;
    if (filterVal !== 'all') {
        filtered = devices.filter(d => d.status === filterVal);
    }

    if (filtered.length === 0) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 40px;">Không tìm thấy thiết bị phù hợp.</div>';
        return;
    }

    let html = '';
    filtered.forEach((d, i) => {
        const badgeClass = d.status === 'online' ? 'badge-online' : 
                          (d.status === 'busy' ? 'badge-busy' : 'badge-offline');
        const batColor = d.battery > 50 ? 'var(--success)' : (d.battery > 20 ? 'var(--warning)' : 'var(--danger)');
        
        html += `
        <div class="device-card glass-panel fade-in" style="animation-delay: ${i*0.01}s">
            <div class="device-header">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <label class="custom-checkbox">
                        <input type="checkbox" class="device-select" data-serial="${d.serial}" onchange="updateSelectedCount()">
                        <span class="checkbox-checkmark"></span>
                    </label>
                    <div class="device-name" style="cursor:pointer;" onclick="openDeviceDetail('${d.serial}')">${d.name || d.serial}</div>
                </div>
                <div class="badge ${badgeClass}">${d.status}</div>
            </div>
            <div class="device-thumb" style="cursor:pointer;" onclick="openDeviceDetail('${d.serial}')">
                <i data-lucide="smartphone" style="width: 48px; height: 48px; opacity: 0.3;"></i>
            </div>
            <div class="device-info">
                <div>Serial: <b>${d.serial}</b></div>
                <div>OS: <b>Android ${d.android_version || '?'}</b></div>
                <div>Battery: <b style="color: ${batColor}">${d.battery || '?'}%</b></div>
                <div>IP: <b>${d.ip_address || 'Offline'}</b></div>
            </div>
            <div style="margin-top: 16px; display: flex; gap: 8px;">
                <button class="btn btn-primary" style="flex:1.5; padding: 6px 12px; font-size:12px; display: flex; align-items: center; justify-content: center; gap: 4px; background: linear-gradient(135deg, var(--accent-color), #764ba2);" onclick="mirrorDevice('${d.serial}')">
                    <i data-lucide="tv" style="width: 14px; height: 14px;"></i> Điều khiển
                </button>
                <button class="btn btn-ghost" style="flex:1; padding: 6px; font-size:12px;" onclick="openDeviceDetail('${d.serial}')">Chi tiết</button>
            </div>
        </div>
        `;
    });
    list.innerHTML = html;
    lucide.createIcons();
    updateSelectedCount();
}

window.updateSelectedCount = function() {
    const checked = document.querySelectorAll('.device-select:checked');
    const countEl = document.getElementById('selected-count');
    if (countEl) countEl.textContent = checked.length;
    
    // Enable/disable batch buttons
    const disabled = checked.length === 0;
    const btnReboot = document.getElementById('btn-batch-reboot');
    const btnApk = document.getElementById('btn-batch-apk');
    const btnShell = document.getElementById('btn-batch-shell');
    
    if (btnReboot) btnReboot.disabled = disabled;
    if (btnApk) btnApk.disabled = disabled;
    if (btnShell) btnShell.disabled = disabled;
}

function getSelectedDevices() {
    const checked = document.querySelectorAll('.device-select:checked');
    const serials = [];
    checked.forEach(cb => serials.push(cb.getAttribute('data-serial')));
    return serials;
}

window.openDeviceDetail = function(serial) {
    const dev = devicesCache.find(d => d.serial === serial);
    if (!dev) return;

    document.getElementById('detail-device-title').textContent = dev.name || dev.serial;
    document.getElementById('detail-serial').textContent = dev.serial;
    document.getElementById('detail-android').textContent = 'Android ' + (dev.android_version || '?');
    document.getElementById('detail-battery').textContent = (dev.battery || '?') + '%';
    document.getElementById('detail-ip').textContent = dev.ip_address || 'Offline';
    
    // Reset screenshot view
    const img = document.getElementById('detail-screen-img');
    const placeholder = document.getElementById('screen-placeholder');
    img.style.display = 'none';
    placeholder.style.display = 'block';
    
    // Reset shell input/output
    document.getElementById('detail-shell-cmd').value = '';
    document.getElementById('detail-shell-res').style.display = 'none';
    document.getElementById('detail-shell-res').innerHTML = '';

    openModal('modal-device-detail');
}

window.sendQuickAction = function(cmd) {
    const serial = document.getElementById('detail-serial').textContent;
    fetch(`/api/devices/${serial}/shell`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd })
    })
    .then(r => r.json())
    .then(data => {
        const resBox = document.getElementById('detail-shell-res');
        resBox.style.display = 'block';
        if (data.success) {
            resBox.innerHTML = `<span style="color:var(--success)">$ ${cmd}</span><br>Lệnh đã gửi thành công!`;
        } else {
            resBox.innerHTML = `<span style="color:var(--danger)">$ ${cmd}</span><br>${data.error}`;
        }
    });
}

// ==========================================
// TASKS PAGE CONTROLLER
// ==========================================
function initTasksPage() {
    loadTasks();
    setInterval(loadTasks, 4000); // Poll tasks progress every 4s
    
    // Load devices list into checklists
    fetch('/api/devices')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const wrapper = document.getElementById('task-devices-checkboxes');
                let html = '';
                data.data.forEach(d => {
                    if (d.status !== 'offline') {
                        html += `
                        <label style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                            <input type="checkbox" name="task-target-devices" value="${d.serial}">
                            <span>${d.name || d.serial} (${d.model})</span>
                        </label>
                        `;
                    }
                });
                wrapper.innerHTML = html || '<div style="color:var(--text-secondary); font-size:12px;">Không có thiết bị trực tuyến (online)</div>';
            }
        });

    // Select all task devices checkbox
    const taskSelectAll = document.getElementById('task-select-all-devices');
    if (taskSelectAll) {
        taskSelectAll.addEventListener('change', () => {
            const checked = taskSelectAll.checked;
            document.querySelectorAll('input[name="task-target-devices"]').forEach(cb => {
                cb.checked = checked;
            });
        });
    }

    // Submit Task
    document.getElementById('btn-submit-task').addEventListener('click', () => {
        const name = document.getElementById('task-name').value;
        const type = document.getElementById('task-type').value;
        
        // Get target devices checked
        const devices = [];
        document.querySelectorAll('input[name="task-target-devices"]:checked').forEach(cb => {
            devices.push(cb.value);
        });

        if (!name) return alert("Vui lòng nhập tên Tác vụ!");
        if (devices.length === 0) return alert("Vui lòng chọn ít nhất một thiết bị áp dụng!");

        let scriptData = {};
        if (type === 'INSTALL_APP') {
            scriptData.apk_path = document.getElementById('task-apk-path').value;
            if (!scriptData.apk_path) return alert("Vui lòng điền đường dẫn APK!");
        } else if (type === 'SHELL_CMD') {
            scriptData.command = document.getElementById('task-shell-cmd').value;
            if (!scriptData.command) return alert("Vui lòng nhập lệnh!");
        } else if (type === 'RUN_SCRIPT') {
            // Simulated nurture script JSON
            scriptData.template = document.getElementById('task-script-template').value;
        }

        fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                type: type,
                target_devices: devices,
                script_data: scriptData
            })
        })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                // Auto-start task immediately
                fetch(`/api/tasks/${d.data.id}/start`, { method: 'POST' });
                alert("Tạo và bắt đầu tác vụ thành công!");
                closeModal('modal-create-task');
                loadTasks();
            }
        });
    });
}

window.toggleTaskParams = function() {
    document.querySelectorAll('.task-param-section').forEach(sec => sec.style.display = 'none');
    const type = document.getElementById('task-type').value;
    if (type === 'INSTALL_APP') {
        document.getElementById('section-install-app').style.display = 'block';
    } else if (type === 'SHELL_CMD') {
        document.getElementById('section-shell-cmd').style.display = 'block';
    } else if (type === 'RUN_SCRIPT') {
        document.getElementById('section-run-script').style.display = 'block';
    }
}

function loadTasks() {
    const list = document.getElementById('tasks-list');
    if (!list) return;

    fetch('/api/tasks')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;
            
            let html = '';
            data.data.forEach(t => {
                const statusBadge = t.status === 'completed' ? 'badge-completed' :
                                    (t.status === 'running' ? 'badge-busy' : 
                                    (t.status === 'failed' ? 'badge-failed' : 'badge-pending'));
                
                html += `
                <tr>
                    <td>${t.id}</td>
                    <td><b>${t.name}</b></td>
                    <td><code style="background:rgba(255,255,255,0.05); padding:3px 6px; border-radius:4px; font-size:12px;">${t.type}</code></td>
                    <td>${t.target_devices ? t.target_devices.length : 0} thiết bị</td>
                    <td>
                        <div style="background:rgba(255,255,255,0.05); border-radius:10px; overflow:hidden; height:10px; width:100%; display:flex; margin-bottom: 4px;">
                            <div style="background:var(--accent-gradient); width:${t.progress}%; height:100%;"></div>
                        </div>
                        <span style="font-size:11px; color:var(--text-secondary);">${t.progress}%</span>
                    </td>
                    <td><span class="badge ${statusBadge}">${t.status}</span></td>
                    <td>${t.created_at ? new Date(t.created_at).toLocaleString('vi-VN') : '-'}</td>
                    <td style="text-align:right;">
                        ${t.status === 'running' ? 
                            `<button class="btn btn-ghost" style="padding:4px 8px; font-size:12px; color:var(--warning);" onclick="stopTask(${t.id})">Stop</button>` :
                            `<button class="btn btn-ghost" style="padding:4px 8px; font-size:12px; color:var(--success);" onclick="startTask(${t.id})">Run</button>`
                        }
                        <button class="btn btn-ghost" style="padding:4px 8px; font-size:12px; color:var(--danger);" onclick="deleteTask(${t.id})">Xóa</button>
                    </td>
                </tr>
                `;
            });
            list.innerHTML = html || '<tr><td colspan="8" style="text-align:center; color:var(--text-secondary); padding: 20px;">Không có tác vụ nào được tạo.</td></tr>';
        });
}

window.startTask = function(id) {
    fetch(`/api/tasks/${id}/start`, { method: 'POST' })
        .then(() => loadTasks());
}

window.stopTask = function(id) {
    fetch(`/api/tasks/${id}/stop`, { method: 'POST' })
        .then(() => loadTasks());
}

window.deleteTask = function(id) {
    if (confirm("Xóa tác vụ này?")) {
        fetch(`/api/tasks/${id}`, { method: 'DELETE' })
            .then(() => loadTasks());
    }
}

// ==========================================
// ACCOUNTS PAGE CONTROLLER
// ==========================================
function initAccountsPage() {
    loadAccounts();

    // Add Account Single
    document.getElementById('btn-submit-create-account').addEventListener('click', () => {
        const platform = document.getElementById('acc-platform').value;
        const user = document.getElementById('acc-username').value;
        const pass = document.getElementById('acc-password').value;
        const email = document.getElementById('acc-email').value;
        const phone = document.getElementById('acc-phone').value;
        const cookies = document.getElementById('acc-cookies').value;
        const token = document.getElementById('acc-token').value;
        const notes = document.getElementById('acc-notes').value;

        if (!user || !pass) return alert("Vui lòng điền UID và Mật khẩu!");

        fetch('/api/accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: platform,
                username: user,
                password: pass,
                email: email,
                phone: phone,
                cookies: cookies,
                token: token,
                notes: notes
            })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert("Đã lưu tài khoản thành công!");
                closeModal('modal-create-account');
                loadAccounts();
            }
        });
    });

    // Import Bulk Accounts
    document.getElementById('btn-submit-import-accounts').addEventListener('click', () => {
        const text = document.getElementById('import-accounts-text').value;
        const platform = document.getElementById('import-platform').value;
        if (!text) return alert("Vui lòng dán danh sách tài khoản!");

        fetch('/api/accounts/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ accounts: text, platform: platform })
        })
        .then(r => r.json())
        .then(data => {
            alert(data.message);
            closeModal('modal-import-accounts');
            loadAccounts();
        });
    });
}

function loadAccounts() {
    const list = document.getElementById('accounts-list');
    if (!list) return;

    fetch('/api/accounts')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;
            
            let html = '';
            data.data.forEach(a => {
                const statusBadge = a.status === 'active' ? 'badge-active' : 
                                    (a.status === 'banned' ? 'badge-banned' : 'badge-pending');
                
                html += `
                <tr>
                    <td>${a.id}</td>
                    <td><span style="text-transform:capitalize; font-weight:600;">${a.platform}</span></td>
                    <td><b>${a.username}</b></td>
                    <td><code>${a.password}</code></td>
                    <td>${a.email || '-'}</td>
                    <td>${a.phone || '-'}</td>
                    <td style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                        <span title="Cookie: ${a.cookies || ''}&#10;Token: ${a.token || ''}">${a.cookies || a.token || '-'}</span>
                    </td>
                    <td><code style="color:var(--accent-color); font-weight:bold;">${a.assigned_device_serial || 'Chưa gán'}</code></td>
                    <td><span class="badge ${statusBadge}">${a.status}</span></td>
                    <td style="text-align:right;">
                        <button class="btn btn-ghost" style="padding:4px 8px; font-size:12px; color:var(--danger);" onclick="deleteAccount(${a.id})">Xóa</button>
                    </td>
                </tr>
                `;
            });
            list.innerHTML = html || '<tr><td colspan="10" style="text-align:center; color:var(--text-secondary); padding: 20px;">Không có tài khoản nào trong cơ sở dữ liệu.</td></tr>';
        });
}

window.deleteAccount = function(id) {
    if (confirm("Xóa tài khoản này khỏi cơ sở dữ liệu?")) {
        fetch(`/api/accounts/${id}`, { method: 'DELETE' })
            .then(() => loadAccounts());
    }
}

// ==========================================
// PROXIES PAGE CONTROLLER
// ==========================================
function initProxiesPage() {
    loadProxies();

    // Import Bulk Proxies
    document.getElementById('btn-submit-import-proxies').addEventListener('click', () => {
        const text = document.getElementById('import-proxies-text').value;
        const type = document.getElementById('import-proxy-type').value;
        if (!text) return alert("Vui lòng dán danh sách Proxy!");

        fetch('/api/proxies/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ proxies: text, type: type })
        })
        .then(r => r.json())
        .then(data => {
            alert(data.message);
            closeModal('modal-import-proxies');
            loadProxies();
        });
    });

    // Check All Proxies
    document.getElementById('btn-check-all-proxies').addEventListener('click', () => {
        const btn = document.getElementById('btn-check-all-proxies');
        btn.innerHTML = '<i data-lucide="loader" class="spin"></i> Đang check...';
        lucide.createIcons();
        btn.disabled = true;

        fetch('/api/proxies/check_all', { method: 'POST' })
            .then(() => {
                setTimeout(() => {
                    btn.innerHTML = '<i data-lucide="check-square"></i> Kiểm tra hoạt động (Check All)';
                    lucide.createIcons();
                    btn.disabled = false;
                    loadProxies();
                }, 4000);
            });
    });

    // Clear Dead Proxies
    document.getElementById('btn-clear-dead-proxies').addEventListener('click', () => {
        if (confirm("Bạn có chắc muốn xóa tất cả proxy đã chết?")) {
            fetch('/api/proxies/clear_dead', { method: 'POST' })
                .then(() => loadProxies());
        }
    });
}

function loadProxies() {
    const list = document.getElementById('proxies-list');
    if (!list) return;

    fetch('/api/proxies')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;
            
            let html = '';
            data.data.forEach(p => {
                const statusBadge = p.status === 'alive' ? 'badge-alive' : 
                                    (p.status === 'dead' ? 'badge-dead' : 'badge-unknown');
                
                html += `
                <tr>
                    <td>${p.id}</td>
                    <td><span style="text-transform:uppercase; font-weight:bold; font-size:11px;">${p.type}</span></td>
                    <td><b>${p.host}:${p.port}</b></td>
                    <td>${p.username || '-'}</td>
                    <td><code>${p.password || '-'}</code></td>
                    <td>${p.country || 'Unknown'}</td>
                    <td>${p.last_check ? new Date(p.last_check).toLocaleString('vi-VN') : 'Chưa Check'}</td>
                    <td><span class="badge ${statusBadge}">${p.status}</span></td>
                    <td style="text-align:right;">
                        <button class="btn btn-ghost" style="padding:4px 8px; font-size:12px; color:var(--danger);" onclick="deleteProxy(${p.id})">Xóa</button>
                    </td>
                </tr>
                `;
            });
            list.innerHTML = html || '<tr><td colspan="9" style="text-align:center; color:var(--text-secondary); padding: 20px;">Không có Proxy nào.</td></tr>';
        });
}

window.deleteProxy = function(id) {
    if (confirm("Xóa Proxy này?")) {
        fetch(`/api/proxies/${id}`, { method: 'DELETE' })
            .then(() => loadProxies());
    }
}

// ==========================================
// LOGS PAGE CONTROLLER
// ==========================================
function initLogsPage() {
    loadLogsViewer();

    document.getElementById('btn-refresh-logs').addEventListener('click', loadLogsViewer);
    
    document.getElementById('btn-clear-logs').addEventListener('click', () => {
        if (confirm("Xóa sạch toàn bộ log trong cơ sở dữ liệu?")) {
            fetch('/api/database/clear_logs', { method: 'POST' })
                .then(() => loadLogsViewer());
        }
    });

    document.getElementById('filter-log-level').addEventListener('change', loadLogsViewer);
}

function loadLogsViewer() {
    const box = document.getElementById('logs-viewer-box');
    if (!box) return;

    fetch('/api/logs')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;
            
            const levelVal = document.getElementById('filter-log-level').value;
            let filtered = data.data;
            if (levelVal !== 'all') {
                filtered = data.data.filter(l => l.level === levelVal);
            }

            let html = '';
            filtered.forEach(l => {
                html += `
                <div class="log-row">
                    <span class="log-time">[${l.created_at ? new Date(l.created_at).toLocaleTimeString('vi-VN') : '-'}]</span>
                    <span class="log-level ${l.level.toLowerCase()}">[${l.level}]</span>
                    <span class="log-source">[${l.source || 'SYSTEM'}]</span>: 
                    <span class="log-message">${l.message}</span>
                </div>
                `;
            });
            box.innerHTML = html || '<div style="color:var(--text-secondary); text-align:center; padding: 40px 0;">Không tìm thấy log nào.</div>';
            
            // Auto scroll to bottom
            box.scrollTop = box.scrollHeight;
        });
}

window.mirrorDevice = function(serial) {
    fetch(`/api/devices/${serial}/mirror`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                console.log("Direct control launched for " + serial);
            } else {
                alert("Không thể mở màn hình điều khiển: " + data.error);
            }
        })
        .catch(err => {
            alert("Lỗi kết nối máy chủ: " + err);
        });
}
