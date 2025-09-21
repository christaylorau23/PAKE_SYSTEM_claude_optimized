'use client';

import Image, { ImageProps } from 'next/image';
import { useState } from 'react';
import { cn } from '@/lib/utils';

interface OptimizedImageProps extends Omit<ImageProps, 'placeholder'> {
  fallbackSrc?: string;
  className?: string;
  containerClassName?: string;
  showPlaceholder?: boolean;
  placeholderClassName?: string;
}

export function OptimizedImage({
  src,
  alt,
  fallbackSrc = '/placeholder-image.svg',
  className,
  containerClassName,
  showPlaceholder = true,
  placeholderClassName,
  ...props
}: OptimizedImageProps) {
  const [imgSrc, setImgSrc] = useState(src);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  const handleError = () => {
    setHasError(true);
    setImgSrc(fallbackSrc);
    setIsLoading(false);
  };

  const handleLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  return (
    <div className={cn('relative overflow-hidden', containerClassName)}>
      {isLoading && showPlaceholder && (
        <div
          className={cn(
            'absolute inset-0 bg-gray-200 dark:bg-gray-800 animate-pulse',
            'flex items-center justify-center',
            placeholderClassName
          )}
        >
          <div className='w-8 h-8 text-gray-400'>
            <svg
              fill='none'
              stroke='currentColor'
              viewBox='0 0 24 24'
              className='w-full h-full'
            >
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={2}
                d='M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z'
              />
            </svg>
          </div>
        </div>
      )}

      <Image
        src={imgSrc}
        alt={alt}
        className={cn(
          'transition-opacity duration-300',
          isLoading ? 'opacity-0' : 'opacity-100',
          hasError && 'grayscale',
          className
        )}
        onLoad={handleLoad}
        onError={handleError}
        quality={90}
        placeholder='blur'
        blurDataURL='data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAIAAoDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAhEAACAQMDBQAAAAAAAAAAAAABAgMABAUGIWGRkqGx0f/EABUBAQEAAAAAAAAAAAAAAAAAAAMF/8QAGhEAAgIDAAAAAAAAAAAAAAAAAAECEgMRkf/aAAwDAQACEQMRAD8AltJagyeH0AthI5xdrLcNM91BF5pX2HaH9bcfaSXWGaRmknyJckliyjqTzSlT54b6bk+h0R//2Q=='
        {...props}
      />
    </div>
  );
}

// Specialized image components for common use cases
export function AvatarImage({
  src,
  alt,
  size = 40,
  ...props
}: Omit<OptimizedImageProps, 'width' | 'height'> & { size?: number }) {
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      width={size}
      height={size}
      className='rounded-full object-cover'
      {...props}
    />
  );
}

export function LogoImage({
  src,
  alt,
  height = 32,
  ...props
}: Omit<OptimizedImageProps, 'height'> & { height?: number }) {
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      height={height}
      width={0}
      className='w-auto h-full object-contain'
      priority
      {...props}
    />
  );
}

export function HeroImage({ src, alt, ...props }: OptimizedImageProps) {
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      fill
      className='object-cover'
      priority
      sizes='(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw'
      {...props}
    />
  );
}

export function ThumbnailImage({
  src,
  alt,
  size = 150,
  ...props
}: Omit<OptimizedImageProps, 'width' | 'height'> & { size?: number }) {
  return (
    <OptimizedImage
      src={src}
      alt={alt}
      width={size}
      height={size}
      className='rounded-lg object-cover'
      sizes={`${size}px`}
      {...props}
    />
  );
}
