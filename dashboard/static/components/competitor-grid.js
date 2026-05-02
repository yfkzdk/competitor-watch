/**
 * CompetitorGrid — responsive grid of competitor cards.
 *
 * Props:  competitors (Array)
 * Events: select (competitor)
 */
const CompetitorGrid = {
    props: {
        competitors: { type: Array, required: true },
    },
    emits: ['select'],
    template: `
    <div class="cyber-comp-grid">
        <div v-for="comp in competitors" :key="comp.id"
             class="cyber-comp-card" @click="$emit('select', comp)">
            <div class="cyber-comp-header">
                <div class="cyber-comp-name">{{ comp.name }}</div>
                <div :class="['cyber-comp-status', comp.status === 'active' ? 'status-monitoring' : 'status-paused']">
                    {{ comp.status === 'active' ? '监控中' : '已暂停' }}
                </div>
            </div>
            <div class="cyber-comp-url">{{ comp.url }}</div>
            <div class="cyber-comp-metrics">
                <div class="cyber-comp-metric">
                    <div class="cyber-comp-metric-value">{{ (comp.metrics?.market_share || 0).toFixed(1) }}%</div>
                    <div class="cyber-comp-metric-label">市场份额</div>
                </div>
                <div class="cyber-comp-metric">
                    <div class="cyber-comp-metric-value">{{ (comp.metrics?.user_rating || 0).toFixed(1) }}</div>
                    <div class="cyber-comp-metric-label">用户评分</div>
                </div>
                <div class="cyber-comp-metric">
                    <div class="cyber-comp-metric-value">{{ (comp.metrics?.growth || 0).toFixed(1) }}%</div>
                    <div class="cyber-comp-metric-label">增长率</div>
                </div>
            </div>
        </div>
    </div>
    `
}
