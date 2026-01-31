
import React, { useEffect } from 'react';
import './InfoPage.css';

export function InfoPage({ title, content, onBack, imageIcon, heroImage }) {
    // Scroll to top when page opens
    useEffect(() => {
        window.scrollTo(0, 0);
    }, []);

    return (
        <div className="info-page fade-in">
            <div className="back-button-wrapper">
                <button onClick={onBack} className="back-button">
                    ← Назад на головну
                </button>
            </div>

            <div className="info-hero">
                <div className="info-icon-large">{imageIcon}</div>
                <h1>{title}</h1>
                {heroImage && (
                    <div className="hero-image-container">
                        <img src={heroImage} alt={title} className="hero-image" />
                    </div>
                )}
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
