
import React from 'react';
import textHeroImage from '../assets/text_disinfo_hero.png';

export const pagesContent = {
    text: {
        title: 'Як протидіяти текстовій дезінформації',
        icon: '📝',
        heroImage: textHeroImage,
        content: (
            <>
                <section className="info-section">
                    <h2>🧠 Чому наш мозок так легко обманути?</h2>
                    <p>
                        Психологи називають це <strong>«ефектом ілюзії правди»</strong>: чим частіше ми бачимо інформацію, навіть неправдиву, тим більше вона здається нам істинною.
                        Наша схильність довіряти знайомому — це когнітивна вразливість, яку активно використовують творці фейків.
                    </p>
                    <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '1.5rem', borderRadius: '12px', borderLeft: '4px solid var(--color-primary)', fontStyle: 'italic' }}>
                        "Якщо новина викликає у вас миттєве бажання поширити її або сильне обурення — зупиніться. Вас, ймовірно, намагаються використати."
                    </div>
                </section>

                <section className="info-section">
                    <h2>🚩 Розвиваємо «цифрову інтуїцію»</h2>
                    <ul className="info-list">
                        <li>
                            <strong>Вмикайте здоровий скептицизм.</strong> Не довіряйте сліпо текстам, які викликають сильні емоції (гнів, страх, захоплення). Це перша ознака маніпуляції.
                        </li>
                        <li>
                            <strong>Клікбейтні заголовки.</strong> "ШОК!", "ТЕРМІНОВО!", "Цього вам не розкажуть!". Надмірне використання великих літер та знаків оклику — ознака сміття.
                        </li>
                        <li>
                            <strong>Думайте перед репостом.</strong> Поширення неперевіреної інформації підживлює дезінформацію. Зупиніться на хвилину перед тим, як натиснути «Поділитися».
                        </li>
                        <li>
                            <strong>Задавайте правильні питання.</strong> «Хто автор?», «Яка мета цього повідомлення?», «Де докази?».
                        </li>
                    </ul>
                </section>

                <section className="info-section">
                    <h2>🛠 Інструменти перевірки</h2>
                    <p>
                        Завжди перевіряйте першоджерело. Якщо новина посилається на "анонімні джерела" або "вчених без імен", це привід засумніватися.
                        Шукайте підтвердження в авторитетних медіа.
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1.5rem' }}>
                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                            <h3 style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.5rem' }}>🔍 Google Search</h3>
                            <p style={{ fontSize: '0.9rem', margin: 0 }}>Гугліть заголовок. Якщо про це пише лише один "сміттєвий" сайт — це фейк.</p>
                        </div>
                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                            <h3 style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.5rem' }}>🏛 Офіційні джерела</h3>
                            <p style={{ fontSize: '0.9rem', margin: 0 }}>Шукайте заяви на сайтах держустанов, а не в Viber-чатах.</p>
                        </div>
                    </div>
                </section>

                <section className="info-section">
                    <h2>🔗 Корисні ресурси</h2>
                    <p>Додайте ці сайти в закладки, щоб швидко перевіряти сумнівні новини:</p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', marginTop: '1rem' }}>
                        <a href="https://www.stopfake.org/uk/golovna/" target="_blank" rel="noopener noreferrer" className="source-link">🛑 StopFake</a>
                        <a href="https://voxukraine.org/voxcheck" target="_blank" rel="noopener noreferrer" className="source-link">✅ VoxCheck</a>
                        <a href="https://filter.mg.gov.ua/" target="_blank" rel="noopener noreferrer" className="source-link">🇺🇦 Фільтр</a>
                    </div>
                </section>
            </>
        )
    },
    deepfake: {
        title: 'Як виявити діпфейки (зображення)',
        icon: '🎭',
        content: (
            <>
                <section className="info-section">
                    <h2>Шерлок Холмс у світі пікселів</h2>
                    <p>
                        Навіть найсучасніші нейромережі (Midjourney, DALL-E) залишають «цифрові відбитки». Ось 5 головних доказів підробки:
                    </p>
                </section>

                <section className="info-section">
                    <h2>1. Руки та Обличчя — Ахіллесова п'ята ШІ</h2>
                    <ul className="info-list">
                        <li><strong>Руки:</strong> Порахуйте пальці. ШІ часто малює 6 пальців, або неприродно вигнуті суглоби.</li>
                        <li><strong>Очі:</strong> Подивіться на відблиски в зіницях. У реальної людини вони однакові. У ШІ — часто різні.</li>
                        <li><strong>Вуха та зуби:</strong> Вуха можуть бути асиметричними, а зуби — надто ідеальними або "злитими" в один ряд.</li>
                    </ul>
                </section>

                <section className="info-section">
                    <h2>2. Гра світла і тіні</h2>
                    <p>
                        ШІ часто плутає фізику. Тіні можуть падати в різні боки, або об'єкт може бути освітлений інакше, ніж фон.
                    </p>
                </section>

                <section className="info-section">
                    <h2>3. Деталі фону</h2>
                    <p>
                        Придивіться до фону: візерунки на шпалерах, цегла, написи. ШІ часто робить їх розмитими або викривленими (наприклад, "пливучий" текст).
                    </p>
                </section>
            </>
        )
    },
    family: {
        title: 'Як говорити про фейки з близькими',
        icon: '👨‍👩‍👧‍👦',
        content: (
            <>
                <section className="info-section">
                    <h2>Розмова без конфліктів</h2>
                    <p>
                        Найважливіше — зберегти довіру. Не звинувачуйте і не висміюйте.
                    </p>
                </section>

                <section className="info-section">
                    <h2>Метод «Сендвіча істини»</h2>
                    <ol className="info-list" style={{ listStyle: 'decimal', paddingLeft: '1.5rem' }}>
                        <li>
                            <strong>Факт:</strong> Почніть з незаперечної правди.
                        </li>
                        <li>
                            <strong>Попередження про міф:</strong> Коротко згадайте фейк і поясніть, чому він маніпулятивний (без детального повторення брехні).
                        </li>
                        <li>
                            <strong>Факт:</strong> Закінчіть повторенням правди, щоб саме вона запам'яталася.
                        </li>
                    </ol>
                </section>

                <section className="info-section">
                    <h2>Приватність та Емпатія</h2>
                    <p>
                        Говоріть приватно, не в спільних чатах. Це допоможе уникнути захисної реакції.
                        Слухайте активно: зрозумійте, чому людина повірила (страх, турбота).
                    </p>
                </section>
            </>
        )
    }
};
