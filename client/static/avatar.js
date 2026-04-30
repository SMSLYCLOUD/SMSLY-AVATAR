const API_HEADERS = {
    'X-SMSLY-User-ID': 'demo-user'
};

let activeSession = null;
let webcamStream = null;
let currentSkins = [];

// --- INITIALIZATION ---

document.addEventListener('DOMContentLoaded', () => {
    // Add Tailwind via CDN for styling since we used tailwind classes in HTML
    const script = document.createElement('script');
    script.src = "https://cdn.tailwindcss.com";
    document.head.appendChild(script);

    loadSkins();
    loadSession();
    loadRequests();

    // Poll requests
    setInterval(loadRequests, 5000);
});

// --- UI / TABS ---

function switchTab(tabId) {
    const tabs = ['skins', 'playground', 'settings'];
    tabs.forEach(t => {
        document.getElementById(`tab-${t}`).classList.add('hidden');
        document.getElementById(`tab-btn-${t}`).classList.remove('bg-gray-700', 'text-white');
        document.getElementById(`tab-btn-${t}`).classList.add('text-gray-400');
    });

    document.getElementById(`tab-${tabId}`).classList.remove('hidden');
    document.getElementById(`tab-btn-${tabId}`).classList.remove('text-gray-400');
    document.getElementById(`tab-btn-${tabId}`).classList.add('bg-gray-700', 'text-white');
}

// --- SKINS API ---

async function loadSkins() {
    try {
        const res = await fetch('/api/avatar/skins', { headers: API_HEADERS });
        const skins = await res.json();
        currentSkins = skins;
        renderSkins(skins);
    } catch (e) {
        console.error("Failed to load skins", e);
    }
}

function renderSkins(skins) {
    const container = document.getElementById('skins-list');
    container.innerHTML = '';

    if (skins.length === 0) {
        container.innerHTML = '<div class="text-center text-sm text-gray-500 py-4">No skins uploaded yet.</div>';
        return;
    }

    skins.forEach(skin => {
        const div = document.createElement('div');
        const isActive = activeSession && activeSession.active_skin_id === skin.id;
        const isApproved = skin.moderation_status === 'approved';

        div.className = `skin-card p-3 bg-gray-800 rounded-lg border cursor-pointer transition-all ${isActive ? 'active' : 'border-gray-700 hover:border-gray-500'}`;
        div.onclick = () => selectSkin(skin.id);

        div.innerHTML = `
            <div class="flex gap-3 items-center">
                <img src="${skin.source_image_url}" class="w-12 h-12 rounded object-cover bg-gray-900 border border-gray-700" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0OCIgaGVpZ2h0PSI0OCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iIzM3NDE1MSIvPjwvc3ZnPg=='"/>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-200 truncate">${skin.name}</div>
                    <div class="flex items-center gap-2 mt-1">
                        <span class="text-[10px] uppercase px-1.5 py-0.5 rounded ${isApproved ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'}">
                            ${skin.moderation_status}
                        </span>
                    </div>
                </div>
                ${isActive ? '<span class="text-xs font-bold text-purple-400">ACTIVE</span>' : ''}
                <button class="text-gray-500 hover:text-red-400 ml-2" onclick="event.stopPropagation(); deleteSkin('${skin.id}')">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            </div>
        `;
        container.appendChild(div);
    });
}

