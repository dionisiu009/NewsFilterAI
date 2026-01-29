
import React, { useEffect } from 'react';

export function InfoPage({ title, content, onBack, imageIcon }) {
    // Scroll to top when page opens
    useEffect(() => {
        window.scrollTo(0, 0);
    }, []);

    return (
        <div className="info-page fade-in">
            <button onClick={onBack} className="back-button">
                ← Назад на головну
            </button>

            <div className="info-header">
                <div className="info-icon-large">{imageIcon}</div>
                <h1>{title}</h1>
            </div>

            <div className="info-content">
                {content}
            </div>

            <div className="info-footer">
                <button onClick={onBack} className="primary-button">
                    Зрозуміло, дякую!
                </button>
            </div>
        </div>
    );
}
