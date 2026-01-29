// ==============================================================================
// NEWSFILTERAI - MAIN APPLICATION COMPONENT
// ==============================================================================

import { useState } from 'react';
import {
  Header,
  UrlInputForm,
  LoadingIndicator,
  ResultCard,
  ErrorMessage,
  DebugToggle,
  InfoPage,
  DisinfoCards
} from './components';
import { pagesContent } from './data/disinfoContent';
import { useNewsCheck, CheckStatus } from './hooks/useNewsCheck';
import './App.css';

function App() {
  const [debugEnabled, setDebugEnabled] = useState(false);
  const [currentView, setCurrentView] = useState('home');

  const handleCardClick = (id) => {
    setCurrentView(id);
  };


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
                    </div>
                    <div className="verdict-example verdict-example--false">
                      <span>🔴</span> Фейк
                    </div>
                    <div className="verdict-example verdict-example--partial">
                      <span>🟡</span> Частково правда
                    </div>
                    <div className="verdict-example verdict-example--unknown">
                      <span>❓</span> Неможливо перевірити
                    </div>
                  </div>
                </div>
              </div>

              <DisinfoCards onCardClick={handleCardClick} />
            </>
          );
        } else {
          const page = pagesContent[currentView];
          return (
            <InfoPage
              title={page?.title}
              content={page?.content}
              imageIcon={page?.icon}
              onBack={() => setCurrentView('home')}
            />
          );
        }
    }
  };

  return (
    <div className="app">
      <Header />

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
          Powered by Google Gemini AI
        </p>
        <DebugToggle
          enabled={debugEnabled}
          onToggle={setDebugEnabled}
        />
      </footer>
    </div>
  );
}

export default App;

