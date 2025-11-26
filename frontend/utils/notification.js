/**
 * 通知系統模組
 * 提供統一的通知顯示功能
 */

import { createElement, addClass } from './dom-helper.js';

/**
 * 顯示通知
 * @param {string} message - 通知消息
 * @param {string} type - 通知類型 ('success', 'error', 'warning', 'info')
 * @param {number} duration - 顯示時長（毫秒），0 表示不自動關閉
 */
export function showNotification(message, type = 'info', duration = 3000) {
    // 創建或獲取通知容器
    let container = document.getElementById('notification-container');
    if (!container) {
        container = createElement('div', {
            id: 'notification-container',
            className: 'notification-container'
        });
        document.body.appendChild(container);
    }

    // 圖標映射
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    // 創建通知元素
    const notification = createElement('div', {
        className: `notification notification-${type} show`
    });

    const icon = createElement('span', {
        className: 'notification-icon'
    }, icons[type] || icons.info);

    const text = createElement('span', {
        className: 'notification-text'
    }, message);

    const closeBtn = createElement('button', {
        className: 'notification-close',
        onclick: () => removeNotification(notification)
    }, '×');

    notification.appendChild(icon);
    notification.appendChild(text);
    notification.appendChild(closeBtn);
    container.appendChild(notification);

    // 自動關閉
    if (duration > 0) {
        setTimeout(() => {
            removeNotification(notification);
        }, duration);
    }

    return notification;
}

/**
 * 移除通知
 * @param {Element} notification - 通知元素
 */
function removeNotification(notification) {
    if (!notification) return;

    addClass(notification, 'notification-hide');

    setTimeout(() => {
        notification.remove();

        // 如果容器為空，移除容器
        const container = document.getElementById('notification-container');
        if (container && container.children.length === 0) {
            container.remove();
        }
    }, 300);
}

/**
 * 成功通知
 * @param {string} message - 通知消息
 * @param {number} duration - 顯示時長（毫秒）
 */
export function success(message, duration) {
    return showNotification(message, 'success', duration);
}

/**
 * 錯誤通知
 * @param {string} message - 通知消息
 * @param {number} duration - 顯示時長（毫秒）
 */
export function error(message, duration) {
    return showNotification(message, 'error', duration);
}

/**
 * 警告通知
 * @param {string} message - 通知消息
 * @param {number} duration - 顯示時長（毫秒）
 */
export function warning(message, duration) {
    return showNotification(message, 'warning', duration);
}

/**
 * 信息通知
 * @param {string} message - 通知消息
 * @param {number} duration - 顯示時長（毫秒）
 */
export function info(message, duration) {
    return showNotification(message, 'info', duration);
}

/**
 * 確認對話框
 * @param {string} message - 確認消息
 * @returns {boolean}
 */
export function confirm(message) {
    return window.confirm(message);
}

/**
 * 提示對話框
 * @param {string} message - 提示消息
 * @param {string} defaultValue - 默認值
 * @returns {string|null}
 */
export function prompt(message, defaultValue = '') {
    return window.prompt(message, defaultValue);
}
