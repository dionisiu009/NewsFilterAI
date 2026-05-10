// ==============================================================================
// NEWSFILTERAI - CHECKED SITES BLOCK
// ==============================================================================
// Блок перевірених сайтів з розумним пошуком та фільтрами

import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import Fuse from 'fuse.js';
import axios from 'axios';
import './CheckedSitesBlock.css';

// --- Константи ---
const VERDICT_CONFIG = {
  fact: { label: 'Достовірна', icon: '✅', color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  true: { label: 'Достовірна', icon: '✅', color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  'false-fake': { label: 'Фейк', icon: '🔴', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  false: { label: 'Фейк', icon: '🔴', color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  partial: { label: 'Частково правда', icon: '🟡', color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  clickbait: { label: 'Клікбейт', icon: '🟠', color: '#f97316', bg: 'rgba(249,115,22,0.15)' },
  opinion: { label: 'Думка', icon: '🗣️', color: '#a78bfa', bg: 'rgba(167,139,250,0.15)' },
  satire: { label: 'Сатира', icon: '🎭', color: '#38bdf8', bg: 'rgba(56,189,248,0.15)' },
  unverifiable: { label: 'Неможливо перевірити', icon: '⚪', color: '#9ca3af', bg: 'rgba(107,114,128,0.15)' },
  error: { label: 'Помилка', icon: '⚫', color: '#6b7280', bg: 'rgba(107,114,128,0.1)' },
};

const getVerdict = (key) =>
  VERDICT_CONFIG[key] || { label: key || 'Невідомо', icon: '❓', color: '#9ca3af', bg: 'rgba(107,114,128,0.1)' };

const TIME_FILTERS = [
  { value: 'all', label: 'Весь час' },
  { value: 'today', label: 'Сьогодні' },
  { value: 'week', label: 'Цей тиждень' },
  { value: 'month', label: 'Цей місяць' },
];

const FUSE_OPTIONS = {
  keys: [
    { name: 'title', weight: 0.5 },
    { name: 'url', weight: 0.3 },
    { name: 'source_domain', weight: 0.2 },
    { name: 'summary', weight: 0.1 },
  ],
  threshold: 0.4,       // tolerates typos
  distance: 200,
  includeScore: true,
  minMatchCharLength: 2,
  ignoreLocation: true,
};

// --- Утиліти ---
function formatDate(iso) {
  return new Date(iso).toLocaleString('uk-UA', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function isWithinTimeFilter(isoDate, filter) {
  if (filter === 'all') return true;
  const d = new Date(isoDate);
  const now = new Date();
  if (filter === 'today') {
    return d.toDateString() === now.toDateString();
  }
  const diffMs = now - d;
  if (filter === 'week') return diffMs < 7 * 24 * 3600 * 1000;
  if (filter === 'month') return diffMs < 30 * 24 * 3600 * 1000;
  return true;
}

// =====================================================================
// Main Component
// =====================================================================
const CheckedSitesBlock = ({ onCardClick }) => {
  const [allItems, setAllItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [domainFilter, setDomainFilter] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('');
  const [timeFilter, setTimeFilter] = useState('all');

  // UI state
  const [domainSuggestions, setDomainSuggestions] = useState([]);
  const [showDomainDropdown, setShowDomainDropdown] = useState(false);
  const gridRef = useRef(null);
  const domainRef = useRef(null);

  // ---- Fetch ----
  useEffect(() => {
    const fetchAll = async () => {
      try {
        setLoading(true);
        const resp = await axios.get('/api/history/?limit=500&offset=0');
        setAllItems(resp.data.results || []);
      } catch (e) {
        setError('Не вдалося завантажити дані');
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  // ---- Unique domains for autocomplete ----
  const uniqueDomains = useMemo(() => {
    const set = new Set(allItems.map(i => i.source_domain).filter(Boolean));
    return Array.from(set).sort();
  }, [allItems]);

  // ---- Fuse instance ----
  const fuse = useMemo(() => new Fuse(allItems, FUSE_OPTIONS), [allItems]);

  // ---- Filtered & searched results ----
  const filteredItems = useMemo(() => {
    let items = allItems;

    // Time filter
    if (timeFilter !== 'all') {
      items = items.filter(i => isWithinTimeFilter(i.created_at, timeFilter));
    }

    // Verdict filter
    if (verdictFilter) {
      items = items.filter(i => i.verdict === verdictFilter);
    }

    // Domain filter
    if (domainFilter.trim()) {
      const q = domainFilter.trim().toLowerCase();
      items = items.filter(i => i.source_domain?.toLowerCase().includes(q));
    }

    // Fuzzy search
    if (searchQuery.trim().length >= 2) {
      const fuseOnSubset = new Fuse(items, FUSE_OPTIONS);
      const results = fuseOnSubset.search(searchQuery.trim());
      items = results.map(r => r.item);
    }

    return items;
  }, [allItems, searchQuery, domainFilter, verdictFilter, timeFilter, fuse]);

  // ---- Stats ----
  const stats = useMemo(() => {
    const counts = {};
    allItems.forEach(i => {
      const v = i.verdict || 'unknown';
      counts[v] = (counts[v] || 0) + 1;
    });
    return counts;
  }, [allItems]);

  // ---- Domain autocomplete ----
  const handleDomainInput = useCallback((val) => {
    setDomainFilter(val);
    if (val.trim().length > 0) {
      const filtered = uniqueDomains.filter(d => d.toLowerCase().includes(val.toLowerCase()));
      setDomainSuggestions(filtered.slice(0, 6));
      setShowDomainDropdown(filtered.length > 0);
    } else {
      setShowDomainDropdown(false);
    }
  }, [uniqueDomains]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (domainRef.current && !domainRef.current.contains(e.target)) {
        setShowDomainDropdown(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // ---- Scroll helpers ----
  const scrollGrid = (dir) => {
    if (gridRef.current) {
      gridRef.current.scrollBy({ left: dir * 320, behavior: 'smooth' });
    }
  };

  const resetFilters = () => {
    setSearchQuery('');
    setDomainFilter('');
    setVerdictFilter('');
    setTimeFilter('all');
  };

  const hasActiveFilters = searchQuery || domainFilter || verdictFilter || timeFilter !== 'all';

  // ---- Unique verdicts present in data ----
  const presentVerdicts = useMemo(() => {
    const set = new Set(allItems.map(i => i.verdict).filter(Boolean));
    return Array.from(set);
  }, [allItems]);

  // =====================================================================
  return (
    <section className="csb-wrapper" id="checked-sites-block">
      {/* Header */}
      <div className="csb-header">
        <div className="csb-title-row">
          <div className="csb-title-left">
            <span className="csb-icon">🗂️</span>
            <div>
              <h2 className="csb-title">Вже перевірені сайти</h2>
              <p className="csb-subtitle">
                {loading
                  ? 'Завантаження...'
                  : `${allItems.length} перевірок у базі`}
              </p>
            </div>
          </div>

          {/* Stat pills */}
          {!loading && allItems.length > 0 && (
            <div className="csb-stat-pills">
              {Object.entries(stats).slice(0, 4).map(([v, cnt]) => {
                const cfg = getVerdict(v);
                return (
                  <button
                    key={v}
                    className={`csb-stat-pill ${verdictFilter === v ? 'active' : ''}`}
                    style={{ '--pill-color': cfg.color, '--pill-bg': cfg.bg }}
                    onClick={() => setVerdictFilter(prev => prev === v ? '' : v)}
                    title={`Фільтрувати: ${cfg.label}`}
                  >
                    <span>{cfg.icon}</span>
                    <span className="pill-count">{cnt}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Search & Filters */}
        <div className="csb-controls">
          {/* Smart search */}
          <div className="csb-search-wrap">
            <span className="csb-search-icon">🔍</span>
            <input
              id="csb-search"
              type="text"
              className="csb-search"
              placeholder="Назва, URL або частина тексту новини..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              autoComplete="off"
            />
            {searchQuery && (
              <button className="csb-clear-btn" onClick={() => setSearchQuery('')} title="Очистити">✕</button>
            )}
          </div>

          <div className="csb-filters-row">
            {/* Domain autocomplete */}
            <div className="csb-domain-wrap" ref={domainRef}>
              <input
                id="csb-domain-filter"
                type="text"
                className="csb-filter-input"
                placeholder="🌐 Домен"
                value={domainFilter}
                onChange={e => handleDomainInput(e.target.value)}
                onFocus={() => domainFilter && setShowDomainDropdown(domainSuggestions.length > 0)}
                autoComplete="off"
              />
              {showDomainDropdown && (
                <ul className="csb-domain-dropdown">
                  {domainSuggestions.map(d => (
                    <li
                      key={d}
                      className="csb-domain-option"
                      onClick={() => { setDomainFilter(d); setShowDomainDropdown(false); }}
                    >
                      {d}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Verdict select */}
            <select
              id="csb-verdict-filter"
              className="csb-filter-select"
              value={verdictFilter}
              onChange={e => setVerdictFilter(e.target.value)}
            >
              <option value="">⚖️ Всі вердикти</option>
              {presentVerdicts.map(v => {
                const cfg = getVerdict(v);
                return <option key={v} value={v}>{cfg.icon} {cfg.label}</option>;
              })}
            </select>

            {/* Time filter */}
            <select
              id="csb-time-filter"
              className="csb-filter-select"
              value={timeFilter}
              onChange={e => setTimeFilter(e.target.value)}
            >
              {TIME_FILTERS.map(t => (
                <option key={t.value} value={t.value}>📅 {t.label}</option>
              ))}
            </select>

            {/* Reset */}
            {hasActiveFilters && (
              <button className="csb-reset-btn" onClick={resetFilters} title="Скинути фільтри">
                Скинути
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Results count */}
      {!loading && hasActiveFilters && (
        <div className="csb-results-count">
          {filteredItems.length > 0
            ? `Знайдено: ${filteredItems.length} ${filteredItems.length === 1 ? 'результат' : filteredItems.length < 5 ? 'результати' : 'результатів'}`
            : 'Нічого не знайдено за заданими фільтрами'}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="csb-loading">
          <div className="csb-spinner" />
          <span>Завантаження перевірок...</span>
        </div>
      ) : error ? (
        <div className="csb-error">⚠️ {error}</div>
      ) : allItems.length === 0 ? (
        <div className="csb-empty">
          <span className="csb-empty-icon">🔍</span>
          <p>Ще немає перевірених новин</p>
          <p className="csb-empty-hint">Вставте URL вище щоб перевірити першу новину</p>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="csb-empty">
          <span className="csb-empty-icon">🤷</span>
          <p>Нічого не знайдено</p>
          <button className="csb-reset-btn csb-reset-btn--center" onClick={resetFilters}>
            Скинути фільтри
          </button>
        </div>
      ) : (
        <div className="csb-carousel-wrap">
          {/* Scroll left button */}
          {filteredItems.length > 4 && (
            <button className="csb-scroll-btn csb-scroll-btn--left" onClick={() => scrollGrid(-1)} aria-label="Прокрутити ліворуч">
              ‹
            </button>
          )}

          {/* 2-row horizontal grid */}
          <div className="csb-grid" ref={gridRef}>
            {filteredItems.map(item => (
              <SiteCard key={item.id} item={item} onCardClick={onCardClick} />
            ))}
          </div>

          {/* Scroll right button */}
          {filteredItems.length > 4 && (
            <button className="csb-scroll-btn csb-scroll-btn--right" onClick={() => scrollGrid(1)} aria-label="Прокрутити праворуч">
              ›
            </button>
          )}
        </div>
      )}
    </section>
  );
};

const SiteCard = ({ item, onCardClick }) => {
  const verdict = getVerdict(item.verdict);
  const domain = item.source_domain || '';
  const title = item.title || 'Без заголовка';
  const date = formatDate(item.created_at);

  // Клік на картку → показати сторінку результату
  const handleCardClick = () => {
    if (onCardClick && item.url) onCardClick(item.url);
  };

  // Клік на домен → відкрити оригінальну статтю в новій вкладці
  const handleDomainClick = (e) => {
    e.stopPropagation();
    if (item.url) window.open(item.url, '_blank', 'noopener,noreferrer');
  };

  return (
    <article
      className="csb-card"
      style={{ '--card-accent': verdict.color, '--card-bg': verdict.bg }}
      onClick={handleCardClick}
      title="Переглянути результат аналізу"
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && handleCardClick()}
    >
      {/* Accent line */}
      <div className="csb-card-accent" />

      {/* Verdict badge */}
      <div className="csb-card-verdict">
        <span className="csb-verdict-icon">{verdict.icon}</span>
        <span className="csb-verdict-label">{verdict.label}</span>
      </div>

      {/* Title */}
      <h3 className="csb-card-title">{title}</h3>

      {/* Domain + date */}
      <div className="csb-card-meta">
        <span
          className="csb-card-domain csb-card-domain--link"
          onClick={handleDomainClick}
          title={`Відкрити статтю: ${item.url}`}
        >
          🌐 {domain || '—'}
        </span>
        <span className="csb-card-date">{date}</span>
      </div>

      {/* URL */}
      <div className="csb-card-url" title={item.url}>
        {item.url}
      </div>

      {/* Hover indicator */}
      <div className="csb-card-arrow">↗</div>
    </article>
  );
};

export default CheckedSitesBlock;
