// ==============================================================================
// NEWSFILTERAI - API SERVICE
// ==============================================================================
// Сервіс для взаємодії з Django Backend API

import axios from 'axios';

// Базовий URL API (через Traefik proxy)
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Таймаути
const REQUEST_TIMEOUT = 60000; // 60 секунд
const POLLING_TIMEOUT = 300000; // 300 секунд (5 хвилин)
const POLLING_INTERVAL = 2000; // 2 секунди

// Створюємо axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Перевіряє новину за URL
 * @param {string} url - URL новини
 * @returns {Promise<Object>} - Результат перевірки або task_id
 */
export const checkNews = async (url) => {
  try {
    const response = await apiClient.post('/check/', { url });
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    // Формуємо детальне повідомлення про помилку
    let errorMessage = 'Помилка з\'єднання';
    let errorDetails = null;

    if (error.response) {
      // Сервер відповів з помилкою
      const data = error.response.data;
      errorMessage = data.error || data.message || `Помилка сервера (${error.response.status})`;
      errorDetails = {
        status: error.response.status,
        errorCode: data.error_code,
        message: data.message,
        traceback: data.traceback
      };
    } else if (error.request) {
      // Запит був відправлений, але відповіді не отримано
      errorMessage = 'Сервер не відповідає. Перевірте з\'єднання.';
    } else {
      errorMessage = error.message;
    }

    return {
      success: false,
      error: errorMessage,
      errorDetails
    };
  }
};

/**
 * Отримує статус Celery задачі
 * @param {string} taskId - ID задачі
 * @returns {Promise<Object>} - Статус та результат задачі
 */
export const getTaskStatus = async (taskId) => {
  try {
    const response = await apiClient.get(`/task-status/${taskId}/`);
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data?.error || error.message,
    };
  }
};

/**
 * Очікує завершення задачі з polling
 * @param {string} taskId - ID задачі
 * @param {Function} onProgress - Callback для оновлення прогресу
 * @returns {Promise<Object>} - Результат задачі
 */
export const waitForResult = async (taskId, onProgress = null) => {
  const startTime = Date.now();

  while (Date.now() - startTime < POLLING_TIMEOUT) {
    const result = await getTaskStatus(taskId);

    if (!result.success) {
      return result;
    }

    const status = result.data.status?.toLowerCase();

    if (onProgress) {
      onProgress({
        status,
        elapsed: Math.floor((Date.now() - startTime) / 1000),
      });
    }

    if (status === 'success') {
      return {
        success: true,
        data: result.data.result,
      };
    }

    if (status === 'failure') {
      return {
        success: false,
        error: result.data.error || 'Помилка обробки задачі',
      };
    }

    // Чекаємо перед наступним запитом
    await new Promise(resolve => setTimeout(resolve, POLLING_INTERVAL));
  }

  return {
    success: false,
    error: 'Перевищено час очікування. Спробуйте пізніше.',
  };
};

/**
 * Перевіряє репутацію домену
 * @param {string} domain - Домен для перевірки
 * @returns {Promise<Object>} - Інформація про репутацію
 */
export const checkDomain = async (domain) => {
  try {
    const response = await apiClient.get('/domain-check/', { params: { domain } });
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
};

/**
 * Отримує історію перевірок
 * @param {Object} params - Параметри запиту (limit, offset, domain, verdict)
 * @returns {Promise<Object>} - Список перевірок
 */
export const getHistory = async (params = {}) => {
  try {
    const response = await apiClient.get('/history/', { params });
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
};

/**
 * Отримує списки доменів (білий/чорний)
 * @param {string} type - Тип списку: 'all', 'whitelist', 'blacklist'
 * @returns {Promise<Object>} - Списки доменів
 */
export const getDomainLists = async (type = 'all') => {
  try {
    const response = await apiClient.get('/domains/', { params: { type } });
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
    };
  }
};

/**
 * Перевіряє здоров'я API
 * @returns {Promise<boolean>}
 */
export const healthCheck = async () => {
  try {
    const response = await apiClient.get('/health/');
    return response.data?.status === 'healthy';
  } catch {
    return false;
  }
};

/**
 * Debug перевірка - покрокова діагностика
 * @param {string} url - URL новини для діагностики
 * @returns {Promise<Object>} - Результат діагностики
 */
export const debugCheck = async (url) => {
  try {
    const response = await apiClient.post('/debug/check/', { url });
    return {
      success: true,
      data: response.data,
    };
  } catch (error) {
    return {
      success: false,
      error: error.response?.data || error.message,
      data: error.response?.data
    };
  }
};

export default {
  checkNews,
  getTaskStatus,
  waitForResult,
  checkDomain,
  getHistory,
  getDomainLists,
  healthCheck,
  debugCheck,
};

