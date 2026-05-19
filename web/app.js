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
            const res = await fetch(`/api/jobs/${jobId}`);
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
            <div class="job-card" data-id="${job.job_id}">
                <div class="job-info">
                    <div class="job-id">${job.job_id}</div>
                    <div class="job-meta">${new Date(job.timestamp).toLocaleString()} • ${job.profile}</div>
                </div>
                <div class="status-badge status-${job.status}">${job.status}</div>
            </div>
        `).join('');

        // Add click listeners to cards
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

    let activeWs = null;

    // --- Modal Logic ---
    async function openJobModal(jobId) {
        modalTitle.textContent = `Job: ${jobId}`;
        modalContent.innerHTML = '<div style="text-align:center; padding: 2rem;"><div class="spinner" style="margin: 0 auto; border-top-color: var(--accent);"></div></div>';
        const terminalLogs = document.getElementById('terminal-logs');
        terminalLogs.textContent = 'Connecting to live logs...\n';
        modal.classList.remove('hidden');

        // Connect WebSocket
        if (activeWs) {
            activeWs.close();
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/logs/${jobId}`;
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
            modalContent.innerHTML = '<div class="empty-state text-danger">Failed to load details</div>';
            return;
        }

        const { record, manifest, comfy_outputs, video } = details;
        const baseUrl = `/renders/previews/${jobId}`;

        let html = `
            <div style="margin-bottom: 1rem;">
                <strong>Status:</strong> <span class="status-badge status-${record.status}">${record.status}</span><br>
                <strong>Last Event:</strong> ${record.event}
            </div>
        `;
        
        if (video) {
            html += `
            <h3 style="margin-top: 1.5rem; margin-bottom: 1rem; color: var(--accent);">Final Rendered Video</h3>
            <div class="img-container" style="max-width: 800px; margin: 0 auto; border: 2px solid var(--accent); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(99,102,241,0.3);">
                <video src="${baseUrl}/comfy_output/${video}" controls autoplay loop style="width: 100%; display: block;"></video>
            </div>
            `;
        }

        if (manifest && manifest.passes) {
            html += `<h3 style="margin-top: 1.5rem;">Blender Passes</h3><div class="gallery">`;
            for (const [passName, fileName] of Object.entries(manifest.passes)) {
                html += `
                    <div class="img-container">
                        <img src="${baseUrl}/${fileName}" alt="${passName}" loading="lazy">
                        <div class="img-label">${passName}</div>
                    </div>
                `;
            }
            html += `</div>`;
        }

        if (comfy_outputs && comfy_outputs.length > 0) {
            html += `<h3 style="margin-top: 1.5rem;">ComfyUI Frames</h3><div class="gallery">`;
            comfy_outputs.forEach(fileName => {
                html += `
                    <div class="img-container">
                        <img src="${baseUrl}/comfy_output/${fileName}" alt="${fileName}" loading="lazy">
                        <div class="img-label">${fileName}</div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        if (!manifest && (!comfy_outputs || comfy_outputs.length === 0) && !video) {
            html += '<div class="empty-state">No visual outputs generated yet. Check back later.</div>';
        }

        modalContent.innerHTML = html;
    }

    function closeModal() {
        modal.classList.add('hidden');
        if (activeWs) {
            activeWs.close();
            activeWs = null;
        }
    }

    // --- Event Listeners ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const prompt = document.getElementById('prompt').value;
        const duration = parseInt(document.getElementById('duration').value, 10);
        const fps = parseInt(document.getElementById('fps').value, 10);
        const workflow = document.getElementById('workflow').value;

        // UI State loading
        btnSubmit.disabled = true;
        btnText.textContent = 'Starting...';
        spinner.classList.remove('hidden');

        await startPipeline(prompt, duration, fps, workflow);

        // Reset UI State
        btnSubmit.disabled = false;
        btnText.textContent = 'Run Auto-Director';
        spinner.classList.add('hidden');
        document.getElementById('prompt').value = '';

        // Trigger refresh and start polling for a bit
        refreshJobs();
        let polls = 0;
        const interval = setInterval(() => {
            refreshJobs();
            polls++;
            if (polls > 10) clearInterval(interval); // Poll 10 times (e.g. 1 min total)
        }, 5000);
    });

    btnRefresh.addEventListener('click', refreshJobs);
    btnCloseModal.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Init
    refreshJobs();
});
