/* AI-Enhanced Input Component - Intelligent Form Input */
/* Revolutionary input with AI assistance and predictive capabilities */

'use client';

import * as React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Input, type InputProps } from '@/components/ui/input';
import {
  useFormAssistant,
  type CompletionResult,
  type FieldAnalysis,
} from '@/lib/ai/form-assistant';
import { useStore } from '@/lib/store';
import { cn } from '@/lib/utils';

// AI Input Configuration
interface AIInputConfig {
  enableSmartCompletion?: boolean;
  enablePredictiveValidation?: boolean;
  enableVoiceInput?: boolean;
  enableAccessibilityAI?: boolean;
  enableTranslation?: boolean;
  completionDelay?: number;
  confidenceThreshold?: number;
  maxSuggestions?: number;
}

// AI Input Props
export interface AIInputProps extends Omit<InputProps, 'onChange'> {
  name: string;
  formContext?: Record<string, unknown>;
  aiConfig?: AIInputConfig;
  onValueChange?: (
    value: string,
    aiMetadata?: {
      completion?: CompletionResult;
      analysis?: FieldAnalysis;
      confidence?: number;
    }
  ) => void;
  onAIEvent?: (event: {
    type: 'completion' | 'validation' | 'voice' | 'analysis';
    data: unknown;
    timestamp: number;
  }) => void;
}

// Suggestion Item Component
interface SuggestionProps {
  suggestion: string;
  confidence: number;
  isSelected: boolean;
  onClick: () => void;
  onHover: () => void;
}

function SuggestionItem({
  suggestion,
  confidence,
  isSelected,
  onClick,
  onHover,
}: SuggestionProps) {
  return (
    <motion.div
      className={cn(
        'px-3 py-2 cursor-pointer text-sm border-l-2 transition-all',
        isSelected
          ? 'bg-brand-primary-50 dark:bg-brand-primary-900/20 border-brand-primary-500 text-brand-primary-700 dark:text-brand-primary-300'
          : 'bg-white dark:bg-neutral-800 border-transparent hover:bg-neutral-50 dark:hover:bg-neutral-700'
      )}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -10 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      onMouseEnter={onHover}
    >
      <div className='flex items-center justify-between'>
        <span className='flex-1'>{suggestion}</span>
        <span className='text-xs text-neutral-500 ml-2'>
          {Math.round(confidence * 100)}%
        </span>
      </div>
    </motion.div>
  );
}

