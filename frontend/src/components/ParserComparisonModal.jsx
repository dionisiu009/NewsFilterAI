// ==============================================================================
// NEWSFILTERAI - PARSER COMPARISON MODAL
// ==============================================================================

import React, { useEffect } from 'react';
import './ParserComparisonModal.css';

/**
 * Helper to check if two strings are roughly similar (for highlighting)
 * Since backend cleans the winner text, we need loose comparison.
 */
const isMatch = (val1, val2) => {
    if (!val1 || !val2) return false;

    // Normalize: remove whitespace, lowercase
    const n1 = String(val1).replace(/\s+/g, '').toLowerCase();
    const n2 = String(val2).replace(/\s+/g, '').toLowerCase();

    if (n1 === n2) return true;
    if (n1.includes(n2) || n2.includes(n1)) {
        // Check if length difference is small ( < 5%)
        const lenDiff = Math.abs(n1.length - n2.length);
        const maxLen = Math.max(n1.length, n2.length);
        if (lenDiff / maxLen < 0.05) return true;
    }
    return false;
};

const ParserCard = ({ data, winnerData }) => {
    const { source, title, text, date, authors, error } = data;
    const [isExpanded, setIsExpanded] = React.useState(false);

    // Prefer explicit winner flags from backend if present
    const isTitleMatch = data.is_winner_title || isMatch(title, winnerData.parsed_title);

    // For text, prefer backend flag, else fuzzy compare / word count
    const isTextMatch = data.is_winner_text || isMatch(text?.substring(0, 1000), winnerData.parsed_text?.substring(0, 1000));

    // Date: try normalized compare - if backend marked is_winner_date use it
    const normalizeDateOnly = (d) => {
        if (!d) return null;
        try {
            const dateObj = new Date(d);
            if (isNaN(dateObj.getTime())) return d;
            return dateObj.toISOString().slice(0, 10);
        } catch {
            return d;
        }
    };

    const isDateMatch = data.is_winner_date || (normalizeDateOnly(date) === normalizeDateOnly(winnerData.parsed_publish_date));

    // Authors: flexible comparison (handles both arrays and strings)
    const normalizeAuthors = (a) => {
        if (!a) return [];
        if (Array.isArray(a)) return a.map(x => String(x).trim().toLowerCase());
        return [String(a).trim().toLowerCase()];
    };

    const currentAuthors = normalizeAuthors(authors);
    const winnerAuthors = normalizeAuthors(winnerData.parsed_authors);

    const isAuthorsMatch = data.is_winner_authors || (
        currentAuthors.length > 0 &&
        winnerAuthors.length > 0 &&
        currentAuthors.some(a => winnerAuthors.includes(a))
    );

    const parserName = source ? source.charAt(0).toUpperCase() + source.slice(1) : 'Unknown';
    const hasData = text && text.length > 0;

    const textPreviewLimit = 200;
    const shouldTruncate = text && text.length > textPreviewLimit;

    return (
        <div className={`parser-card ${!hasData ? 'is-empty' : ''}`}>
            <div className="parser-header">
                <span className="parser-name">{parserName}</span>
                <span className={`parser-status ${hasData ? 'success' : 'empty'}`}>
                    {hasData ? 'Success' : 'Empty/Error'}
                </span>
            </div>

            <div className="parser-content">
                {/* Title */}
                <div className="field-group">
                    <span className="field-label">Title</span>
                    <div className={`field-value ${isTitleMatch ? 'match-title' : ''}`}>
                        {title || 'No Title'}
                    </div>
                </div>

                {/* Date */}
                <div className="field-group">
                    <span className="field-label">Date</span>
                    <div className={`field-value ${isDateMatch ? 'match-date' : ''}`}>
                        {date || 'None'}
                    </div>
                </div>

                {/* Authors */}
                <div className="field-group">
                    <span className="field-label">Authors</span>
                    <div className={`field-value ${isAuthorsMatch ? 'match-authors' : ''}`}>
                        {authors && authors.length > 0 ? authors.join(', ') : 'None'}
                    </div>
                </div>

                {/* Text Preview */}
                <div className="field-group" style={{ flex: 1 }}>
                    <span className="field-label">Text Content</span>
                    <div className={`field-value text-preview ${isTextMatch ? 'match-text' : ''} ${isExpanded ? 'expanded' : ''}`}>
                        {shouldTruncate && !isExpanded
                            ? (text || '').substring(0, textPreviewLimit) + '...'
                            : (text || 'No Content')}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '5px' }}>
                        <span className="text-length-badge">
                            {text ? text.length : 0} chars
                        </span>

                        {shouldTruncate && (
                            <button
                                onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    color: '#3498db',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    textDecoration: 'underline',
                                    padding: '0'
                                }}
                            >
                                {isExpanded ? 'Show Less' : 'Show More'}
                            </button>
                        )}
                    </div>
                </div>

                {/* Image - removed per request */}
                {/* previously displayed image url here */}
            </div>
        </div>
    );
};

const ParserComparisonModal = ({ isOpen, onClose, parsersDebug, winnerData }) => {
    // Prevent background scrolling when modal is open
    // moved hook to top to follow React rules (hooks must run before conditional returns)
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
        }
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, [isOpen]);

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">
                        🔍 Parser Comparison
                        <span className="modal-subtitle">
                            Compare results from {parsersDebug ? parsersDebug.length : 0} parallel parsers
                        </span>
                    </h2>
                    <button className="close-button" onClick={onClose}>&times;</button>
                </div>

                <div className="modal-body">
                    <div className="parsers-container">
                        {parsersDebug && parsersDebug.map((parserData, idx) => (
                            <ParserCard
                                key={idx}
                                data={parserData}
                                winnerData={winnerData}
                            />
                        ))}

                        {!parsersDebug || parsersDebug.length === 0 && (
                            <div style={{ color: '#fff', padding: 20 }}>
                                No detailed parser data available for this result.
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ParserComparisonModal;
