import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './HistoryPage.css';

const HistoryPage = ({ onBack }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [selectedCheckId, setSelectedCheckId] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [details, setDetails] = useState(null);
  
  const LIMIT = 100;

  const fetchHistory = async (currentOffset) => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/history/?limit=${LIMIT}&offset=${currentOffset}`);
      const data = response.data;
      
      if (currentOffset === 0) {
        setHistory(data.results);
      } else {
        setHistory(prev => [...prev, ...data.results]);
      }
      
      setHasMore(data.results.length === LIMIT && (currentOffset + LIMIT) < data.total);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(0);
  }, []);

  const handleLoadMore = () => {
    const newOffset = offset + LIMIT;
    setOffset(newOffset);
    fetchHistory(newOffset);
  };

  const handleRowClick = async (id) => {
    if (selectedCheckId === id) {
      setSelectedCheckId(null);
      setDetails(null);
      return;
    }
    
    setSelectedCheckId(id);
    setDetailsLoading(true);
    setDetails(null);
    try {
      const response = await axios.get(`/api/check/${id}/`);
      setDetails(response.data);
    } catch (error) {
      console.error('Failed to fetch details:', error);
    } finally {
      setDetailsLoading(false);
    }
  };

  const getVerdictIcon = (verdict) => {
    switch (verdict) {
      case 'fact':
      case 'true':
        return '✅';
      case 'false-fake':
      case 'false':
        return '🔴';
      case 'partial':
      case 'clickbait':
        return '🟡';
      default:
        return '❓';
    }
  };

  return (
    <div className="history-page">
      <button className="back-btn" onClick={onBack}>← На головну</button>
      <h2 className="history-title">Історія перевірок</h2>
      
      <div className="history-table-container">
        <table className="history-table">
          <thead>
            <tr>
              <th>Статус</th>
              <th>Заголовок / URL</th>
              <th>Домен</th>
              <th>Дата</th>
            </tr>
          </thead>
          <tbody>
            {history.map((item) => (
              <React.Fragment key={item.id}>
                <tr 
                  className={`history-row ${selectedCheckId === item.id ? 'active' : ''}`}
                  onClick={() => handleRowClick(item.id)}
                >
                  <td className="status-cell">
                    <span className="verdict-icon">{getVerdictIcon(item.verdict)}</span>
                    <span className="verdict-text">{item.verdict_display}</span>
                  </td>
                  <td className="title-cell">
                    <div className="item-title">{item.title || 'Без заголовка'}</div>
                    <div className="item-url">{item.url}</div>
                  </td>
                  <td>{item.source_domain}</td>
                  <td className="date-cell">
                    {new Date(item.created_at).toLocaleString('uk-UA', {
                      day: '2-digit', month: '2-digit', year: 'numeric',
                      hour: '2-digit', minute: '2-digit'
                    })}
                  </td>
                </tr>
                {selectedCheckId === item.id && (
                  <tr className="details-row">
                    <td colSpan="4">
                      {detailsLoading ? (
                        <div className="details-loading">Завантаження деталей...</div>
                      ) : details ? (
                        <ArtifactsViewer artifacts={details.pipeline_artifacts} />
                      ) : (
                        <div className="details-error">Не вдалося завантажити деталі</div>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        
        {loading && <div className="loading-indicator">Завантаження...</div>}
        
        {!loading && hasMore && (
          <button className="load-more-btn" onClick={handleLoadMore}>
            Завантажити ще
          </button>
        )}
        
        {!loading && history.length === 0 && (
          <div className="empty-state">Історія перевірок порожня</div>
        )}
      </div>
    </div>
  );
};

// Component for rendering artifacts like folder structure
const ArtifactsViewer = ({ artifacts }) => {
  const [selectedFile, setSelectedFile] = useState(null);

  if (!artifacts || Object.keys(artifacts).length === 0) {
    return <div className="no-artifacts">Немає збережених проміжних результатів (artifacts)</div>;
  }

  const files = Object.keys(artifacts).sort();

  return (
    <div className="artifacts-viewer">
      <div className="artifacts-sidebar">
        <h4 className="sidebar-title">📁 Pipeline Artifacts</h4>
        <ul className="file-list">
          {files.map(file => (
            <li 
              key={file} 
              className={`file-item ${selectedFile === file ? 'selected' : ''}`}
              onClick={() => setSelectedFile(file)}
            >
              📄 {file}
            </li>
          ))}
        </ul>
      </div>
      <div className="artifacts-content">
        {selectedFile ? (
          <div className="file-content">
            <h4 className="file-title">{selectedFile}</h4>
            <pre className="markdown-content">
              <SyntaxHighlight content={artifacts[selectedFile]} />
            </pre>
          </div>
        ) : (
          <div className="empty-content">Виберіть файл зліва для перегляду</div>
        )}
      </div>
    </div>
  );
};

// Extremely simple JSON syntax highlighter
const SyntaxHighlight = ({ content }) => {
  if (!content) return null;
  
  // Basic heuristic: if it looks like JSON markdown block, we color it
  if (content.includes('```json')) {
    const parts = content.split(/(```json\n[\s\S]*?\n```)/);
    
    return (
      <>
        {parts.map((part, i) => {
          if (part.startsWith('```json')) {
            const jsonText = part.replace(/```json\n|\n```/g, '');
            return (
              <div key={i} className="json-block">
                {highlightJson(jsonText)}
              </div>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </>
    );
  }
  
  return content;
};

const highlightJson = (jsonStr) => {
  try {
    // try formatting it first if it's not well-formatted
    const obj = JSON.parse(jsonStr);
    const formatted = JSON.stringify(obj, null, 2);
    
    // regex for basic json syntax highlighting
    const html = formatted.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
      (match) => {
        let cls = 'json-number';
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            cls = 'json-key';
          } else {
            cls = 'json-string';
          }
        } else if (/true|false/.test(match)) {
          cls = 'json-boolean';
        } else if (/null/.test(match)) {
          cls = 'json-null';
        }
        return `<span class="${cls}">${match}</span>`;
      }
    );
    
    return <code dangerouslySetInnerHTML={{ __html: html }} />;
  } catch (e) {
    return <code>{jsonStr}</code>;
  }
};

export default HistoryPage;
