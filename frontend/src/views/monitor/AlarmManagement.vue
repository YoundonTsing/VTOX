<template>
  <div class="alarm-management-container">
    <h2 class="page-title">告警管理</h2>
    <p class="page-description">
      集中管理和处理所有系统生成的告警信息，确保及时响应和处理。
    </p>

    <!-- 筛选区域 -->
    <div class="filter-section">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-select v-model="filters.level" placeholder="告警级别" style="width: 100%;">
            <el-option label="全部级别" value="all" />
            <el-option label="预警" value="warning" />
            <el-option label="故障" value="fault" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filters.status" placeholder="处理状态" style="width: 100%;">
            <el-option label="全部状态" value="all" />
            <el-option label="未确认" value="unacknowledged" />
            <el-option label="已确认" value="acknowledged" />
          </el-select>
        </el-col>
        <el-col :span="8">
          <el-date-picker
            v-model="filters.timeRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%;"
          />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="fetchAlarms">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-col>
      </el-row>
    </div>

    <!-- 统计信息 -->
    <el-row :gutter="20" class="stats-section">
      <el-col :span="8">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-title">总告警数</div>
          <div class="stat-value">{{ totalAlarms }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card warning" shadow="hover">
          <div class="stat-title">未确认告警</div>
          <div class="stat-value">{{ unacknowledgedCount }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card class="stat-card today" shadow="hover">
          <div class="stat-title">今日新增</div>
          <div class="stat-value">{{ todayAlarmsCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 告警列表 -->
    <el-card class="alarms-table-card">
      <el-table v-loading="loading" :data="alarms" style="width: 100%">
        <el-table-column prop="timestamp" label="告警时间" width="180" :formatter="formatTimestamp" />
        <el-table-column prop="fault_type" label="故障类型" width="150" :formatter="formatFaultType" />
        <el-table-column prop="level" label="告警级别" width="120">
          <template #default="scope">
            <el-tag :type="getLevelType(scope.row.level)">
              {{ getLevelText(scope.row.level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="告警描述" show-overflow-tooltip />
        <el-table-column prop="status" label="处理状态" width="120">
           <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)" disable-transitions>
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="scope">
            <el-button 
              type="primary" 
              link 
              size="small"
              @click="handleAcknowledge(scope.row)" 
              :disabled="scope.row.status === 'acknowledged'"
            >
              确认
            </el-button>
            <el-button type="primary" link size="small" @click="viewDetails(scope.row)">详情</el-button>
             <el-button type="danger" link size="small" @click="deleteAlarm(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <el-pagination
        v-if="totalAlarms > 0"
        class="pagination"
        :current-page="pagination.currentPage"
        :page-size="pagination.pageSize"
        :total="totalAlarms"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </el-card>

    <!-- 告警详情对话框 -->
    <el-dialog v-model="dialogVisible" title="告警详情" width="60%">
      <div v-if="selectedAlarm" class="alarm-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="告警ID">{{ selectedAlarm.id }}</el-descriptions-item>
          <el-descriptions-item label="告警时间">{{ formatTimestamp(null, selectedAlarm) }}</el-descriptions-item>
          <el-descriptions-item label="故障类型">{{ formatFaultType(null, selectedAlarm) }}</el-descriptions-item>
          <el-descriptions-item label="告警级别">
            <el-tag :type="getLevelType(selectedAlarm.level)">{{ getLevelText(selectedAlarm.level) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="处理状态">
            <el-tag :type="getStatusType(selectedAlarm.status)">{{ getStatusText(selectedAlarm.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="确认时间">{{ selectedAlarm.acknowledged_at ? formatTimestamp(null, { timestamp: selectedAlarm.acknowledged_at }) : 'N/A' }}</el-descriptions-item>
          <el-descriptions-item label="告警描述" :span="2">{{ selectedAlarm.description }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';

// 模拟的故障类型数据
const faultTypes = {
  turn_fault: '匝间短路',
  broken_bar: '断条故障',
  insulation: '绝缘失效',
  bearing: '轴承故障',
  eccentricity: '偏心故障'
};

// 状态变量
const filters = reactive({
  level: 'all',
  status: 'all',
  timeRange: null,
});
const alarms = ref([]);
const totalAlarms = ref(0);
const loading = ref(false);
const pagination = reactive({
  currentPage: 1,
  pageSize: 10
});
const dialogVisible = ref(false);
const selectedAlarm = ref(null);
let mockAlarmData = [];

// 计算统计数据
const unacknowledgedCount = computed(() => mockAlarmData.filter(a => a.status === 'unacknowledged').length);
const todayAlarmsCount = computed(() => {
  const today = new Date().toISOString().slice(0, 10);
  return mockAlarmData.filter(a => a.timestamp.slice(0, 10) === today).length;
});

// 重置筛选
const resetFilters = () => {
  filters.level = 'all';
  filters.status = 'all';
  filters.timeRange = null;
  fetchAlarms();
};

// 获取告警列表
const fetchAlarms = () => {
  loading.value = true;
  setTimeout(() => {
    let filteredData = mockAlarmData;

    if (filters.level !== 'all') {
      filteredData = filteredData.filter(a => a.level === filters.level);
    }
    if (filters.status !== 'all') {
      filteredData = filteredData.filter(a => a.status === filters.status);
    }
    if (filters.timeRange) {
      const [start, end] = filters.timeRange;
      filteredData = filteredData.filter(a => {
        const timestamp = new Date(a.timestamp);
        return timestamp >= start && timestamp <= end;
      });
    }

    totalAlarms.value = filteredData.length;
    const start = (pagination.currentPage - 1) * pagination.pageSize;
    const end = start + pagination.pageSize;
    alarms.value = filteredData.slice(start, end);
    
    loading.value = false;
  }, 500);
};

// 处理确认告警
const handleAcknowledge = (alarm) => {
  ElMessageBox.confirm('确定要确认此告警吗？', '确认操作', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(() => {
    const originalAlarm = mockAlarmData.find(a => a.id === alarm.id);
    if (originalAlarm) {
      originalAlarm.status = 'acknowledged';
      originalAlarm.acknowledged_at = new Date().toISOString();
      ElMessage.success('告警已确认');
      fetchAlarms();
    }
  }).catch(() => {});
};

// 查看详情
const viewDetails = (alarm) => {
  selectedAlarm.value = alarm;
  dialogVisible.value = true;
};

// 删除告警
const deleteAlarm = (alarm) => {
  ElMessageBox.confirm('确定要删除此告警记录吗？此操作不可恢复。', '确认删除', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    mockAlarmData = mockAlarmData.filter(a => a.id !== alarm.id);
    ElMessage.success('告警已删除');
    fetchAlarms();
  }).catch(() => {});
};

// 分页大小变化
const handleSizeChange = (size) => {
  pagination.pageSize = size;
  fetchAlarms();
};

// 当前页码变化
const handleCurrentChange = (page) => {
  pagination.currentPage = page;
  fetchAlarms();
};

// 格式化函数
const formatTimestamp = (row, column) => {
  const timestamp = row ? row.timestamp : column.timestamp;
  if (!timestamp) return 'N/A';
  return new Date(timestamp).toLocaleString('zh-CN');
};
const formatFaultType = (row, column) => faultTypes[row ? row.fault_type : column.fault_type] || '未知类型';
const getLevelText = (level) => ({ warning: '预警', fault: '故障' }[level] || '未知');
const getLevelType = (level) => ({ warning: 'warning', fault: 'danger' }[level] || 'info');
const getStatusText = (status) => ({ unacknowledged: '未确认', acknowledged: '已确认' }[status] || '未知');
const getStatusType = (status) => ({ unacknowledged: 'info', acknowledged: 'success' }[status] || 'info');

// 生成模拟数据
const generateMockAlarms = (count) => {
  const data = [];
  const faultTypeKeys = Object.keys(faultTypes);
  for (let i = 0; i < count; i++) {
    const faultType = faultTypeKeys[Math.floor(Math.random() * faultTypeKeys.length)];
    const level = Math.random() > 0.3 ? 'warning' : 'fault';
    const status = Math.random() > 0.5 ? 'acknowledged' : 'unacknowledged';
    const timestamp = new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000);
    data.push({
      id: i + 1,
      timestamp: timestamp.toISOString(),
      fault_type: faultType,
      level: level,
      description: `${faultTypes[faultType]}指标异常，当前值为 ${(Math.random() * 100).toFixed(2)}，超过阈值。`,
      status: status,
      acknowledged_at: status === 'acknowledged' ? new Date(timestamp.getTime() + Math.random() * 1000 * 60 * 60).toISOString() : null
    });
  }
  return data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
};

onMounted(() => {
  mockAlarmData = generateMockAlarms(150);
  fetchAlarms();
});
</script>

<style scoped>
.alarm-management-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  margin-bottom: 10px;
  color: #303133;
}

.page-description {
  color: #606266;
  margin-bottom: 20px;
}

.filter-section {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.stats-section {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-card .stat-title {
  color: #909399;
  font-size: 14px;
  margin-bottom: 10px;
}

.stat-card .stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-card.warning .stat-value {
  color: #e6a23c;
}

.stat-card.today .stat-value {
  color: #409eff;
}

.alarms-table-card {
  border-radius: 8px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.alarm-detail .el-descriptions {
  margin-bottom: 20px;
}
</style> 