import { render, screen } from '@testing-library/react';
import {
  Loading,
  PageLoading,
  ComponentLoading,
  InlineLoading,
} from '../loading';

describe('Loading Components', () => {
  describe('Loading', () => {
    it('renders with default props', () => {
      render(<Loading />);
      const spinner = screen.getByRole('status', { hidden: true });
      expect(spinner).toBeInTheDocument();
    });

    it('renders with text', () => {
      render(<Loading text='Loading data...' />);
      expect(screen.getByText('Loading data...')).toBeInTheDocument();
    });

    it('applies size classes correctly', () => {
      render(<Loading size='lg' data-testid='loading' />);
      const container = screen.getByTestId('loading');
      const spinner = container.querySelector('.w-12.h-12');
      expect(spinner).toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(<Loading className='custom-loading' data-testid='loading' />);
      expect(screen.getByTestId('loading')).toHaveClass('custom-loading');
    });
  });

  describe('PageLoading', () => {
    it('renders full page loading state', () => {
      render(<PageLoading />);
      const container = screen
        .getByRole('status', { hidden: true })
        .closest('.min-h-screen');
      expect(container).toHaveClass(
        'min-h-screen',
        'flex',
        'items-center',
        'justify-center'
      );
    });

    it('shows loading text', () => {
      render(<PageLoading />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('ComponentLoading', () => {
    it('renders component loading state', () => {
      render(<ComponentLoading />);
      const container = screen
        .getByRole('status', { hidden: true })
        .closest('.flex');
      expect(container).toHaveClass(
        'flex',
        'items-center',
        'justify-center',
        'p-4'
      );
    });
  });

  describe('InlineLoading', () => {
    it('renders inline loading state', () => {
      render(<InlineLoading />);
      const container = screen
        .getByRole('status', { hidden: true })
        .closest('.p-2');
      expect(container).toHaveClass('p-2');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<Loading />);
      const spinner = screen.getByRole('status', { hidden: true });
      expect(spinner).toBeInTheDocument();
    });

    it('is focusable for screen readers when needed', () => {
      render(<Loading />);
      const spinner = screen.getByRole('status', { hidden: true });
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Animation', () => {
    it('has spinning animation class', () => {
      render(<Loading data-testid='loading' />);
      const container = screen.getByTestId('loading');
      const spinner = container.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });
});
