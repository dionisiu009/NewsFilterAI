// ==============================================================================
// NEWSFILTERAI - DEBUG TOGGLE COMPONENT
// ==============================================================================
// Компонент перемикача Debug режиму

import './DebugToggle.css';

/**
 * Компонент перемикача debug режиму
 * @param {boolean} enabled - Чи увімкнено debug
 * @param {Function} onToggle - Callback при зміні
 * @param {Function} onHistoryClick - Callback для переходу до історії
 */
const DebugToggle = ({ enabled, onToggle, onHistoryClick }) => {
  return (
    <div className="debug-toggle-container">
      <button className="history-link-btn" onClick={() => onHistoryClick()}>
        📊 Історія (debug)
      </button>
      <div className="debug-toggle">
        <label className="debug-toggle__label">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onToggle(e.target.checked)}
            className="debug-toggle__input"
          />
          <span className="debug-toggle__slider"></span>
          <span className="debug-toggle__text">
            Debug {enabled ? 'ON' : 'OFF'}
          </span>
        </label>
      </div>
    </div>
  );
};

export default DebugToggle;
