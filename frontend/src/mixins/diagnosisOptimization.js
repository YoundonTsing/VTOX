/**
 * 诊断组件性能优化混入
 * 用于优化实时诊断组件的数据处理和内存使用
 */

import { ref, onBeforeUnmount } from 'vue';
import { globalOptimizer, HistoryDataManager } from '@/utils/performanceOptimizer.js';

export function useDiagnosisOptimization(options = {}) {
  const config = {
    maxHistorySize: options.maxHistorySize || 100,
    updateThrottle: options.updateThrottle || 200,
    chartUpdateThrottle: options.chartUpdateThrottle || 500,
    autoCleanup: options.autoCleanup !== false,
    ...options
  };

  // 历史数据管理器
  const historyManager = new HistoryDataManager(config.maxHistorySize);
  
  // 性能统计
  const performanceStats = ref({
    processedCount: 0,
    droppedCount: 0,
    lastUpdate: null,
    avgProcessTime: 0
  });

  // 处理诊断数据的优化版本
  const processOptimizedDiagnosisData = (data, originalProcessor) => {
    const startTime = performance.now();
    
    try {
      // 使用节流避免过于频繁的更新
      globalOptimizer.throttleUpdate('diagnosis_update', () => {
        originalProcessor(data);
        
        // 更新性能统计
        const processingTime = performance.now() - startTime;
        performanceStats.value.processedCount++;
        performanceStats.value.lastUpdate = Date.now();
        performanceStats.value.avgProcessTime = 
          (performanceStats.value.avgProcessTime * 0.9) + (processingTime * 0.1);
      }, config.updateThrottle);
      
    } catch (error) {
      performanceStats.value.droppedCount++;
      console.error('诊断数据处理失败:', error);
    }
  };

  // 优化的历史数据添加
  const addToHistoryOptimized = (data) => {
    historyManager.addData(data);
    return historyManager.getSampledData(50); // 返回采样后的数据用于图表
  };

  // 优化的图表更新
  const updateChartOptimized = (chartRef, dataProvider) => {
    globalOptimizer.throttleUpdate('chart_update', () => {
      if (chartRef.value) {
        const sampledData = dataProvider();
        chartRef.value.updateChart(sampledData);
      }
    }, config.chartUpdateThrottle);
  };

  // 内存清理函数
  const cleanup = () => {
    historyManager.cleanup();
    globalOptimizer.destroy();
  };

  // 自动清理
  if (config.autoCleanup) {
    onBeforeUnmount(() => {
      cleanup();
    });
  }

  // 获取性能统计
  const getPerformanceStats = () => {
    return {
      ...performanceStats.value,
      historySize: historyManager.getSize(),
      memoryUsage: performance.memory ? 
        (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2) + ' MB' : 
        'N/A'
    };
  };

  return {
    // 数据处理
    processOptimizedDiagnosisData,
    addToHistoryOptimized,
    updateChartOptimized,
    
    // 性能监控
    performanceStats,
    getPerformanceStats,
    
    // 资源管理
    cleanup,
    historyManager
  };
}

/**
 * WebSocket消息优化处理器
 */
export class WebSocketMessageOptimizer {
  constructor(options = {}) {
    this.options = {
      maxQueueSize: options.maxQueueSize || 1000,
      batchSize: options.batchSize || 10,
      processInterval: options.processInterval || 100,
      ...options
    };
    
    this.messageQueue = [];
    this.isProcessing = false;
    this.processors = new Map();
    this.stats = {
      received: 0,
      processed: 0,
      dropped: 0,
      queued: 0
    };
  }

  /**
   * 注册消息处理器
   */
  registerProcessor(type, processor) {
    this.processors.set(type, processor);
  }

  /**
   * 添加消息到队列
   */
  addMessage(message) {
    this.stats.received++;
    
    // 检查队列大小，防止内存溢出
    if (this.messageQueue.length >= this.options.maxQueueSize) {
      // 删除最旧的消息
      const droppedMessage = this.messageQueue.shift();
      this.stats.dropped++;
      
      // 通知外部统计系统有消息被丢弃
      if (message.onDrop) {
        message.onDrop();
      }
    }
    
    this.messageQueue.push({
      ...message,
      timestamp: Date.now()
    });
    
    this.stats.queued = this.messageQueue.length;
    
    // 启动处理器（如果未运行）
    if (!this.isProcessing) {
      this.startProcessing();
    }
  }

  /**
   * 开始批量处理消息
   */
  startProcessing() {
    if (this.isProcessing) return;
    
    this.isProcessing = true;
    
    const processBatch = () => {
      if (this.messageQueue.length === 0) {
        this.isProcessing = false;
        return;
      }
      
      // 处理一批消息
      const batch = this.messageQueue.splice(0, this.options.batchSize);
      
      requestAnimationFrame(() => {
        for (const message of batch) {
          try {
            const processor = this.processors.get(message.type);
            if (processor) {
              processor(message);
              this.stats.processed++;
            }
          } catch (error) {
            console.error('消息处理失败:', error);
            this.stats.dropped++;
          }
        }
        
        this.stats.queued = this.messageQueue.length;
        
        // 继续处理下一批
        setTimeout(processBatch, this.options.processInterval);
      });
    };
    
    processBatch();
  }

  /**
   * 获取统计信息
   */
  getStats() {
    return { ...this.stats };
  }

  /**
   * 清理资源
   */
  destroy() {
    this.messageQueue = [];
    this.processors.clear();
    this.isProcessing = false;
  }
}

/**
 * 图表性能优化器
 */
export class ChartPerformanceOptimizer {
  constructor(options = {}) {
    this.options = {
      maxDataPoints: options.maxDataPoints || 200,
      updateThrottle: options.updateThrottle || 500,
      downsampleRatio: options.downsampleRatio || 0.5,
      ...options
    };
    
    this.updateTimers = new Map();
  }

  /**
   * 优化图表数据
   */
  optimizeChartData(data) {
    if (!Array.isArray(data)) return data;
    
    // 如果数据点太多，进行下采样
    if (data.length > this.options.maxDataPoints) {
      return globalOptimizer.sampleData(data, this.options.maxDataPoints);
    }
    
    return data;
  }

  /**
   * 节流图表更新
   */
  throttleChartUpdate(chartId, updateFn) {
    if (this.updateTimers.has(chartId)) {
      clearTimeout(this.updateTimers.get(chartId));
    }
    
    const timer = setTimeout(() => {
      updateFn();
      this.updateTimers.delete(chartId);
    }, this.options.updateThrottle);
    
    this.updateTimers.set(chartId, timer);
  }

  /**
   * 批量更新多个图表
   */
  batchUpdateCharts(charts) {
    requestAnimationFrame(() => {
      for (const [chartId, updateFn] of Object.entries(charts)) {
        try {
          updateFn();
        } catch (error) {
          console.error(`图表更新失败 [${chartId}]:`, error);
        }
      }
    });
  }

  /**
   * 清理资源
   */
  destroy() {
    for (const timer of this.updateTimers.values()) {
      clearTimeout(timer);
    }
    this.updateTimers.clear();
  }
}

// 导出全局实例
export const globalWebSocketOptimizer = new WebSocketMessageOptimizer({
  maxQueueSize: 2000,  // 增加队列大小以处理高频消息
  batchSize: 10,       // 增加批处理大小提高效率
  processInterval: 16  // 约60FPS的处理频率，提高响应性
});

export const globalChartOptimizer = new ChartPerformanceOptimizer({
  maxDataPoints: 100,
  updateThrottle: 300
});