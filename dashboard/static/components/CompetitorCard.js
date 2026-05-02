// CompetitorCard 组件 - 竞品卡片

const CompetitorCard = {
    name: 'CompetitorCard',
    props: {
        competitor: {
            type: Object,
            required: true
        },
        loading: {
            type: Boolean,
            default: false
        }
    },
    emits: ['fetch', 'skill'],
    template: `
        <article class="card">
            <header class="card-header">
                <h3 class="card-title">{{ competitor.name }}</h3>
                <span :class="['status-badge', \`status-\${competitor.status}\`]">
                    {{ competitor.status }}
                </span>
            </header>

            <div class="card-body">
                <p class="card-url">{{ competitor.url }}</p>

                <div class="metrics-grid">
                    <div class="metric">
                        <span class="metric-label">功能数</span>
                        <span class="metric-value">{{ competitor.metrics?.feature_count || 0 }}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">价格指数</span>
                        <span class="metric-value">{{ competitor.metrics?.price_index || 0 }}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">创新速度</span>
                        <span class="metric-value">{{ (competitor.metrics?.innovation_velocity || 0).toFixed(1) }}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">稳定性</span>
                        <span class="metric-value">{{ (competitor.metrics?.stability_index || 0).toFixed(1) }}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">市场份额</span>
                        <span class="metric-value">{{ (competitor.metrics?.market_share || 0).toFixed(1) }}%</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">用户评分</span>
                        <span class="metric-value">{{ (competitor.metrics?.user_rating || 0).toFixed(1) }}</span>
                    </div>
                </div>
            </div>

            <footer class="card-footer">
                <button
                    class="btn btn-sm"
                    @click="$emit('fetch', competitor.id)"
                    :disabled="loading"
                >
                    {{ loading ? '采集中...' : '采集数据' }}
                </button>
                <button
                    class="btn btn-sm btn-outline"
                    @click="$emit('skill', competitor.id)"
                >
                    Skill 调用
                </button>
            </footer>
        </article>
    `
};
