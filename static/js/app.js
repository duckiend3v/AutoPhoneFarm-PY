document.addEventListener('DOMContentLoaded', () => {
    // Clock
    const clockEl = document.getElementById('clock');
    if (clockEl) {
        setInterval(() => {
            const now = new Date();
            clockEl.textContent = now.toLocaleTimeString('vi-VN');
        }, 1000);
    }

    // Set active nav based on pathname
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === path) {
            link.classList.add('active');
        }
    });

    // Socket.IO
    const socket = io();
    
    socket.on('stats_update', (data) => {
        const totalEl = document.getElementById('stat-total-devices');
        const onlineEl = document.getElementById('stat-online-devices');
        if (totalEl) totalEl.textContent = data.total_devices;
        if (onlineEl) onlineEl.textContent = data.online_devices;
    });

    // Load Dashboard Devices
    if (path === '/') {
        loadDevices();
        setInterval(loadDevices, 5000); // refresh every 5s
    }

    // Scan Button
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
                        if (path === '/') loadDevices();
                    }, 1000);
                });
        });
    }
});

function loadDevices() {
    const container = document.getElementById('device-container');
    if (!container) return;

    fetch('/api/devices')
        .then(res => res.json())
        .then(data => {
            if (!data.success) return;
            
            const devices = data.data;
            if (devices.length === 0) {
                container.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 40px;">No devices connected. Plug in a device and click Scan.</div>';
                return;
            }

            let html = '';
            devices.forEach((d, i) => {
                const badgeClass = d.status === 'online' ? 'badge-online' : 
                                  (d.status === 'busy' ? 'badge-busy' : 'badge-offline');
                const batColor = d.battery > 50 ? 'var(--success)' : (d.battery > 20 ? 'var(--warning)' : 'var(--danger)');
                
                html += `
                <div class="device-card glass-panel fade-in" style="animation-delay: ${i*0.05}s">
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
                        <button class="btn btn-ghost" style="flex:1; padding: 6px;" onclick="action('${d.serial}', 'screenshot')">Capture</button>
                        <button class="btn btn-ghost" style="flex:1; padding: 6px;" onclick="action('${d.serial}', 'reboot')">Reboot</button>
                    </div>
                </div>
                `;
            });
            container.innerHTML = html;
            lucide.createIcons();
        });
}

function action(serial, act) {
    fetch(`/api/devices/${serial}/${act}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if(data.success && act === 'screenshot') {
                // Show modal with screenshot (to be implemented)
                alert("Screenshot saved to: " + data.data);
            }
        });
}
