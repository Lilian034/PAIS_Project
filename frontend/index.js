// ==================== 桃園市民政通 - 前端 JS ====================
// 連接到 FastAPI 後端 (LangChain + Gemini)

let chatHistory = [];
let sessionId = null;

// API 基礎 URL (Nginx 會自動轉發到後端)
const API_BASE_URL = '/api';

// DOM 元素
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const chatMessages = document.getElementById('chatMessages');

// 可愛表情池
const cuteEmojis = ['✨','🌟','💡','💬','🎈','🍀','👍','🙌','😊','🧡','📌'];

// ==================== 工具函數 ====================

// 轉義 HTML
function escapeHTML(str) {
  return str.replace(/[&<>"']/g, m => (
    { "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[m]
  ));
}

// 格式化 AI 回應（支援 markdown）
function formatAIResponse(text) {
  // 處理粗體
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // 處理程式碼
  text = text.replace(/`([^`]+)`/g, '<code style="background:#f4f4f4;padding:2px 6px;border-radius:4px;">$1</code>');
  // 處理換行
  text = text.replace(/\n/g, '<br>');
  return text;
}

// 取得或建立 Session ID
function getSessionId() {
  if (!sessionId) {
    sessionId = localStorage.getItem('pais_session_id');
    if (!sessionId) {
      sessionId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('pais_session_id', sessionId);
    }
  }
  return sessionId;
}

// ==================== 訊息顯示 ====================

function addMessage(content, sender, opts = {asHTML: false}) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${sender}`;
  
  const avatar = document.createElement('div');
  avatar.className = `message-avatar ${sender}-avatar`;
  avatar.textContent = sender === 'ai' ? '' : '我'; // ai-avatar 使用 CSS 背景圖

  const contentDiv = document.createElement('div');
  contentDiv.className = `message-content ${sender}-message`;
  
  if (opts.asHTML) {
    contentDiv.innerHTML = content;
  } else {
    contentDiv.textContent = content;
  }

  messageDiv.appendChild(avatar);
  messageDiv.appendChild(contentDiv);
  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message typing-message';
  typingDiv.innerHTML = `
    <div class="message-avatar ai-avatar"></div>
    <div class="message-content ai-message loading">
      <span>善寶正在查詢知識庫</span>
      <div class="loading-dots">
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
      </div>
    </div>
  `;
  chatMessages.appendChild(typingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTyping() {
  const typingMessage = document.querySelector('.typing-message');
  if (typingMessage) typingMessage.remove();
}

// ==================== 發送訊息 ====================

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) return;

  // 顯示使用者訊息
  addMessage(escapeHTML(message), 'user', {asHTML: false});
  messageInput.value = '';
  messageInput.style.height = 'auto';

  // 顯示思考中
  setTimeout(() => {
    showTyping();
  }, 300);

  try {
    // 呼叫 FastAPI 後端（使用 public-api.js 中的函數）
    const data = await sendChatMessage(message, getSessionId(), true);
    
    // 移除思考中訊息
    removeTyping();
    
    // 取得 AI 回應
    const aiReply = data.reply;
    
    if (aiReply) {
      // 加上可愛的 emoji
      const emoji = cuteEmojis[Math.floor(Math.random() * cuteEmojis.length)];
      const formattedReply = formatAIResponse(aiReply) + ` ${emoji}`;
      
      addMessage(formattedReply, 'ai', {asHTML: true});

      // 如果有來源資訊，顯示
      if (data.sources && data.sources.length > 0) {
        const sourcesText = `<div style="margin-top:8px;font-size:12px;color:#6b7280;">
          📚 資料來源: ${data.sources.map(s => s.split('/').pop()).join(', ')}
        </div>`;
        addMessage(sourcesText, 'ai', {asHTML: true});
      }
      
      // 如果訊息包含數據關鍵字，顯示圖表提示
      if (/數據|統計|圖|成效|KPI|指標|分析/.test(message)) {
        setTimeout(() => {
          generateMultimediaResponse(message);
        }, 800);
      }
    } else {
      throw new Error('未收到回應內容');
    }

  } catch (error) {
    removeTyping();
    console.error('API 連接錯誤:', error);
    
    // 顯示友善的錯誤訊息
    const errorMsg = `抱歉，目前無法連接到知識庫系統<br>
      <span style="font-size:12px;color:#6b7280;">
      錯誤訊息: ${escapeHTML(error.message)}<br>
      請確認後端服務已啟動，或聯繫技術人員
      </span>`;
    addMessage(errorMsg, 'ai', {asHTML: true});
  }
}

// ==================== 多媒體回應 ====================

function generateMultimediaResponse(message) {
  const imageMessage = document.createElement('div');
  imageMessage.className = 'message';
  imageMessage.innerHTML = `
    <div class="message-avatar ai-avatar"></div>
    <div class="message-content ai-message">
      這裡用一張可愛小圖幫你看重點 📊
      <div class="media-content">
        <div style="width: 230px; height: 140px; background: #fff; border: 2px dashed #cfe8ff; border-radius: 12px; display:flex; align-items:center; justify-content:center; color:#6c7a89; font-size:12px;">
          <div style="text-align:center; line-height:1.4;">
            <div style="font-size:20px; margin-bottom:6px;">📈 政策成效圖</div>
            <div>指標 A ↑ 指標 B → 指標 C ↑</div>
            <div style="font-size:10px; opacity:.7; margin-top:6px;">（示意圖，實際數據以公告為準）</div>
          </div>
        </div>
      </div>
    </div>
  `;
  chatMessages.appendChild(imageMessage);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ==================== 事件綁定 ====================

document.addEventListener('DOMContentLoaded', () => {
  // 發送按鈕
  sendBtn.addEventListener('click', sendMessage);
  
  // Enter 送出
  messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); 
      sendMessage();
    }
  });

  // 標籤一鍵發問（如果 HTML 中有 .tag 元素）
  document.querySelectorAll('.tag').forEach(tag => {
    tag.addEventListener('click', () => {
      const topic = tag.textContent.trim();
      messageInput.value = `請說明「${topic}」的近期進度與成效。`;
      sendMessage();
    });
  });

  // 自動高度調整
  messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 110) + 'px';
  });

  // 健康檢查
  checkBackendHealth();

  console.log('🎉 桃園市民政通-AI助手已就緒！');
  console.log('📡 API端點:', API_BASE_URL);
  console.log('🆔 Session ID:', getSessionId());
});

// ==================== 健康檢查 ====================

async function checkBackendHealth() {
  try {
    const data = await checkPublicHealth();
    console.log('✅ 後端健康狀態:', data);
  } catch (error) {
    console.warn('⚠️ 後端健康檢查失敗:', error);
  }
}