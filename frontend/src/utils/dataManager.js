/**
 * 高性能数据管理器
 * 专门用于处理实时监控数据的内存优化
 */

class DataManager {
  constructor(options = {}) {
    this.maxHistoryLength = options.maxHistoryLength || 20; // 最大历史记录数
    this.maxSpectrumPoints = options.maxSpectrumPoints || 50; // 最大频谱点数
    this.maxTimeSeriesPoints = options.maxTimeSeriesPoints || 100; // 最大时序点数
    this.compressionRatio = options.compressionRatio || 0.7; // 压缩比例
    this.memoryThreshold = options.memoryThreshold || 100 * 1024 * 1024; // 内存阈值100MB
    
    // 数据缓存池
    this.dataPool = new Map();
    this.memoryUsage = 0;
    
    // 防抖和节流配置
    this.updateQueue = new Map();
    this.isProcessing = false;
    
    // 性能监控
    this.performanceMetrics = {
      updateCount: 0,
      avgUpdateTime: 0,
      memoryPeek: 0,
      lastCleanup: Date.now()
    };
  }

  /**
   * 数据采样 - 智能减少数据点数量
   */
  sampleData(data, maxPoints, preservePattern = true) {
    if (!Array.isArray(data) || data.length <= maxPoints) {
      return data;
    }

    if (preservePattern && data.length > maxPoints * 2) {
      // 保持数据模式的采样算法
      return this.adaptiveSampling(data, maxPoints);
    } else {
      // 简单均匀采样
      const step = Math.ceil(data.length / maxPoints);
      return data.filter((_, index) => index % step === 0).slice(0, maxPoints);
    }
  }

  /**
   * 自适应采样 - 保留重要特征点
   */
  adaptiveSampling(data, maxPoints) {
    if (data.length <= maxPoints) return data;

    const result = [];
    const step = data.length / maxPoints;
    let currentIndex = 0;

    for (let i = 0; i < maxPoints; i++) {
      const index = Math.floor(currentIndex);
      
      // 在当前窗口内寻找最有代表性的点
      const windowStart = Math.max(0, index - 2);
      const windowEnd = Math.min(data.length - 1, index + 2);
      
      let bestIndex = index;
      let maxVariation = 0;
      
      // 寻找变化最大的点
      for (let j = windowStart; j <= windowEnd; j++) {
        const variation = this.calculateVariation(data, j);
        if (variation > maxVariation) {
          maxVariation = variation;
          bestIndex = j;
        }
      }
      
      result.push(data[bestIndex]);
      currentIndex += step;
    }

    return result;
  }

  /**
   * 计算数据点的变化程度
   */
  calculateVariation(data, index) {
    if (index <= 0 || index >= data.length - 1) return 0;
    
    const prev = typeof data[index - 1] === 'number' ? data[index - 1] : 0;
    const curr = typeof data[index] === 'number' ? data[index] : 0;
    const next = typeof data[index + 1] === 'number' ? data[index + 1] : 0;
    
    return Math.abs(curr - prev) + Math.abs(next - curr);
  }

  /**
   * 压缩时域数据
   */
  compressTimeSeriesData(timeSeriesData) {
    if (!timeSeriesData || !timeSeriesData.time) return timeSeriesData;

    const compressed = { ...timeSeriesData };
    const targetPoints = this.maxTimeSeriesPoints;

    // 压缩时间轴
    compressed.time = this.sampleData(timeSeriesData.time, targetPoints);

    // 压缩各相数据
    if (timeSeriesData.values_a) {
      compressed.values_a = this.sampleData(timeSeriesData.values_a, targetPoints);
    }
    if (timeSeriesData.values_b) {
      compressed.values_b = this.sampleData(timeSeriesData.values_b, targetPoints);
    }
    if (timeSeriesData.values_c) {
      compressed.values_c = this.sampleData(timeSeriesData.values_c, targetPoints);
    }
    if (timeSeriesData.values_ia) {
      compressed.values_ia = this.sampleData(timeSeriesData.values_ia, targetPoints);
    }
    if (timeSeriesData.values_ib) {
      compressed.values_ib = this.sampleData(timeSeriesData.values_ib, targetPoints);
    }
    if (timeSeriesData.values_ic) {
      compressed.values_ic = this.sampleData(timeSeriesData.values_ic, targetPoints);
    }

    // 绝缘相关数据
    if (timeSeriesData.values_resistance) {
      compressed.values_resistance = this.sampleData(timeSeriesData.values_resistance, targetPoints);
    }
    if (timeSeriesData.values_leakage_current) {
      compressed.values_leakage_current = this.sampleData(timeSeriesData.values_leakage_current, targetPoints);
    }

    // 振动数据
    if (timeSeriesData.values_vibration) {
      compressed.values_vibration = this.sampleData(timeSeriesData.values_vibration, targetPoints);
    }
    if (timeSeriesData.values) {
      compressed.values = this.sampleData(timeSeriesData.values, targetPoints);
    }

    return compressed;
  }