// AI Input Component
export const AIInput = React.forwardRef<HTMLInputElement, AIInputProps>(
  (
    {
      name,
      formContext = {},
      aiConfig,
      onValueChange,
      onAIEvent,
      className,
      ...props
    },
    ref
  ) => {
    const { user } = useStore();
    const animationsEnabled = !user.reducedMotion;

    // AI Configuration
    const config: Required<AIInputConfig> = React.useMemo(
      () => ({
        enableSmartCompletion: true,
        enablePredictiveValidation: true,
        enableVoiceInput: true,
        enableAccessibilityAI: true,
        enableTranslation: false,
        completionDelay: 500,
        confidenceThreshold: 0.7,
        maxSuggestions: 3,
        ...aiConfig,
      }),
      [aiConfig]
    );

    // Form Assistant
    const formAssistant = useFormAssistant({
      enableCompletion: config.enableSmartCompletion,
      enableValidation: config.enablePredictiveValidation,
      enableVoiceInput: config.enableVoiceInput,
      enableAccessibilityEnhancement: config.enableAccessibilityAI,
      enableTranslation: config.enableTranslation,
      confidenceThreshold: config.confidenceThreshold,
    });

    // State Management
    const [value, setValue] = React.useState(props.value || '');
    const [suggestions, setSuggestions] =
      React.useState<CompletionResult | null>(null);
    const [selectedSuggestionIndex, setSelectedSuggestionIndex] =
      React.useState(0);
    const [showSuggestions, setShowSuggestions] = React.useState(false);
    const [fieldAnalysis, setFieldAnalysis] =
      React.useState<FieldAnalysis | null>(null);
    const [isAnalyzing, setIsAnalyzing] = React.useState(false);
    const [isVoiceActive, setIsVoiceActive] = React.useState(false);
    const [confidence, setConfidence] = React.useState(0);

    // Refs
    const inputRef = React.useRef<HTMLInputElement>(null);
    const completionTimeoutRef = React.useRef<NodeJS.Timeout>();
    const suggestionsRef = React.useRef<HTMLDivElement>(null);

    // Combined ref handling
    React.useImperativeHandle(ref, () => inputRef.current!, []);

    // Smart Completion Logic
    const handleSmartCompletion = React.useCallback(
      async (currentValue: string) => {
        if (!config.enableSmartCompletion || currentValue.length < 2) {
          setSuggestions(null);
          setShowSuggestions(false);
          return;
        }

        try {
          const completion = await formAssistant.getCompletion(
            name,
            currentValue,
            formContext
          );

          if (completion.confidence >= config.confidenceThreshold) {
            setSuggestions(completion);
            setShowSuggestions(true);
            setSelectedSuggestionIndex(0);
            setConfidence(completion.confidence);

            // Emit AI event
            onAIEvent?.({
              type: 'completion',
              data: completion,
              timestamp: Date.now(),
            });
          }
        } catch (error) {
          console.error('Smart completion error:', error);
          setSuggestions(null);
          setShowSuggestions(false);
        }
      },
      [name, formContext, config, formAssistant, onAIEvent]
    );

    // Field Analysis
    const handleFieldAnalysis = React.useCallback(
      async (currentValue: string) => {
        if (!config.enablePredictiveValidation) return;

        setIsAnalyzing(true);

        try {
          const analysis = await formAssistant.analyzeField(
            name,
            currentValue,
            props.type
          );

          setFieldAnalysis(analysis);

          // Emit AI event
          onAIEvent?.({
            type: 'analysis',
            data: analysis,
            timestamp: Date.now(),
          });
        } catch (error) {
          console.error('Field analysis error:', error);
        } finally {
          setIsAnalyzing(false);
        }
      },
      [name, props.type, config, formAssistant, onAIEvent]
    );

    // Handle value changes
    const handleValueChange = React.useCallback(
      (newValue: string) => {
        setValue(newValue);

        // Clear existing completion timeout
        if (completionTimeoutRef.current) {
          clearTimeout(completionTimeoutRef.current);
        }

        // Schedule smart completion
        if (config.enableSmartCompletion) {
          completionTimeoutRef.current = setTimeout(() => {
            handleSmartCompletion(newValue);
          }, config.completionDelay);
        }

        // Immediate field analysis for validation
        if (config.enablePredictiveValidation && newValue.length > 0) {
          handleFieldAnalysis(newValue);
        }

        // Call parent onChange with AI metadata
        onValueChange?.(newValue, {
          completion: suggestions,
          analysis: fieldAnalysis,
          confidence,
        });
      },
      [
        config,
        handleSmartCompletion,
        handleFieldAnalysis,
        suggestions,
        fieldAnalysis,
        confidence,
        onValueChange,
      ]
    );

    // Handle input changes
    const handleInputChange = React.useCallback(
      (event: React.ChangeEvent<HTMLInputElement>) => {
        handleValueChange(event.target.value);
      },
      [handleValueChange]
    );

    // Handle suggestion selection
    const handleSuggestionSelect = React.useCallback(
      (suggestion: string) => {
        const newValue = value + suggestion;
        handleValueChange(newValue);
        setShowSuggestions(false);
        inputRef.current?.focus();
      },
      [value, handleValueChange]
    );

    // Handle voice input
    const handleVoiceInput = React.useCallback(async () => {
      if (!config.enableVoiceInput) return;

      setIsVoiceActive(true);

      try {
        const voiceResult = await formAssistant.processVoice();

        if (voiceResult.confidence >= config.confidenceThreshold) {
          handleValueChange(voiceResult.text);

          // Emit AI event
          onAIEvent?.({
            type: 'voice',
            data: voiceResult,
            timestamp: Date.now(),
          });
        }
      } catch (error) {
        console.error('Voice input error:', error);
      } finally {
        setIsVoiceActive(false);
      }
    }, [config, formAssistant, handleValueChange, onAIEvent]);

    // Keyboard navigation for suggestions
    const handleKeyDown = React.useCallback(
      (event: React.KeyboardEvent<HTMLInputElement>) => {
        if (!showSuggestions || !suggestions) {
          props.onKeyDown?.(event);
          return;
        }

        const totalSuggestions = Math.min(
          suggestions.alternatives.length + 1,
          config.maxSuggestions
        );

        switch (event.key) {
          case 'ArrowDown':
            event.preventDefault();
            setSelectedSuggestionIndex(prev =>
              prev < totalSuggestions - 1 ? prev + 1 : 0
            );
            break;

          case 'ArrowUp':
            event.preventDefault();
            setSelectedSuggestionIndex(prev =>
              prev > 0 ? prev - 1 : totalSuggestions - 1
            );
            break;

          case 'Enter':
            if (selectedSuggestionIndex === 0) {
              event.preventDefault();
              handleSuggestionSelect(suggestions.value);
            } else {
              const altIndex = selectedSuggestionIndex - 1;
              if (suggestions.alternatives[altIndex]) {
                event.preventDefault();
                handleSuggestionSelect(
                  suggestions.alternatives[altIndex].value
                );
              }
            }
            break;

          case 'Escape':
            event.preventDefault();
            setShowSuggestions(false);
            break;

          default:
            props.onKeyDown?.(event);
        }
      },
      [
        showSuggestions,
        suggestions,
        selectedSuggestionIndex,
        config.maxSuggestions,
        props,
        handleSuggestionSelect,
      ]
    );

    // Click outside to close suggestions
    React.useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (
          suggestionsRef.current &&
          !suggestionsRef.current.contains(event.target as Node) &&
          !inputRef.current?.contains(event.target as Node)
        ) {
          setShowSuggestions(false);
        }
      };

      document.addEventListener('mousedown', handleClickOutside);
      return () =>
        document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Enhanced accessibility based on AI analysis
    const accessibilityProps = React.useMemo(() => {
      if (!fieldAnalysis?.accessibility) return {};

      return {
        'aria-label': fieldAnalysis.accessibility.ariaLabel,
        'aria-describedby': fieldAnalysis.accessibility.description
          ? `${name}-ai-description`
          : undefined,
        'aria-invalid': fieldAnalysis.validation.isValid === false,
      };
    }, [fieldAnalysis, name]);

    // Dynamic error/success states based on AI analysis
    const dynamicValidationState = React.useMemo(() => {
      if (!fieldAnalysis) return {};

      if (fieldAnalysis.validation.errors.length > 0) {
        return { error: fieldAnalysis.validation.errors[0] };
      }

      if (fieldAnalysis.confidence > 0.9 && fieldAnalysis.validation.isValid) {
        return { success: 'Field looks good!' };
      }

      return {};
    }, [fieldAnalysis]);

    return (
      <div className='relative'>
        {/* Main Input */}
        <Input
          ref={inputRef}
          name={name}
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          className={cn(
            'transition-all duration-200',
            isAnalyzing &&
              'border-brand-primary-300 dark:border-brand-primary-600',
            className
          )}
          rightIcon={
            <div className='flex items-center gap-1'>
              {/* Voice Input Button */}
              {config.enableVoiceInput && (
                <motion.button
                  type='button'
                  onClick={handleVoiceInput}
                  disabled={isVoiceActive}
                  className={cn(
                    'w-4 h-4 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300 transition-colors',
                    isVoiceActive && 'text-brand-primary-500 animate-pulse'
                  )}
                  whileHover={animationsEnabled ? { scale: 1.1 } : undefined}
                  whileTap={animationsEnabled ? { scale: 0.9 } : undefined}
                  aria-label='Voice input'
                  title='Click to speak'
                >
                  {isVoiceActive ? '🎙️' : '🎤'}
                </motion.button>
              )}

              {/* AI Confidence Indicator */}
              {confidence > 0 && (
                <div
                  className={cn(
                    'w-2 h-2 rounded-full',
                    confidence > 0.8
                      ? 'bg-success-500'
                      : confidence > 0.6
                        ? 'bg-warning-500'
                        : 'bg-error-500'
                  )}
                  title={`AI Confidence: ${Math.round(confidence * 100)}%`}
                />
              )}

              {/* Analysis Loading */}
              {isAnalyzing && (
                <motion.div
                  className='w-3 h-3 border border-brand-primary-600 border-t-transparent rounded-full'
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  title='Analyzing field...'
                />
              )}

              {/* Original right icon */}
              {props.rightIcon}
            </div>
          }
          {...dynamicValidationState}
          {...accessibilityProps}
          {...props}
        />

        {/* AI Suggestions */}
        <AnimatePresence>
          {showSuggestions && suggestions && (
            <motion.div
              ref={suggestionsRef}
              className='absolute top-full left-0 right-0 z-50 mt-1 bg-white dark:bg-neutral-800 rounded-md shadow-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden'
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.2 }}
            >
              {/* Primary Suggestion */}
              <SuggestionItem
                suggestion={suggestions.value}
                confidence={suggestions.confidence}
                isSelected={selectedSuggestionIndex === 0}
                onClick={() => handleSuggestionSelect(suggestions.value)}
                onHover={() => setSelectedSuggestionIndex(0)}
              />

              {/* Alternative Suggestions */}
              {suggestions.alternatives
                .slice(0, config.maxSuggestions - 1)
                .map((alt, index) => (
                  <SuggestionItem
                    key={index}
                    suggestion={alt.value}
                    confidence={alt.confidence}
                    isSelected={selectedSuggestionIndex === index + 1}
                    onClick={() => handleSuggestionSelect(alt.value)}
                    onHover={() => setSelectedSuggestionIndex(index + 1)}
                  />
                ))}

              {/* AI Attribution */}
              <div className='px-3 py-1 bg-neutral-50 dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-700'>
                <div className='flex items-center justify-between text-xs text-neutral-500'>
                  <span>🤖 AI Suggestions</span>
                  <span>{suggestions.reasoning}</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* AI Field Description */}
        {fieldAnalysis?.accessibility?.description && (
          <div
            id={`${name}-ai-description`}
            className='text-xs text-neutral-600 dark:text-neutral-400 mt-1'
          >
            {fieldAnalysis.accessibility.description}
          </div>
        )}

        {/* AI Field Instructions */}
        {fieldAnalysis?.accessibility?.instructions && (
          <div className='text-xs text-brand-primary-600 dark:text-brand-primary-400 mt-1'>
            💡 {fieldAnalysis.accessibility.instructions}
          </div>
        )}
      </div>
    );
  }
);

AIInput.displayName = 'AIInput';

export type { AIInputProps, AIInputConfig };
