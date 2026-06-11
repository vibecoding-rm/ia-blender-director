document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('pipeline-form');
    const btnSubmit = document.getElementById('btn-submit');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.getElementById('submit-spinner');
    const jobsContainer = document.getElementById('jobs-container');
    const btnRefresh = document.getElementById('btn-refresh');

    const modal = document.getElementById('job-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const modalContent = document.getElementById('modal-content');
    const modalTitle = document.getElementById('modal-title');

    // --- Tab Switching ---
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
        });
    });

    function esc(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // --- API Calls ---
    async function startPipeline(prompt, duration, fps, workflow) {
        try {
            const res = await fetch('/api/pipeline', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, duration, fps, workflow })
            });
            if (!res.ok) throw new Error('Failed to start pipeline');
            return await res.json();
        } catch (error) {
            console.error(error);
            alert('Error starting pipeline');
        }
    }

    async function fetchDirectorPlan(prompt, n_shots, duration) {
        const res = await fetch('/api/director/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, n_shots, duration })
        });
        if (!res.ok) throw new Error('Failed to fetch plan');
        return await res.json();
    }

    async function startDirectorRender(prompt, n_shots, duration) {
        const res = await fetch('/api/director/render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, n_shots, duration })
        });
        if (!res.ok) throw new Error('Failed to start director render');
        return await res.json();
    }

    async function fetchPlanStatus(planId) {
        const res = await fetch(`/api/plans/${encodeURIComponent(planId)}`);
        if (!res.ok) return null;
        return await res.json();
    }

    async function fetchJobs() {
        try {
            const res = await fetch('/api/jobs');
            if (!res.ok) throw new Error('Failed to fetch jobs');
            return await res.json();
        } catch (error) {
            console.error(error);
            return [];
        }
    }

    async function fetchJobDetails(jobId) {
        try {
            const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
            if (!res.ok) throw new Error('Failed to fetch job details');
            return await res.json();
        } catch (error) {
            console.error(error);
            return null;
        }
    }

    // --- UI Updates ---
    function renderJobsList(jobs) {
        if (!jobs || jobs.length === 0) {
            jobsContainer.innerHTML = '<div class="empty-state">No jobs found. Start a new shot!</div>';
            return;
        }

        jobsContainer.innerHTML = jobs.map(job => `
            <div class="job-card" data-id="${esc(job.job_id)}">
                <div class="job-info">
                    <div class="job-id">${esc(job.job_id)}</div>
                    <div class="job-meta">${esc(new Date(job.timestamp).toLocaleString())} &bull; ${esc(job.profile)}</div>
                </div>
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    ${job.has_video ? '<span class="video-badge">&#9654; video</span>' : ''}
                    <div class="status-badge status-${esc(job.status)}">${esc(job.status)}</div>
                </div>
            </div>
        `).join('');

        document.querySelectorAll('.job-card').forEach(card => {
            card.addEventListener('click', () => openJobModal(card.dataset.id));
        });
    }

    async function refreshJobs() {
        btnRefresh.style.transform = 'rotate(180deg)';
        setTimeout(() => btnRefresh.style.transform = 'rotate(0deg)', 300);
        const jobs = await fetchJobs();
        renderJobsList(jobs);
    }

    // --- Modal Logic ---
    let activeWs = null;
    let modalRefreshInterval = null;
    let currentModalJobId = null;

    function renderModalDetails(details) {
        const { record, manifest, comfy_outputs, video } = details;
        const baseUrl = `/renders/previews/${encodeURIComponent(record.job_id)}`;

        let html = `
            <div style="margin-bottom: 1rem;">
                <strong>Status:</strong> <span class="status-badge status-${esc(record.status)}">${esc(record.status)}</span><br>
                <strong>Last Event:</strong> ${esc(record.event)}
            </div>
        `;

        if (video) {
            const videoSrc = `${baseUrl}/comfy_output/${encodeURIComponent(video)}`;
            html += `
            <h3 style="margin-top: 1.5rem; margin-bottom: 1rem; color: var(--accent);">Final Rendered Video</h3>
            <div class="img-container" style="max-width: 800px; margin: 0 auto; border: 2px solid var(--accent); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(99,102,241,0.3);">
                <video src="${videoSrc}" controls autoplay loop style="width: 100%; display: block;"></video>
            </div>
            `;
        }

        if (manifest && manifest.passes) {
            html += `<h3 style="margin-top: 1.5rem;">Blender Passes</h3><div class="gallery">`;
            for (const [passName, fileName] of Object.entries(manifest.passes)) {
                const src = `${baseUrl}/${encodeURIComponent(fileName)}`;
                html += `
                    <div class="img-container">
                        <img src="${src}" alt="${esc(passName)}" loading="lazy">
                        <div class="img-label">${esc(passName)}</div>
                    </div>
                `;
            }
            html += `</div>`;
        }

        if (comfy_outputs && comfy_outputs.length > 0) {
            html += `<h3 style="margin-top: 1.5rem;">ComfyUI Frames</h3><div class="gallery">`;
            comfy_outputs.forEach(fileName => {
                const src = `${baseUrl}/comfy_output/${encodeURIComponent(fileName)}`;
                html += `
                    <div class="img-container">
                        <img src="${src}" alt="${esc(fileName)}" loading="lazy">
                        <div class="img-label">${esc(fileName)}</div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        if (!manifest && (!comfy_outputs || comfy_outputs.length === 0) && !video) {
            html += '<div class="empty-state">No visual outputs generated yet. Check back later.</div>';
        }

        modalContent.innerHTML = html;
        return record.status;
    }

    async function openJobModal(jobId) {
        currentModalJobId = jobId;
        modalTitle.textContent = `Job: ${jobId}`;
        modalContent.innerHTML = '<div style="text-align:center; padding: 2rem;"><div class="spinner" style="margin: 0 auto; border-top-color: var(--accent);"></div></div>';
        const terminalLogs = document.getElementById('terminal-logs');
        terminalLogs.textContent = 'Connecting to live logs...\n';
        modal.classList.remove('hidden');

        if (activeWs) activeWs.close();
        if (modalRefreshInterval) {
            clearInterval(modalRefreshInterval);
            modalRefreshInterval = null;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs/${encodeURIComponent(jobId)}`;
        activeWs = new WebSocket(wsUrl);

        activeWs.onmessage = (event) => {
            terminalLogs.textContent += event.data;
            terminalLogs.scrollTop = terminalLogs.scrollHeight;
        };
        activeWs.onclose = () => {
            terminalLogs.textContent += '\n[Disconnected from log stream]';
        };

        const details = await fetchJobDetails(jobId);
        if (!details) {
            modalContent.innerHTML = '<div class="empty-state">Failed to load details</div>';
            return;
        }

        const status = renderModalDetails(details);

        if (status === 'running' || status === 'created') {
            modalRefreshInterval = setInterval(async () => {
                if (currentModalJobId !== jobId) {
                    clearInterval(modalRefreshInterval);
                    modalRefreshInterval = null;
                    return;
                }
                const updated = await fetchJobDetails(jobId);
                if (!updated) return;
                const newStatus = renderModalDetails(updated);
                refreshJobs();
                if (newStatus !== 'running' && newStatus !== 'created') {
                    clearInterval(modalRefreshInterval);
                    modalRefreshInterval = null;
                }
            }, 3000);
        }
    }

    function closeModal() {
        currentModalJobId = null;
        modal.classList.add('hidden');
        if (activeWs) {
            activeWs.close();
            activeWs = null;
        }
        if (modalRefreshInterval) {
            clearInterval(modalRefreshInterval);
            modalRefreshInterval = null;
        }
    }

    // --- Director Panel ---
    const btnPreviewPlan = document.getElementById('btn-preview-plan');
    const btnRenderPlan = document.getElementById('btn-render-plan');
    const planPreview = document.getElementById('plan-preview');
    const previewBtnText = document.getElementById('preview-btn-text');
    const previewSpinner = document.getElementById('preview-spinner');
    const renderPlanBtnText = document.getElementById('render-plan-btn-text');
    const renderPlanSpinner = document.getElementById('render-plan-spinner');

    function renderShotCards(shots) {
        if (!shots || shots.length === 0) {
            planPreview.innerHTML = '<div class="empty-state">No shots generated.</div>';
            return;
        }
        planPreview.innerHTML = shots.map((shot, i) => {
            const roleClass = `role-${esc(shot.role || 'shot')}`;
            const weather = shot.weather ? ` · ${esc(shot.weather)}` : '';
            return `
                <div class="shot-card">
                    <span class="shot-number">${i + 1}</span>
                    <span class="shot-role-badge ${roleClass}">${esc(shot.role || 'shot')}</span>
                    <div class="shot-info">
                        <div class="shot-scene">${esc(shot.scene)}</div>
                        <div class="shot-meta">${esc(shot.camera_movement)} · ${esc(shot.lens_mm)}mm${weather} — ${esc(shot.action)}</div>
                    </div>
                </div>
            `;
        }).join('');
    }

    btnPreviewPlan.addEventListener('click', async () => {
        const prompt = document.getElementById('director-prompt').value.trim();
        if (!prompt) { alert('Enter a video idea first.'); return; }

        const n_shots = parseInt(document.getElementById('director-shots').value, 10);
        const duration = parseInt(document.getElementById('director-duration').value, 10);

        btnPreviewPlan.disabled = true;
        previewBtnText.textContent = 'Generating...';
        previewSpinner.classList.remove('hidden');
        planPreview.classList.add('hidden');
        btnRenderPlan.classList.add('hidden');

        try {
            const data = await fetchDirectorPlan(prompt, n_shots, duration);
            renderShotCards(data.shots);
            planPreview.classList.remove('hidden');
            btnRenderPlan.classList.remove('hidden');
        } catch (err) {
            alert('Error generating plan. Check server logs.');
            console.error(err);
        } finally {
            btnPreviewPlan.disabled = false;
            previewBtnText.textContent = 'Preview Plan';
            previewSpinner.classList.add('hidden');
        }
    });

    btnRenderPlan.addEventListener('click', async () => {
        const prompt = document.getElementById('director-prompt').value.trim();
        if (!prompt) return;

        const n_shots = parseInt(document.getElementById('director-shots').value, 10);
        const duration = parseInt(document.getElementById('director-duration').value, 10);

        btnRenderPlan.disabled = true;
        renderPlanBtnText.textContent = 'Launching...';
        renderPlanSpinner.classList.remove('hidden');

        try {
            const data = await startDirectorRender(prompt, n_shots, duration);
            const planId = data.plan_id;

            // Open log modal for the plan
            modalTitle.textContent = `Plan: ${planId}`;
            modalContent.innerHTML = `
                <div style="margin-bottom:1rem;">
                    <strong>Status:</strong> <span class="status-badge status-running">running</span>
                </div>
                <div style="color:var(--text-muted); font-size:0.9rem;">${data.n_shots} shot(s) queued: ${data.job_ids.join(', ')}</div>
            `;
            document.getElementById('terminal-logs').textContent = 'Connecting to plan logs...\n';
            modal.classList.remove('hidden');

            if (activeWs) activeWs.close();
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            activeWs = new WebSocket(`${protocol}//${window.location.host}/ws/logs/${encodeURIComponent(planId)}`);
            activeWs.onmessage = (event) => {
                const logs = document.getElementById('terminal-logs');
                logs.textContent += event.data;
                logs.scrollTop = logs.scrollHeight;
            };

            // Poll plan status
            const planInterval = setInterval(async () => {
                const state = await fetchPlanStatus(planId);
                if (!state) return;

                const badge = `<span class="status-badge status-${esc(state.status)}">${esc(state.status)}</span>`;
                let html = `<div style="margin-bottom:1rem;"><strong>Status:</strong> ${badge}</div>`;
                if (state.video) {
                    html += `
                        <h3 style="margin-top:1.5rem; margin-bottom:1rem; color:var(--accent);">Final Plan Video</h3>
                        <div class="img-container" style="max-width:800px; margin:0 auto; border:2px solid var(--accent); border-radius:12px; overflow:hidden;">
                            <video src="/${esc(state.video)}" controls autoplay loop style="width:100%; display:block;"></video>
                        </div>
                    `;
                } else {
                    html += `<div style="color:var(--text-muted); font-size:0.9rem;">${data.n_shots} shot(s): ${data.job_ids.join(', ')}</div>`;
                }
                modalContent.innerHTML = html;

                if (state.status !== 'running') {
                    clearInterval(planInterval);
                    refreshJobs();
                }
            }, 4000);

        } catch (err) {
            alert('Error starting render. Check server logs.');
            console.error(err);
        } finally {
            btnRenderPlan.disabled = false;
            renderPlanBtnText.textContent = 'Render All Shots';
            renderPlanSpinner.classList.add('hidden');
        }
    });

    // --- Event Listeners ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const prompt = document.getElementById('prompt').value;
        const duration = parseInt(document.getElementById('duration').value, 10);
        const fps = parseInt(document.getElementById('fps').value, 10);
        const workflow = document.getElementById('workflow').value;

        btnSubmit.disabled = true;
        btnText.textContent = 'Starting...';
        spinner.classList.remove('hidden');

        await startPipeline(prompt, duration, fps, workflow);

        btnSubmit.disabled = false;
        btnText.textContent = 'Run Auto-Director';
        spinner.classList.add('hidden');
        document.getElementById('prompt').value = '';

        refreshJobs();
        let polls = 0;
        const interval = setInterval(() => {
            refreshJobs();
            polls++;
            if (polls > 10) clearInterval(interval);
        }, 5000);
    });

    btnRefresh.addEventListener('click', refreshJobs);
    btnCloseModal.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    refreshJobs();
});
