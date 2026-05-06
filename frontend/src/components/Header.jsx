// ==============================================================================
// NEWSFILTERAI - HEADER COMPONENT
// ==============================================================================

import './Header.css';

const Header = ({ onLogoClick }) => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-logo" onClick={() => onLogoClick('home')} style={{ cursor: 'pointer' }}>
          <span className="logo-icon">🔍</span>
          <h1 className="logo-text">NewsFilter AI</h1>
        </div>
        <p className="header-subtitle">
          Інтелектуальна система перевірки новин на достовірність
        </p>
      </div>
    </header>
  );
};

export default Header;
