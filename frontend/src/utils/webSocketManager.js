/**
 * 高性能WebSocket管理器
 * 处理实时数据流的缓冲、队列和性能优化
 */

class WebSocketManager {
  constructor(url, options = {}) {
    this.url = url;
    this.reconnectInterval = options.reconnectInterval || 2000;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    this.messageBufferSize = options.messageBufferSize || 1000; // 🚀 进一步增加缓冲区：500 -> 1000
    this.batchProcessSize = options.batchProcessSize || 80; // 🚀 增加批处理大小：50 -> 80
    this.processingInterval = options.processingInterval || 10; // 🚀 高频处理：16ms -> 10ms (100fps)
    
    // 连接状态
    this.socket = null;
    this.isConnected = false;
    this.reconnectAttempts = 0;
    this.connectionStartTime = null;
    this.totalConnectionTime = 0;
    
    // 消息处理 - 异步批处理优化
    this.messageBuffer = [];
    this.messageHandlers = new Map();
    this.processingTimer = null;
    
    // 🚀 异步并发控制 - 替代isProcessing阻塞
    this.maxConcurrentBatches = 10; // 🚀 大幅增加并发：6 -> 10
    this.activeBatchCount = 0;      // 当前活跃批处理数
    this.processingQueue = [];      // 待处理队列
    
    // 🚀 性能优化配置
    this.fastProcessingMode = true;   // 快速处理模式
    this.staticBatchSize = this.batchProcessSize; // 使用静态批处理大小，避免动态计算
    this.turboMode = false;          // 极速模式 - 高负载时自动启用
    this.loadThreshold = 0.5;        // 🚀 降低负载阈值：0.7 -> 0.5，更早启用极速模式
    this.ultraMode = false;          // 🆕 超极速模式 - 处理消息丢失严重情况
    this.ultraThreshold = 0.8;       // 🆕 超极速模式阈值
    
    // 🚀 增强性能监控
    this.stats = {
      // 原有统计
      messagesReceived: 0,
      messagesProcessed: 0,
      bufferOverflows: 0,
      avgProcessingTime: 0,
      lastProcessTime: 0,
      
      // 🆕 新增详细统计
      rawReceiveRate: 0,        // WebSocket原始接收速率
      actualProcessRate: 0,     // 实际处理速率
      bufferUtilization: 0,     // 缓冲区利用率
      messagesDropped: 0,       // 丢弃的消息数
      peakReceiveRate: 0,       // 峰值接收速率
      peakProcessRate: 0,       // 峰值处理速率
      latencyMs: 0,             // 消息处理延迟
      
      // 🆕 异步处理统计
      concurrentBatches: 0,     // 并发批处理数
      queuedBatches: 0,         // 排队批处理数
      totalBatchesProcessed: 0, // 总批处理数
      avgBatchSize: 0,          // 平均批处理大小
      
      // 时间窗口统计
      lastReceiveTime: 0,
      lastProcessTime: 0,
      receiveHistory: [],       // 接收历史（用于计算峰值）
      processHistory: []        // 处理历史
    };
    
    // 事件监听器
    this.eventListeners = {
      open: [],
      close: [],
      error: [],
      message: [],
      reconnect: []
    };
    
    // 数据压缩阈值
    this.compressionThreshold = 1024; // 1KB以上的消息进行压缩检查
  }

