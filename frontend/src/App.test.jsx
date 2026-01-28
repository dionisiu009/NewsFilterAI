import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
import * as useNewsCheckHook from './hooks/useNewsCheck';

// Дефолтний стан хука для тестів
const defaultHookValues = {
    status: 'IDLE',
    check: vi.fn(),
    reset: vi.fn(),
    isLoading: false,
    isProcessing: false,
    result: null,
    error: null,
    progress: null,
    errorDetails: null
};

// Мок хука useNewsCheck для ізоляції UI від бізнес-логіки
vi.mock('./hooks/useNewsCheck', () => ({
    CheckStatus: {
        IDLE: 'IDLE',
        LOADING: 'LOADING',
        PROCESSING: 'PROCESSING',
        SUCCESS: 'SUCCESS',
        ERROR: 'ERROR'
    },
    useNewsCheck: vi.fn(() => defaultHookValues)
}));

describe('App Component Integration Tests', () => {

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(useNewsCheckHook.useNewsCheck).mockReturnValue(defaultHookValues);
    });

    it('renders initial state correctly (IDLE)', () => {
        render(<App />);

        expect(screen.getByRole('heading', { name: /NewsFilter AI/i })).toBeInTheDocument();
        expect(screen.getByPlaceholderText(/Вставте URL новини/i)).toBeInTheDocument();
        expect(screen.getByText(/Як це працює?/i)).toBeInTheDocument();
    });

    it('handles user input and submission', async () => {
        const checkMock = vi.fn();
        vi.mocked(useNewsCheckHook.useNewsCheck).mockReturnValue({
            ...defaultHookValues,
            check: checkMock
        });

        const user = userEvent.setup();
        render(<App />);

        const input = screen.getByPlaceholderText(/Вставте URL новини/i);
        const submitButton = screen.getByRole('button', { name: /Перевірити/i });

        await act(async () => {
            await user.type(input, 'https://example.com/news');
            await user.click(submitButton);
        });

        expect(checkMock).toHaveBeenCalledWith('https://example.com/news');
    });

    it('displays loading state correctly', () => {
        vi.mocked(useNewsCheckHook.useNewsCheck).mockReturnValue({
            ...defaultHookValues,
            status: 'LOADING',
            isLoading: true,
            progress: { message: 'Завантаження...', elapsed: 2 }
        });

        render(<App />);

        expect(screen.getByText(/Завантаження.../i)).toBeInTheDocument();
        expect(screen.getByText(/Час очікування: 2с/i)).toBeInTheDocument();

        // Переконуємось, що лендінг прихований, а форма заблокована
        expect(screen.queryByText(/Як це працює?/i)).not.toBeInTheDocument();
        expect(screen.getByPlaceholderText(/Вставте URL новини/i)).toBeDisabled();
    });

    it('displays success result correctly', () => {
        const mockResult = {
            verdict: 'true',
            title: 'Test News Article',
            source_domain: 'example.com',
            confidence_score: 85,
            summary: 'This is a true news article.',
            recommendation: 'You can trust this source.',
            cached: false
        };

        vi.mocked(useNewsCheckHook.useNewsCheck).mockReturnValue({
            ...defaultHookValues,
            status: 'SUCCESS',
            result: mockResult
        });

        render(<App />);

        expect(screen.getByText('ДОСТОВІРНА')).toBeInTheDocument();
        expect(screen.getByText('Test News Article')).toBeInTheDocument();
        expect(screen.getByText('This is a true news article.')).toBeInTheDocument();

        expect(screen.getByRole('button', { name: /Перевірити іншу новину/i })).toBeInTheDocument();
    });

    it('displays error state correctly', () => {
        const resetMock = vi.fn();
        vi.mocked(useNewsCheckHook.useNewsCheck).mockReturnValue({
            ...defaultHookValues,
            status: 'ERROR',
            error: 'Server unavailable',
            reset: resetMock
        });

        render(<App />);

        expect(screen.getByText(/Виникла помилка/i)).toBeInTheDocument();
        expect(screen.getByText('Server unavailable')).toBeInTheDocument();

        const retryButton = screen.getByRole('button', { name: /Спробувати ще раз/i });
        fireEvent.click(retryButton);
        expect(resetMock).toHaveBeenCalled();
    });

    it('calls reset when "Check another news" is clicked in Result view', () => {
        const resetMock = vi.fn();
        vi.mocked(useNewsCheckHook.useNewsCheck).mockReturnValue({
            ...defaultHookValues,
            status: 'SUCCESS',
            result: { verdict: 'true' },
            reset: resetMock
        });

        render(<App />);

        const resetButton = screen.getByRole('button', { name: /Перевірити іншу новину/i });
        fireEvent.click(resetButton);

        expect(resetMock).toHaveBeenCalled();
    });
});
