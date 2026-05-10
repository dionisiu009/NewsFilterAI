// ==============================================================================
// NEWSFILTERAI - MAIN APPLICATION COMPONENT
// ==============================================================================

import { useState, useEffect } from 'react';
import {
  Header,
  UrlInputForm,
  LoadingIndicator,
  ResultCard,
  ErrorMessage,
  DebugToggle,
  InfoPage,
  DisinfoCards,
  HistoryPage,
  CheckedSitesBlock
} from './components';
import { pagesContent } from './data/disinfoContent';
import { useNewsCheck, CheckStatus } from './hooks/useNewsCheck';
import './App.css';

function App() {
  const [debugEnabled, setDebugEnabled] = useState(false);
  const [currentView, setCurrentView] = useState(() => {
    return window.location.pathname === '/history' ? 'history' : 'home';
  });

  const {
    status,
    result,
    error,
    errorDetails,
    progress,
    check,
    reset,
    isLoading,
    isProcessing,
  } = useNewsCheck();

  // --- HISTORY MANAGEMENT ---
  useEffect(() => {
    const handlePopState = (event) => {
      const view = (event.state && event.state.view) || 'home';
      setCurrentView(view);
    };

    window.addEventListener('popstate', handlePopState);

    // Initial state setup to handle "Back" to home correctly
    if (!window.history.state) {
      window.history.replaceState({ view: 'home' }, '', "");
    }

    return () => window.removeEventListener('popstate', handlePopState);
  }, []);
  // --------------------------

  const handleLogoClick = (view = 'home') => {
    reset();
    if (currentView !== view) {
      setCurrentView(view);
      window.history.pushState({ view }, '', view === 'home' ? '/' : `/${view}`);
    }
  };

  const handleCardClick = (id) => {
    setCurrentView(id);
    window.history.pushState({ view: id }, '', "");
  };


  const handleSubmit = (url) => {
    check(url);
  };

  const renderContent = () => {
    switch (status) {
      case CheckStatus.LOADING:
      case CheckStatus.PROCESSING:
        return (
          <LoadingIndicator
            message={progress?.message || 'Обробка...'}
            elapsed={progress?.elapsed}
          />
        );

      case CheckStatus.SUCCESS:
        return (
          <ResultCard
            result={result}
            onReset={reset}
            debugEnabled={debugEnabled}
          />
        );

      case CheckStatus.ERROR:
        return (
          <ErrorMessage
            message={error}
            onRetry={reset}
            errorDetails={errorDetails}
          />
        );

      case CheckStatus.IDLE:
      default:
        if (currentView === 'home') {
          return (
            <>
              <CheckedSitesBlock />

              <div className="features">
                <h2 className="features-title">🚀 Як це працює?</h2>
                <div className="features-grid">
                  <div className="feature-card">
                    <span className="feature-icon">🔗</span>
                    <h3>Вставте посилання</h3>
                    <p>Скопіюйте URL новини, яку хочете перевірити</p>
                  </div>
                  <div className="feature-card">
                    <span className="feature-icon">🤖</span>
                    <h3>AI аналізує</h3>
                    <p>Штучний інтелект перевіряє факти та джерело</p>
                  </div>
                  <div className="feature-card">
                    <span className="feature-icon">✅</span>
                    <h3>Отримайте результат</h3>
                    <p>Дізнайтеся чи можна довіряти цій новині</p>
                  </div>
                </div>

                <div className="stats-section">
                  <h3 className="stats-title">📊 Вердикти</h3>
                  <div className="verdict-examples">
                    <div className="verdict-example verdict-example--true">
                      <span>✅</span> Достовірна
                      <span className="verdict-tooltip">Всі ключові твердження підтверджені надійними джерелами</span>
                    </div>
                    <div className="verdict-example verdict-example--false">
                      <span>🔴</span> Фейк
                      <span className="verdict-tooltip">Більшість ключових тверджень або основна суть новини є неправдивими</span>
                    </div>
                    <div className="verdict-example verdict-example--partial">
                      <span>🟡</span> Частково правда
                      <span className="verdict-tooltip">Мікс фактів: частина правдива, але є і явна брехня чи маніпуляції</span>
                    </div>
                    <div className="verdict-example verdict-example--clickbait">
                      <span>🟠</span> Клікбейт
                      <span className="verdict-tooltip">Заголовок перебільшений або вводить в оману для кліків</span>
                    </div>
                    <div className="verdict-example verdict-example--opinion">
                      <span>🗣️</span> Думка
                      <span className="verdict-tooltip">Суб'єктивна точка зору автора, а не об'єктивна новина</span>
                    </div>
                    <div className="verdict-example verdict-example--satire">
                      <span>🎭</span> Сатира
                      <span className="verdict-tooltip">Гумористичний контент, який не претендує на достовірність</span>
                    </div>
                    <div className="verdict-example verdict-example--unknown">
                      <span>❓</span> Неможливо перевірити
                      <span className="verdict-tooltip">Недостатньо інформації в мережі для підтвердження або спростування</span>
                    </div>
                  </div>
                </div>
              </div>

              <DisinfoCards onCardClick={handleCardClick} />
            </>
          );
        } else if (currentView === 'history') {
          return (
            <HistoryPage
              debugEnabled={debugEnabled}
              onBack={() => {
                setCurrentView('home');
                window.history.pushState({ view: 'home' }, '', "/");
              }}
            />
          );
        } else {
          const page = pagesContent[currentView];
          return (
            <InfoPage
              title={page?.title}
              content={page?.content}
              imageIcon={page?.icon}
              heroImage={page?.heroImage}
              onBack={() => {
                setCurrentView('home');
                window.history.pushState({ view: 'home' }, '', "/");
              }}
            />
          );
        }
    }
  };

  return (
    <div className={`app ${currentView === 'history' ? 'app--full-width' : ''}`}>
      <Header onLogoClick={handleLogoClick} />

      <main className="app-main">
        {/* Форма завжди видима, крім моменту коли є результат АБО ми на сторінці інфо */}
        {status !== CheckStatus.SUCCESS && status !== CheckStatus.ERROR && currentView === 'home' && (

          <UrlInputForm
            onSubmit={handleSubmit}
            isLoading={isLoading}
            isProcessing={isProcessing}
          />
        )}

        {/* Динамічний контент */}
        {renderContent()}
      </main>

      <footer className="app-footer">
        <p>
          🔍 NewsFilter AI — Інтелектуальна система перевірки новин
        </p>
        <p>
          Відповіді сгенеровані AI та можуть бути хибними.
        </p>
        <p className="footer-note">
          Powered by Google, Groq, Cohere, Tavily
        </p>
        <DebugToggle
          enabled={debugEnabled}
          onToggle={setDebugEnabled}
          onHistoryClick={() => handleLogoClick('history')}
        />
      </footer>
    </div>
  );
}

export default App;

