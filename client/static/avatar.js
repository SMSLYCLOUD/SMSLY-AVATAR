const API_HEADERS = {
    'X-SMSLY-User-ID': 'demo-user'
};

let activeSession = null;
let webcamStream = null;
let currentSkins = [];
let previewMode = "camera"; // "camera" | "avatar_output"

// --- INITIALIZATION ---

document.addEventListener('DOMContentLoaded', () => {
    // Add Tailwind via CDN for styling since we used tailwind classes in HTML
    const script = document.createElement('script');
    script.src = "https://cdn.tailwindcss.com";
    document.head.appendChild(script);

    loadSkins();
    loadSession();
    loadRequests();
    loadOpenRouterSettings();

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

        let reasonTooltip = '';
        if (!isApproved && skin.moderation_status !== 'pending') {
            reasonTooltip = 'title="Moderation Flagged: Content review pending/failed"';
        }

        div.className = `skin-card p-3 bg-gray-800 rounded-lg border cursor-pointer transition-all ${isActive ? 'active border-purple-500' : 'border-gray-700 hover:border-gray-500'}`;
        div.onclick = () => selectSkin(skin.id);

        const thumbnail = skin.thumbnail_url || skin.processed_asset_url || skin.source_image_url;

        div.innerHTML = `
            <div class="flex gap-3 items-center">
                <img src="${thumbnail}" class="w-12 h-12 rounded object-cover bg-gray-900 border ${isActive ? 'border-purple-500' : 'border-gray-700'}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0OCIgaGVpZ2h0PSI0OCI+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iIzM3NDE1MSIvPjwvc3ZnPg=='"/>
                <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-200 truncate">${skin.name}</div>
                    <div class="flex items-center gap-2 mt-1">
                        <span ${reasonTooltip} class="text-[10px] uppercase px-1.5 py-0.5 rounded ${isApproved ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'} cursor-help">
                            ${skin.moderation_status}
                        </span>
                        <span class="text-[10px] uppercase px-1.5 py-0.5 rounded ${skin.consent_status === 'confirmed' ? 'bg-blue-900/50 text-blue-400' : 'bg-gray-700 text-gray-400'}">
                            ${skin.consent_status === 'confirmed' ? 'Consent ✅' : 'No Consent ⚠️'}
                        </span>
                    </div>
                </div>
                ${isActive ? '<span class="text-[10px] font-bold text-purple-400 tracking-wider">ACTIVE</span>' : ''}
                <button class="text-gray-500 hover:text-red-400 ml-2 p-1" onclick="event.stopPropagation(); deleteSkin('${skin.id}')" title="Delete Skin">
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

            // Do not override user's preview mode, but ensure we render correctly
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

function setPreviewMode(mode) {
    previewMode = mode;

    const btnCamera = document.getElementById('btn-mode-camera');
    const btnAvatar = document.getElementById('btn-mode-avatar');

    if (mode === 'camera') {
        btnCamera.classList.add('bg-gray-700', 'text-white');
        btnCamera.classList.remove('text-gray-400');
        btnAvatar.classList.remove('bg-gray-700', 'text-white');
        btnAvatar.classList.add('text-gray-400');
    } else {
        btnAvatar.classList.add('bg-gray-700', 'text-white');
        btnAvatar.classList.remove('text-gray-400');
        btnCamera.classList.remove('bg-gray-700', 'text-white');
        btnCamera.classList.add('text-gray-400');
    }

    updatePreviewState();
}

function updatePreviewState() {
    const activeSkin = currentSkins.find(s => s.id === activeSession?.active_skin_id);
    const imgEl = document.getElementById('processed-preview');
    const videoEl = document.getElementById('webcam-video');
    const fallbackEl = document.getElementById('preview-fallback');

    if (previewMode === 'avatar_output') {
        videoEl.classList.add('hidden');
        if (activeSkin && activeSkin.processed_asset_url) {
            imgEl.src = activeSkin.processed_asset_url;
            imgEl.classList.remove('hidden');
            fallbackEl.classList.add('hidden');
        } else {
            imgEl.classList.add('hidden');
            imgEl.src = '';
            fallbackEl.classList.remove('hidden');
            fallbackEl.innerHTML = `
                <p class="font-medium text-gray-400">No generated avatar output yet.</p>
                <p class="text-sm mt-1 text-gray-500">Capture a frame to create one.</p>
            `;
        }
    } else {
        imgEl.classList.add('hidden');
        if (webcamStream) {
            videoEl.classList.remove('hidden');
            fallbackEl.classList.add('hidden');
        } else {
            videoEl.classList.add('hidden');
            fallbackEl.classList.remove('hidden');
            fallbackEl.innerHTML = `
                <svg class="w-16 h-16 mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                <p class="font-medium">Camera not active</p>
                <p class="text-sm mt-1">Start session to enable live preview</p>
            `;
        }
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

// --- SETTINGS / OPENROUTER ---

function loadOpenRouterSettings() {
    const key = localStorage.getItem('openrouter_key');
    const model = localStorage.getItem('openrouter_model') || 'openai/gpt-4o-mini';
    const customModel = localStorage.getItem('openrouter_model_custom') || '';

    if (key) {
        document.getElementById('openrouter-key').value = key;
        document.getElementById('openrouter-status').textContent = 'Status: Configured (Browser Storage)';
        document.getElementById('openrouter-status').classList.replace('text-gray-500', 'text-green-500');
    }

    const selectEl = document.getElementById('openrouter-model');
    const options = Array.from(selectEl.options).map(o => o.value);

    if (options.includes(model)) {
        selectEl.value = model;
    } else {
        selectEl.value = 'custom';
        document.getElementById('openrouter-model-custom').value = customModel;
        document.getElementById('openrouter-model-custom').classList.remove('hidden');
    }

    selectEl.addEventListener('change', (e) => {
        if (e.target.value === 'custom') {
            document.getElementById('openrouter-model-custom').classList.remove('hidden');
        } else {
            document.getElementById('openrouter-model-custom').classList.add('hidden');
        }
    });
}

function saveOpenRouterKey() {
    const key = document.getElementById('openrouter-key').value;
    const model = document.getElementById('openrouter-model').value;
    const customModel = document.getElementById('openrouter-model-custom').value;

    if (key) localStorage.setItem('openrouter_key', key);
    localStorage.setItem('openrouter_model', model);
    if (model === 'custom') {
        localStorage.setItem('openrouter_model_custom', customModel);
    }

    document.getElementById('openrouter-status').textContent = 'Status: Configured (Browser Storage)';
    document.getElementById('openrouter-status').classList.replace('text-gray-500', 'text-green-500');
    alert('Settings saved to local storage.');
}

function clearOpenRouterKey() {
    localStorage.removeItem('openrouter_key');
    document.getElementById('openrouter-key').value = '';
    document.getElementById('openrouter-status').textContent = 'Status: Not configured (Demo/local only)';
    document.getElementById('openrouter-status').classList.replace('text-green-500', 'text-gray-500');
}

function toggleOpenRouterKeyVisibility() {
    const el = document.getElementById('openrouter-key');
    el.type = el.type === 'password' ? 'text' : 'password';
}

function getOpenRouterSettings() {
    const model = localStorage.getItem('openrouter_model') || 'openai/gpt-4o-mini';
    return {
        key: localStorage.getItem('openrouter_key') || '',
        model: model === 'custom' ? localStorage.getItem('openrouter_model_custom') : model
    };
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

// --- PLAYGROUND ---

async function generatePlaygroundPrompt() {
    const btn = document.getElementById('btn-generate-prompt');
    const err = document.getElementById('playground-error');
    const idea = document.getElementById('playground-idea').value;
    const style = document.getElementById('playground-style').value;

    if (!idea) {
        err.textContent = "Idea cannot be empty.";
        err.classList.remove('hidden');
        return;
    }

    err.classList.add('hidden');
    btn.disabled = true;
    btn.textContent = "Generating...";

    const settings = getOpenRouterSettings();

    try {
        const res = await fetch('/api/avatar/prompts/generate', {
            method: 'POST',
            headers: {
                ...API_HEADERS,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                idea: idea,
                style: style,
                model: settings.model,
                openrouter_api_key: settings.key
            })
        });

        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.detail || "Generation failed");
        }

        document.getElementById('playground-generated-prompt').value = data.prompt;
        document.getElementById('playground-result-container').classList.remove('hidden');
        document.getElementById('playground-result-container').classList.add('flex');

    } catch (e) {
        err.textContent = e.message;
        err.classList.remove('hidden');
    } finally {
        btn.disabled = false;
        btn.textContent = "Generate Prompt";
    }
}

function useGeneratedPrompt() {
    const prompt = document.getElementById('playground-generated-prompt').value;
    if (!prompt) return;

    // Copy to clipboard or ideally pass to a generation form
    navigator.clipboard.writeText(prompt);
    alert("Prompt copied to clipboard. You can paste it into the frame preview test (once fully integrated)!");
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
        formData.append('prompt', activeSkin.name + ', synthetic avatar, high quality, detailed, best quality, 8k');
        formData.append('strength', '0.6');

        const res = await fetch(`/api/avatar/skins/${activeSkin.id}/generate-preview`, {
            method: 'POST',
            headers: API_HEADERS,
            body: formData
        });

        if(!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || "Transformation failed");
        }

        const data = await res.json();

        // Update local skins state
        const index = currentSkins.findIndex(s => s.id === data.skin.id);
        if (index !== -1) {
            currentSkins[index] = data.skin;
        }

        // Show performance string
        if (data.performance) {
            const badge = document.getElementById('performance-badge');
            badge.textContent = `Generated in ${data.performance.generation_time}s on ${data.performance.device.toUpperCase()}`;
            badge.classList.remove('hidden');
        }

        setPreviewMode('avatar_output');

    } catch (e) {
        console.error(e);
        alert("Error generating preview: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Generate Frame Preview';
    }
}
