/**
 * StatsRow — four stat cards in a row.
 *
 * Props:  cards (Array of {icon, value, label, sub, trend})
 */
const StatsRow = {
    props: {
        cards: { type: Array, required: true },
    },
    template: `
    <div class="cyber-stats-row">
        <div class="cyber-stat-card" v-for="s in cards" :key="s.label">
            <div class="cyber-stat-icon">{{ s.icon }}</div>
            <div class="cyber-stat-value">{{ s.value }}</div>
            <div class="cyber-stat-label">{{ s.label }}</div>
            <div class="cyber-stat-change" :class="s.trend">{{ s.sub }}</div>
        </div>
    </div>
    `
}