  /**
   * 压缩频谱数据
   */
  compressSpectrumData(spectrumData) {
    if (!spectrumData || !spectrumData.frequency) return spectrumData;

    const compressed = { ...spectrumData };
    const targetPoints = this.maxSpectrumPoints;

    // 压缩频率轴 - 对于频谱数据，低频部分更重要
    compressed.frequency = this.sampleSpectrumFrequency(spectrumData.frequency, targetPoints);

    // 压缩幅值数据
    if (spectrumData.amplitude_a) {
      compressed.amplitude_a = this.sampleData(spectrumData.amplitude_a, targetPoints, true);
    }
    if (spectrumData.amplitude_b) {
      compressed.amplitude_b = this.sampleData(spectrumData.amplitude_b, targetPoints, true);
    }
    if (spectrumData.amplitude_c) {
      compressed.amplitude_c = this.sampleData(spectrumData.amplitude_c, targetPoints, true);
    }

    return compressed;
  }

  /**
   * 频谱专用采样 - 重点保留低频信息
   */
  sampleSpectrumFrequency(frequencies, maxPoints) {
    if (!Array.isArray(frequencies) || frequencies.length <= maxPoints) {
      return frequencies;
    }

    const result = [];
    const totalPoints = frequencies.length;
    
    // 低频部分（0-30%）取50%的点
    const lowFreqEnd = Math.floor(totalPoints * 0.3);
    const lowFreqPoints = Math.floor(maxPoints * 0.5);
    const lowFreqStep = Math.ceil(lowFreqEnd / lowFreqPoints);
    
    for (let i = 0; i < lowFreqEnd; i += lowFreqStep) {
      result.push(frequencies[i]);
    }

    // 中频部分（30%-70%）取30%的点
    const midFreqEnd = Math.floor(totalPoints * 0.7);
    const midFreqPoints = Math.floor(maxPoints * 0.3);
    const midFreqStep = Math.ceil((midFreqEnd - lowFreqEnd) / midFreqPoints);
    
    for (let i = lowFreqEnd; i < midFreqEnd; i += midFreqStep) {
      result.push(frequencies[i]);
    }

    // 高频部分（70%-100%）取20%的点
    const highFreqPoints = maxPoints - result.length;
    const highFreqStep = Math.ceil((totalPoints - midFreqEnd) / highFreqPoints);
    
    for (let i = midFreqEnd; i < totalPoints; i += highFreqStep) {
      result.push(frequencies[i]);
    }

    return result.slice(0, maxPoints);
  }

  /**
   * 处理实时数据
   */
  processRealtimeData(faultType, data) {
    const startTime = performance.now();

    try {
      // 获取或创建数据缓存
      if (!this.dataPool.has(faultType)) {
        this.dataPool.set(faultType, {
          latest: null,
          history: [],
          timeSeries: { labels: [], datasets: [] },
          spectrum: { labels: [], datasets: [] },
          featureTrend: { labels: [], datasets: [] },
          historyChart: { labels: [], datasets: [] },
          lastUpdate: 0
        });
      }

      const typeData = this.dataPool.get(faultType);
      
      // 检查是否需要更新（防抖）- 提高防抖时间
      const now = Date.now();
      if (now - typeData.lastUpdate < 200) { // 提高到200ms防抖
        return typeData;
      }

      // 压缩数据
      const compressedData = this.compressData(data);

      // 更新最新数据
      typeData.latest = compressedData;
      typeData.lastUpdate = now;

      // 管理历史记录
      this.manageHistory(typeData, compressedData);

      // 更新性能指标
      this.updatePerformanceMetrics(performance.now() - startTime);

      // 每10次更新检查一次内存使用情况
      if (this.performanceMetrics.updateCount % 10 === 0) {
        this.checkMemoryUsage();
      }

      return typeData;

    } catch (error) {
      console.error(`处理${faultType}数据时出错:`, error);
      return this.dataPool.get(faultType) || null;
    }
  }

