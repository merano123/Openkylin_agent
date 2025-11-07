<template>
  <div class="chat-container">
    <h1>openKylin 智能体</h1>

    <div class="chat-box">
      <div v-for="(msg, index) in messages" :key="index" class="message">
        <b>{{ msg.role }}:</b> {{ msg.text }}
      </div>
    </div>

    <div class="input-area">
      <input
        v-model="input"
        @keyup.enter="sendMessage"
        placeholder="输入消息后按回车发送..."
      />
      <button @click="sendMessage">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

// 后端 FastAPI 地址
const API_URL = 'http://localhost:8080/chat'

const input = ref('')
const messages = ref([])

const sendMessage = async () => {
  if (!input.value.trim()) return
  const userMsg = input.value
  messages.value.push({ role: '你', text: userMsg })
  input.value = ''
  try {
    const res = await axios.post(API_URL, { message: userMsg })
    messages.value.push({ role: 'Agent', text: res.data.reply })
  } catch (err) {
    messages.value.push({ role: '系统', text: '❌ 请求失败，请检查后端是否在运行' })
  }
}
</script>

<style>
.chat-container {
  max-width: 600px;
  margin: 40px auto;
  font-family: sans-serif;
  text-align: center;
}

.chat-box {
  border: 1px solid #ccc;
  border-radius: 8px;
  padding: 12px;
  height: 400px;
  overflow-y: auto;
  text-align: left;
  margin-bottom: 10px;
}

.message {
  margin: 5px 0;
}

.input-area {
  display: flex;
  gap: 8px;
}

input {
  flex: 1;
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #aaa;
}

button {
  padding: 8px 12px;
  background-color: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>
