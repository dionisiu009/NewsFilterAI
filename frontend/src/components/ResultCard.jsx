// ==============================================================================
// NEWSFILTERAI - RESULT CARD COMPONENT
// ==============================================================================

import DebugInfo from './DebugInfo';
import './ResultCard.css';

/**
 * Конфігурація вердиктів
 */
const verdictConfig = {
  true: {
    emoji: '✅',
    text: 'ДОСТОВІРНА',
    className: 'verdict--true',
    description: 'Інформація підтверджена',
  },
  false: {
    emoji: '🔴',
    text: 'ФЕЙК',
    className: 'verdict--false',
    description: 'Виявлено недостовірну інформацію',
  },
  partial: {
    emoji: '🟡',
    text: 'ЧАСТКОВО ПРАВДА',
    className: 'verdict--partial',
    description: 'Містить як правдиву, так і сумнівну інформацію',
  },
  unverifiable: {
    emoji: '❓',
    text: 'НЕМОЖЛИВО ПЕРЕВІРИТИ',
    className: 'verdict--unverifiable',
    description: 'Недостатньо даних для висновку',
  },
  error: {
    emoji: '⚠️',
    text: 'ПОМИЛКА',
    className: 'verdict--error',
    description: 'Виникла помилка при перевірці',
  },
};

/**
 * Компонент картки результату
 */
const ResultCard = ({ result, onReset, debugEnabled = false }) => {
  const {
    verdict = 'unverifiable',
    confidence_score: confidence = 0,
    title = 'Без заголовку',
    source_domain: domain = 'Невідомо',
    summary = '',
    recommendation = '',
    ai_verdict_json: analysis = {},
    cached = false,
    debug_info: debugInfo = null,
  } = result;

  const config = verdictConfig[verdict] || verdictConfig.unverifiable;

  return (
    <div className={`result-card ${config.className}`}>
      {/* Заголовок з вердиктом */}
      <div className="result-header">
        <div className="verdict-badge">
          <span className="verdict-emoji">{config.emoji}</span>
          <span className="verdict-text">{config.text}</span>
        </div>
        {cached && (
          <span className="cache-badge" title="Результат з кешу">
            📦 Кеш
          </span>
        )}
      </div>

      {/* Опис вердикту */}
      <p className="verdict-description">{config.description}</p>

      {/* Інформація про новину */}
      <div className="result-info">
        <div className="info-item">
          <span className="info-icon">📰</span>
          <div className="info-content">
            <span className="info-label">Заголовок</span>
            <span className="info-value">{title}</span>
          </div>
        </div>

        <div className="info-item">
          <span className="info-icon">🌐</span>
          <div className="info-content">
            <span className="info-label">Джерело</span>
            <span className="info-value">{domain}</span>
          </div>
        </div>

        <div className="info-item">
          <span className="info-icon">📊</span>
          <div className="info-content">
            <span className="info-label">Впевненість AI</span>
            <div className="confidence-bar-wrapper">
              <div
                className="confidence-bar"
                style={{ width: `${Math.min(confidence, 100)}%` }}
              />
              <span className="confidence-value">{confidence.toFixed(0)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Аналіз */}
      {summary && (
        <div className="result-section">
          <h3 className="section-title">
            <span>📝</span> Аналіз
          </h3>
          <p className="section-content">{summary}</p>
        </div>
      )}

      {/* Рекомендація */}
      {recommendation && (
        <div className="result-section result-section--highlight">
          <h3 className="section-title">
            <span>💡</span> Рекомендація
          </h3>
          <p className="section-content">{recommendation}</p>
        </div>
      )}

      {/* Детальний аналіз AI */}
      {analysis && (analysis.analysis || analysis.factual_accuracy || analysis.summary) && (
        <details className="ai-analysis-accordion">
          <summary>
            🔬 Детальний аналіз AI
          </summary>

          <div className="details-content">
            {/* Точність фактів */}
            {(analysis.analysis?.factual_accuracy || analysis.factual_accuracy) && (
              <div className="detail-item">
                <strong>Точність фактів:</strong>
                <p>{analysis.analysis?.factual_accuracy || analysis.factual_accuracy}</p>
              </div>
            )}

            {/* Достовірність джерела */}
            {(analysis.analysis?.source_credibility || analysis.source_credibility) && (
              <div className="detail-item">
                <strong>Достовірність джерела:</strong>
                <p>{analysis.analysis?.source_credibility || analysis.source_credibility}</p>
              </div>
            )}

            {/* Ознаки маніпуляції */}
            {((analysis.analysis?.manipulation_signs?.length > 0) || (analysis.manipulation_signs?.length > 0)) && (
              <div className="detail-item">
                <strong>Ознаки маніпуляції:</strong>
                <ul>
                  {(analysis.analysis?.manipulation_signs || analysis.manipulation_signs).map((sign, i) => (
                    <li key={i}>{sign}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Динамічне відображення будь-яких інших полів аналізу */}
            {analysis.analysis && Object.entries(analysis.analysis).map(([key, value]) => {
              if (['factual_accuracy', 'source_credibility', 'manipulation_signs', 'verified_facts', 'note'].includes(key)) return null;
              if (!value || (typeof value === 'string' && value.length < 5)) return null;

              const labels = {
                'detailed_analysis': 'Детальний аналіз',
                'evidence': 'Докази',
                'context': 'Контекст'
              };

              return (
                <div className="detail-item" key={key}>
                  <strong>{labels[key] || key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}:</strong>
                  {Array.isArray(value) ? (
                    <ul>{value.map((v, i) => <li key={i}>{v}</li>)}</ul>
                  ) : (
                    <p>{value}</p>
                  )}
                </div>
              );
            })}
          </div>
        </details>
      )}

      {/* Debug інформація про парсинг */}
      {debugEnabled && (
        <DebugInfo debugInfo={debugInfo} />
      )}

      {/* Кнопка нової перевірки */}
      <button className="reset-button" onClick={onReset}>
        🔄 Перевірити іншу новину
      </button>
    </div>
  );
};

export default ResultCard;
