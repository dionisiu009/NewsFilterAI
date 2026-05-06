// ==============================================================================
// NEWSFILTERAI - RESULT CARD COMPONENT
// ==============================================================================

import DebugInfo from './DebugInfo';
import './ResultCard.css';
import { DisinfoCards } from "./DisinfoCards";

const verdictConfig = {
    true: { emoji: "🟢", label: "Достовірно" },
    partial: { emoji: "🟡", label: "Частково достовірно" },
    false: { emoji: "🔴", label: "Фейк" },
    fact: { emoji: "🟢", label: "Факт" },
    "false-fake": { emoji: "🔴", label: "Фейк" },
    clickbait: { emoji: "🟠", label: "Клікбейт" },
    opinion: { emoji: "🗣️", label: "Думка" },
    satire: { emoji: "🎭", label: "Сатира" },
    unverifiable: { emoji: "⚪", label: "Неможливо перевірити" },
    error: { emoji: "⚫", label: "Помилка" },
    pending: { emoji: "⏳", label: "В обробці" },
};

function ResultCard({ result, onReset }) {
  let verdictClass = 'unknown';

  if (result.verdict === 'true' || result.verdict === 'fact') verdictClass = 'true';
  else if (result.verdict === 'partial') verdictClass = 'partial';
  else if (result.verdict === 'false' || result.verdict === 'false-fake') verdictClass = 'false';
  else if (result.verdict === 'clickbait') verdictClass = 'clickbait';
  else if (result.verdict === 'opinion') verdictClass = 'opinion';
  else if (result.verdict === 'satire') verdictClass = 'satire';
  else if (result.verdict === 'unverifiable') verdictClass = 'unverifiable';
  else if (result.verdict === 'error') verdictClass = 'error';

  const hasDetailedAnalysis = Array.isArray(result.analysis) ? result.analysis.length > 0 : (result.analysis && (result.analysis.analysis || result.analysis.factual_accuracy || result.analysis.summary));

  const isUnverifiable = result.verdict === 'unverifiable';
  const isError = result.verdict === 'error';

  const displayRecommendation = isUnverifiable
    ? "⚠️ Штучному інтелекту не вдалося знайти достатньо надійних джерел для перевірки цієї новини. Рекомендуємо:\n1. Перевірити наявність цієї інформації у відомих світових чи національних ЗМІ.\n2. Звернути увагу на першоджерело (чи є воно офіційним та надійним).\n3. Пошукати ключові слова з новини в Google самостійно."
    : result.recommendation;

  const renderExplanationWithLinks = (text, references) => {
    if (!text) return null;
    if (!references || Object.keys(references).length === 0) return text;
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, idx) => {
        const match = part.match(/\[(\d+)\]/);
        if (match && references[match[1]]) {
            return (
                <a
                    key={idx}
                    href={references[match[1]]}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#646cff', textDecoration: 'underline' }}
                    title={references[match[1]]}
                >
                    {part}
                </a>
            );
        }
        return part;
    });
  };

  return (
    <div className={`result-card ${verdictClass}`}>
      {/* Заголовок з вердиктом */}
      <div className="result-header">
        <div className="verdict-badge">
          <span className="verdict-emoji">{verdictConfig[result.verdict]?.emoji}</span>
          <span className="verdict-text">
            {isError && result.summary ? result.summary : verdictConfig[result.verdict]?.label}
          </span>
        </div>
        {result.cached && (
          <span className="cache-badge" title="Результат з кешу">
            📦 Кеш
          </span>
        )}
      </div>

      {/* Опис вердикту */}
      <p className="verdict-description">{verdictConfig[result.verdict]?.description}</p>

      {/* Інформація про новину */}
      {!isError && (
        <div className="result-info">
          <div className="info-item">
            <span className="info-icon">📰</span>
            <div className="info-content">
              <span className="info-label">Заголовок</span>
              <span className="info-value">{result.title}</span>
            </div>
          </div>

          <div className="info-item">
            <span className="info-icon">🌐</span>
            <div className="info-content">
              <span className="info-label">Джерело</span>
              <span className="info-value">{result.source_domain}</span>
            </div>
          </div>


        </div>
      )}

      {/* Аналіз */}
      {result.summary && !isError && (
        <div className="result-section">
          <h3 className="section-title">
            <span>📝</span> Аналіз
          </h3>
          <p className="section-content" style={{ whiteSpace: 'pre-wrap' }}>{result.summary}</p>
        </div>
      )}

      {/* Рекомендація */}
      {displayRecommendation && (
        <div className="result-section result-section--highlight">
          <h3 className="section-title">
            <span>💡</span> Рекомендація
          </h3>
          <p className="section-content" style={{ whiteSpace: 'pre-wrap' }}>{displayRecommendation}</p>
        </div>
      )}

      {/* Детальний аналіз AI */}
      {hasDetailedAnalysis && (
        <details className="ai-analysis-accordion">
          <summary>
            🔬 Детальний аналіз AI
          </summary>

          <div className="details-content">
            {Array.isArray(result.analysis) ? (
              <div className="intents-analysis" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                {result.analysis.map((intent, idx) => (
                  <div key={idx} className="intent-item" style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', padding: '12px', borderRadius: '8px' }}>
                    <div style={{ marginBottom: '8px', fontSize: '1.1em', fontWeight: 'bold' }}>
                      {verdictConfig[intent.intent_verdict]?.emoji || '❔'} {verdictConfig[intent.intent_verdict]?.label || intent.intent_verdict}
                    </div>
                    <p style={{ margin: '0 0 10px 0', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                      {renderExplanationWithLinks(intent.explanation, intent.references)}
                    </p>
                    {intent.references && Object.keys(intent.references).length > 0 && (
                      <div style={{ fontSize: '0.9em', opacity: 0.8 }}>
                        <strong style={{ display: 'block', marginBottom: '4px' }}>🔗 Джерела:</strong>
                        <ul style={{ margin: 0, paddingLeft: '20px' }}>
                          {Object.entries(intent.references).map(([id, url]) => {
                            let domain = url;
                            try { domain = new URL(url).hostname; } catch (e) {}
                            return (
                              <li key={id}>
                                <a href={url} target="_blank" rel="noopener noreferrer" style={{ color: 'inherit' }}>
                                  [{id}] {domain}
                                </a>
                              </li>
                            );
                          })}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
             <>
            {/* Точність фактів */}
            {(result.analysis.analysis?.factual_accuracy || result.analysis.factual_accuracy) && (
              <div className="detail-item">
                <strong>Точність фактів:</strong>
                <p>{result.analysis.analysis?.factual_accuracy || result.analysis.factual_accuracy}</p>
              </div>
            )}

            {/* Достовірність джерела */}
            {(result.analysis.analysis?.source_credibility || result.analysis.source_credibility) && (
              <div className="detail-item">
                <strong>Достовірність джерела:</strong>
                <p>{result.analysis.analysis?.source_credibility || result.analysis.source_credibility}</p>
              </div>
            )}

            {/* Ознаки маніпуляції */}
            {((result.analysis.analysis?.manipulation_signs?.length > 0) || (result.analysis.manipulation_signs?.length > 0)) && (
              <div className="detail-item">
                <strong>Ознаки маніпуляції:</strong>
                <ul>
                  {(result.analysis.analysis?.manipulation_signs || result.analysis.manipulation_signs).map((sign, i) => (
                    <li key={i}>{sign}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Динамічне відображення будь-яких інших полів аналізу */}
            {result.analysis.analysis && Object.entries(result.analysis.analysis).map(([key, value]) => {
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
             </>
            )}
          </div>
        </details>
      )}

      {/* Debug інформація про парсинг */}
      {result.debugEnabled && (
        <DebugInfo debugInfo={result.debug_info} />
      )}

      {/* Кнопка нової перевірки */}
      <button className="reset-button" onClick={onReset}>
        🔄 Перевірити іншу новину
      </button>
    </div>
  );
};

export default ResultCard;
