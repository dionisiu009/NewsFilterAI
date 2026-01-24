// ==============================================================================
// NEWSFILTERAI - DEBUG TOGGLE COMPONENT
// ==============================================================================
// Компонент перемикача Debug режиму

import './DebugToggle.css';

/**
 * Компонент перемикача debug режиму
 * @param {boolean} enabled - Чи увімкнено debug
 * @param {Function} onToggle - Callback при зміні
 */
const DebugToggle = ({ enabled, onToggle }) => {
  return (
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
  );
};

export default DebugToggle;
