/**
 * 標籤管理模組
 * 負責幕僚系統的標籤切換功能
 */

import { $$, addClass, removeClass } from '../utils/dom-helper.js';

/**
 * 初始化標籤切換功能
 * @export
 */
export function init() {
    const navItems = $$('.nav-item');
    const tabContents = $$('.tab-content');

    if (navItems.length === 0 || tabContents.length === 0) {
        console.warn('標籤管理：找不到必要的 DOM 元素');
        return;
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tabId = item.getAttribute('data-tab');

            // 移除所有活動狀態
            navItems.forEach(nav => removeClass(nav, 'active'));
            tabContents.forEach(content => removeClass(content, 'active'));

            // 添加活動狀態到當前標籤
            addClass(item, 'active');

            const targetTab = document.getElementById(tabId);
            if (targetTab) {
                addClass(targetTab, 'active');
            } else {
                console.warn(`找不到標籤內容: ${tabId}`);
            }
        });
    });

    console.log('✅ 標籤管理已初始化');
}

/**
 * 切換到指定標籤
 * @param {string} tabId - 標籤 ID
 * @export
 */
export function switchToTab(tabId) {
    const navItem = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
    if (navItem) {
        navItem.click();
    } else {
        console.warn(`找不到標籤: ${tabId}`);
    }
}

/**
 * 獲取當前活動的標籤 ID
 * @returns {string|null}
 * @export
 */
export function getActiveTab() {
    const activeNav = document.querySelector('.nav-item.active');
    return activeNav ? activeNav.getAttribute('data-tab') : null;
}
