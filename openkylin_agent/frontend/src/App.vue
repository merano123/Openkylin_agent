<template>
  <div class="app-wrapper">
    <div class="chat-container">
      <div class="header">
        <div class="logo-section">
          <div class="logo">🐧</div>
          <h1>openKylin 智能助手</h1>
        </div>
        <div class="status-indicator">
          <span class="status-dot"></span>
          <span class="status-text">在线</span>
        </div>
      </div>

      <div class="chat-box" ref="chatBox">
        <div v-if="messages.length === 0" class="welcome-message">
          <div class="welcome-icon">👋</div>
          <h2>欢迎使用 openKylin 智能助手</h2>
          <p>我可以帮助您解答问题、执行任务和提供建议</p>
        </div>
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message-wrapper', msg.role === '你' ? 'user' : 'agent']"
        >
          <div class="avatar">
            {{ msg.role === '你' ? '👤' : msg.role === '系统' ? '⚙️' : '🤖' }}
          </div>
          <div class="message-content">
            <div class="message-header">{{ msg.role }}</div>
            <div class="message-text">{{ msg.text }}</div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <input
          v-model="input"
          @keyup.enter="sendMessage"
          :placeholder="placeholderText"
          :disabled="isLoading"
        />
        <button @click="sendMessage" :disabled="isLoading" class="send-button">
          <span v-if="!isLoading">发送</span>
          <span v-else class="loading-spinner">⟳</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
const placeholderText = '输入您的问题...';
import { ref, nextTick, onMounted, watch } from 'vue'
import axios from 'axios'

const API_URL = 'http://localhost:8080/api/agent'
const input = ref('')
const messages = ref([])
const isLoading = ref(false)
const chatBox = ref(null)
const sessionId = ref('')

// 生成唯一的会话 ID
const generateSessionId = () => {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9)
}

// 从 sessionStorage 恢复会话（刷新页面时恢复，关闭标签页后清除）
const restoreSession = () => {
  try {
    const savedSessionId = sessionStorage.getItem('openkylin_session_id')
    const savedMessages = sessionStorage.getItem('openkylin_messages')

    if (savedSessionId && savedMessages) {
      sessionId.value = savedSessionId
      messages.value = JSON.parse(savedMessages)
    } else {
      // 没有保存的会话，创建新会话
      sessionId.value = generateSessionId()
      sessionStorage.setItem('openkylin_session_id', sessionId.value)
    }
  } catch (error) {
    console.error('恢复会话失败:', error)
    sessionId.value = generateSessionId()
    sessionStorage.setItem('openkylin_session_id', sessionId.value)
  }
}

// 保存消息到 sessionStorage
const saveMessages = () => {
  try {
    sessionStorage.setItem('openkylin_messages', JSON.stringify(messages.value))
  } catch (error) {
    console.error('保存消息失败:', error)
  }
}

// 监听消息变化，自动保存
watch(messages, () => {
  saveMessages()
}, { deep: true })

// 页面加载时恢复会话
onMounted(() => {
  restoreSession()
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatBox.value) {
      chatBox.value.scrollTop = chatBox.value.scrollHeight
    }
  })
}

const sendMessage = async () => {
  if (!input.value.trim() || isLoading.value) return

  const userMsg = input.value
  messages.value.push({ role: '你', text: userMsg })
  input.value = ''
  isLoading.value = true
  scrollToBottom()

  try {
    const res = await axios.post(API_URL, {
      message: userMsg,
      session_id: sessionId.value
    })
    messages.value.push({ role: 'Agent', text: res.data.reply })
  } catch (err) {
    console.error('请求错误:', err)
    messages.value.push({ role: '系统', text: '❌ 请求失败，请检查后端是否在运行' })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.app-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.chat-container {
  width: 100%;
  max-width: 800px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 85vh;
  max-height: 700px;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px 25px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  font-size: 32px;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

.header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.2);
  padding: 6px 12px;
  border-radius: 20px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #4ade80;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 14px;
  font-weight: 500;
}

.chat-box {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f8f9fa;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-box::-webkit-scrollbar {
  width: 8px;
}

.chat-box::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.chat-box::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.chat-box::-webkit-scrollbar-thumb:hover {
  background: #a1a1a1;
}

.welcome-message {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
}

.welcome-icon {
  font-size: 64px;
  margin-bottom: 20px;
  animation: wave 1.5s ease-in-out infinite;
}

@keyframes wave {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(20deg); }
  75% { transform: rotate(-20deg); }
}

.welcome-message h2 {
  font-size: 28px;
  color: #334155;
  margin: 0 0 12px 0;
}

.welcome-message p {
  font-size: 16px;
  margin: 0;
}

.message-wrapper {
  display: flex;
  gap: 12px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-wrapper.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.message-content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.message-header {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  padding: 0 4px;
}

.message-wrapper.user .message-header {
  text-align: right;
}

.message-text {
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.6;
  word-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.message-wrapper.user .message-text {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-bottom-right-radius: 4px;
}

.message-wrapper.agent .message-text {
  background: white;
  color: #1e293b;
  border-bottom-left-radius: 4px;
}

.input-area {
  padding: 20px 25px;
  background: white;
  border-top: 1px solid #e5e7eb;
  display: flex;
  gap: 12px;
}

input {
  flex: 1;
  padding: 14px 18px;
  border-radius: 12px;
  border: 2px solid #e5e7eb;
  font-size: 15px;
  transition: all 0.3s ease;
  outline: none;
}

input:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

input:disabled {
  background: #f3f4f6;
  cursor: not-allowed;
}

.send-button {
  padding: 14px 28px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.send-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
}

.send-button:active:not(:disabled) {
  transform: translateY(0);
}

.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .app-wrapper {
    padding: 0;
  }

  .chat-container {
    max-width: 100%;
    height: 100vh;
    max-height: 100vh;
    border-radius: 0;
  }

  .header h1 {
    font-size: 18px;
  }

  .logo {
    font-size: 24px;
  }

  .message-content {
    max-width: 80%;
  }

  .welcome-message {
    padding: 40px 20px;
  }

  .welcome-icon {
    font-size: 48px;
  }

  .welcome-message h2 {
    font-size: 22px;
  }
}
</style>
