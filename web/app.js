const { createApp, ref, reactive, onMounted, nextTick } = Vue;

createApp({
    setup() {
        const activeTab = ref('single');
        const jobs = ref([]);
        
        // Single shot state
        const singleShot = reactive({
            prompt: '',
            duration: 4,
            fps: 24,
            workflow: 'stylization_v1'
        });
        const isSubmittingSingle = ref(false);

        // Director plan state
        const directorPlan = reactive({
            prompt: '',
            n_shots: 3,
            duration: 4
        });
        const planShots = ref([]);
        const isPreviewing = ref(false);
        const isRenderingPlan = ref(false);

        // Modal state
        const modal = reactive({
            isOpen: false,
            title: '',
            isLoading: false,
            error: null,
            data: {},
            logs: ''
        });
        const terminalLogs = ref(null);
        let activeWs = null;
        let pollInterval = null;

        // --- API Calls ---
        const api = {
            async startPipeline(data) {
                const res = await fetch('/api/pipeline', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!res.ok) throw new Error('Failed to start pipeline');
                return res.json();
            },
            async fetchDirectorPlan(data) {
                const res = await fetch('/api/director/plan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!res.ok) throw new Error('Failed to fetch plan');
                return res.json();
            },
            async startDirectorRender(data) {
                const res = await fetch('/api/director/render', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!res.ok) throw new Error('Failed to start render');
                return res.json();
            },
            async fetchJobs() {
                const res = await fetch('/api/jobs');
                if (!res.ok) return [];
                return res.json();
            },
            async fetchJobDetails(jobId) {
                const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
                if (!res.ok) return null;
                return res.json();
            },
            async fetchPlanStatus(planId) {
                const res = await fetch(`/api/plans/${encodeURIComponent(planId)}`);
                if (!res.ok) return null;
                return res.json();
            }
        };

        // --- Actions ---
        const refreshJobs = async () => {
            jobs.value = await api.fetchJobs();
        };

        const submitSingleShot = async () => {
            if (!singleShot.prompt.trim()) return;
            isSubmittingSingle.value = true;
            try {
                await api.startPipeline(singleShot);
                singleShot.prompt = '';
                await refreshJobs();
                startJobPolling();
            } catch (err) {
                alert('Error starting pipeline');
            } finally {
                isSubmittingSingle.value = false;
            }
        };

        const previewPlan = async () => {
            if (!directorPlan.prompt.trim()) return alert('Enter a video idea first.');
            isPreviewing.value = true;
            planShots.value = [];
            try {
                const data = await api.fetchDirectorPlan(directorPlan);
                planShots.value = data.shots;
            } catch (err) {
                alert('Error generating plan');
            } finally {
                isPreviewing.value = false;
            }
        };

        const renderPlan = async () => {
            if (!directorPlan.prompt.trim() || planShots.value.length === 0) return;
            isRenderingPlan.value = true;
            try {
                const requestData = {
                    ...directorPlan,
                    shots: planShots.value
                };
                const data = await api.startDirectorRender(requestData);
                openPlanModal(data.plan_id, data.n_shots);
                startJobPolling();
            } catch (err) {
                alert('Error starting render');
            } finally {
                isRenderingPlan.value = false;
            }
        };

        // --- Polling for list ---
        let listPoller = null;
        const startJobPolling = () => {
            let count = 0;
            if (listPoller) clearInterval(listPoller);
            listPoller = setInterval(async () => {
                await refreshJobs();
                count++;
                if (count > 10) clearInterval(listPoller);
            }, 5000);
        };

        // --- Modal Logic ---
        const connectLogs = (id) => {
            modal.logs = 'Connecting to live logs...\n';
            if (activeWs) activeWs.close();
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            activeWs = new WebSocket(`${protocol}//${window.location.host}/ws/logs/${encodeURIComponent(id)}`);
            activeWs.onmessage = (event) => {
                modal.logs += event.data;
                nextTick(() => {
                    if (terminalLogs.value) {
                        terminalLogs.value.scrollTop = terminalLogs.value.scrollHeight;
                    }
                });
            };
            activeWs.onclose = () => modal.logs += '\n[Disconnected from log stream]';
        };

        const openModal = async (jobId) => {
            modal.isOpen = true;
            modal.title = `Job: ${jobId}`;
            modal.isLoading = true;
            modal.error = null;
            connectLogs(jobId);

            const details = await api.fetchJobDetails(jobId);
            modal.isLoading = false;

            if (!details) {
                modal.error = 'Failed to load details';
                return;
            }

            updateModalData(jobId, details);

            if (['created', 'running'].includes(details.record.status)) {
                if (pollInterval) clearInterval(pollInterval);
                pollInterval = setInterval(async () => {
                    const up = await api.fetchJobDetails(jobId);
                    if (up) {
                        updateModalData(jobId, up);
                        if (!['created', 'running'].includes(up.record.status)) {
                            clearInterval(pollInterval);
                            refreshJobs();
                        }
                    }
                }, 3000);
            }
        };

        const updateModalData = (jobId, details) => {
            const baseUrl = `/renders/previews/${encodeURIComponent(jobId)}`;
            const passes = {};
            if (details.manifest?.passes) {
                for (const [k, v] of Object.entries(details.manifest.passes)) {
                    passes[k] = `${baseUrl}/${encodeURIComponent(v)}`;
                }
            }
            const comfy = details.comfy_outputs ? details.comfy_outputs.map(f => `${baseUrl}/comfy_output/${encodeURIComponent(f)}`) : [];
            const videoUrl = details.video ? `${baseUrl}/comfy_output/${encodeURIComponent(details.video)}` : null;

            modal.data = {
                status: details.record.status,
                event: details.record.event,
                video: videoUrl,
                passes,
                comfy_outputs: comfy
            };
        };

        const openPlanModal = (planId, n_shots) => {
            modal.isOpen = true;
            modal.title = `Plan: ${planId}`;
            modal.isLoading = false;
            modal.error = null;
            modal.data = { status: 'running', n_shots };
            connectLogs(planId);

            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(async () => {
                const up = await api.fetchPlanStatus(planId);
                if (up) {
                    modal.data = {
                        status: up.status,
                        n_shots,
                        video: up.video ? `/${up.video}` : null
                    };
                    if (up.status !== 'running') {
                        clearInterval(pollInterval);
                        refreshJobs();
                    }
                }
            }, 4000);
        };

        const closeModal = () => {
            modal.isOpen = false;
            if (activeWs) activeWs.close();
            if (pollInterval) clearInterval(pollInterval);
        };

        onMounted(() => {
            refreshJobs();
        });

        return {
            activeTab, jobs, singleShot, isSubmittingSingle,
            directorPlan, planShots, isPreviewing, isRenderingPlan,
            modal, terminalLogs,
            refreshJobs, submitSingleShot, previewPlan, renderPlan, openModal, closeModal
        };
    }
}).mount('#app');
