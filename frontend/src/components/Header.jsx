// ==============================================================================
// NEWSFILTERAI - HEADER COMPONENT
// ==============================================================================

import './Header.css';

const Header = () => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-logo">
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

