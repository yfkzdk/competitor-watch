/* 竞品监控仪表板 - 主JavaScript文件 */

class CompetitorDashboard {
    constructor() {
        this.baseUrl = window.location.origin;
        this.updateInterval = null;
        this.autoRefresh = true;
        this.autoRefreshInterval = 30000; // 30秒

        this.initialize();
    }

    /**
     * 初始化仪表板
     */
    initialize() {
        console.log('🚀 竞品监控仪表板初始化...');

        // 绑定事件监听器
        this.bindEvents();

        // 加载初始数据
        this.loadDashboardData();

        // 设置自动刷新
        this.startAutoRefresh();

        // 初始化图表
        this.initializeCharts();
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 刷新按钮
        document.getElementById('btnRefresh')?.addEventListener('click', () => {
            this.loadDashboardData();
        });

        // 自动刷新切换
        document.getElementById('toggleAutoRefresh')?.addEventListener('change', (e) => {
            this.autoRefresh = e.target.checked;
            if (this.autoRefresh) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });

        // 执行监控按钮
        document.querySelectorAll('.btn-execute').forEach(button => {
            button.addEventListener('click', (e) => {
                const monitorId = e.target.dataset.monitorId;
                this.executeMonitor(monitorId);
            });
        });

        // 配置切换
        document.querySelectorAll('.config-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchConfigTab(e.target.dataset.tab);
            });
        });

        // 搜索功能
        document.getElementById('searchMonitors')?.addEventListener('input', (e) => {
            this.filterMonitors(e.target.value);
        });
    }

    /**
     * 加载仪表板数据
     */
    async loadDashboardData() {
        try {
            this.showLoading('dashboardContent', '正在加载监控数据...');

            // 并行加载多个API
            const [monitorsData, configsData, statusData] = await Promise.all([
                this.fetchData('/api/monitors'),
                this.fetchData('/api/configs'),
                this.fetchData('/api/status')
            ]);

            // 更新UI
            this.updateMonitors(monitorsData);
            this.updateConfigs(configsData);
            this.updateSystemStatus(statusData);

            // 更新图表数据
            this.updateCharts(monitorsData);

            this.hideLoading('dashboardContent');

            // 显示成功消息
            this.showNotification('监控数据已更新', 'success');

        } catch (error) {
            console.error('加载仪表板数据失败:', error);
            this.showNotification('加载数据失败: ' + error.message, 'error');
            this.hideLoading('dashboardContent');
        }
    }

    /**
     * 获取API数据
     */
    async fetchData(endpoint) {
        const response = await fetch(`${this.baseUrl}${endpoint}`);

        if (!response.ok) {
            throw new Error(`API请求失败: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'API返回错误');
        }

        return data.data;
    }

    /**
     * 更新监控器列表
     */
    updateMonitors(monitorsData) {
        const container = document.getElementById('monitorsList');
        if (!container) return;

        const monitors = monitorsData?.monitors || [];

        if (monitors.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <p>暂无监控器配置</p>
                    <button class="btn btn-primary" onclick="location.href='/config'">
                        添加监控器
                    </button>
                </div>
            `;
            return;
        }

        let html = '';
        monitors.forEach(monitor => {
            const statusClass = this.getStatusClass(monitor.status);
            const trendIcon = this.getTrendIcon(monitor.trend);

            html += `
                <div class="monitor-item" data-monitor-id="${monitor.id}">
                    <div class="monitor-icon">
                        <i class="fas fa-chart-line"></i>
                    </div>
                    <div class="monitor-info">
                        <div class="monitor-name">${monitor.name}</div>
                        <div class="monitor-meta">
                            <span class="status-indicator ${statusClass}">
                                ${this.getStatusText(monitor.status)}
                            </span>
                            <span> | 最后检查: ${this.formatTime(monitor.last_check)}</span>
                            <span> | 数据点: ${monitor.data_points}</span>
                            <span> | 告警: ${monitor.alerts}</span>
                        </div>
                    </div>
                    <div class="monitor-actions">
                        <span class="trend-indicator" title="趋势">
                            ${trendIcon}
                        </span>
                        <button class="btn btn-primary btn-sm btn-execute"
                                data-monitor-id="${monitor.id}">
                            <i class="fas fa-play"></i> 执行
                        </button>
                        <button class="btn btn-outline btn-sm"
                                onclick="dashboard.showMonitorDetails('${monitor.id}')">
                            <i class="fas fa-eye"></i> 详情
                        </button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;

        // 重新绑定执行按钮事件
        container.querySelectorAll('.btn-execute').forEach(button => {
            button.addEventListener('click', (e) => {
                const monitorId = e.target.closest('.btn-execute').dataset.monitorId;
                this.executeMonitor(monitorId);
            });
        });
    }

    /**
     * 更新配置列表
     */
    updateConfigs(configsData) {
        // 更新配置文件列表
        const configFiles = configsData?.config_files || [];
        const container = document.getElementById('configFilesList');

        if (container) {
            if (configFiles.length === 0) {
                container.innerHTML = '<p class="text-muted">暂无配置文件</p>';
            } else {
                let html = '';
                configFiles.forEach(file => {
                    html += `
                        <div class="config-file-item">
                            <div class="file-name">
                                <i class="fas fa-file-code"></i> ${file.name}
                            </div>
                            <div class="file-meta">
                                <small>大小: ${this.formatFileSize(file.size)} |
                                修改: ${this.formatTime(file.modified)}</small>
                            </div>
                            <div class="file-preview">${file.preview}</div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            }
        }

        // 更新生成文件列表
        const generatedFiles = configsData?.generated_files || [];
        const genContainer = document.getElementById('generatedFilesList');

        if (genContainer) {
            if (generatedFiles.length === 0) {
                genContainer.innerHTML = '<p class="text-muted">暂无生成文件</p>';
            } else {
                let html = '';
                generatedFiles.forEach(file => {
                    html += `
                        <div class="config-file-item">
                            <div class="file-name">
                                <i class="fas fa-cogs"></i> ${file.name}
                            </div>
                            <div class="file-meta">
                                <small>监控器: ${file.monitors} |
                                大小: ${this.formatFileSize(file.size)} |
                                修改: ${this.formatTime(file.modified)}</small>
                            </div>
                        </div>
                    `;
                });
                genContainer.innerHTML = html;
            }
        }
    }

    /**
     * 更新系统状态
     */
    updateSystemStatus(statusData) {
        // 更新状态卡片
        const statusCards = [
            { id: 'monitorCount', value: statusData?.monitor_count || 0 },
            { id: 'activeMonitors', value: statusData?.active_monitors || 0 },
            { id: 'systemUptime', value: statusData?.uptime || '未知' },
            { id: 'lastUpdate', value: this.formatTime(statusData?.last_update) || '未知' }
        ];

        statusCards.forEach(card => {
            const element = document.getElementById(card.id);
            if (element) {
                element.textContent = card.value;
            }
        });

        // 更新资源使用情况
        const resources = {
            'cpuUsage': statusData?.cpu_usage?.percent || 0,
            'memoryUsage': statusData?.memory_usage?.percent || 0,
            'diskSpace': statusData?.disk_space?.percent || 0
        };

        Object.entries(resources).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = `${value}%`;

                // 根据值设置颜色
                if (value > 80) {
                    element.style.color = this.getStatusColor('danger');
                } else if (value > 60) {
                    element.style.color = this.getStatusColor('warning');
                } else {
                    element.style.color = this.getStatusColor('success');
                }
            }
        });
    }

    /**
     * 初始化图表
     */
    initializeCharts() {
        // 如果有Chart.js，初始化图表
        if (typeof Chart !== 'undefined') {
            this.charts = {};

            // 监控活动图表
            const monitorActivityCtx = document.getElementById('monitorActivityChart');
            if (monitorActivityCtx) {
                this.charts.monitorActivity = new Chart(monitorActivityCtx, {
                    type: 'line',
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'top' },
                        }
                    }
                });
            }

            // 状态分布图表
            const statusDistributionCtx = document.getElementById('statusDistributionChart');
            if (statusDistributionCtx) {
                this.charts.statusDistribution = new Chart(statusDistributionCtx, {
                    type: 'doughnut',
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom' }
                        }
                    }
                });
            }
        }
    }

    /**
     * 更新图表数据
     */
    updateCharts(monitorsData) {
        if (!this.charts) return;

        const monitors = monitorsData?.monitors || [];

        // 更新监控活动图表 - 使用真实API数据
        if (this.charts.monitorActivity) {
            this.fetchData('/api/monitor/stats').then(stats => {
                const history = stats?.activity_history || [];
                if (history.length > 0) {
                    this.charts.monitorActivity.data = {
                        labels: history.map(h => this.formatTime(h.timestamp, true)),
                        datasets: [{
                            label: '监控活动',
                            data: history.map(h => h.value),
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            fill: true,
                            tension: 0.4
                        }]
                    };
                    this.charts.monitorActivity.update();
                }
            }).catch(() => {
                // 数据不可用时不更新图表
                console.warn('监控活动历史数据不可用');
            });
        }

        // 更新状态分布图表
        if (this.charts.statusDistribution) {
            const statusCounts = {
                active: monitors.filter(m => m.status === 'active').length,
                inactive: monitors.filter(m => m.status === 'inactive').length,
                warning: monitors.filter(m => m.status === 'warning').length
            };

            this.charts.statusDistribution.data = {
                labels: ['活跃', '未激活', '警告'],
                datasets: [{
                    data: [statusCounts.active, statusCounts.inactive, statusCounts.warning],
                    backgroundColor: [
                        'rgba(46, 204, 113, 0.8)',
                        'rgba(149, 165, 166, 0.8)',
                        'rgba(243, 156, 18, 0.8)'
                    ],
                    borderWidth: 1
                }]
            };
            this.charts.statusDistribution.update();
        }
    }

    /**
     * 执行监控任务
     */
    async executeMonitor(monitorId) {
        try {
            this.showLoading(`monitor-${monitorId}`, '正在执行监控...');

            const response = await fetch(`${this.baseUrl}/api/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ monitor_id: monitorId })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification(`监控任务 ${monitorId} 执行成功`, 'success');

                // 刷新数据
                setTimeout(() => {
                    this.loadDashboardData();
                }, 1000);

            } else {
                throw new Error(result.error || '执行失败');
            }

        } catch (error) {
            console.error('执行监控失败:', error);
            this.showNotification(`执行监控失败: ${error.message}`, 'error');

        } finally {
            this.hideLoading(`monitor-${monitorId}`);
        }
    }

    /**
     * 显示监控详情
     */
    showMonitorDetails(monitorId) {
        // 可以在这里实现详情模态框
        alert(`监控详情: ${monitorId}\n功能待实现...`);
    }

    /**
     * 切换配置标签页
     */
    switchConfigTab(tabName) {
        // 更新标签页状态
        document.querySelectorAll('.config-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // 显示对应内容
        document.querySelectorAll('.config-content').forEach(content => {
            content.style.display = content.id === `${tabName}Content` ? 'block' : 'none';
        });
    }

    /**
     * 过滤监控器
     */
    filterMonitors(searchTerm) {
        const items = document.querySelectorAll('.monitor-item');
        const term = searchTerm.toLowerCase();

        items.forEach(item => {
            const name = item.querySelector('.monitor-name').textContent.toLowerCase();
            const shouldShow = name.includes(term) || term === '';
            item.style.display = shouldShow ? 'flex' : 'none';
        });
    }

    /**
     * 开始自动刷新
     */
    startAutoRefresh() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }

        this.updateInterval = setInterval(() => {
            if (this.autoRefresh && document.visibilityState === 'visible') {
                this.loadDashboardData();
            }
        }, this.autoRefreshInterval);

        console.log(`🔄 自动刷新已启动，间隔: ${this.autoRefreshInterval}ms`);
    }

    /**
     * 停止自动刷新
     */
    stopAutoRefresh() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
        console.log('⏸️ 自动刷新已停止');
    }

    /**
     * 显示加载状态
     */
    showLoading(elementId, message = '加载中...') {
        const element = document.getElementById(elementId);
        if (element) {
            const loadingHtml = `
                <div class="loading-overlay" id="loading-${elementId}">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">${message}</div>
                </div>
            `;
            element.insertAdjacentHTML('beforeend', loadingHtml);
        }
    }

    /**
     * 隐藏加载状态
     */
    hideLoading(elementId) {
        const loadingElement = document.getElementById(`loading-${elementId}`);
        if (loadingElement) {
            loadingElement.remove();
        }
    }

    /**
     * 显示通知
     */
    showNotification(message, type = 'info') {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        // 添加到页面
        const container = document.getElementById('notifications') || document.body;
        if (!document.getElementById('notifications')) {
            const notificationsContainer = document.createElement('div');
            notificationsContainer.id = 'notifications';
            notificationsContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
                max-width: 400px;
            `;
            document.body.appendChild(notificationsContainer);
            container = notificationsContainer;
        }

        container.appendChild(notification);

        // 自动移除
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * 工具函数
     */
    getStatusClass(status) {
        const classes = {
            'active': 'status-active',
            'inactive': 'status-inactive',
            'warning': 'status-warning',
            'danger': 'status-danger'
        };
        return classes[status] || 'status-inactive';
    }

    getStatusText(status) {
        const texts = {
            'active': '活跃',
            'inactive': '未激活',
            'warning': '警告',
            'danger': '危险'
        };
        return texts[status] || '未知';
    }

    getStatusColor(status) {
        const colors = {
            'success': '#2ecc71',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'active': '#3498db',
            'inactive': '#95a5a6'
        };
        return colors[status] || '#95a5a6';
    }

    getTrendIcon(trend) {
        const icons = {
            'up': '↗️',
            'down': '↘️',
            'stable': '→',
            'up': '↑',
            'down': '↓'
        };
        return icons[trend] || '→';
    }

    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    formatTime(timestamp, short = false) {
        if (!timestamp) return '未知';

        const date = new Date(timestamp);

        if (short) {
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        return date.toLocaleString();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 带验证的数据获取 - 数据不可用时显示提示
     */
    async fetchDataWithValidation(endpoint) {
        try {
            const data = await this.fetchData(endpoint);
            if (!data) {
                this.showNotification('数据不可用，请先触发数据采集', 'warning');
            }
            return data;
        } catch (error) {
            this.showNotification('数据获取失败: ' + error.message, 'error');
            return null;
        }
    }

    /**
     * 显示数据采集中提示
     */
    showDataPendingMessage(retryMinutes = 30) {
        const container = document.getElementById('dashboardContent');
        if (!container) return;
        container.innerHTML = `
            <div style="text-align:center;padding:40px;color:#7f8c8d;">
                <i class="fas fa-database" style="font-size:48px;color:#f39c12;margin-bottom:16px;"></i>
                <h3>数据采集与清洗中</h3>
                <p>系统正在获取并验证竞品数据，预计 ${retryMinutes} 分钟后更新</p>
                <p style="font-size:13px;margin-top:8px;">请先触发数据采集：POST /api/competitors/&lt;id&gt;/fetch</p>
                <button onclick="dashboard.loadDashboardData()" style="margin-top:16px;padding:8px 20px;background:#3498db;color:white;border:none;border-radius:6px;cursor:pointer;">
                    <i class="fas fa-sync-alt"></i> 重新获取
                </button>
            </div>
        `;
    }

    /**
     * 销毁清理
     */
    destroy() {
        this.stopAutoRefresh();

        // 清理事件监听器
        document.querySelectorAll('.btn-execute').forEach(button => {
            button.replaceWith(button.cloneNode(true));
        });

        console.log('🧹 仪表板已清理');
    }
}

// 全局仪表板实例
let dashboard;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    dashboard = new CompetitorDashboard();

    // 页面可见性变化处理
    document.addEventListener('visibilitychange', () => {
        if (dashboard.autoRefresh && document.visibilityState === 'visible') {
            dashboard.loadDashboardData();
        }
    });

    // 页面卸载前清理
    window.addEventListener('beforeunload', () => {
        if (dashboard) {
            dashboard.destroy();
        }
    });
});

// 导出到全局
if (typeof window !== 'undefined') {
    window.dashboard = dashboard;
}