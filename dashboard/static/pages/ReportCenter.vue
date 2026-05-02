<!--
  报告中心页面
  任务：task-014 - Week 9: 实现个性化设置和报告中心
-->

<template>
  <div class="report-center">
    <div class="report-header">
      <h2>报告中心</h2>
      <button @click="generateReport" class="btn-generate">生成报告</button>
    </div>

    <div class="report-content">
      <!-- 报告筛选 -->
      <div class="report-filters">
        <div class="filter-group">
          <label>报告类型</label>
          <select v-model="filters.reportType" class="filter-select">
            <option value="all">全部</option>
            <option value="price">价格分析</option>
            <option value="sentiment">情感分析</option>
            <option value="competitor">竞品对比</option>
            <option value="trend">趋势预测</option>
          </select>
        </div>
        <div class="filter-group">
          <label>时间范围</label>
          <select v-model="filters.timeRange" class="filter-select">
            <option value="7d">最近7天</option>
            <option value="30d">最近30天</option>
            <option value="90d">最近90天</option>
            <option value="all">全部</option>
          </select>
        </div>
        <div class="filter-group">
          <label>状态</label>
          <select v-model="filters.status" class="filter-select">
            <option value="all">全部</option>
            <option value="completed">已完成</option>
            <option value="pending">生成中</option>
            <option value="failed">失败</option>
          </select>
        </div>
      </div>

      <!-- 报告列表 -->
      <div class="report-list">
        <div
          v-for="report in filteredReports"
          :key="report.id"
          class="report-item"
        >
          <div class="report-info">
            <h3>{{ report.title }}</h3>
            <div class="report-meta">
              <span class="meta-item">
                <strong>类型:</strong> {{ getReportTypeLabel(report.type) }}
              </span>
              <span class="meta-item">
                <strong>生成时间:</strong> {{ report.generatedAt }}
              </span>
              <span class="meta-item">
                <strong>状态:</strong>
                <span :class="['status-badge', report.status]">
                  {{ getStatusLabel(report.status) }}
                </span>
              </span>
            </div>
          </div>
          <div class="report-actions">
            <button @click="viewReport(report)" class="btn-view">查看</button>
            <button @click="downloadReport(report)" class="btn-download">下载</button>
            <button @click="deleteReport(report.id)" class="btn-delete">删除</button>
          </div>
        </div>

        <div v-if="filteredReports.length === 0" class="empty-state">
          <p>暂无报告</p>
        </div>
      </div>

      <!-- 报告统计 -->
      <div class="report-stats">
        <div class="stat-item">
          <span class="stat-label">总报告数</span>
          <span class="stat-value">{{ reports.length }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">已完成</span>
          <span class="stat-value">{{ completedCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">生成中</span>
          <span class="stat-value">{{ pendingCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">失败</span>
          <span class="stat-value">{{ failedCount }}</span>
        </div>
      </div>
    </div>

    <!-- 生成报告对话框 -->
    <div v-if="showGenerateDialog" class="dialog-overlay">
      <div class="dialog">
        <div class="dialog-header">
          <h3>生成报告</h3>
          <button @click="closeGenerateDialog" class="btn-close">关闭</button>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>报告类型</label>
            <select v-model="newReport.type" class="form-select">
              <option value="price">价格分析</option>
              <option value="sentiment">情感分析</option>
              <option value="competitor">竞品对比</option>
              <option value="trend">趋势预测</option>
            </select>
          </div>
          <div class="form-group">
            <label>报告标题</label>
            <input v-model="newReport.title" type="text" class="form-input" placeholder="报告标题">
          </div>
          <div class="form-group">
            <label>时间范围</label>
            <select v-model="newReport.timeRange" class="form-select">
              <option value="7d">最近7天</option>
              <option value="30d">最近30天</option>
              <option value="90d">最近90天</option>
            </select>
          </div>
          <div class="form-group">
            <label>竞品ID（可选）</label>
            <input v-model.number="newReport.competitorId" type="number" class="form-input" placeholder="留空表示全部竞品">
          </div>
        </div>
        <div class="dialog-footer">
          <button @click="confirmGenerateReport" class="btn-confirm">确认生成</button>
          <button @click="closeGenerateDialog" class="btn-cancel">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue';

export default {
  name: 'ReportCenter',
  setup() {
    const filters = ref({
      reportType: 'all',
      timeRange: 'all',
      status: 'all'
    });

    const reports = ref([
      {
        id: 1,
        title: '价格分析报告 - 2026年4月',
        type: 'price',
        generatedAt: '2026-04-26 10:00:00',
        status: 'completed'
      },
      {
        id: 2,
        title: '情感分析报告 - 第17周',
        type: 'sentiment',
        generatedAt: '2026-04-25 15:30:00',
        status: 'completed'
      },
      {
        id: 3,
        title: '竞品对比报告 - Q1',
        type: 'competitor',
        generatedAt: '2026-04-24 09:00:00',
        status: 'pending'
      }
    ]);

    const showGenerateDialog = ref(false);
    const newReport = ref({
      type: 'price',
      title: '',
      timeRange: '30d',
      competitorId: null
    });

    const filteredReports = computed(() => {
      return reports.value.filter(report => {
        if (filters.value.reportType !== 'all' && report.type !== filters.value.reportType) {
          return false;
        }
        if (filters.value.status !== 'all' && report.status !== filters.value.status) {
          return false;
        }
        return true;
      });
    });

    const completedCount = computed(() => reports.value.filter(r => r.status === 'completed').length);
    const pendingCount = computed(() => reports.value.filter(r => r.status === 'pending').length);
    const failedCount = computed(() => reports.value.filter(r => r.status === 'failed').length);

    const getReportTypeLabel = (type) => {
      const labels = {
        price: '价格分析',
        sentiment: '情感分析',
        competitor: '竞品对比',
        trend: '趋势预测'
      };
      return labels[type] || type;
    };

    const getStatusLabel = (status) => {
      const labels = {
        completed: '已完成',
        pending: '生成中',
        failed: '失败'
      };
      return labels[status] || status;
    };

    const generateReport = () => {
      showGenerateDialog.value = true;
      newReport.value = {
        type: 'price',
        title: '',
        timeRange: '30d',
        competitorId: null
      };
    };

    const closeGenerateDialog = () => {
      showGenerateDialog.value = false;
    };

    const confirmGenerateReport = () => {
      const report = {
        id: Date.now(),
        title: newReport.value.title || `${getReportTypeLabel(newReport.value.type)}报告`,
        type: newReport.value.type,
        generatedAt: new Date().toISOString().replace('T', ' ').substring(0, 19),
        status: 'pending'
      };

      reports.value.unshift(report);
      closeGenerateDialog();

      // 模拟报告生成
      setTimeout(() => {
        const index = reports.value.findIndex(r => r.id === report.id);
        if (index !== -1) {
          reports.value[index].status = 'completed';
        }
      }, 3000);
    };

    const viewReport = (report) => {
      console.log('View report:', report);
      alert(`查看报告: ${report.title}`);
    };

    const downloadReport = (report) => {
      console.log('Download report:', report);
      alert(`下载报告: ${report.title}`);
    };

    const deleteReport = (reportId) => {
      if (confirm('确定要删除此报告吗？')) {
        reports.value = reports.value.filter(r => r.id !== reportId);
      }
    };

    return {
      filters,
      reports,
      filteredReports,
      completedCount,
      pendingCount,
      failedCount,
      showGenerateDialog,
      newReport,
      getReportTypeLabel,
      getStatusLabel,
      generateReport,
      closeGenerateDialog,
      confirmGenerateReport,
      viewReport,
      downloadReport,
      deleteReport
    };
  }
};
</script>

<style scoped>
.report-center {
  padding: 20px;
  background: #F9FAFB;
  min-height: 100vh;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding: 20px;
  background: #FFFFFF;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.report-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #1F2937;
}

.btn-generate {
  padding: 10px 20px;
  background: #3B82F6;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-generate:hover {
  background: #2563EB;
}

.report-content {
  background: #FFFFFF;
  border-radius: 8px;
  padding: 30px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.report-filters {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #E5E7EB;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.filter-group label {
  font-size: 12px;
  font-weight: 500;
  color: #6B7280;
}

.filter-select {
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
  min-width: 150px;
}

.report-list {
  margin-bottom: 30px;
}

.report-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  margin-bottom: 15px;
  background: #F9FAFB;
  border-radius: 6px;
  border: 1px solid #E5E7EB;
}

.report-info h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1F2937;
}

.report-meta {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #6B7280;
}

.meta-item {
  display: flex;
  gap: 5px;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.completed {
  background: #D1FAE5;
  color: #065F46;
}

.status-badge.pending {
  background: #FEF3C7;
  color: #92400E;
}

.status-badge.failed {
  background: #FEE2E2;
  color: #991B1B;
}

.report-actions {
  display: flex;
  gap: 8px;
}

.btn-view {
  padding: 6px 12px;
  background: #3B82F6;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn-download {
  padding: 6px 12px;
  background: #10B981;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn-delete {
  padding: 6px 12px;
  background: #EF4444;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #6B7280;
}

.report-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  padding-top: 20px;
  border-top: 1px solid #E5E7EB;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background: #F9FAFB;
  border-radius: 6px;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #6B7280;
  margin-bottom: 5px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #1F2937;
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: #FFFFFF;
  border-radius: 8px;
  width: 500px;
  max-width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #E5E7EB;
}

.dialog-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1F2937;
}

.btn-close {
  padding: 4px 8px;
  background: #F3F4F6;
  color: #374151;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.dialog-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.form-input,
.form-select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  color: #374151;
}

.dialog-footer {
  display: flex;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #E5E7EB;
}

.btn-confirm {
  flex: 1;
  padding: 10px 20px;
  background: #3B82F6;
  color: #FFFFFF;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel {
  padding: 10px 20px;
  background: #F3F4F6;
  color: #374151;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}
</style>
