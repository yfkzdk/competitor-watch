// TaskQueue 组件 - 任务队列

const TaskQueue = {
    name: 'TaskQueue',
    props: {
        tasks: {
            type: Object,
            required: true
        }
    },
    emits: ['cancel'],
    computed: {
        taskList() {
            return Object.entries(this.tasks)
                .map(([id, task]) => ({ ...task, task_id: id }))
                .sort((a, b) => {
                    // 按状态排序：running > pending > completed > failed
                    const order = { running: 0, pending: 1, completed: 2, failed: 3 };
                    return (order[a.status] || 99) - (order[b.status] || 99);
                });
        },
        runningCount() {
            return this.taskList.filter(t => t.status === 'running').length;
        },
        pendingCount() {
            return this.taskList.filter(t => t.status === 'pending').length;
        }
    },
    template: `
        <div class="task-queue">
            <header class="queue-header">
                <h3 class="queue-title">任务队列</h3>
                <div class="queue-stats">
                    <span class="stat running" v-if="runningCount > 0">
                        🔄 {{ runningCount }} 运行中
                    </span>
                    <span class="stat pending" v-if="pendingCount > 0">
                        ⏳ {{ pendingCount }} 等待中
                    </span>
                    <span class="stat total">
                        共 {{ taskList.length }} 个任务
                    </span>
                </div>
            </header>

            <div class="queue-body">
                <div v-if="taskList.length === 0" class="queue-empty">
                    <span class="empty-icon">📭</span>
                    <span class="empty-text">暂无任务</span>
                </div>

                <div v-else class="queue-list">
                    <TaskItem
                        v-for="task in taskList"
                        :key="task.task_id"
                        :task="task"
                        @cancel="$emit('cancel', task.task_id)"
                    />
                </div>
            </div>
        </div>
    `
};
