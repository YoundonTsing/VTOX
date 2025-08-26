// Optimized global realtime store with performance enhancements
// Manages persistent WebSocket connection and exposes reactive-like getters

import { globalWebSocketOptimizer } from '../mixins/diagnosisOptimization.js';

let subscribers = new Set();
let messageListeners = new Set();

const state = {
  isConnected: false,
  reconnectAttempts: 0,
  detailedStats: {
    rawReceiveRate: 0,
    actualProcessRate: 0,
    latencyMs: 0,
    messagesReceived: 0,
    messagesProcessed: 0,
    messagesDropped: 0
  }
};

let ws;
let processingTimer;

// 🚀 注册优化的消息处理器
globalWebSocketOptimizer.registerProcessor('websocket_message', (message) => {
  // fan-out to listeners; protect against exceptions
  if (messageListeners.size > 0) {
    let processedCount = 0;
    messageListeners.forEach((fn) => {
      try {
        fn(message.data);
        processedCount++;
      } catch {
        state.detailedStats.messagesDropped++;
      }
    });
    // 只有成功处理的消息才计入处理数
    if (processedCount > 0) {
      state.detailedStats.messagesProcessed++;
    }
  } else {
    // 没有监听器时，将消息计入丢弃数
    state.detailedStats.messagesDropped++;
  }
});

function notify() {
  subscribers.forEach((fn) => {
    try { fn(getSnapshot()); } catch {}
  });
}

function getSnapshot() {
  return JSON.parse(JSON.stringify(state));
}

export function subscribe(listener) {
  subscribers.add(listener);
  // immediate emit
  try { listener(getSnapshot()); } catch {}
  return () => subscribers.delete(listener);
}

export function getState() {
  return getSnapshot();
}

export async function ensureConnected(url = 'ws://localhost:8000/ws/frontend') {
  if (ws && state.isConnected) return true;
  return new Promise((resolve) => {
    try {
      ws = new WebSocket(url);
      ws.onopen = () => {
        state.isConnected = true;
        state.reconnectAttempts = 0;
        startProcessing();
        notify();
        resolve(true);
      };
      ws.onmessage = (event) => {
        // 🚀 性能优化：使用消息队列处理
        state.detailedStats.messagesReceived++;
        const now = Date.now();
        if (state.__lastReceive) {
          const dt = (now - state.__lastReceive) / 1000;
          if (dt > 0) state.detailedStats.rawReceiveRate = Math.round(1 / dt);
        }
        state.__lastReceive = now;

        // 使用优化的消息处理器
        globalWebSocketOptimizer.addMessage({
          type: 'websocket_message',
          data: event.data,
          timestamp: now,
          onDrop: () => {
            // 队列溢出时记录丢弃的消息
            state.detailedStats.messagesDropped++;
          }
        });
      };
      ws.onclose = () => {
        state.isConnected = false;
        stopProcessing();
        notify();
      };
      ws.onerror = () => {
        // no-op
      };
    } catch {
      resolve(false);
    }
  });
}

function startProcessing() {
  if (processingTimer) clearInterval(processingTimer);
  processingTimer = setInterval(() => {
    // naive process rate approximation = rawReceiveRate (fallback)
    state.detailedStats.actualProcessRate = state.detailedStats.rawReceiveRate;
    notify();
  }, 1000);
}

function stopProcessing() {
  if (processingTimer) {
    clearInterval(processingTimer);
    processingTimer = null;
  }
}

export function disconnect() {
  try { if (ws && ws.readyState === WebSocket.OPEN) ws.close(); } catch {}
  ws = null;
  state.isConnected = false;
  stopProcessing();
  notify();
}

// Expose message subscription for consumers that need raw messages
export function onMessage(listener) {
  messageListeners.add(listener);
  return () => messageListeners.delete(listener);
}


