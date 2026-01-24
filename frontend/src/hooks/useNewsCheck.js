// ==============================================================================
// NEWSFILTERAI - USE NEWS CHECK HOOK
// ==============================================================================
// Custom hook для перевірки новин з управлінням станом

import { useState, useCallback } from 'react';
import { checkNews, waitForResult } from '../services/api';

/**
 * Статуси перевірки
 */
export const CheckStatus = {
  IDLE: 'idle',
  LOADING: 'loading',
  PROCESSING: 'processing',
  SUCCESS: 'success',
  ERROR: 'error',
};

/**
 * Custom hook для перевірки новин
 * @returns {Object} - Стан та функції для перевірки
 */
export const useNewsCheck = () => {
  const [status, setStatus] = useState(CheckStatus.IDLE);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [errorDetails, setErrorDetails] = useState(null);
  const [progress, setProgress] = useState(null);

  /**
   * Скидає стан
   */
  const reset = useCallback(() => {
    setStatus(CheckStatus.IDLE);
    setResult(null);
    setError(null);
    setErrorDetails(null);
    setProgress(null);
  }, []);

  /**
   * Виконує перевірку новини
   * @param {string} url - URL новини
   */
  const check = useCallback(async (url) => {
    // Скидаємо попередній стан
    reset();
    setStatus(CheckStatus.LOADING);
    setProgress({ message: 'Відправляємо запит...' });

    try {
      // Крок 1: Відправляємо запит на перевірку
      const response = await checkNews(url);

      if (!response.success) {
        setStatus(CheckStatus.ERROR);
        setError(response.error);
        setErrorDetails(response.errorDetails || null);
        return;
      }

      const data = response.data;

      // Якщо результат з кешу - одразу повертаємо
      if (data.cached) {
        setStatus(CheckStatus.SUCCESS);
        setResult({
          ...data.result,
          cached: true,
        });
        return;
      }

      // Крок 2: Якщо задача запущена - чекаємо на результат
      if (data.task_id) {
        setStatus(CheckStatus.PROCESSING);
        setProgress({
          message: 'AI аналізує новину...',
          taskId: data.task_id,
          elapsed: 0,
        });

        // Polling для отримання результату
        const finalResult = await waitForResult(data.task_id, (progressInfo) => {
          setProgress({
            message: `AI аналізує новину... (${progressInfo.elapsed}с)`,
            taskId: data.task_id,
            elapsed: progressInfo.elapsed,
            status: progressInfo.status,
          });
        });

        if (finalResult.success) {
          setStatus(CheckStatus.SUCCESS);
          setResult({
            ...finalResult.data,
            cached: false,
          });
        } else {
          setStatus(CheckStatus.ERROR);
          setError(finalResult.error);
          setErrorDetails(finalResult.errorDetails || null);
        }
      } else {
        setStatus(CheckStatus.ERROR);
        setError('Неочікувана відповідь сервера');
      }
    } catch (err) {
      setStatus(CheckStatus.ERROR);
      setError(err.message || 'Невідома помилка');
    }
  }, [reset]);

  return {
    status,
    result,
    error,
    errorDetails,
    progress,
    check,
    reset,
    isLoading: status === CheckStatus.LOADING,
    isProcessing: status === CheckStatus.PROCESSING,
    isSuccess: status === CheckStatus.SUCCESS,
    isError: status === CheckStatus.ERROR,
    isIdle: status === CheckStatus.IDLE,
  };
};

export default useNewsCheck;

