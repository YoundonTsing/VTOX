<template>
  <div class="threshold-settings-container">
    <h2 class="page-title">阈值设置</h2>
    <p class="page-description">
      为不同类型的故障诊断设置预警和告警阈值。这些阈值将用于实时监控和告警生成。
    </p>

    <el-card class="settings-card">
      <el-tabs v-model="activeTab" type="border-card" class="settings-tabs">
        <el-tab-pane
          v-for="fault in faultTypes"
          :key="fault.type"
          :label="fault.name"
          :name="fault.type"
        >
          <div class="tab-content">
            <h3>{{ fault.name }} 阈值配置</h3>
            <p class="tab-description">{{ fault.description }}</p>

            <div v-for="threshold in fault.thresholds" :key="threshold.key" class="threshold-item">
              <span class="threshold-label">{{ threshold.name }}</span>
              <div class="slider-container">
                <el-slider
                  v-model="threshold.value"
                  :min="threshold.min"
                  :max="threshold.max"
                  :step="threshold.step"
                  show-input
                  :marks="getMarks(threshold)"
                  class="threshold-slider"
                />
              </div>
            </div>

            <div class="actions">
              <el-button type="primary" @click="saveSettings(fault.type)">保存设置</el-button>
              <el-button @click="resetSettings(fault.type)">恢复默认</el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';

const activeTab = ref('turn_fault');

const faultTypes = reactive([
  {
    type: 'turn_fault',
    name: '匝间短路',
    description: '设置匝间短路故障诊断相关的指标阈值。',
    thresholds: [
      { key: 'score_warning', name: '预警评分阈值', value: 60, min: 0, max: 100, step: 1, unit: '%' },
      { key: 'score_fault', name: '故障评分阈值', value: 80, min: 0, max: 100, step: 1, unit: '%' },
      { key: 'imbalance_warning', name: '电流不平衡度预警', value: 5, min: 0, max: 20, step: 0.1, unit: '%' },
      { key: 'imbalance_fault', name: '电流不平衡度故障', value: 10, min: 0, max: 20, step: 0.1, unit: '%' }
    ]
  },
  {
    type: 'broken_bar',
    name: '断条故障',
    description: '设置断条故障诊断相关的指标阈值。',
    thresholds: [
      { key: 'score_warning', name: '预警评分阈值', value: 65, min: 0, max: 100, step: 1, unit: '%' },
      { key: 'score_fault', name: '故障评分阈值', value: 85, min: 0, max: 100, step: 1, unit: '%' },
      { key: 'sideband_warning', name: '边带幅值比预警', value: 0.5, min: 0, max: 2, step: 0.01, unit: '%' },
      { key: 'sideband_fault', name: '边带幅值比故障', value: 1.0, min: 0, max: 2, step: 0.01, unit: '%' }
    ]
  },
   {
    type: 'insulation',
    name: '绝缘失效',
    description: '设置绝缘失效诊断相关的指标阈值。',
    thresholds: [
      { key: 'resistance_warning', name: '绝缘电阻预警 (MΩ)', value: 100, min: 0, max: 1000, step: 10 },
      { key: 'resistance_fault', name: '绝缘电阻故障 (MΩ)', value: 50, min: 0, max: 1000, step: 10 },
      { key: 'leakage_warning', name: '泄漏电流预警 (mA)', value: 5, min: 0, max: 20, step: 0.1 },
      { key: 'leakage_fault', name: '泄漏电流故障 (mA)', value: 10, min: 0, max: 20, step: 0.1 }
    ]
  },
  {
    type: 'bearing',
    name: '轴承故障',
    description: '设置轴承故障诊断相关的指标阈值。',
    thresholds: [
      { key: 'score_warning', name: '预警评分阈值', value: 70, min: 0, max: 100, step: 1, unit: '%' },
      { key: 'score_fault', name: '故障评分阈值', value: 90, min: 0, max: 100, step: 1, unit: '%' },
      { key: 'crest_factor_warning', name: '冲击因子预警', value: 4, min: 0, max: 10, step: 0.1 },
      { key: 'crest_factor_fault', name: '冲击因子故障', value: 6, min: 0, max: 10, step: 0.1 },
      { key: 'kurtosis_warning', name: '峭度预警', value: 5, min: 0, max: 10, step: 0.1 },
      { key: 'kurtosis_fault', name: '峭度故障', value: 8, min: 0, max: 10, step: 0.1 }
    ]
  },
  {
    type: 'eccentricity',
    name: '偏心故障',
    description: '设置偏心故障诊断相关的指标阈值。',
    thresholds: [
      { key: 'score_warning', name: '预警评分阈值', value: 60, min: 0, max: 100, step: 1, unit: '%' },
      { key: 'score_fault', name: '故障评分阈值', value: 80, min: 0, max: 100, step: 1, unit: '%' },
      { key: 'static_ecc_warning', name: '静态偏心率预警', value: 8, min: 0, max: 20, step: 0.1, unit: '%' },
      { key: 'static_ecc_fault', name: '静态偏心率故障', value: 15, min: 0, max: 20, step: 0.1, unit: '%' }
    ]
  }
]);

// 获取滑块标记
const getMarks = (threshold) => {
  const marks = {};
  marks[threshold.min] = `${threshold.min}${threshold.unit || ''}`;
  marks[threshold.max] = `${threshold.max}${threshold.unit || ''}`;
  return marks;
};

// 加载设置
const loadSettings = () => {
  faultTypes.forEach(fault => {
    const savedSettings = localStorage.getItem(`threshold_settings_${fault.type}`);
    if (savedSettings) {
      const parsedSettings = JSON.parse(savedSettings);
      fault.thresholds.forEach(threshold => {
        if (parsedSettings[threshold.key] !== undefined) {
          threshold.value = parsedSettings[threshold.key];
        }
      });
    }
  });
  ElMessage.success('已加载保存的设置');
};

// 保存设置
const saveSettings = (faultType) => {
  const fault = faultTypes.find(f => f.type === faultType);
  if (fault) {
    const settingsToSave = {};
    fault.thresholds.forEach(threshold => {
      settingsToSave[threshold.key] = threshold.value;
    });
    localStorage.setItem(`threshold_settings_${faultType}`, JSON.stringify(settingsToSave));
    ElMessage.success(`${fault.name} 设置已保存！`);
  }
};

// 重置为默认设置 (此功能为示例，实际应从后端或配置文件获取默认值)
const resetSettings = (faultType) => {
   ElMessage.info('恢复默认功能将在后续版本中实现');
  // 在实际应用中，您需要一个默认配置的源
};

onMounted(() => {
  loadSettings();
});
</script>

<style scoped>
.threshold-settings-container {
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

.settings-card {
  border-radius: 8px;
}

.settings-tabs {
  border-radius: 8px;
}

.tab-content {
  padding: 20px;
}

.tab-content h3 {
  font-size: 18px;
  margin-bottom: 10px;
}

.tab-description {
  color: #909399;
  margin-bottom: 30px;
  font-size: 14px;
}

.threshold-item {
  margin-bottom: 25px;
  display: flex;
  align-items: center;
}

.threshold-label {
  width: 200px;
  font-weight: 500;
  color: #606266;
  flex-shrink: 0;
  padding-right: 20px;
}

.slider-container {
  flex-grow: 1;
}

.threshold-slider {
  max-width: 600px;
}

.actions {
  margin-top: 30px;
  display: flex;
  justify-content: flex-start;
  gap: 15px;
}
</style> 