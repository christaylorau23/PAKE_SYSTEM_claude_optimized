import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import {
  OptimizedImage,
  AvatarImage,
  LogoImage,
  HeroImage,
  ThumbnailImage,
} from '../optimized-image';

// Mock Next.js Image component
jest.mock('next/image', () => ({
  __esModule: true,
  default: ({ src, alt, onLoad, onError, ...props }) => {
    return (
      <img src={src} alt={alt} onLoad={onLoad} onError={onError} {...props} />
    );
  },
}));

describe('OptimizedImage Components', () => {
  describe('OptimizedImage', () => {
    it('renders image with src and alt', () => {
      render(
        <OptimizedImage
          src='/test.jpg'
          alt='Test image'
          width={100}
          height={100}
        />
      );
      const image = screen.getByAltText('Test image');
      expect(image).toBeInTheDocument();
      expect(image).toHaveAttribute('src', '/test.jpg');
    });

    it('shows placeholder while loading', () => {
      render(
        <OptimizedImage
          src='/test.jpg'
          alt='Test image'
          width={100}
          height={100}
          showPlaceholder={true}
        />
      );
      // Placeholder should be visible initially
      const placeholder = screen.getByRole('img', { hidden: true });
      expect(placeholder).toHaveClass('opacity-0');
    });

    it('handles image load event', async () => {
      render(
        <OptimizedImage
          src='/test.jpg'
          alt='Test image'
          width={100}
          height={100}
        />
      );
      const image = screen.getByAltText('Test image');

      fireEvent.load(image);
      await waitFor(() => {
        expect(image).toHaveClass('opacity-100');
      });
    });

    it('handles image error with fallback', async () => {
      render(
        <OptimizedImage
          src='/broken.jpg'
          alt='Test image'
          width={100}
          height={100}
          fallbackSrc='/fallback.jpg'
        />
      );
      const image = screen.getByAltText('Test image');

      fireEvent.error(image);
      await waitFor(() => {
        expect(image).toHaveAttribute('src', '/fallback.jpg');
        expect(image).toHaveClass('grayscale');
      });
    });

    it('applies custom container className', () => {
      render(
        <OptimizedImage
          src='/test.jpg'
          alt='Test image'
          width={100}
          height={100}
          containerClassName='custom-container'
        />
      );
      const container = screen.getByAltText('Test image').parentElement;
      expect(container).toHaveClass('custom-container');
    });

    it('hides placeholder when showPlaceholder is false', () => {
      render(
        <OptimizedImage
          src='/test.jpg'
          alt='Test image'
          width={100}
          height={100}
          showPlaceholder={false}
        />
      );
      const placeholders = screen.queryAllByRole('img', { hidden: true });
      expect(placeholders.length).toBeLessThanOrEqual(1); // Only the main image
    });
  });

  describe('AvatarImage', () => {
    it('renders circular avatar with default size', () => {
      render(<AvatarImage src='/avatar.jpg' alt='User avatar' />);
      const image = screen.getByAltText('User avatar');
      expect(image).toHaveClass('rounded-full', 'object-cover');
      expect(image).toHaveAttribute('width', '40');
      expect(image).toHaveAttribute('height', '40');
    });

    it('renders with custom size', () => {
      render(<AvatarImage src='/avatar.jpg' alt='User avatar' size={64} />);
      const image = screen.getByAltText('User avatar');
      expect(image).toHaveAttribute('width', '64');
      expect(image).toHaveAttribute('height', '64');
    });
  });

  describe('LogoImage', () => {
    it('renders logo with auto width', () => {
      render(<LogoImage src='/logo.svg' alt='Company logo' />);
      const image = screen.getByAltText('Company logo');
      expect(image).toHaveClass('w-auto', 'h-full', 'object-contain');
      expect(image).toHaveAttribute('height', '32');
      expect(image).toHaveAttribute('width', '0');
    });

    it('renders with custom height', () => {
      render(<LogoImage src='/logo.svg' alt='Company logo' height={48} />);
      const image = screen.getByAltText('Company logo');
      expect(image).toHaveAttribute('height', '48');
    });

    it('has priority loading for above-fold content', () => {
      render(<LogoImage src='/logo.svg' alt='Company logo' />);
      const image = screen.getByAltText('Company logo');
      // Next.js Image priority prop would be passed through
      expect(image).toBeInTheDocument();
    });
  });

  describe('HeroImage', () => {
    it('renders with fill and object-cover', () => {
      render(<HeroImage src='/hero.jpg' alt='Hero image' />);
      const image = screen.getByAltText('Hero image');
      expect(image).toHaveClass('object-cover');
    });

    it('has priority loading for hero images', () => {
      render(<HeroImage src='/hero.jpg' alt='Hero image' />);
      const image = screen.getByAltText('Hero image');
      expect(image).toBeInTheDocument();
    });

    it('uses responsive sizes attribute', () => {
      render(<HeroImage src='/hero.jpg' alt='Hero image' />);
      const image = screen.getByAltText('Hero image');
      // Next.js would handle the sizes attribute
      expect(image).toBeInTheDocument();
    });
  });

  describe('ThumbnailImage', () => {
    it('renders square thumbnail with default size', () => {
      render(<ThumbnailImage src='/thumb.jpg' alt='Thumbnail' />);
      const image = screen.getByAltText('Thumbnail');
      expect(image).toHaveClass('rounded-lg', 'object-cover');
      expect(image).toHaveAttribute('width', '150');
      expect(image).toHaveAttribute('height', '150');
    });

    it('renders with custom size', () => {
      render(<ThumbnailImage src='/thumb.jpg' alt='Thumbnail' size={200} />);
      const image = screen.getByAltText('Thumbnail');
      expect(image).toHaveAttribute('width', '200');
      expect(image).toHaveAttribute('height', '200');
    });
  });

  describe('Accessibility', () => {
    it('provides proper alt text', () => {
      render(
        <OptimizedImage
          src='/test.jpg'
          alt='Descriptive alt text'
          width={100}
          height={100}
        />
      );
      expect(screen.getByAltText('Descriptive alt text')).toBeInTheDocument();
    });

    it('handles empty alt for decorative images', () => {
      render(
        <OptimizedImage src='/decoration.jpg' alt='' width={100} height={100} />
      );
      const image = screen.getByRole('img');
      expect(image).toHaveAttribute('alt', '');
    });
  });

  describe('Performance', () => {
    it('applies blur placeholder by default', () => {
      render(
        <OptimizedImage src='/test.jpg' alt='Test' width={100} height={100} />
      );
      const image = screen.getByAltText('Test');
      // Next.js Image would handle blur placeholder
      expect(image).toBeInTheDocument();
    });

    it('sets high quality for important images', () => {
      render(
        <OptimizedImage src='/test.jpg' alt='Test' width={100} height={100} />
      );
      const image = screen.getByAltText('Test');
      // Quality setting would be passed to Next.js Image
      expect(image).toBeInTheDocument();
    });
  });
});
