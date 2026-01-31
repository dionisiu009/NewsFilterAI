import deepfakeHeroImage from '../assets/deepfake_disinfo_hero.png';
import familyHeroImage from '../assets/family_disinfo_hero.png';
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
        heroImage: deepfakeHeroImage,
        content: (
            <>
                <section className="info-section">
                    <h2>🕵️ Шерлок Холмс у світі пікселів</h2>
                    <p>
                        Навіть найсучасніші нейромережі (Midjourney, DALL-E) залишають «цифрові відбитки». Часто перше враження "щось тут не так" є найвірнішим.
                        Ось детальна інструкція, куди дивитися.
                    </p>
                    <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '1.5rem', borderRadius: '12px', borderLeft: '4px solid var(--color-secondary)', fontStyle: 'italic' }}>
                        "Діпфейк – це не магія, це математика. І вона часто помиляється в деталях."
                    </div>
                </section>

                <section className="info-section">
                    <h2>1. Анатомія та "Глічі"</h2>
                    <ul className="info-list">
                        <li><strong>Руки та пальці:</strong> Класична проблема ШІ. Шукайте зайві пальці, неприродні вигини, або руки, що "зливаються" з предметами.</li>
                        <li><strong>Очі:</strong> У реальної людини відблиски в зіницях (від сонця чи лампи) мають бути в одному місці. У ШІ вони часто різні. Також зверніть увагу на колір райдужки.</li>
                        <li><strong>Вуха та зуби:</strong> Вуха можуть бути різної форми або розміру. Зуби часто виглядають як суцільна біла смуга або їх занадто багато.</li>
                        <li><strong>Шкіра та волосся:</strong> Шкіра може виглядати "пластиковою", без пор і зморшок. Волосся іноді розмивається на кінчиках або виглядає як намальоване.</li>
                    </ul>
                </section>

                <section className="info-section">
                    <h2>2. Фізика та Логіка</h2>
                    <p>
                        ШІ часто плутає закони фізики. Зверніть увагу на тіні: чи відповідають вони джерелу світла? Чи є віддзеркалення в окулярах?
                        Також перевіряйте фон: написи можуть бути "інопланетною мовою", а архітектура — викривленою.
                    </p>
                </section>

                <section className="info-section">
                    <h2>🛠 Інструменти розслідувача</h2>
                    <p>
                        Найпростіший спосіб перевірити фото — це <strong>зворотний пошук зображень</strong>.
                    </p>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1.5rem' }}>
                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                            <h3 style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.5rem' }}>🔍 Google Images</h3>
                            <p style={{ fontSize: '0.9rem', margin: 0 }}>Натисніть "Пошук по картинці". Знайдете, де це фото з'явилося вперше.</p>
                        </div>
                        <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px' }}>
                            <h3 style={{ color: '#fff', fontSize: '1.1rem', marginBottom: '0.5rem' }}>🌐 TinEye</h3>
                            <p style={{ fontSize: '0.9rem', margin: 0 }}>Потужний інструмент для пошуку оригіналів та модифікацій зображення.</p>
                        </div>
                    </div>
                </section>

                <section className="info-section">
                    <h2>🔗 Корисні лінки</h2>
                    <div style={{ display: 'flex', flexWrap: 'wrap', marginTop: '1rem' }}>
                        <a href="https://images.google.com/" target="_blank" rel="noopener noreferrer" className="source-link">Google Images</a>
                        <a href="https://tineye.com/" target="_blank" rel="noopener noreferrer" className="source-link">TinEye</a>
                        <a href="https://fotoforensics.com/" target="_blank" rel="noopener noreferrer" className="source-link">FotoForensics (Pro)</a>
                    </div>
                </section>
            </>
        )
    },
    family: {
        title: 'Як говорити про фейки з близькими',
        icon: '👨‍👩‍👧‍👦',
        heroImage: familyHeroImage,
        content: (
            <>
                <section className="info-section">
                    <h2>🕊️ Розмова без конфліктів</h2>
                    <p>
                        Коли близькі діляться фейками, наша перша реакція — суперечити. Це помилка.
                        Агресія будує емоційну стіну, за якою вас більше не чують (так званий "ефект зворотного вогню").
                    </p>
                    <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '1.5rem', borderRadius: '12px', borderLeft: '4px solid var(--color-true)', fontStyle: 'italic' }}>
                        "Ваша мета — не виграти суперечку, а зберегти стосунки та допомогти рідній людині розібратися."
                    </div>
                </section>

                <section className="info-section">
                    <h2>🍔 Метод «Сендвіча істини»</h2>
                    <p>Психологи рекомендують подавати інформацію в такій послідовності, щоб вона запам’яталася:</p>
                    <ol className="info-list" style={{ listStyle: 'decimal', paddingLeft: '1.5rem' }}>
                        <li>
                            <strong>Хліб (Факт):</strong> Почніть з простої, незаперечної правди, з якою ви обоє згодні. Це створює спільну землю.
                        </li>
                        <li>
                            <strong>Начинка (Попередження про міф):</strong> Коротко згадайте фейк, але не фокусуйтеся на ньому. Поясніть, ДЕ маніпуляція (наприклад, "це фото 5-річної давнини").
                        </li>
                        <li>
                            <strong>Хліб (Факт):</strong> Закінчіть повторенням правди, але вже з аргументами. Останнє речення мозок запам'ятовує найкраще.
                        </li>
                    </ol>
                </section>

                <section className="info-section">
                    <h2>🤫 Приватність та Емпатія</h2>
                    <ul className="info-list">
                        <li>
                            <strong>Говоріть приватно.</strong> Ніколи не виправляйте людину в сімейному чаті чи коментарях. Публічний сором змушує захищатися, а не думати.
                        </li>
                        <li>
                            <strong>Слухайте страх.</strong> За кожним репостом фейку стоїть емоція. Бабуся поширює "ліки від усього" не тому, що дурна, а тому що боїться хвороб і хоче про вас подбати. Подякуйте за турботу, а потім поясніть суть.
                        </li>
                        <li>
                            <strong>Дайте вихід.</strong> Дозвольте людині зберегти обличчя. "Це дуже якісний фейк, я б теж повірив, якби не перевірив джерело".
                        </li>
                    </ul>
                </section>

                <section className="info-section">
                    <h2>📚 Що почитати разом?</h2>
                    <div style={{ display: 'flex', flexWrap: 'wrap', marginTop: '1rem' }}>
                        <a href="https://filter.mg.gov.ua/publication/" target="_blank" rel="noopener noreferrer" className="source-link">Посібники з медіаграмотності</a>
                        <a href="https://www.youtube.com/watch?v=HuW3GjY_iQo" target="_blank" rel="noopener noreferrer" className="source-link">Відео пояснення</a>
                    </div>
                </section>
            </>
        )
    }
};
