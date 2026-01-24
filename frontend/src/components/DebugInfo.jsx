// ==============================================================================
// NEWSFILTERAI - DEBUG INFO COMPONENT
// ==============================================================================
// Компонент для відображення debug інформації про парсинг

import './DebugInfo.css';
import React from 'react';
import ParserComparisonModal from './ParserComparisonModal';

/**
 * Форматує дату для відображення
 */
const formatDate = (dateStr) => {
  if (!dateStr || dateStr === 'None' || dateStr === 'null') {
    return 'Не знайдено';
  }
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return dateStr;
    }
    return date.toLocaleString('uk-UA', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateStr;
  }
};

/**
 * Компонент debug інформації про парсинг
 * @param {Object} debugInfo - Інформація про парсинг
 */
const DebugInfo = ({ debugInfo }) => {
  if (!debugInfo) {
    return (
      <div className="debug-info debug-info--empty">
        <div className="debug-info__header">
          <span className="debug-info__icon">🔧</span>
          <span>Debug Info</span>
        </div>
        <p className="debug-info__no-data">
          Debug інформація недоступна для кешованих результатів.
          <br />
          Спробуйте перевірити нову новину.
        </p>
      </div>
    );
  }

  const {
    parsed_title,
    parsed_text,
    parsed_authors,
    parsed_publish_date,
    parsed_top_image,
    parsed_domain,
    parsed_meta_description,
    parsed_word_count,
    parsers_debug
  } = debugInfo;

  const [showModal, setShowModal] = React.useState(false);

  return (
    <div className="debug-info">
      <div className="debug-info__header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="debug-info__icon">🔧</span>
          <span>Parser Debug Info</span>
        </div>

        {parsers_debug && parsers_debug.length > 0 && (
          <button
            className="compare-parsers-btn"
            onClick={() => setShowModal(true)}
            style={{
              backgroundColor: '#3498db',
              border: 'none',
              color: 'white',
              padding: '5px 12px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '0.8rem',
              fontWeight: 'bold',
              marginLeft: 'auto'
            }}
          >
            ⚖️ Compare Parsers
          </button>
        )}
      </div>

      <div className="debug-info__grid">
        {/* Заголовок */}
        <div className="debug-info__item">
          <span className="debug-info__label">📰 Заголовок (parsed)</span>
          <span className="debug-info__value">
            {parsed_title || 'Не знайдено'}
          </span>
        </div>

        {/* Автори */}
        <div className="debug-info__item">
          <span className="debug-info__label">✍️ Автор(и)</span>
          <span className="debug-info__value">
            {parsed_authors && parsed_authors.length > 0
              ? parsed_authors.join(', ')
              : 'Не знайдено'}
          </span>
        </div>

        {/* Дата публікації */}
        <div className="debug-info__item debug-info__item--highlight">
          <span className="debug-info__label">📅 Дата публікації</span>
          <span className="debug-info__value">
            {formatDate(parsed_publish_date)}
            {parsed_publish_date && (
              <span className="debug-info__raw">
                (raw: {parsed_publish_date})
              </span>
            )}
          </span>
        </div>

        {/* Домен */}
        <div className="debug-info__item">
          <span className="debug-info__label">🌐 Домен</span>
          <span className="debug-info__value">{parsed_domain || 'Не знайдено'}</span>
        </div>

        {/* Кількість слів */}
        <div className="debug-info__item">
          <span className="debug-info__label">📊 Кількість слів</span>
          <span className="debug-info__value">{parsed_word_count || 0}</span>
        </div>


        {/* Meta Description */}
        {parsed_meta_description && (
          <div className="debug-info__item debug-info__item--full">
            <span className="debug-info__label">📝 Meta Description</span>
            <span className="debug-info__value debug-info__value--small">
              {parsed_meta_description}
            </span>
          </div>
        )}
      </div>

      {/* Текст статті */}
      <details className="debug-info__text-section">
        <summary className="debug-info__text-summary">
          📄 Повний текст статті ({parsed_word_count} слів)
        </summary>
        <div className="debug-info__text-content">
          {parsed_text || 'Текст не знайдено'}
        </div>
      </details>

      {/* Модальне вікно для порівняння парсерів */}
      <ParserComparisonModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        parsersDebug={parsers_debug}
        winnerData={debugInfo}
      />
    </div>
  );
};

export default DebugInfo;
