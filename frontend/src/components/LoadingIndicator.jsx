// ==============================================================================
// NEWSFILTERAI - LOADING INDICATOR COMPONENT
// ==============================================================================

import './LoadingIndicator.css';

/**
 * Компонент індикатора завантаження
 */
const LoadingIndicator = ({ message, elapsed }) => {
  return (
    <div className="loading-indicator">
      <div className="loading-animation">
        <div className="loading-circle"></div>
        <div className="loading-circle"></div>
        <div className="loading-circle"></div>
      </div>

      <div className="loading-content">
        <p className="loading-message">{message}</p>
        {elapsed !== undefined && (
          <p className="loading-elapsed">⏱️ Час очікування: {elapsed}с</p>
        )}
      </div>

      <div className="loading-steps">
        <div className="step step--active">
          <span className="step-icon">📥</span>
          <span className="step-text">Отримання</span>
        </div>
        <div className={`step ${elapsed > 2 ? 'step--active' : ''}`}>
          <span className="step-icon">📝</span>
          <span className="step-text">Парсинг</span>
        </div>
        <div className={`step ${elapsed > 5 ? 'step--active' : ''}`}>
          <span className="step-icon">🤖</span>
          <span className="step-text">AI аналіз</span>
        </div>
        <div className={`step ${elapsed > 15 ? 'step--active' : ''}`}>
          <span className="step-icon">✅</span>
          <span className="step-text">Результат</span>
        </div>
      </div>
    </div>
  );
};

export default LoadingIndicator;