  /**
   * 压缩数据
   */
  compressData(data) {
    const compressed = { ...data };

    // 压缩时域数据
    if (data.time_series) {
      compressed.time_series = this.compressTimeSeriesData(data.time_series);
    }

    // 压缩频谱数据
    if (data.frequency_spectrum) {
      compressed.frequency_spectrum = this.compressSpectrumData(data.frequency_spectrum);
    }

    // 特征数据通常较小，不需要压缩
    if (data.features) {
      compressed.features = { ...data.features };
    }

    return compressed;
  }

  /**
   * 管理历史记录
   */
  manageHistory(typeData, newData) {
    // 添加到历史记录
    typeData.history.push(newData);

    // 限制历史记录长度
    while (typeData.history.length > this.maxHistoryLength) {
      typeData.history.shift();
    }

    // 当历史记录较多时，进行压缩
    if (typeData.history.length > this.maxHistoryLength * 0.8) {
      this.compressHistory(typeData);
    }
  }

  /**
   * 压缩历史记录
   */
  compressHistory(typeData) {
    if (typeData.history.length <= this.maxHistoryLength) return;

    // 保留最新的数据，压缩较旧的数据
    const keepRecent = Math.floor(this.maxHistoryLength * 0.7);
    const compressOld = typeData.history.length - keepRecent;

    if (compressOld > 0) {
      // 对旧数据进行采样压缩
      const oldData = typeData.history.slice(0, compressOld);
      const compressedOld = this.sampleData(oldData, Math.floor(compressOld * this.compressionRatio));
      const recentData = typeData.history.slice(compressOld);

      typeData.history = [...compressedOld, ...recentData];
    }
  }

  /**
   * 更新性能指标
   */
  updatePerformanceMetrics(updateTime) {
    this.performanceMetrics.updateCount++;
    this.performanceMetrics.avgUpdateTime = 
      (this.performanceMetrics.avgUpdateTime * (this.performanceMetrics.updateCount - 1) + updateTime) / 
      this.performanceMetrics.updateCount;
  }

  /**
   * 检查内存使用情况
   */
  checkMemoryUsage() {
    // 估算内存使用
    let memoryUsage = 0;
    for (const [key, value] of this.dataPool) {
      memoryUsage += this.estimateObjectSize(value);
    }

    this.memoryUsage = memoryUsage;
    this.performanceMetrics.memoryPeek = Math.max(this.performanceMetrics.memoryPeek, memoryUsage);

    // 如果内存使用过高，触发清理
    if (memoryUsage > this.memoryThreshold) {
      this.triggerMemoryCleanup();
    }
  }

  /**
   * 估算对象内存大小
   */
  estimateObjectSize(obj) {
    let size = 0;
    const seen = new WeakSet();

    const calculateSize = (item) => {
      if (seen.has(item)) return 0;
      
      switch (typeof item) {
        case 'string':
          return item.length * 2; // Unicode字符
        case 'number':
          return 8;
        case 'boolean':
          return 4;
        case 'object':
          if (item === null) return 0;
          if (Array.isArray(item)) {
            seen.add(item);
            return item.reduce((acc, val) => acc + calculateSize(val), 0);
          } else {
            seen.add(item);
            return Object.values(item).reduce((acc, val) => acc + calculateSize(val), 0);
          }
        default:
          return 0;
      }
    };

    return calculateSize(obj);
  }

  /**
   * 触发内存清理
   */
  triggerMemoryCleanup() {
    console.log('触发内存清理，当前使用:', (this.memoryUsage / 1024 / 1024).toFixed(2), 'MB');

    // 清理过期数据
    for (const [faultType, typeData] of this.dataPool) {
      // 减少历史记录长度
      if (typeData.history.length > this.maxHistoryLength / 2) {
        typeData.history = typeData.history.slice(-Math.floor(this.maxHistoryLength / 2));
      }

      // 清理图表数据缓存
      if (typeData.timeSeries && typeData.timeSeries.datasets) {
        typeData.timeSeries.datasets.forEach(dataset => {
          if (dataset.data && dataset.data.length > this.maxTimeSeriesPoints / 2) {
            dataset.data = this.sampleData(dataset.data, Math.floor(this.maxTimeSeriesPoints / 2));
          }
        });
      }
    }

    this.performanceMetrics.lastCleanup = Date.now();

    // 强制垃圾回收（如果可用）
    if (window.gc) {
      window.gc();
    }
  }

