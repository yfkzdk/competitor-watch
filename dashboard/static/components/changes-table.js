/**
 * ChangesTable — sortable table of recent competitor changes.
 *
 * Props:  changes (Array of {id, competitor_name, change_type, new_value, severity, detected_at})
 * Events: none
 */
const ChangesTable = {
    props: {
        changes: { type: Array, required: true },
    },
    methods: {
        formatDate(d) {
            if (!d) return ''
            return new Date(d).toLocaleString('zh-CN', {
                month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
            })
        },
    },
    template: `
    <div class="cyber-panel">
        <div class="cyber-panel-header">
            <h2 class="cyber-panel-title">最近变更</h2>
        </div>
        <div class="cyber-panel-body">
            <table class="cyber-table" v-if="changes.length">
                <thead>
                    <tr>
                        <th>竞品</th>
                        <th>变更类型</th>
                        <th>描述</th>
                        <th>严重度</th>
                        <th>时间</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="c in changes" :key="c.id">
                        <td>{{ c.competitor_name || '#' + c.competitor_id }}</td>
                        <td><span class="cyber-badge">{{ c.change_type }}</span></td>
                        <td>{{ c.new_value || c.field_name }}</td>
                        <td><span :class="['cyber-severity', 'sev-' + (c.severity || 'info').toLowerCase()]">{{ c.severity }}</span></td>
                        <td>{{ formatDate(c.detected_at) }}</td>
                    </tr>
                </tbody>
            </table>
            <div v-else class="cyber-empty-state">暂无变更数据</div>
        </div>
    </div>
    `
}