  /**
   * 建立WebSocket连接
   */
  connect() {
    if (this.isConnected || this.socket) {
      console.warn('WebSocket已经连接或正在连接中');
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(this.url);
        
        this.socket.onopen = (event) => {
          this.isConnected = true;
          this.reconnectAttempts = 0;
          this.connectionStartTime = Date.now();
          
          // 启动消息处理定时器
          this.startMessageProcessing();
          
          console.log('WebSocket连接成功');
          this.emit('open', event);
          resolve();
        };

        this.socket.onclose = (event) => {
          this.handleClose(event);
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket连接错误:', error);
          this.emit('error', error);
          if (!this.isConnected) {
            reject(error);
          }
        };

        this.socket.onmessage = (event) => {
          this.handleMessage(event);
        };

        // 连接超时处理
        setTimeout(() => {
          if (!this.isConnected) {
            try {
              if (this.socket && typeof this.socket.close === 'function') {
                this.socket.close();
              }
            } catch {}
            reject(new Error('WebSocket连接超时'));
          }
        }, 10000);

      } catch (error) {
        console.error('创建WebSocket连接失败:', error);
        reject(error);
      }
    });
  }

  /**
   * 处理连接关闭
   */
  handleClose(event) {
    const wasConnected = this.isConnected;
    this.isConnected = false;
    
    // 更新连接时间
    if (this.connectionStartTime) {
      this.totalConnectionTime += Date.now() - this.connectionStartTime;
      this.connectionStartTime = null;
    }
    
    // 停止消息处理
    this.stopMessageProcessing();
    
    if (wasConnected) {
      console.log('WebSocket连接已断开');
      this.emit('close', event);
      
      // 自动重连
      this.attemptReconnect();
    }
  }

  /**
   * 尝试重连
   */
  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('超过最大重连次数，停止重连');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectInterval * this.reconnectAttempts, 10000);
    
    console.log(`${delay}ms后尝试第${this.reconnectAttempts}次重连...`);
    
    setTimeout(() => {
      if (!this.isConnected) {
        this.socket = null;
        this.connect().catch(() => {
          // 重连失败，继续尝试
          this.attemptReconnect();
        });
        this.emit('reconnect', { attempt: this.reconnectAttempts });
      }
    }, delay);
  }

  /**
   * 处理WebSocket消息
   */
  handleMessage(event) {
    const now = Date.now();
    this.stats.messagesReceived++;
    
    // 🆕 计算原始接收速率
    if (this.stats.lastReceiveTime) {
      const timeDiff = (now - this.stats.lastReceiveTime) / 1000;
      if (timeDiff > 0) {
        const currentRate = 1 / timeDiff;
        this.stats.rawReceiveRate = Math.round(currentRate);
        
        // 更新峰值接收速率
        this.stats.peakReceiveRate = Math.max(this.stats.peakReceiveRate, currentRate);
        
        // 维护接收历史（最近50次）
        this.stats.receiveHistory.push(currentRate);
        if (this.stats.receiveHistory.length > 50) {
          this.stats.receiveHistory.shift();
        }
      }
    }
    this.stats.lastReceiveTime = now;
    
    try {
      // 🚀 优化缓冲区溢出处理 - 减少消息丢失
      if (this.messageBuffer.length >= this.messageBufferSize * 0.95) { // 95%时开始预防性清理
        this.stats.bufferOverflows++;
        
        // 🚀 更激进的清理策略：保留更多最新消息
        const keepRatio = 0.7; // 保留70%的消息
        const keepCount = Math.floor(this.messageBufferSize * keepRatio);
        const dropCount = this.messageBuffer.length - keepCount;
        
        this.stats.messagesDropped += dropCount;
        this.messageBuffer = this.messageBuffer.slice(-keepCount);
        
        // 🚀 立即触发紧急处理模式
        if (!this.ultraMode && this.messageBuffer.length > this.messageBufferSize * 0.8) {
          console.warn(`🚨 启动紧急处理模式 - 缓冲区压力过大`);
          this.ultraMode = true;
          this.turboMode = true;
          // 立即处理一批消息
          this.scheduleUltraBatch();
        }
        
        // 减少警告频率，只在每5次溢出时记录一次
        if (this.stats.bufferOverflows % 5 === 1) {
          console.warn(`🚨 缓冲区预防性清理，保留${keepCount}条最新消息，丢弃${dropCount}条`);
          console.warn(`📊 接收速率: ${this.stats.rawReceiveRate} msg/s, 处理速率: ${this.stats.actualProcessRate} msg/s, 缓冲区: ${Math.round(this.stats.bufferUtilization)}%`);
        }
      }

      // 🆕 计算缓冲区利用率
      this.stats.bufferUtilization = (this.messageBuffer.length / this.messageBufferSize) * 100;

      // 将消息添加到缓冲区
      this.messageBuffer.push({
        data: event.data,
        timestamp: now,
        size: event.data.length,
        receivedAt: now  // 🆕 添加接收时间戳
      });

    } catch (error) {
      console.error('处理WebSocket消息时出错:', error);
    }
  }

  /**
   * 启动消息处理 - 异步优化版本
   */
  startMessageProcessing() {
    if (this.processingTimer) {
      clearInterval(this.processingTimer);
    }

    // 🚀 高频异步处理，去除不必要的延迟
    if (this.fastProcessingMode) {
      // 🚀 使用超高频的处理间隔 - 优化性能
      this.processingTimer = setInterval(() => {
        this.adaptiveScheduleBatch();
      }, 5); // 🚀 5ms = 200fps，超高频处理
    } else {
      // 降级到原有逻辑
      this.processingTimer = setInterval(() => {
        this.scheduleAsyncBatch();
      }, this.processingInterval);
    }
    
    console.log(`🚀 ${this.fastProcessingMode ? '超高性能自适应' : '标准'}异步批处理已启动`);
    console.log(`📊 配置详情: 处理间隔${this.fastProcessingMode ? 5 : this.processingInterval}ms, 最大并发${this.maxConcurrentBatches}, 缓冲区${this.messageBufferSize}, 批处理${this.batchProcessSize}`);
    console.log(`⚡ 理论处理能力: ${this.batchProcessSize * (1000 / (this.fastProcessingMode ? 5 : this.processingInterval))} msg/s, 三级处理模式已激活`);
  }

  /**
   * 停止消息处理
   */
  stopMessageProcessing() {
    if (this.processingTimer) {
      clearTimeout(this.processingTimer);
      this.processingTimer = null;
    }
    
    // 等待所有活跃批处理完成
    console.log(`🛑 停止批处理，等待${this.activeBatchCount}个活跃批处理完成`);
  }

  /**
   * 🚀 自适应批处理调度 - 根据负载自动选择最优策略
   */
  adaptiveScheduleBatch() {
    // 计算当前负载
    const bufferLoad = this.messageBuffer.length / this.messageBufferSize;
    const concurrencyLoad = this.activeBatchCount / this.maxConcurrentBatches;
    const overallLoad = Math.max(bufferLoad, concurrencyLoad);
    
    // 🚀 根据负载选择处理策略 - 三级处理模式
    if (overallLoad > this.ultraThreshold) {
      // 🆕 超高负载：启用超极速同步模式
      if (!this.ultraMode) {
        this.ultraMode = true;
        this.turboMode = true;
        console.log(`🚀 启用超极速模式 - 负载${(overallLoad * 100).toFixed(1)}%`);
      }
      this.scheduleUltraBatch();
    } else if (overallLoad > this.loadThreshold) {
      // 高负载：启用极速同步模式
      if (!this.turboMode) {
        this.turboMode = true;
        console.log(`⚡ 启用极速模式 - 负载${(overallLoad * 100).toFixed(1)}%`);
      }
      if (this.ultraMode) {
        this.ultraMode = false;
        console.log(`🔄 从超极速切换到极速模式 - 负载${(overallLoad * 100).toFixed(1)}%`);
      }
      this.scheduleTurboBatch();
    } else {
      // 正常负载：使用优化异步模式
      if (this.turboMode || this.ultraMode) {
        this.turboMode = false;
        this.ultraMode = false;
        console.log(`🔄 切换回优化模式 - 负载${(overallLoad * 100).toFixed(1)}%`);
      }
      this.scheduleOptimizedBatch();
    }
  }

  /**
   * 🚀 优化的异步批处理调度 - 性能优先版本
   */
  async scheduleOptimizedBatch() {
    // 快速检查
    if (this.messageBuffer.length === 0 || 
        this.activeBatchCount >= this.maxConcurrentBatches) {
      return;
    }
    
    // 🚀 使用静态批处理大小，避免动态计算开销
    const batchSize = Math.min(this.staticBatchSize, this.messageBuffer.length);
    if (batchSize === 0) return;
    
    // 立即提取批处理数据
    const batch = this.messageBuffer.splice(0, batchSize);
    
    // 🚀 同步启动异步处理，避免微任务延迟
    this.processOptimizedBatch(batch);
  }

  /**
   * 🚀 优化的异步批处理 - 去除延迟版本
   */
  processOptimizedBatch(batch) {
    if (batch.length === 0) return;
    
    // 增加活跃批处理计数
    this.activeBatchCount++;
    this.stats.concurrentBatches = this.activeBatchCount;
    
    const batchId = `opt_${Date.now()}_${this.activeBatchCount}`;
    const startTime = performance.now();
    const batchStartTime = Date.now();
    
    // 🚀 使用立即执行的Promise，避免setTimeout延迟
    Promise.resolve().then(async () => {
      try {
        let totalLatency = 0;
        let successCount = 0;
        
        // 🚀 同步处理消息，避免异步开销
        for (const messageData of batch) {
          try {
            const messageLatency = batchStartTime - messageData.receivedAt;
            totalLatency += messageLatency;
            
            // 🚀 直接同步处理，去除异步包装
            this.processMessage(messageData);
            successCount++;
          } catch (error) {
            console.error(`批处理消息失败 [${batchId}]:`, error);
          }
        }
        
        // 更新统计信息
        this.stats.messagesProcessed += successCount;
        this.stats.totalBatchesProcessed++;
        this.stats.avgBatchSize = ((this.stats.avgBatchSize * (this.stats.totalBatchesProcessed - 1)) + batch.length) / this.stats.totalBatchesProcessed;
        
        // 计算平均延迟
        this.stats.latencyMs = Math.round(totalLatency / batch.length);
        
        // 更新处理速率
        this.updateProcessingRate(batch.length, batchStartTime);
        
        // 更新平均处理时间
        const processingTime = performance.now() - startTime;
        this.updateAvgProcessingTime(processingTime);
        
        // 降低日志频率以提高性能
        if (this.stats.totalBatchesProcessed % 20 === 0) {
          console.log(`⚡ 优化批处理${batchId}: ${successCount}/${batch.length}条消息, 耗时${processingTime.toFixed(1)}ms, 并发${this.activeBatchCount}`);
        }
        
      } catch (error) {
        console.error(`优化批处理${batchId}失败:`, error);
      } finally {
        // 减少活跃批处理计数
        this.activeBatchCount--;
        this.stats.concurrentBatches = this.activeBatchCount;
      }
    });
  }

  /**
   * 🚀 极速同步批处理 - 最高性能模式
   */
  scheduleTurboBatch() {
    if (this.messageBuffer.length === 0) return;
    
    // 🚀 大批处理：在高负载时使用更大的批处理
    const turboBatchSize = Math.min(
      Math.floor(this.staticBatchSize * 1.5), // 增加50%批处理大小
      this.messageBuffer.length,
      100 // 最大限制
    );
    
    if (turboBatchSize === 0) return;
    
    // 立即同步处理，无并发控制开销
    const batch = this.messageBuffer.splice(0, turboBatchSize);
    this.processTurboBatch(batch);
  }

  /**
   * 🚀 极速同步批处理处理器 - 零延迟版本
   */
  processTurboBatch(batch) {
    if (batch.length === 0) return;
    
    const startTime = performance.now();
    const batchStartTime = Date.now();
    let totalLatency = 0;
    let successCount = 0;
    
    // 🚀 直接同步处理，零异步开销
    for (const messageData of batch) {
      try {
        const messageLatency = batchStartTime - messageData.receivedAt;
        totalLatency += messageLatency;
        
        // 直接调用处理方法，无包装
        this.processMessage(messageData);
        successCount++;
      } catch (error) {
        console.error(`极速批处理消息失败:`, error);
      }
    }
    
    // 更新统计信息
    this.stats.messagesProcessed += successCount;
    this.stats.totalBatchesProcessed++;
    this.stats.avgBatchSize = ((this.stats.avgBatchSize * (this.stats.totalBatchesProcessed - 1)) + batch.length) / this.stats.totalBatchesProcessed;
    
    // 计算延迟
    this.stats.latencyMs = Math.round(totalLatency / batch.length);
    
    // 更新处理速率
    this.updateProcessingRate(batch.length, batchStartTime);
    
    // 更新平均处理时间
    const processingTime = performance.now() - startTime;
    this.updateAvgProcessingTime(processingTime);
    
    // 极低频率日志（性能优先）
    if (this.stats.totalBatchesProcessed % 50 === 0) {
      console.log(`🚀 极速批处理: ${successCount}/${batch.length}条消息, 耗时${processingTime.toFixed(1)}ms, 负载${Math.round((this.messageBuffer.length / this.messageBufferSize) * 100)}%`);
    }
  }

  /**
   * 🚀 超极速批处理调度 - 最大吞吐量模式
   */
  scheduleUltraBatch() {
    if (this.messageBuffer.length === 0) return;
    
    // 🚀 超大批处理：处理所有可用消息，最大化吞吐量
    const ultraBatchSize = Math.min(
      this.messageBuffer.length,  // 处理所有可用消息
      200 // 设置合理上限，避免单次处理时间过长
    );
    
    if (ultraBatchSize === 0) return;
    
    // 立即处理所有消息，忽略并发控制
    const batch = this.messageBuffer.splice(0, ultraBatchSize);
    this.processUltraBatch(batch);
  }

  /**
   * 🚀 超极速批处理处理器 - 最大吞吐量版本
   */
  processUltraBatch(batch) {
    if (batch.length === 0) return;
    
    const startTime = performance.now();
    const batchStartTime = Date.now();
    let totalLatency = 0;
    let successCount = 0;
    
    // 🚀 批量处理，最小化循环开销
    try {
      for (let i = 0; i < batch.length; i++) {
        const messageData = batch[i];
        totalLatency += batchStartTime - messageData.receivedAt;
        
        // 🚀 内联处理逻辑，避免函数调用开销
        try {
          let jsonString = messageData.data;
          jsonString = jsonString.replace(/:\s*NaN\s*([,}])/g, ': null$1');
          const data = JSON.parse(jsonString);
          
          if (data.vehicle_id) {
            data._processedAt = batchStartTime;
            data._receivedAt = messageData.timestamp;
            this.emit('message', data);
            successCount++;
          }
        } catch (parseError) {
          // 静默跳过解析失败的消息，避免日志开销
        }
      }
    } catch (error) {
      console.error(`超极速批处理失败:`, error);
    }
    
    // 🚀 批量更新统计信息
    this.stats.messagesProcessed += successCount;
    this.stats.totalBatchesProcessed++;
    this.stats.avgBatchSize = ((this.stats.avgBatchSize * (this.stats.totalBatchesProcessed - 1)) + batch.length) / this.stats.totalBatchesProcessed;
    this.stats.latencyMs = Math.round(totalLatency / batch.length);
    
    // 更新处理速率
    this.updateProcessingRate(batch.length, batchStartTime);
    
    // 更新平均处理时间
    const processingTime = performance.now() - startTime;
    this.updateAvgProcessingTime(processingTime);
    
    // 极低频率日志（性能优先）
    if (this.stats.totalBatchesProcessed % 100 === 0) {
      console.log(`🚀 超极速批处理: ${successCount}/${batch.length}条消息, 耗时${processingTime.toFixed(1)}ms, 吞吐量${Math.round(successCount / (processingTime / 1000))} msg/s`);
    }
  }

  /**
   * 🚀 调度异步批处理 - 核心优化方法 (降级版本)
   */
  async scheduleAsyncBatch() {
    // 检查是否有消息需要处理
    if (this.messageBuffer.length === 0) {
      return;
    }
    
    // 检查并发限制
    if (this.activeBatchCount >= this.maxConcurrentBatches) {
      this.stats.queuedBatches++;
      return;
    }
    
    // 计算动态批处理大小
    const dynamicBatchSize = this.calculateOptimalBatchSize();
    const batchSize = Math.min(dynamicBatchSize, this.messageBuffer.length);
    
    if (batchSize === 0) return;
    
    // 提取批处理数据
    const batch = this.messageBuffer.splice(0, batchSize);
    
    // 🚀 异步处理批次，不阻塞主线程
    this.processAsyncBatch(batch);
  }

  /**
   * 🚀 计算最优批处理大小 - 动态调整
   */
  calculateOptimalBatchSize() {
    // 基础批处理大小
    let batchSize = this.batchProcessSize;
    
    // 根据缓冲区压力动态调整
    const bufferPressure = this.messageBuffer.length / this.messageBufferSize;
    
    if (bufferPressure > 0.8) {
      // 高压力：增加批处理大小
      batchSize = Math.floor(batchSize * 1.5);
    } else if (bufferPressure < 0.3) {
      // 低压力：减少批处理大小，提高响应性
      batchSize = Math.floor(batchSize * 0.7);
    }
    
    // 根据历史性能调整
    if (this.stats.avgProcessingTime > 50) {
      // 处理时间过长，减少批处理大小
      batchSize = Math.floor(batchSize * 0.8);
    }
    
    return Math.max(1, Math.min(batchSize, 100)); // 限制在1-100之间
  }

  /**
   * 🚀 异步批处理核心方法 - 无阻塞处理
   */
  async processAsyncBatch(batch) {
    if (batch.length === 0) return;
    
    // 增加活跃批处理计数
    this.activeBatchCount++;
    this.stats.concurrentBatches = this.activeBatchCount;
    
    const batchId = `batch_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const startTime = performance.now();
    const batchStartTime = Date.now();
    
    try {
      // 🆕 计算消息延迟
      let totalLatency = 0;
      
      // 🚀 使用异步迭代器并行处理消息
      const processPromises = batch.map(async (messageData, index) => {
        try {
          const messageLatency = batchStartTime - messageData.receivedAt;
          totalLatency += messageLatency;
          
          // 异步处理单条消息
          await this.processMessageAsync(messageData);
          return { success: true, latency: messageLatency };
        } catch (error) {
          console.error(`异步处理消息失败 [${batchId}][${index}]:`, error);
          return { success: false, error: error.message };
        }
      });
      
      // 等待所有消息处理完成
      const results = await Promise.allSettled(processPromises);
      const successCount = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
      
      // 更新统计信息
      this.stats.messagesProcessed += successCount;
      this.stats.totalBatchesProcessed++;
      this.stats.avgBatchSize = ((this.stats.avgBatchSize * (this.stats.totalBatchesProcessed - 1)) + batch.length) / this.stats.totalBatchesProcessed;
      
      // 🆕 计算平均延迟
      this.stats.latencyMs = Math.round(totalLatency / batch.length);
      
      // 🆕 更新处理速率
      this.updateProcessingRate(batch.length, batchStartTime);
      
      // 更新平均处理时间
      const processingTime = performance.now() - startTime;
      this.updateAvgProcessingTime(processingTime);
      
      // 性能日志 (降低频率)
      if (this.stats.totalBatchesProcessed % 10 === 0) {
        console.log(`📊 批处理${batchId}: ${successCount}/${batch.length}条消息, 耗时${processingTime.toFixed(2)}ms, 并发${this.activeBatchCount}`);
      }
      
    } catch (error) {
      console.error(`批处理${batchId}失败:`, error);
    } finally {
      // 减少活跃批处理计数
      this.activeBatchCount--;
      this.stats.concurrentBatches = this.activeBatchCount;
    }
  }

  /**
   * 🚀 异步处理单条消息
   */
  async processMessageAsync(messageData) {
    // 使用微任务确保异步执行
    return new Promise((resolve) => {
      setTimeout(() => {
        try {
          this.processMessage(messageData);
          resolve();
        } catch (error) {
          console.error('异步处理消息失败:', error);
          resolve(); // 继续处理，不中断批处理
        }
      }, 0);
    });
  }

  /**
   * 🆕 更新处理速率统计
   */
  updateProcessingRate(batchSize, batchStartTime) {
    if (this.stats.lastProcessTime) {
      const timeDiff = (batchStartTime - this.stats.lastProcessTime) / 1000;
      if (timeDiff > 0) {
        const currentProcessRate = batchSize / timeDiff;
        this.stats.actualProcessRate = Math.round(currentProcessRate);
        
        // 更新峰值处理速率
        this.stats.peakProcessRate = Math.max(this.stats.peakProcessRate, currentProcessRate);
        
        // 维护处理历史
        this.stats.processHistory.push(currentProcessRate);
        if (this.stats.processHistory.length > 50) {
          this.stats.processHistory.shift();
        }
      }
    }
    this.stats.lastProcessTime = batchStartTime;
  }

  /**
   * 🆕 更新平均处理时间
   */
  updateAvgProcessingTime(processingTime) {
    if (this.stats.totalBatchesProcessed === 1) {
      this.stats.avgProcessingTime = processingTime;
    } else {
      this.stats.avgProcessingTime = 
        (this.stats.avgProcessingTime * (this.stats.totalBatchesProcessed - 1) + processingTime) / 
        this.stats.totalBatchesProcessed;
    }
  }

  /**
   * 批量处理消息 - 废弃的同步方法，保留兼容性
   * @deprecated 使用 scheduleAsyncBatch 替代
   */
  processMessageBatch() {
    console.warn('⚠️ processMessageBatch已废弃，使用异步批处理替代');
    this.scheduleAsyncBatch();
  }

  /**
   * 处理单条消息
   */
  processMessage(messageData) {
    try {
      // 清理JSON数据，处理NaN值
      let jsonString = messageData.data;
      
      // 将NaN替换为null，使其成为有效JSON
      jsonString = jsonString.replace(/:\s*NaN\s*([,}])/g, ': null$1');
      
      // 解析JSON数据
      const data = JSON.parse(jsonString);
      
      // 数据验证：确保关键字段存在
      if (!data.vehicle_id) {
        console.warn('消息缺少vehicle_id字段，跳过处理:', data);
        return;
      }
      
      // 数据压缩检查
      if (messageData.size > this.compressionThreshold) {
        data._compressed = true;
        data._originalSize = messageData.size;
      }
      
      // 添加处理时间戳
      data._processedAt = Date.now();
      data._receivedAt = messageData.timestamp;
      
      // 触发消息处理器
      this.emit('message', data);
      
    } catch (error) {
      console.error('解析消息数据失败:', error);
      console.error('原始数据:', messageData.data);
      // 不阻止其他消息的处理
    }
  }

  /**
   * 发送消息
   */
  send(data) {
    if (!this.isConnected || !this.socket) {
      console.warn('WebSocket未连接，无法发送消息');
      return false;
    }

    try {
      const message = typeof data === 'string' ? data : JSON.stringify(data);
      this.socket.send(message);
      return true;
    } catch (error) {
      console.error('发送WebSocket消息失败:', error);
      return false;
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.reconnectAttempts = this.maxReconnectAttempts; // 阻止自动重连
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    this.stopMessageProcessing();
    this.isConnected = false;
    
    // 清理消息缓冲区
    this.messageBuffer = [];
  }

  /**
   * 重置连接时间
   */
  resetConnectionTime() {
    this.totalConnectionTime = 0;
    if (this.isConnected) {
      this.connectionStartTime = Date.now();
    }
  }

  /**
   * 获取连接持续时间
   */
  getConnectionDuration() {
    let currentSessionTime = 0;
    if (this.connectionStartTime) {
      currentSessionTime = Date.now() - this.connectionStartTime;
    }
    
    const totalTime = this.totalConnectionTime + currentSessionTime;
    
    const hours = Math.floor(totalTime / (1000 * 60 * 60));
    const minutes = Math.floor((totalTime % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((totalTime % (1000 * 60)) / 1000);
    
    return {
      total: totalTime,
      formatted: `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
    };
  }

  /**
   * 添加事件监听器
   */
  on(event, callback) {
    if (this.eventListeners[event]) {
      this.eventListeners[event].push(callback);
    }
  }

  /**
   * 移除事件监听器
   */
  off(event, callback) {
    if (this.eventListeners[event]) {
      const index = this.eventListeners[event].indexOf(callback);
      if (index > -1) {
        this.eventListeners[event].splice(index, 1);
      }
    }
  }

  /**
   * 触发事件
   */
  emit(event, data) {
    if (this.eventListeners[event]) {
      this.eventListeners[event].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`事件${event}的回调函数执行失败:`, error);
        }
      });
    }
  }

  /**
   * 注册消息处理器
   */
  registerHandler(faultType, handler) {
    this.messageHandlers.set(faultType, handler);
  }

  /**
   * 注销消息处理器
   */
  unregisterHandler(faultType) {
    this.messageHandlers.delete(faultType);
  }

  /**
   * 检查是否已连接（方法形式）
   */
  getIsConnected() {
    return this.socket && this.socket.readyState === WebSocket.OPEN;
  }

  /**
   * 获取连接状态
   */
  getConnectionStatus() {
    if (this.isConnected) {
      return 'connected';
    } else if (this.socket) {
      return 'connecting';
    } else if (this.reconnectAttempts > 0 && this.reconnectAttempts < this.maxReconnectAttempts) {
      return 'reconnecting';
    } else {
      return 'disconnected';
    }
  }

  /**
   * 获取性能统计
   */
  getStats() {
    return {
      ...this.stats,
      bufferSize: this.messageBuffer.length,
      connectionDuration: this.getConnectionDuration(),
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts
    };
  }

  /**
   * 获取详细性能统计 - 异步处理增强版
   */
  getDetailedStats() {
    const avgReceiveRate = this.stats.receiveHistory.length > 0 
      ? Math.round(this.stats.receiveHistory.reduce((a, b) => a + b, 0) / this.stats.receiveHistory.length)
      : 0;
      
    const avgProcessRate = this.stats.processHistory.length > 0
      ? Math.round(this.stats.processHistory.reduce((a, b) => a + b, 0) / this.stats.processHistory.length)
      : 0;

    return {
      // 实时指标
      rawReceiveRate: this.stats.rawReceiveRate,
      actualProcessRate: this.stats.actualProcessRate,
      bufferUtilization: Math.round(this.stats.bufferUtilization),
      latencyMs: this.stats.latencyMs,
      
      // 峰值指标
      peakReceiveRate: Math.round(this.stats.peakReceiveRate),
      peakProcessRate: Math.round(this.stats.peakProcessRate),
      
      // 平均指标
      avgReceiveRate,
      avgProcessRate,
      
      // 累计统计
      messagesReceived: this.stats.messagesReceived,
      messagesProcessed: this.stats.messagesProcessed,
      messagesDropped: this.stats.messagesDropped,
      bufferOverflows: this.stats.bufferOverflows,
      
      // 🚀 异步处理统计
      concurrentBatches: this.stats.concurrentBatches,
      queuedBatches: this.stats.queuedBatches,
      totalBatchesProcessed: this.stats.totalBatchesProcessed,
      avgBatchSize: Math.round(this.stats.avgBatchSize),
      maxConcurrentBatches: this.maxConcurrentBatches,
      activeBatchCount: this.activeBatchCount,
      
      // 缓冲区状态
      bufferSize: this.messageBuffer.length,
      bufferCapacity: this.messageBufferSize,
      
      // 处理效率 - 异步优化计算
      processingEfficiency: this.stats.messagesReceived > 0 
        ? Math.round((this.stats.messagesProcessed / this.stats.messagesReceived) * 100)
        : 100,
      
      // 🆕 异步处理效率
      asyncProcessingUtilization: this.maxConcurrentBatches > 0
        ? Math.round((this.activeBatchCount / this.maxConcurrentBatches) * 100)
        : 0,
      
      // 🆕 批处理效率
      batchProcessingEfficiency: this.stats.totalBatchesProcessed > 0 && this.stats.avgBatchSize > 0
        ? Math.round((this.stats.messagesProcessed / (this.stats.totalBatchesProcessed * this.stats.avgBatchSize)) * 100)
        : 100,
      
      // 连接状态
      isConnected: this.isConnected,
      reconnectAttempts: this.reconnectAttempts
    };
  }

  /**
   * 重置统计数据 - 异步处理增强版
   */
  resetStats() {
    this.stats = {
      messagesReceived: 0,
      messagesProcessed: 0,
      bufferOverflows: 0,
      avgProcessingTime: 0,
      lastProcessTime: 0,
      rawReceiveRate: 0,
      actualProcessRate: 0,
      bufferUtilization: 0,
      messagesDropped: 0,
      peakReceiveRate: 0,
      peakProcessRate: 0,
      
      // 🚀 重置异步处理统计
      concurrentBatches: 0,
      queuedBatches: 0,
      totalBatchesProcessed: 0,
      avgBatchSize: 0,
      latencyMs: 0,
      lastReceiveTime: 0,
      receiveHistory: [],
      processHistory: []
    };
    
    // 🚀 重置异步处理状态
    this.activeBatchCount = 0;
    this.processingQueue = [];
    
    console.log('📊 异步批处理统计已重置');
  }

  /**
   * 获取内存使用情况
   */
  getMemoryUsage() {
    let bufferSize = 0;
    this.messageBuffer.forEach(msg => {
      bufferSize += msg.size || 0;
    });

    return {
      bufferSize: bufferSize,
      bufferCount: this.messageBuffer.length,
      formattedSize: this.formatBytes(bufferSize)
    };
  }

  /**
   * 格式化字节数
   */
  formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * 清理资源
   */
  destroy() {
    this.disconnect();
    
    // 清理所有事件监听器
    Object.keys(this.eventListeners).forEach(event => {
      this.eventListeners[event] = [];
    });
    
    // 清理处理器
    this.messageHandlers.clear();
    
    // 清理统计数据
    this.stats = {
      messagesReceived: 0,
      messagesProcessed: 0,
      bufferOverflows: 0,
      avgProcessingTime: 0,
      lastProcessTime: 0
    };
  }
}

// 创建全局WebSocket管理器实例 - 🚀 高性能优化配置
const globalWebSocketManager = new WebSocketManager('ws://localhost:8000/ws/frontend', {
  reconnectInterval: 2000,
  maxReconnectAttempts: 10,
  messageBufferSize: 1000,   // 🚀 超大缓冲区：500 -> 1000
  batchProcessSize: 80,      // 🚀 大批处理：50 -> 80  
  processingInterval: 10     // 🚀 超高频处理：20ms -> 10ms (100fps)，理论处理能力：80条 × (1000/10) = 8000 msg/s
});

export default globalWebSocketManager;

// 导出类，供其他地方使用
export { WebSocketManager }; 