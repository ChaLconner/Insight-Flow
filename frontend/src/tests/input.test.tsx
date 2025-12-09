/**
 * Input Component Tests
 * Tests for the Input UI component
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Input } from '@/components/ui/input';

describe('Input Component', () => {
    it('renders Input component', () => {
        render(<Input data-testid="input" />);
        expect(screen.getByTestId('input')).toBeInTheDocument();
    });

    it('renders without type attribute when not specified', () => {
        render(<Input data-testid="input" />);
        const input = screen.getByTestId('input');
        // Input component doesn't add default type, browser defaults to text
        expect(input).not.toHaveAttribute('type');
    });

    it('renders with specified type', () => {
        render(<Input type="email" data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toHaveAttribute('type', 'email');
    });

    it('renders password input', () => {
        render(<Input type="password" data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toHaveAttribute('type', 'password');
    });

    it('applies custom className', () => {
        render(<Input className="custom-input" data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toHaveClass('custom-input');
    });

    it('renders with placeholder', () => {
        render(<Input placeholder="Enter your name" data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toHaveAttribute('placeholder', 'Enter your name');
    });

    it('handles value changes', () => {
        const handleChange = vi.fn();
        render(<Input onChange={handleChange} data-testid="input" />);
        const input = screen.getByTestId('input');

        fireEvent.change(input, { target: { value: 'test value' } });
        expect(handleChange).toHaveBeenCalledTimes(1);
    });

    it('displays value correctly', () => {
        render(<Input value="initial value" onChange={() => { }} data-testid="input" />);
        const input = screen.getByTestId('input') as HTMLInputElement;
        expect(input.value).toBe('initial value');
    });

    it('can be disabled', () => {
        render(<Input disabled data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toBeDisabled();
    });

    it('can be read-only', () => {
        render(<Input readOnly value="readonly value" data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toHaveAttribute('readonly');
    });

    it('forwards ref correctly', () => {
        const ref = { current: null };
        render(<Input ref={ref} data-testid="input" />);
        expect(ref.current).toBeInstanceOf(HTMLInputElement);
    });

    it('handles focus events', () => {
        const handleFocus = vi.fn();
        render(<Input onFocus={handleFocus} data-testid="input" />);
        const input = screen.getByTestId('input');

        fireEvent.focus(input);
        expect(handleFocus).toHaveBeenCalledTimes(1);
    });

    it('handles blur events', () => {
        const handleBlur = vi.fn();
        render(<Input onBlur={handleBlur} data-testid="input" />);
        const input = screen.getByTestId('input');

        fireEvent.blur(input);
        expect(handleBlur).toHaveBeenCalledTimes(1);
    });

    it('accepts name attribute', () => {
        render(<Input name="username" data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toHaveAttribute('name', 'username');
    });

    it('accepts required attribute', () => {
        render(<Input required data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toBeRequired();
    });

    it('accepts maxLength attribute', () => {
        render(<Input maxLength={50} data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toHaveAttribute('maxLength', '50');
    });

    it('accepts autoComplete attribute', () => {
        render(<Input autoComplete="email" data-testid="input" />);
        const input = screen.getByTestId('input');
        expect(input).toHaveAttribute('autocomplete', 'email');
    });
});
