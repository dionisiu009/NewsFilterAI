// ==============================================================================
// NEWSFILTERAI - URL INPUT FORM COMPONENT
// ==============================================================================

import { useState } from 'react';
import './UrlInputForm.css';

/**
 * Валідує URL
 * @param {string} url
 * @returns {boolean}
 */
const isValidUrl = (url) => {
  try {
    const parsed = new URL(url);
    return ['http:', 'https:'].includes(parsed.protocol);
  } catch {
    return false;
  }
};

/**
 * Компонент форми введення URL
 */
const UrlInputForm = ({ onSubmit, isLoading, isProcessing }) => {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();

    const trimmedUrl = url.trim();

    if (!trimmedUrl) {
      setError('Введіть URL новини');
      return;
    }

    if (!isValidUrl(trimmedUrl)) {
      setError('Невалідний URL. Переконайтеся, що він починається з http:// або https://');
      return;
    }

    setError('');
    onSubmit(trimmedUrl);
  };

  const handleChange = (e) => {
    setUrl(e.target.value);
    if (error) setError('');
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && isValidUrl(text.trim())) {
        setUrl(text.trim());
        setError('');
      }
    } catch {
      // Clipboard API може бути недоступний
    }
  };

  const isDisabled = isLoading || isProcessing;

  return (
    <form className="url-form" onSubmit={handleSubmit}>
      <div className="url-input-wrapper">
        <div className="input-container">
          <span className="input-icon">🔗</span>
          <input
            type="text"
            className={`url-input ${error ? 'url-input--error' : ''}`}
            placeholder="Вставте URL новини для перевірки..."
            value={url}
            onChange={handleChange}
            disabled={isDisabled}
          />
          <button
            type="button"
            className="paste-button"
            onClick={handlePaste}
            disabled={isDisabled}
            title="Вставити з буферу"
          >
            📋
          </button>
        </div>

        {error && <span className="url-error">{error}</span>}
      </div>

      <button
        type="submit"
        className={`submit-button ${isDisabled ? 'submit-button--disabled' : ''}`}
        disabled={isDisabled}
      >
        {isLoading ? (
          <>
            <span className="spinner"></span>
            Відправляємо...
          </>
        ) : isProcessing ? (
          <>
            <span className="spinner"></span>
            AI аналізує...
          </>
        ) : (
          <>
            <span className="button-icon">🔍</span>
            Перевірити
          </>
        )}
      </button>

      <p className="url-hint">
        💡 Приклад: <code>https://www.bbc.com/news/article</code>
      </p>
    </form>
  );
};

export default UrlInputForm;

