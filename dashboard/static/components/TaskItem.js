// TaskItem 组件 - 任务项

const TaskItem = {
    name: 'TaskItem',
    props: {
        task: {
            type: Object,
            required: true
        }
    },
    emits: ['cancel'],
    computed: {
        statusIcon() {
            const icons = {
                pending: '⏳',
                running: '🔄',
                completed: '✅',
                failed: '❌'
            };
            return icons[this.task.status] || '❓';
        },
        statusClass() {
            return `task-status-${this.task.status}`;
        }
    },
    methods: {
        formatTime(timestamp) {
            if (!timestamp) return '';
            const date = new Date(timestamp);
            return date.toLocaleTimeString('zh-CN', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        },
        getStepIcon(status) {
            const icons = {
                pending: '○',
                running: '◐',
                completed: '●',
                failed: '✗',
                warning: '⚠'
            };
            return icons[status] || '○';
        }
    },
    template: `
        <div class="task-item" :class="statusClass">
            <header class="task-header">
                <span class="task-icon">{{ statusIcon }}</span>
                <span class="task-id">Task {{ task.task_id?.slice(0, 8) || 'unknown' }}</span>
                <span class="task-status">{{ task.status }}</span>
            </header>

            <div class="task-steps" v-if="task.steps && task.steps.length > 0">
                <div
                    v-for="(step, index) in task.steps"
                    :key="index"
                    class="step-item"
                    :class="\`step-\${step.status}\`"
                >
                    <span class="step-icon">{{ getStepIcon(step.status) }}</span>
                    <div class="step-content">
                        <div class="step-header">
                            <span class="step-label">{{ step.label || step.key }}</span>
                            <span class="step-time">{{ formatTime(step.timestamp) }}</span>
                        </div>
                        <div class="step-detail" v-if="step.detail">{{ step.detail }}</div>
                        <div class="step-log" v-if="step.log">{{ step.log }}</div>
                    </div>
                </div>
            </div>

            <div class="task-empty" v-else>
                <span class="empty-text">等待执行...</span>
            </div>

            <div class="task-error" v-if="task.error">
                <span class="error-icon">⚠</span>
                <span class="error-text">{{ task.error }}</span>
            </div>

            <div class="task-result" v-if="task.result">
                <span class="result-icon">📊</span>
                <span class="result-text">
                    完成: {{ task.result.events_count }} 个事件
                </span>
            </div>
        </div>
    `
};
