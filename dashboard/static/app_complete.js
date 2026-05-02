// 竞品监控系统 - 完整前端应用
// Vue 3 Composition API

const { createApp, ref, reactive, computed, onMounted, watch } = Vue;

createApp({
    setup() {
        // ==================== 状态管理 ====================

        // 导航状态
        const currentTab = ref('dashboard');
        const tabs = [
            { id: 'dashboard', label: '仪表板', icon: '📊' },
            { id: 'competitors', label: '竞品', icon: '🎯' },
            { id: 'logs', label: '日志', icon: '📋' }
        ];

        // 系统状态
        const systemOnline = ref(false);
        const loading = reactive({
            competitors: false,
            logs: false,
            add: false,
            fetch: false
        });

        // 数据状态
        const competitors = ref([]);
        const monitoringLogs = ref([]);
        const monitoringStats = reactive({
            total: 0,
            last_24h: 0,
            by_status: {}
        });

        // UI 状态
        const showAddModal = ref(false);
        const showDetailModal = ref(false);
        const selectedCompetitor = ref(null);
        const fetchingId = ref(null);
        const notification = reactive({
            show: false,
            type: 'success',
            message: ''
        });

        // 表单数据
        const newCompetitor = reactive({
            name: '',
            url: ''
        });

        // 日志筛选
        const logFilter = reactive({
            status: ''
        });

        // 任务系统
        const tasks = reactive({});

        // ==================== 计算属性 ====================

        const filteredLogs = computed(() => {
            if (!logFilter.status) return monitoringLogs.value;
            return monitoringLogs.value.filter(log => log.status === logFilter.status);
        });

        // ==================== API 调用 ====================

        const api = {
            // 获取竞品列表
            async getCompetitors() {
                const res = await fetch('/api/competitors');
                return await res.json();
            },

            // 获取单个竞品
            async getCompetitor(id) {
                const res = await fetch(`/api/competitors/${id}`);
                return await res.json();
            },

            // 添加竞品
            async addCompetitor(data) {
                const res = await fetch('/api/competitors', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                return await res.json();
            },

            // 更新竞品
            async updateCompetitor(id, data) {
                const res = await fetch(`/api/competitors/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                return await res.json();
            },

            // 删除竞品
            async deleteCompetitor(id) {
                const res = await fetch(`/api/competitors/${id}`, {
                    method: 'DELETE'
                });
                return await res.json();
            },

            // 触发数据采集
            async fetchData(id) {
                const res = await fetch(`/api/competitors/${id}/fetch`, {
                    method: 'POST'
                });
                return await res.json();
            },

            // 获取监控日志
            async getLogs(competitorId, hours = 168) {
                const res = await fetch(`/api/competitors/${competitorId}/logs?hours=${hours}`);
                return await res.json();
            },

            // 获取监控统计
            async getMonitoringStats() {
                const res = await fetch('/api/monitoring/stats');
                return await res.json();
            },

            // 获取仪表板统计
            async getDashboardStats() {
                const res = await fetch('/api/dashboard/stats');
                return await res.json();
            },

            // 健康检查
            async healthCheck() {
                const res = await fetch('/api/health');
                return await res.json();
            }
        };

        // ==================== 数据加载 ====================

        async function loadCompetitors() {
            loading.competitors = true;
            try {
                const json = await api.getCompetitors();
                if (json.success) {
                    competitors.value = json.data || [];
                    console.log(`✅ 加载了 ${competitors.value.length} 个竞品`);
                } else {
                    showNotification('error', '加载竞品失败: ' + json.error);
                }
            } catch (err) {
                console.error('加载竞品失败:', err);
                showNotification('error', '加载竞品失败');
            } finally {
                loading.competitors = false;
            }
        }

        async function loadMonitoringLogs() {
            loading.logs = true;
            try {
                // 加载统计
                const statsJson = await api.getMonitoringStats();
                if (statsJson.success) {
                    Object.assign(monitoringStats, statsJson.data);
                }

                // 加载所有竞品的日志
                const allLogs = [];
                for (const comp of competitors.value) {
                    const logsJson = await api.getLogs(comp.id, 168);
                    if (logsJson.success && logsJson.data) {
                        allLogs.push(...logsJson.data);
                    }
                }

                // 按时间排序
                monitoringLogs.value = allLogs.sort((a, b) =>
                    new Date(b.timestamp) - new Date(a.timestamp)
                );

                console.log(`✅ 加载了 ${monitoringLogs.value.length} 条日志`);
            } catch (err) {
                console.error('加载日志失败:', err);
            } finally {
                loading.logs = false;
            }
        }

        async function loadAllData() {
            await loadCompetitors();
            await loadMonitoringLogs();
            systemOnline.value = true;
        }

        // ==================== 竞品操作 ====================

        async function addCompetitor() {
            if (!newCompetitor.name || !newCompetitor.url) {
                showNotification('error', '请填写完整信息');
                return;
            }

            loading.add = true;
            try {
                const json = await api.addCompetitor(newCompetitor);
                if (json.success) {
                    showNotification('success', '竞品添加成功');
                    showAddModal.value = false;
                    newCompetitor.name = '';
                    newCompetitor.url = '';
                    await loadCompetitors();
                } else {
                    showNotification('error', '添加失败: ' + json.error);
                }
            } catch (err) {
                console.error('添加竞品失败:', err);
                showNotification('error', '添加失败');
            } finally {
                loading.add = false;
            }
        }

        async function triggerFetch(compId) {
            fetchingId.value = compId;
            try {
                const json = await api.fetchData(compId);
                if (json.success) {
                    const count = json.data?.fetched || 0;
                    showNotification('success', `采集成功，获取 ${count} 条数据`);
                    await loadAllData();
                } else {
                    showNotification('error', '采集失败: ' + json.error);
                }
            } catch (err) {
                console.error('采集失败:', err);
                showNotification('error', '采集失败');
            } finally {
                fetchingId.value = null;
            }
        }

        async function viewDetails(compId) {
            try {
                const json = await api.getCompetitor(compId);
                if (json.success) {
                    selectedCompetitor.value = json.data;
                    showDetailModal.value = true;
                } else {
                    showNotification('error', '加载详情失败');
                }
            } catch (err) {
                console.error('加载详情失败:', err);
                showNotification('error', '加载详情失败');
            }
        }

        async function deleteCompetitor(compId) {
            if (!confirm('确定要删除这个竞品吗？')) return;

            try {
                const json = await api.deleteCompetitor(compId);
                if (json.success) {
                    showNotification('success', '删除成功');
                    await loadCompetitors();
                } else {
                    showNotification('error', '删除失败');
                }
            } catch (err) {
                console.error('删除失败:', err);
                showNotification('error', '删除失败');
            }
        }

        // ==================== 辅助函数 ====================

        function getRecentLogs(competitorId) {
            return monitoringLogs.value
                .filter(log => log.competitor_id === competitorId)
                .slice(0, 5);
        }

        function getCompetitorName(id) {
            const comp = competitors.value.find(c => c.id === id);
            return comp ? comp.name : '未知';
        }

        function formatTime(timestamp) {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            return date.toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        function showNotification(type, message) {
            notification.type = type;
            notification.message = message;
            notification.show = true;
            setTimeout(() => {
                notification.show = false;
            }, 3000);
        }

        // ==================== 生命周期 ====================

        onMounted(async () => {
            console.log('🚀 初始化竞品监控系统...');
            await loadAllData();
        });

        // ==================== 返回 ====================

        return {
            // 状态
            currentTab,
            tabs,
            systemOnline,
            loading,
            competitors,
            monitoringLogs,
            monitoringStats,
            showAddModal,
            showDetailModal,
            selectedCompetitor,
            fetchingId,
            notification,
            newCompetitor,
            logFilter,
            tasks,

            // 计算属性
            filteredLogs,

            // 方法
            loadCompetitors,
            loadMonitoringLogs,
            loadAllData,
            addCompetitor,
            triggerFetch,
            viewDetails,
            deleteCompetitor,
            getRecentLogs,
            getCompetitorName,
            formatTime,
            showNotification
        };
    }
}).mount('#app');
