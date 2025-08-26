/**
 * 前端性能优化工具类
 * 用于优化大量数据流传递时的内存使用和刷新效率
 */

export class PerformanceOptimizer {
  constructor(options = {}) {
    this.options = {
      maxHistorySize: options.maxHistorySize || 1000, // 最大历史记录数
      maxVehicleCount: options.maxVehicleCount || 100, // 最大车辆数
      batchSize: options.batchSize || 10, // 批处理大小
      throttleInterval: options.throttleInterval || 100, // 节流间隔(ms)
      cleanupInterval: options.cleanupInterval || 30000, // 清理间隔(ms)
      memoryThreshold: options.memoryThreshold || 0.8, // 内存阈值
      ...options
    };
    
    this.lastCleanup = Date.now();
    this.updateQueue = new Map();
    this.throttledUpdates = new Map();
    this.isProcessing = false;
  }

  /**
   * 限制数组大小，防止内存泄漏
   */
  limitArraySize(array, maxSize = this.options.maxHistorySize) {
    if (array.length > maxSize) {
      // 保留最新的数据，删除旧数据
      const removeCount = array.length - maxSize;
      array.splice(0, removeCount);
    }
    return array;
  }

  /**
   * 限制对象属性数量
   */
  limitObjectSize(obj, maxCount = this.options.maxVehicleCount) {
    const keys = Object.keys(obj);
    if (keys.length > maxCount) {
      // 按最后更新时间排序，删除最旧的数据
      const sortedKeys = keys.sort((a, b) => {
        const timeA = obj[a].lastUpdate || 0;
        const timeB = obj[b].lastUpdate || 0;
        return timeA - timeB;
      });
      
      const removeCount = keys.length - maxCount;
      for (let i = 0; i < removeCount; i++) {
        delete obj[sortedKeys[i]];
      }
    }
    return obj;
  }

  /**
   * 节流更新 - 避免过于频繁的DOM更新
   */
  throttleUpdate(key, updateFn, interval = this.options.throttleInterval) {
    if (this.throttledUpdates.has(key)) {
      clearTimeout(this.throttledUpdates.get(key));
    }

    const timeoutId = setTimeout(() => {
      updateFn();
      this.throttledUpdates.delete(key);
    }, interval);

    this.throttledUpdates.set(key, timeoutId);
  }

  /**
   * 批量处理更新
   */
  batchUpdate(key, data, processFn) {
    if (!this.updateQueue.has(key)) {
      this.updateQueue.set(key, []);
    }

    this.updateQueue.get(key).push(data);

    // 当达到批处理大小或超时时处理
    if (this.updateQueue.get(key).length >= this.options.batchSize) {
      this.processBatch(key, processFn);
    } else {
      // 设置超时处理
      this.throttleUpdate(`batch_${key}`, () => {
        this.processBatch(key, processFn);
      }, this.options.throttleInterval);
    }
  }

  /**
   * 处理批量数据
   */
  processBatch(key, processFn) {
    const batch = this.updateQueue.get(key) || [];
    if (batch.length === 0) return;

    this.updateQueue.set(key, []);
    
    // 使用 requestAnimationFrame 确保在浏览器空闲时执行
    requestAnimationFrame(() => {
      processFn(batch);
    });
  }

  /**
   * 深度清理未使用的数据
   */
  deepCleanup(dataObject, maxAge = 300000) { // 5分钟
    const now = Date.now();
    const keys = Object.keys(dataObject);
    
    for (const key of keys) {
      const item = dataObject[key];
      if (item && item.lastUpdate && (now - item.lastUpdate) > maxAge) {
        delete dataObject[key];
      }
    }
    
    return dataObject;
  }

  /**
   * 内存监控和自动清理
   */
  startMemoryMonitoring(cleanupCallback) {
    setInterval(() => {
      // 检查是否需要清理
      if (this.shouldCleanup()) {
        console.log('🧹 执行内存清理...');
        cleanupCallback();
        this.lastCleanup = Date.now();
      }
    }, this.options.cleanupInterval);
  }

  /**
   * 判断是否需要清理
   */
  shouldCleanup() {
    const now = Date.now();
    
    // 基于时间的清理
    if (now - this.lastCleanup > this.options.cleanupInterval) {
      return true;
    }

    // 基于内存使用的清理（如果支持）
    if (performance.memory) {
      const memoryUsage = performance.memory.usedJSHeapSize / performance.memory.totalJSHeapSize;
      if (memoryUsage > this.options.memoryThreshold) {
        return true;
      }
    }

    return false;
  }

  /**
   * 数据采样 - 减少显示的数据点
   */
  sampleData(data, sampleRate = 10) {
    if (!Array.isArray(data) || data.length <= sampleRate) {
      return data;
    }

    const sampled = [];
    const step = Math.floor(data.length / sampleRate);
    
    for (let i = 0; i < data.length; i += step) {
      sampled.push(data[i]);
    }

    // 确保包含最后一个数据点
    if (sampled[sampled.length - 1] !== data[data.length - 1]) {
      sampled.push(data[data.length - 1]);
    }

    return sampled;
  }

