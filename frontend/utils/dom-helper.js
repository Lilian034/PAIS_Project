/**
 * DOM 輔助工具模組
 * 提供常用的 DOM 操作函數
 */

/**
 * 選擇單個元素
 * @param {string} selector - CSS 選擇器
 * @param {Element} parent - 父元素（可選）
 * @returns {Element|null}
 */
export function $(selector, parent = document) {
    return parent.querySelector(selector);
}

/**
 * 選擇多個元素
 * @param {string} selector - CSS 選擇器
 * @param {Element} parent - 父元素（可選）
 * @returns {NodeList}
 */
export function $$(selector, parent = document) {
    return parent.querySelectorAll(selector);
}

/**
 * 創建元素
 * @param {string} tag - 標籤名稱
 * @param {Object} attrs - 屬性對象
 * @param {Array|string} children - 子元素或文字
 * @returns {Element}
 */
export function createElement(tag, attrs = {}, children = []) {
    const element = document.createElement(tag);

    // 設置屬性
    Object.entries(attrs).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(element.style, value);
        } else if (key.startsWith('on') && typeof value === 'function') {
            element.addEventListener(key.slice(2).toLowerCase(), value);
        } else {
            element.setAttribute(key, value);
        }
    });

    // 添加子元素
    if (Array.isArray(children)) {
        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Element) {
                element.appendChild(child);
            }
        });
    } else if (typeof children === 'string') {
        element.textContent = children;
    }

    return element;
}

/**
 * 設置元素的 HTML 內容
 * @param {Element} element - 目標元素
 * @param {string} html - HTML 字符串
 */
export function setHTML(element, html) {
    if (element) {
        element.innerHTML = html;
    }
}

/**
 * 清空元素內容
 * @param {Element} element - 目標元素
 */
export function clearElement(element) {
    if (element) {
        element.innerHTML = '';
    }
}

/**
 * 切換類別
 * @param {Element} element - 目標元素
 * @param {string} className - 類別名稱
 * @param {boolean} force - 強制添加或移除（可選）
 */
export function toggleClass(element, className, force) {
    if (element) {
        element.classList.toggle(className, force);
    }
}

/**
 * 添加類別
 * @param {Element} element - 目標元素
 * @param {...string} classNames - 類別名稱
 */
export function addClass(element, ...classNames) {
    if (element) {
        element.classList.add(...classNames);
    }
}

/**
 * 移除類別
 * @param {Element} element - 目標元素
 * @param {...string} classNames - 類別名稱
 */
export function removeClass(element, ...classNames) {
    if (element) {
        element.classList.remove(...classNames);
    }
}

/**
 * 檢查是否有類別
 * @param {Element} element - 目標元素
 * @param {string} className - 類別名稱
 * @returns {boolean}
 */
export function hasClass(element, className) {
    return element ? element.classList.contains(className) : false;
}

/**
 * 顯示元素
 * @param {Element} element - 目標元素
 */
export function show(element) {
    removeClass(element, 'hidden');
}

/**
 * 隱藏元素
 * @param {Element} element - 目標元素
 */
export function hide(element) {
    addClass(element, 'hidden');
}

/**
 * 切換元素顯示/隱藏
 * @param {Element} element - 目標元素
 */
export function toggle(element) {
    toggleClass(element, 'hidden');
}

/**
 * 添加事件監聽器
 * @param {Element} element - 目標元素
 * @param {string} event - 事件名稱
 * @param {Function} handler - 事件處理函數
 * @param {Object} options - 事件選項（可選）
 */
export function on(element, event, handler, options) {
    if (element) {
        element.addEventListener(event, handler, options);
    }
}

/**
 * 移除事件監聽器
 * @param {Element} element - 目標元素
 * @param {string} event - 事件名稱
 * @param {Function} handler - 事件處理函數
 */
export function off(element, event, handler) {
    if (element) {
        element.removeEventListener(event, handler);
    }
}

/**
 * 委託事件監聽
 * @param {Element} parent - 父元素
 * @param {string} selector - 子元素選擇器
 * @param {string} event - 事件名稱
 * @param {Function} handler - 事件處理函數
 */
export function delegate(parent, selector, event, handler) {
    on(parent, event, (e) => {
        const target = e.target.closest(selector);
        if (target && parent.contains(target)) {
            handler.call(target, e);
        }
    });
}

/**
 * 獲取/設置元素屬性
 * @param {Element} element - 目標元素
 * @param {string} attr - 屬性名稱
 * @param {string} value - 屬性值（可選，如果提供則設置）
 * @returns {string|void}
 */
export function attr(element, attr, value) {
    if (!element) return;

    if (value === undefined) {
        return element.getAttribute(attr);
    } else {
        element.setAttribute(attr, value);
    }
}

/**
 * 移除元素屬性
 * @param {Element} element - 目標元素
 * @param {string} attr - 屬性名稱
 */
export function removeAttr(element, attr) {
    if (element) {
        element.removeAttribute(attr);
    }
}

/**
 * 獲取/設置元素數據屬性
 * @param {Element} element - 目標元素
 * @param {string} key - 數據鍵名
 * @param {*} value - 數據值（可選，如果提供則設置）
 * @returns {*}
 */
export function data(element, key, value) {
    if (!element) return;

    if (value === undefined) {
        return element.dataset[key];
    } else {
        element.dataset[key] = value;
    }
}

/**
 * 轉義 HTML 特殊字符
 * @param {string} text - 要轉義的文字
 * @returns {string}
 */
export function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * 格式化檔案大小
 * @param {number} bytes - 位元組數
 * @returns {string}
 */
export function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
}

/**
 * 獲取檔案圖標
 * @param {string} extension - 檔案副檔名
 * @returns {string}
 */
export function getFileIcon(extension) {
    const iconMap = {
        'pdf': '📄',
        'doc': '📝',
        'docx': '📝',
        'txt': '📋',
        'xls': '📊',
        'xlsx': '📊',
        'ppt': '📊',
        'pptx': '📊',
        'jpg': '🖼️',
        'jpeg': '🖼️',
        'png': '🖼️',
        'gif': '🖼️',
        'mp3': '🎵',
        'wav': '🎵',
        'mp4': '🎬',
        'avi': '🎬',
        'zip': '📦',
        'rar': '📦',
    };
    return iconMap[extension.toLowerCase()] || '📄';
}

/**
 * 數字補零
 * @param {number} n - 數字
 * @returns {string}
 */
export function pad(n) {
    return n < 10 ? '0' + n : n;
}

/**
 * 格式化日期時間
 * @param {Date|string} date - 日期對象或字符串
 * @returns {string}
 */
export function formatDateTime(date) {
    const d = new Date(date);
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
