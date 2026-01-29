
import React from 'react';

export function DisinfoCards({ onCardClick }) {
    const cards = [
        {
            id: 'text',
            icon: '📝',
            title: 'Як протидіяти текстовій дезінформації',
            desc: 'Навчіться розпізнавати маніпуляції текстом, клікбейт та емоційний тиск.'
        },
        {
            id: 'deepfake',
            icon: '🎭',
            title: 'Як виявити діпфейки (зображення)',
            desc: 'Станьте цифровим детективом: руки, очі, тіні та інші ознаки ШІ-генерації.'
        },
        {
            id: 'family',
            icon: '👨‍👩‍👧‍👦',
            title: 'Як говорити про фейки з близькими',
            desc: 'Екологічна комунікація в родині: як попередити поширення фейків без сварок.'
        }
    ];

    return (
        <div className="disinfo-section">
            <h2 className="section-title">🛡️ Медіаграмотність</h2>
            <div className="disinfo-grid">
                {cards.map((card) => (
                    <div
                        key={card.id}
                        className="disinfo-card"
                        onClick={() => onCardClick(card.id)}
                    >
                        <div className="disinfo-icon">{card.icon}</div>
                        <h3>{card.title}</h3>
                        <p>{card.desc}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}