async function uploadSkin(event) {
    event.preventDefault();
    const btn = document.getElementById('btn-upload-submit');
    const err = document.getElementById('upload-error');
    err.classList.add('hidden');
    btn.disabled = true;
    btn.textContent = 'Uploading...';

    const name = document.getElementById('upload-name').value;
    const file = document.getElementById('upload-file').files[0];
    const consent = document.getElementById('upload-consent').checked ? 'confirmed' : 'pending';

    const formData = new FormData();
    formData.append('name', name);
    formData.append('source_type', 'upload');
    formData.append('consent_status', consent);
    formData.append('file', file);

    try {
        const res = await fetch('/api/avatar/skins', {
            method: 'POST',
            headers: API_HEADERS,
            body: formData
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Upload failed');
        }

        document.getElementById('upload-modal').classList.add('hidden');
        document.getElementById('upload-form').reset();
        await loadSkins();
    } catch (e) {
        err.textContent = e.message;
        err.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Upload';
    }
}

async function deleteSkin(id) {
    if(!confirm("Delete this skin?")) return;
    try {
        await fetch(`/api/avatar/skins/${id}`, { method: 'DELETE', headers: API_HEADERS });
        loadSkins();
    } catch (e) {
        console.error(e);
    }
}

// --- SESSION / CAMERA ---

let selectedSkinIdForApply = null;

function selectSkin(id) {
    selectedSkinIdForApply = id;

    const skin = currentSkins.find(s => s.id === id);
    const applyBtn = document.getElementById('btn-apply-skin');

    if (skin && skin.moderation_status === 'approved') {
        applyBtn.disabled = false;
        applyBtn.textContent = `Apply ${skin.name}`;
    } else {
        applyBtn.disabled = true;
        applyBtn.textContent = 'Pending Approval';
    }
}

async function activateSelectedSkin() {
    if(!selectedSkinIdForApply) return;

    try {
        const res = await fetch(`/api/avatar/skins/${selectedSkinIdForApply}/activate`, {
            method: 'POST',
            headers: API_HEADERS
        });
        if(res.ok) {
            await loadSkins();
            await loadSession();
            updatePreviewState();
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadSession() {
    try {
        const res = await fetch('/api/avatar/session', { headers: API_HEADERS });
        const session = await res.json();
        if(session) {
            activeSession = session;
            document.getElementById('obs-token').value = session.overlay_token;
            document.getElementById('obs-url').value = `${window.location.origin}/static/avatar-obs.html?token=${session.overlay_token}`;

            if (session.status === 'live') {
                document.getElementById('studio-status-text').textContent = 'Live';
                document.getElementById('studio-status-indicator').className = 'w-2 h-2 rounded-full bg-red-500 animate-pulse';
                document.getElementById('btn-start-session').classList.add('hidden');
                document.getElementById('btn-stop-session').classList.remove('hidden');
                document.getElementById('live-badge').classList.remove('hidden');
                document.getElementById('preview-container').classList.add('preview-active');
                document.getElementById('btn-generate-preview').disabled = false;
                startCamera();
            } else {
                document.getElementById('studio-status-text').textContent = 'Idle';
                document.getElementById('studio-status-indicator').className = 'w-2 h-2 rounded-full bg-yellow-500';
                document.getElementById('btn-start-session').classList.remove('hidden');
                document.getElementById('btn-stop-session').classList.add('hidden');
                document.getElementById('live-badge').classList.add('hidden');
                document.getElementById('preview-container').classList.remove('preview-active');
                document.getElementById('btn-generate-preview').disabled = true;
                stopCamera();
            }
            updatePreviewState();
        }
    } catch (e) {
        console.error("Failed to load session", e);
    }
}

async function startSession() {
    try {
        const res = await fetch('/api/avatar/session/start', {
            method: 'POST',
            headers: {
                ...API_HEADERS,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ source_type: 'webcam' })
        });
        if(res.ok) loadSession();
    } catch (e) {
        console.error(e);
    }
}

async function stopSession() {
    try {
        const res = await fetch('/api/avatar/session/stop', {
            method: 'POST',
            headers: API_HEADERS
        });
        if(res.ok) loadSession();
    } catch (e) {
        console.error(e);
    }
}

async function startCamera() {
    const video = document.getElementById('webcam-video');
    const fallback = document.getElementById('preview-fallback');
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = webcamStream;
        fallback.classList.add('hidden');
    } catch (e) {
        console.error("Camera access denied", e);
        fallback.classList.remove('hidden');
        fallback.innerHTML = `<p class="text-red-400 font-medium">Camera access denied</p>`;
    }
}

function stopCamera() {
    if(webcamStream) {
        webcamStream.getTracks().forEach(t => t.stop());
        webcamStream = null;
    }
    document.getElementById('webcam-video').srcObject = null;
    document.getElementById('preview-fallback').classList.remove('hidden');
    document.getElementById('preview-fallback').innerHTML = `
        <svg class="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
        <p class="font-medium">Camera not active</p>
        <p class="text-sm mt-1">Start session to enable live preview</p>
    `;
}

function updatePreviewState() {
    const activeSkin = currentSkins.find(s => s.id === activeSession?.active_skin_id);
    const imgEl = document.getElementById('processed-preview');

    if (activeSkin && activeSkin.processed_asset_url) {
        imgEl.src = activeSkin.processed_asset_url;
        imgEl.classList.remove('hidden');
    } else {
        imgEl.classList.add('hidden');
        imgEl.src = '';
    }
}

// --- QUEUE ---

async function loadRequests() {
    if (!activeSession) return;
    try {
        const res = await fetch('/api/avatar/requests', { headers: API_HEADERS });
        const requests = await res.json();

        document.getElementById('queue-count').textContent = requests.length;

        const nowPlaying = requests.filter(r => r.status === 'playing');
        const ready = requests.filter(r => r.status === 'approved' || r.status === 'ready');
        const waiting = requests.filter(r => r.status === 'waiting_mod');

        renderQueueCol('queue-now-playing', nowPlaying);
        renderQueueCol('queue-ready', ready);
        renderQueueCol('queue-waiting', waiting);
    } catch (e) {
        console.error(e);
    }
}

function escapeHTML(str) {
    return (str || '').replace(/[&<>'"]/g,
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

function renderQueueCol(id, items) {
    const el = document.getElementById(id);
    if(items.length === 0) {
        el.innerHTML = '<div class="text-center text-sm text-gray-600 py-4">Empty</div>';
        return;
    }

    el.innerHTML = items.map(req => `
        <div class="bg-gray-700/50 rounded-lg p-3 border border-gray-600">
            <div class="text-sm font-medium text-gray-200">${escapeHTML(req.requester_name)}</div>
            <div class="text-xs text-gray-400 truncate" title="${escapeHTML(req.prompt)}">${escapeHTML(req.prompt) || 'No prompt'}</div>
        </div>
    `).join('');
}

// --- SETTINGS / UTILS ---

function copyToken() {
    const el = document.getElementById('obs-token');
    navigator.clipboard.writeText(el.value);
    alert('Copied token');
}

function copyUrl() {
    const el = document.getElementById('obs-url');
    navigator.clipboard.writeText(el.value);
    alert('Copied URL');
}

async function regenerateToken() {
    try {
        const res = await fetch('/api/avatar/obs-source/regenerate-token', { method: 'POST', headers: API_HEADERS });
        const data = await res.json();
        document.getElementById('obs-token').value = data.token;
        document.getElementById('obs-url').value = `${window.location.origin}/static/avatar-obs.html?token=${data.token}`;
    } catch (e) {
        console.error(e);
    }
}

// --- GENERATION (Static Frame) ---

async function generatePreviewFrame() {
    const video = document.getElementById('webcam-video');
    if(!video.srcObject) {
        alert("Camera is not running.");
        return;
    }

    const activeSkin = currentSkins.find(s => s.id === activeSession?.active_skin_id);
    if(!activeSkin) {
        alert("Please apply a skin first.");
        return;
    }

    const btn = document.getElementById('btn-generate-preview');
    btn.disabled = true;
    btn.textContent = 'Generating...';

    try {
        // Capture frame to canvas
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);

        // Convert to blob
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg'));

        // Send to existing transformation API
        const formData = new FormData();
        formData.append('file', blob, 'frame.jpg');
        formData.append('prompt', activeSkin.name + ', high quality, detailed');
        formData.append('strength', '0.6');

        const res = await fetch('/api/transform', {
            method: 'POST',
            body: formData
        });

        if(!res.ok) throw new Error("Transformation failed");

        // For a true implementation, we would save this Blob to backend and update processed_asset_url.
        // Since we are mocking the UI state here, we'll display it directly using object URL.
        const resultBlob = await res.blob();
        const url = URL.createObjectURL(resultBlob);

        document.getElementById('processed-preview').src = url;
        document.getElementById('processed-preview').classList.remove('hidden');

    } catch (e) {
        console.error(e);
        alert("Error generating preview: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generate Frame Preview';
    }
}