  /**
   * 智能更新频率控制
   */
  adaptiveUpdateRate(currentLoad) {
    if (currentLoad > 0.8) {
      return 5000; // 高负载时降低更新频率
    } else if (currentLoad > 0.5) {
      return 2000; // 中等负载
    } else {
      return 1000; // 正常更新频率
    }
  }

  /**
   * 清理所有资源
   */
  destroy() {
    // 清理所有定时器
    for (const timeoutId of this.throttledUpdates.values()) {
      clearTimeout(timeoutId);
    }
    this.throttledUpdates.clear();
    this.updateQueue.clear();
  }
}

/**
 * 全局性能优化器实例
 */
export const globalOptimizer = new PerformanceOptimizer({
  maxHistorySize: 500,     // 减少历史记录数量
  maxVehicleCount: 50,     // 限制同时监控的车辆数
  batchSize: 5,            // 较小的批处理大小
  throttleInterval: 200,   // 200ms节流
  cleanupInterval: 20000,  // 20秒清理一次
  memoryThreshold: 0.75    // 75%内存阈值
});

/**
 * 车辆数据优化管理器
 */
export class VehicleDataManager {
  constructor(optimizer = globalOptimizer) {
    this.optimizer = optimizer;
    this.vehicleData = new Map(); // 使用Map而不是reactive对象提高性能
    this.lastUpdateTime = new Map();
  }

  /**
   * 高效更新车辆数据
   */
  updateVehicle(vehicleId, data) {
    const now = Date.now();
    
    // 节流检查 - 避免同一车辆过于频繁更新
    const lastUpdate = this.lastUpdateTime.get(vehicleId) || 0;
    if (now - lastUpdate < 100) { // 100ms内只允许一次更新
      return false;
    }

    this.lastUpdateTime.set(vehicleId, now);
    
    // 批量更新
    this.optimizer.batchUpdate(vehicleId, data, (batch) => {
      this.processBatchUpdate(vehicleId, batch);
    });

    return true;
  }

  /**
   * 处理批量车辆数据更新
   */
  processBatchUpdate(vehicleId, batch) {
    // 只保留最新的数据
    const latestData = batch[batch.length - 1];
    
    if (!this.vehicleData.has(vehicleId)) {
      this.vehicleData.set(vehicleId, {
        vehicleId,
        firstSeen: Date.now(),
        messageCount: 0,
        overall: { health_score: 100 }
      });
    }

    const vehicle = this.vehicleData.get(vehicleId);
    vehicle.lastUpdate = Date.now();
    vehicle.messageCount += batch.length;

    // 更新故障数据（只保留最新状态）
    const faultType = latestData.fault_type;
    if (faultType) {
      vehicle[faultType] = {
        lastUpdate: Date.now(),
        score: latestData.fault_score || latestData.score || 0,
        fault_score: latestData.fault_score || latestData.score || 0,
        fault_type: faultType,
        vehicle_id: vehicleId
      };
    }
  }

  /**
   * 获取车辆数据（转换为reactive格式）
   */
  getVehicleData() {
    const result = {};
    for (const [id, data] of this.vehicleData) {
      result[id] = data;
    }
    return result;
  }

  /**
   * 清理过期车辆数据
   */
  cleanup(maxAge = 300000) { // 5分钟
    const now = Date.now();
    for (const [id, vehicle] of this.vehicleData) {
      if (vehicle.lastUpdate && (now - vehicle.lastUpdate) > maxAge) {
        this.vehicleData.delete(id);
        this.lastUpdateTime.delete(id);
      }
    }
  }

  /**
   * 获取车辆数量
   */
  getVehicleCount() {
    return this.vehicleData.size;
  }
}

/**
 * 历史数据管理器
 */
export class HistoryDataManager {
  constructor(maxSize = 500) {
    this.maxSize = maxSize;
    this.data = [];
    this.optimizer = globalOptimizer;
  }

  /**
   * 添加历史数据
   */
  addData(newData) {
    this.data.push({
      ...newData,
      timestamp: Date.now()
    });

    // 限制数组大小
    this.optimizer.limitArraySize(this.data, this.maxSize);
  }

  /**
   * 获取采样后的历史数据
   */
  getSampledData(sampleRate = 50) {
    return this.optimizer.sampleData(this.data, sampleRate);
  }

  /**
   * 清理历史数据
   */
  cleanup() {
    // 只保留最近的一半数据
    const keepCount = Math.floor(this.maxSize / 2);
    if (this.data.length > keepCount) {
      this.data = this.data.slice(-keepCount);
    }
  }

  /**
   * 获取数据大小
   */
  getSize() {
    return this.data.length;
  }
}