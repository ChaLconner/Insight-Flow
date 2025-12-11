/**
 * Badge Component Tests
 * Tests for the Badge UI component with various variants
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '@/components/ui/badge';

describe('Badge Component', () => {
    it('renders Badge component', () => {
        render(<Badge data-testid="badge">Badge Text</Badge>);
        expect(screen.getByTestId('badge')).toBeInTheDocument();
        expect(screen.getByText('Badge Text')).toBeInTheDocument();
    });

    it('applies default variant', () => {
        render(<Badge data-testid="badge">Default</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-primary');
    });

    it('applies secondary variant', () => {
        render(<Badge variant="secondary" data-testid="badge">Secondary</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-secondary');
    });

    it('applies destructive variant', () => {
        render(<Badge variant="destructive" data-testid="badge">Destructive</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-destructive');
    });

    it('applies outline variant', () => {
        render(<Badge variant="outline" data-testid="badge">Outline</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('text-foreground');
    });

    it('applies success variant', () => {
        render(<Badge variant="success" data-testid="badge">Success</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-green-500');
    });

    it('applies warning variant', () => {
        render(<Badge variant="warning" data-testid="badge">Warning</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-yellow-500');
    });

    it('applies error variant', () => {
        render(<Badge variant="error" data-testid="badge">Error</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-red-500');
    });

    it('applies glass variant', () => {
        render(<Badge variant="glass" data-testid="badge">Glass</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('backdrop-blur-sm');
    });

    it('applies glass-primary variant', () => {
        render(<Badge variant="glass-primary" data-testid="badge">Glass Primary</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-blue-500/20');
    });

    it('applies glass-success variant', () => {
        render(<Badge variant="glass-success" data-testid="badge">Glass Success</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('bg-green-500/20');
    });

    it('applies custom className', () => {
        render(<Badge className="custom-class" data-testid="badge">Custom</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('custom-class');
    });

    it('renders with border-radius (rounded-full)', () => {
        render(<Badge data-testid="badge">Rounded</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveClass('rounded-full');
    });

    it('renders children correctly', () => {
        render(
            <Badge data-testid="badge">
                <span>Icon</span>
                <span>Text</span>
            </Badge>
        );
        expect(screen.getByText('Icon')).toBeInTheDocument();
        expect(screen.getByText('Text')).toBeInTheDocument();
    });

    it('passes additional props', () => {
        render(<Badge data-testid="badge" title="Badge Title">Content</Badge>);
        const badge = screen.getByTestId('badge');
        expect(badge).toHaveAttribute('title', 'Badge Title');
    });
});
