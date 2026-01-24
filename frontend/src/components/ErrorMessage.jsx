// ==============================================================================
// NEWSFILTERAI - ERROR MESSAGE COMPONENT
// ==============================================================================

import { useState } from 'react';
import './ErrorMessage.css';

/**
 * Компонент повідомлення про помилку з деталями
 */
const ErrorMessage = ({ message, onRetry, errorDetails }) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div className="error-message">
      <div className="error-icon">⚠️</div>
      <h3 className="error-title">Виникла помилка</h3>
      <p className="error-text">{message}</p>

      {errorDetails && (
        <div className="error-details-container">
          <button
            className="error-details-toggle"
            onClick={() => setShowDetails(!showDetails)}
          >
            {showDetails ? '🔼 Сховати деталі' : '🔽 Показати деталі'}
          </button>

          {showDetails && (
            <div className="error-details">
              {errorDetails.status && (
                <p><strong>HTTP статус:</strong> {errorDetails.status}</p>
              )}
              {errorDetails.errorCode && (
                <p><strong>Код помилки:</strong> {errorDetails.errorCode}</p>
              )}
              {errorDetails.message && (
                <p><strong>Повідомлення:</strong> {errorDetails.message}</p>
              )}
              {errorDetails.traceback && (
                <pre className="error-traceback">{errorDetails.traceback}</pre>
              )}
            </div>
          )}
        </div>
      )}

      <button className="error-button" onClick={onRetry}>
        🔄 Спробувати ще раз
      </button>
    </div>
  );
};

export default ErrorMessage;

