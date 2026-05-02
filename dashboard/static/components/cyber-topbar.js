/**
 * CyberTopbar — navigation bar with brand, links, and live status indicator.
 *
 * Props:   wsConnected (Boolean)
 * Events:  refresh
 * Slots:   none
 */
const CyberTopbar = {
    props: {
        wsConnected: { type: Boolean, default: false },
        navLinks: { type: Array, default: () => [
            { href: '/', label: '首页', active: true },
            { href: '/alerts', label: '告警中心' },
            { href: '/report', label: '分析报告' },
            { href: '/docs', label: '接口文档' },
            { href: '/monitoring/dashboard', label: '监控仪表板' },
            { href: '/product/v2?competitor_id=1', label: '产品详情' },
        ]},
    },
    emits: ['refresh'],
    template: `
    <header class="cyber-topbar">
        <div class="cyber-brand">
            <span class="cyber-brand-icon">&#x26A1;</span>
            <span class="cyber-brand-text">赛博监控</span>
            <span class="cyber-version">v2.0</span>
        </div>
        <nav class="cyber-nav">
            <a v-for="link in navLinks" :key="link.href" :href="link.href"
               :class="['cyber-nav-link', { active: link.active }]">
                {{ link.label }}
            </a>
        </nav>
        <div class="cyber-header-right">
            <span class="cyber-connection-status" :class="{ connected: wsConnected }">
                {{ wsConnected ? 'LIVE' : 'OFFLINE' }}
            </span>
            <button class="cyber-btn cyber-btn-sm" @click="$emit('refresh')">&#x21BB; 刷新</button>
        </div>
    </header>
    `
}