  /**
   * 初始化类型数据结构
   */
  initializeTypeData() {
    return {
      latest: null,
      history: [],
      timeSeries: { labels: [], datasets: [] },
      spectrum: { labels: [], datasets: [] },
      featureTrend: { labels: [], datasets: [] },
      historyChart: { labels: [], datasets: [] },
      lastUpdate: 0,
      score: 0, // 添加默认评分
      status: 'unknown' // 添加默认状态
    };
  }

  /**
   * 获取数据
   */
  getData(faultType) {
    let data = this.dataPool.get(faultType);
    if (!data) {
      // 如果没有数据，初始化默认结构
      data = this.initializeTypeData();
      this.dataPool.set(faultType, data);
    }
    return data;
  }

  /**
   * 清理指定类型的数据
   */
  clearData(faultType) {
    if (this.dataPool.has(faultType)) {
      this.dataPool.delete(faultType);
    }
  }

  /**
   * 清理所有数据
   */
  clearAllData() {
    this.dataPool.clear();
    this.memoryUsage = 0;
    this.performanceMetrics = {
      updateCount: 0,
      avgUpdateTime: 0,
      memoryPeek: 0,
      lastCleanup: Date.now()
    };
  }

  /**
   * 获取性能报告
   */
  getPerformanceReport() {
    return {
      ...this.performanceMetrics,
      currentMemoryUsage: (this.memoryUsage / 1024 / 1024).toFixed(2) + ' MB',
      dataPoolSize: this.dataPool.size,
      avgUpdateTimeMs: this.performanceMetrics.avgUpdateTime.toFixed(2) + ' ms'
    };
  }

  /**
   * 销毁数据管理器
   */
  // 新增：更新基础数据（性能优化版本）
  updateBasicData(faultType, basicData) {
    try {
      let typeData = this.dataPool.get(faultType);
      if (!typeData) {
        typeData = this.initializeTypeData();
        this.dataPool.set(faultType, typeData);
      }
      
      // 直接更新基础信息，不处理图表数据
      typeData.latest = {
        ...typeData.latest,
        ...basicData
      };
      
      // 记录性能指标
      this.recordPerformanceMetric('basicDataUpdate', Date.now());
      
      return typeData;
    } catch (error) {
      console.error(`[DataManager] 更新基础数据失败 ${faultType}:`, error);
      return null;
    }
  }

  // 新增：记录性能指标
  recordPerformanceMetric(operation, timestamp) {
    try {
      if (!this.customPerformanceMetrics) {
        this.customPerformanceMetrics = {
          lastUpdateTime: Date.now(),
          operationCount: 0,
          avgUpdateTime: 0
        };
      }
      
      this.customPerformanceMetrics.operationCount++;
      this.customPerformanceMetrics.lastUpdateTime = timestamp;
      
      // 简单的平均更新时间计算
      const currentTime = Date.now();
      if (this.customPerformanceMetrics.lastOperationTime) {
        const timeDiff = currentTime - this.customPerformanceMetrics.lastOperationTime;
        this.customPerformanceMetrics.avgUpdateTime = 
          (this.customPerformanceMetrics.avgUpdateTime + timeDiff) / 2;
      }
      this.customPerformanceMetrics.lastOperationTime = currentTime;
      
    } catch (error) {
      console.debug('[DataManager] 性能指标记录失败:', error);
    }
  }

  destroy() {
    this.clearAllData();
    // 清理所有引用
    this.dataPool = null;
    this.updateQueue = null;
    this.performanceMetrics = null;
    this.customPerformanceMetrics = null;
  }
}

// 创建全局数据管理器实例
const globalDataManager = new DataManager({
  maxHistoryLength: 10, // 进一步减少到10条历史记录
  maxSpectrumPoints: 30, // 频谱数据减少到30个点
  maxTimeSeriesPoints: 50, // 时序数据减少到50个点
  compressionRatio: 0.5, // 压缩比提高到50%
  memoryThreshold: 50 * 1024 * 1024 // 50MB内存阈值
});

export default globalDataManager;

// 导出数据管理器类，供其他地方使用
export { DataManager }; 