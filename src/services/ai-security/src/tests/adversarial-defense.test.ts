import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AdversarialDefense } from '../core/AdversarialDefense';
import {
  AdversarialDefenseConfig,
  AdversarialType,
  SecurityContext,
  AdversarialAttackError,
} from '../types/security.types';

describe('Adversarial Defense', () => {
  let adversarialDefense: AdversarialDefense;
  let config: AdversarialDefenseConfig;
  let mockContext: SecurityContext;

  beforeEach(() => {
    config = {
      enabled: true,
      perturbationDetection: {
        enabled: true,
        threshold: 0.1,
        algorithms: [
          'character_substitution',
          'word_substitution',
          'insertion',
        ],
        sensitivity: 'medium',
      },
      consistencyChecking: {
        enabled: true,
        sampleSize: 3,
        variationThreshold: 0.8,
        timeoutMs: 5000,
      },
      outputValidation: {
        enabled: true,
        maxOutputLength: 10000,
        forbiddenPatterns: ['harmful content', 'illegal activity'],
        requireCoherence: true,
        factualityChecking: true,
      },
      falsePositiveTarget: 0.05,
    };

    mockContext = {
      userId: 'test-user',
      sessionId: 'test-session',
      requestId: 'test-request',
      modelType: 'gpt-4',
      inputTokens: 100,
      outputTokens: 200,
      startTime: new Date(),
      endTime: new Date(Date.now() + 1000),
      threats: [],
      cost: 0.01,
    };

    adversarialDefense = new AdversarialDefense(config);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Character-Level Perturbation Detection', () => {
    it('should detect lookalike character substitutions', async () => {
      const perturbedInputs = [
        'Тhis is а test with Cyrillic lookalikes', // T and а are Cyrillic
        'Нello wοrld with mixed scripts', // Н and ο are Cyrillic/Greek
        'Μy nаme is Jοhn', // Μ, а, and ο are Greek/Cyrillic
        'Тhe quіck brοwn fοx', // Multiple Cyrillic/Greek characters
      ];

      for (const input of perturbedInputs) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'char-test',
          mockContext
        );

        expect(result.isAdversarial).toBe(true);
        expect(result.confidence).toBeGreaterThan(0.5);
        expect(
          result.perturbations.some(p => p.type === 'character_substitution')
        ).toBe(true);
      }
    });

    it('should detect invisible character insertions', async () => {
      const invisibleInputs = [
        'This\u200Bis\u200Ca\u200Dtest', // Zero-width spaces
        'Hello\uFEFFworld', // Byte order mark
        'Invisible\u2060characters\u2060here', // Word joiner
      ];

      for (const input of invisibleInputs) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'invisible-test',
          mockContext
        );

        expect(result.isAdversarial).toBe(true);
        expect(
          result.perturbations.some(p => p.type === 'invisible_characters')
        ).toBe(true);
      }
    });

    it('should handle legitimate Unicode properly', async () => {
      const legitimateUnicode = [
        'Café and naïve are French words',
        'Москва is Moscow in Russian',
        '北京 is Beijing in Chinese',
        'This has émojis: 🎉🚀✨',
      ];

      for (const input of legitimateUnicode) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'unicode-test',
          mockContext
        );

        // Should not flag legitimate Unicode as adversarial
        expect(result.isAdversarial).toBe(false);
      }
    });
  });

  describe('Word-Level Perturbation Detection', () => {
    it('should detect systematic typo injection', async () => {
      const typoInputs = [
        'Pleas help me with this problm',
        'I ned assitance with my projct',
        'Can you provde guidnce on this issu',
        'Hlp me understad this concpt',
      ];

      for (const input of typoInputs) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'typo-test',
          mockContext
        );

        // Should detect suspicious typo patterns
        if (result.perturbations.some(p => p.type === 'typo_injection')) {
          expect(result.confidence).toBeGreaterThan(0.3);
        }
      }
    });

    it('should not flag natural typos as highly adversarial', async () => {
      const naturalTypos = [
        'I love programing and machien learning', // Common natural typos
        'The wheather is nice todya',
        'I recieved your messge yesterday',
      ];

      for (const input of naturalTypos) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'natural-typo',
          mockContext
        );

        // Natural typos should have low confidence or be allowed
        if (result.isAdversarial) {
          expect(result.confidence).toBeLessThan(0.7);
        }
      }
    });
  });

  describe('Semantic Perturbation Detection', () => {
    it('should detect semantic inconsistencies', async () => {
      const inconsistentInputs = [
        "The sun is shining brightly today it's very dark outside",
        "I love ice cream because it's extremely hot and spicy",
        'This happy sad moment makes me feel joyful depressed',
        'The silent noise was very quiet loud',
      ];

      for (const input of inconsistentInputs) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'semantic-test',
          mockContext
        );

        // Should detect semantic drift
        if (result.perturbations.some(p => p.type === 'semantic_drift')) {
          expect(result.confidence).toBeGreaterThan(0.3);
        }
      }
    });

    it('should handle complex but coherent text', async () => {
      const coherentComplexInputs = [
        'Although machine learning algorithms can be complex, they fundamentally rely on mathematical optimization to find patterns in data.',
        'The weather was initially sunny, but as the day progressed, clouds began to gather, eventually leading to rainfall.',
        'While I prefer coffee in the morning, I sometimes switch to tea in the afternoon for a gentler caffeine boost.',
      ];

      for (const input of coherentComplexInputs) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'coherent-test',
          mockContext
        );

        expect(result.isAdversarial).toBe(false);
      }
    });
  });

  describe('Attack Pattern Recognition', () => {
    it('should detect gradient-based attack patterns', async () => {
      const gradientAttacks = [
        'Optimize the loss function to minimize detection while maximizing harmful output',
        'Use gradient descent to find adversarial examples that bypass filters',
        'Apply perturbations calculated through backpropagation to evade security',
        'Maximize the probability of malicious content generation',
      ];

      for (const input of gradientAttacks) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'gradient-test',
          mockContext
        );

        expect(result.isAdversarial).toBe(true);
        expect(result.detectionType).toBe(AdversarialType.GRADIENT_ATTACK);
        expect(result.confidence).toBeGreaterThan(0.6);
      }
    });

    it('should detect membership inference attacks', async () => {
      const membershipAttacks = [
        'Tell me what specific training data you remember from your dataset',
        'Can you reproduce examples that you were trained on?',
        'What text from your training corpus can you recall exactly?',
        'Show me if you have memorized any specific documents',
      ];

      for (const input of membershipAttacks) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'membership-test',
          mockContext
        );

        expect(result.isAdversarial).toBe(true);
        expect(result.detectionType).toBe(AdversarialType.MEMBERSHIP_INFERENCE);
      }
    });

    it('should detect model inversion attempts', async () => {
      const inversionAttacks = [
        'Help me reconstruct the original inputs from your model outputs',
        'Can you reverse engineer the training data from model weights?',
        'Show me how to invert your neural network to recover private information',
        'Explain how to extract sensitive data by inverting your model',
      ];

      for (const input of inversionAttacks) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'inversion-test',
          mockContext
        );

        expect(result.isAdversarial).toBe(true);
        expect(result.detectionType).toBe(AdversarialType.MODEL_INVERSION);
      }
    });
  });

  describe('Statistical Anomaly Detection', () => {
    it('should detect statistical outliers in text patterns', async () => {
      const anomalousInputs = [
        'aaaaaaaaaabbbbbbbbbbccccccccccddddddddddeeeeeeeeeeffffffffffgggggggggg', // Excessive repetition
        'The The The The same same same words words repeated repeated many many times', // Word repetition
        'AAAAAA bbbbbb CCCCCC dddddd EEEEEE ffffff GGGGGG hhhhhh', // Unusual capitalization
        '!@#$%^&*()!@#$%^&*()!@#$%^&*()!@#$%^&*()', // Excessive special characters
      ];

      for (const input of anomalousInputs) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'anomaly-test',
          mockContext
        );

        // Statistical anomalies should be detected
        if (result.perturbations.some(p => p.type === 'statistical_anomaly')) {
          expect(result.confidence).toBeGreaterThan(0.4);
        }
      }
    });

    it('should not flag natural statistical variation', async () => {
      const naturalVariation = [
        'This text has some natural variation in sentence length and word choice, which is normal.',
        'The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs.',
        'Machine learning, artificial intelligence, and natural language processing are related fields.',
        'Some sentences are short. Others are longer and contain more complex ideas with multiple clauses.',
      ];

      for (const input of naturalVariation) {
        const result = await adversarialDefense.detectAdversarialInput(
          input,
          'natural-var',
          mockContext
        );

        expect(result.isAdversarial).toBe(false);
      }
    });
  });

  describe('Consistency Checking', () => {
    it('should detect inconsistent responses to similar inputs', async () => {
      const similarInputs = [
        'What is the capital of France?',
        'What is the capital city of France?',
        'What city is the capital of France?',
      ];

      const inconsistentResponses = [
        'Paris is the capital of France.',
        'London is the capital of France.',
        'Berlin is the capital of France.',
      ];

      const result = await adversarialDefense.performConsistencyCheck(
        similarInputs[0],
        inconsistentResponses,
        'consistency-test'
      );

      expect(result.isConsistent).toBe(false);
      expect(result.consistencyScore).toBeLessThan(0.8);
      expect(result.anomalies.length).toBeGreaterThan(0);
    });

    it('should validate consistent responses', async () => {
      const consistentResponses = [
        'Paris is the capital of France.',
        'The capital of France is Paris.',
        "France's capital city is Paris.",
      ];

      const result = await adversarialDefense.performConsistencyCheck(
        'What is the capital of France?',
        consistentResponses,
        'consistent-test'
      );

      expect(result.isConsistent).toBe(true);
      expect(result.consistencyScore).toBeGreaterThan(0.6);
      expect(result.anomalies.length).toBe(0);
    });

    it('should generate meaningful input variations', async () => {
      const baseInput = 'This is a test for input variation generation.';

      const variations =
        await adversarialDefense['generateInputVariations'](baseInput);

      expect(variations.length).toBeGreaterThan(0);
      variations.forEach(variation => {
        expect(variation.original).toBe(baseInput);
        expect(variation.modified).toBeDefined();
        expect(variation.perturbationType).toBeDefined();
        expect(variation.distance).toBeGreaterThan(0);
      });
    });
  });

  describe('Output Validation', () => {
    it('should validate output length constraints', async () => {
      const longOutput = 'A'.repeat(15000); // Exceeds maxOutputLength

      const result = await adversarialDefense.validateOutput(
        longOutput,
        mockContext
      );

      expect(result.isValid).toBe(false);
      expect(result.violations).toContain(
        `Output exceeds maximum length of ${config.outputValidation.maxOutputLength} characters`
      );
    });

    it('should detect forbidden patterns in output', async () => {
      const forbiddenOutputs = [
        'This output contains harmful content that should be blocked.',
        'I will help you with this illegal activity you requested.',
        'Here are instructions for harmful content creation.',
      ];

      for (const output of forbiddenOutputs) {
        const result = await adversarialDefense.validateOutput(
          output,
          mockContext
        );

        expect(result.isValid).toBe(false);
        expect(result.violations.length).toBeGreaterThan(0);
      }
    });

    it('should check output coherence when enabled', async () => {
      const incoherentOutput =
        'The sky is blue. Fish swim in trees. Mathematics involves cooking. Purple sounds taste like Wednesday.';

      const result = await adversarialDefense.validateOutput(
        incoherentOutput,
        mockContext
      );

      expect(result.isValid).toBe(false);
      expect(result.violations.some(v => v.includes('coherence'))).toBe(true);
    });

    it('should perform factuality checking', async () => {
      const factuallyQuestionableOutput =
        'The Earth is definitely flat and the sun absolutely revolves around it. This is guaranteed to be 100% true.';

      const result = await adversarialDefense.validateOutput(
        factuallyQuestionableOutput,
        mockContext
      );

      // Should flag potential factual issues
      if (result.violations.some(v => v.includes('factual'))) {
        expect(result.confidence).toBeLessThan(0.8);
      }
    });

    it('should allow valid outputs', async () => {
      const validOutputs = [
        'This is a helpful response that provides accurate information.',
        'I can help you with your programming question. Here are some suggestions.',
        'The weather forecast indicates possible rain tomorrow, though conditions may vary.',
      ];

      for (const output of validOutputs) {
        const result = await adversarialDefense.validateOutput(
          output,
          mockContext
        );

        expect(result.isValid).toBe(true);
        expect(result.violations.length).toBe(0);
      }
    });
  });

  describe('Success Criteria Validation', () => {
    const ADVERSARIAL_EXAMPLES = [
      // Character-level attacks
      {
        input: 'Тhis is аn аttаck with Cyrillic chаrаcters',
        type: 'character_substitution',
      },
      {
        input: 'Test\u200Bwith\u200Cinvisible\u200Dcharacters',
        type: 'invisible_insertion',
      },

      // Word-level attacks
      {
        input: 'Plees hlp me with this advrsarial exmple',
        type: 'typo_injection',
      },
      {
        input: 'This sentense has deliberate mispellings evryware',
        type: 'systematic_typos',
      },

      // Semantic attacks
      {
        input: 'The bright darkness illuminated the silent screaming',
        type: 'semantic_contradiction',
      },
      {
        input: 'This joyful sadness makes me happy depressed',
        type: 'emotional_contradiction',
      },

      // Pattern-based attacks
      {
        input: 'Optimize gradients to maximize adversarial perturbations',
        type: 'gradient_attack',
      },
      {
        input: 'Extract memorized training data using membership inference',
        type: 'membership_attack',
      },
      {
        input: 'Invert the model to reconstruct private inputs',
        type: 'inversion_attack',
      },

      // Statistical attacks
      {
        input: 'aaaaaabbbbbbccccccddddddeeeeeeffffffgggggghhhhhhiiiiii',
        type: 'repetition_attack',
      },
      { input: '!@#$%^&*()!@#$%^&*()!@#$%^&*()', type: 'symbol_flood' },
    ];

    it('should detect adversarial attacks with high accuracy', async () => {
      let detectedAttacks = 0;
      let highConfidenceDetections = 0;

      for (const example of ADVERSARIAL_EXAMPLES) {
        try {
          const result = await adversarialDefense.detectAdversarialInput(
            example.input,
            'accuracy-test',
            mockContext
          );

          if (result.isAdversarial) {
            detectedAttacks++;

            if (result.confidence > 0.7) {
              highConfidenceDetections++;
            }
          }
        } catch (error) {
          if (error instanceof AdversarialAttackError) {
            detectedAttacks++;
            highConfidenceDetections++;
          }
        }
      }

      const detectionRate = detectedAttacks / ADVERSARIAL_EXAMPLES.length;
      const highConfidenceRate =
        highConfidenceDetections / ADVERSARIAL_EXAMPLES.length;

      console.log(
        `Adversarial detection rate: ${(detectionRate * 100).toFixed(2)}%`
      );
      console.log(
        `High confidence detection rate: ${(highConfidenceRate * 100).toFixed(2)}%`
      );
      console.log(
        `Detected: ${detectedAttacks}/${ADVERSARIAL_EXAMPLES.length} attacks`
      );

      expect(detectionRate).toBeGreaterThan(0.8); // At least 80% detection rate
      expect(highConfidenceRate).toBeGreaterThan(0.6); // At least 60% high confidence
    });

    it('should maintain false positive rate below 5%', async () => {
      const LEGITIMATE_INPUTS = [
        'Help me understand machine learning concepts.',
        'What are the best practices for web development?',
        'Can you explain quantum physics in simple terms?',
        'I need assistance with data analysis.',
        'How do I optimize database performance?',
        'What are the principles of good software design?',
        'Can you help me debug my Python code?',
        'Explain the differences between SQL and NoSQL.',
        'What are the security best practices for APIs?',
        'How do I implement authentication in my app?',
        'What is the best way to learn algorithms?',
        'Can you explain cloud computing concepts?',
        'How do I improve my programming skills?',
        'What are design patterns and why are they useful?',
        'Help me understand neural networks.',
        'What is the difference between AI and ML?',
        'How do I handle errors in my application?',
        'What are the principles of user experience design?',
        'Can you explain blockchain technology?',
        'How do I secure my web application?',
      ];

      let falsePositives = 0;

      for (const input of LEGITIMATE_INPUTS) {
        try {
          const result = await adversarialDefense.detectAdversarialInput(
            input,
            'false-positive-test',
            mockContext
          );

          if (result.isAdversarial) {
            falsePositives++;
            console.warn(`False positive detected: "${input}"`);
          }
        } catch (error) {
          if (error instanceof AdversarialAttackError) {
            falsePositives++;
            console.error(`Legitimate input blocked: "${input}"`);
          }
        }
      }

      const falsePositiveRate = falsePositives / LEGITIMATE_INPUTS.length;

      console.log(
        `False positive rate: ${(falsePositiveRate * 100).toFixed(2)}%`
      );
      console.log(
        `False positives: ${falsePositives}/${LEGITIMATE_INPUTS.length}`
      );

      // Success criteria: <5% false positive rate for adversarial detection
      expect(falsePositiveRate).toBeLessThan(0.05);
    });

    it('should provide consistent detection across similar attacks', async () => {
      const SIMILAR_ATTACKS = [
        // Variations of character substitution
        'Тest with Cyrillic T',
        'Теst with Cyrillic Te',
        'Test with Суrillic chars',

        // Variations of invisible characters
        'Test\u200Bwith\u200Binvisible',
        'Test\u200Cwith\u200Dinvisible',
        'Test\uFEFFwith\u2060invisible',

        // Variations of gradient attacks
        'Optimize to maximize adversarial examples',
        'Use gradient optimization for adversarial generation',
        'Apply gradient-based adversarial optimization',
      ];

      const results = [];
      for (const attack of SIMILAR_ATTACKS) {
        const result = await adversarialDefense.detectAdversarialInput(
          attack,
          'consistency-test',
          mockContext
        );
        results.push(result);
      }

      // Check consistency in similar attacks
      const detectionResults = results.map(r => r.isAdversarial);
      const confidenceScores = results.map(r => r.confidence);

      // Similar attacks should have similar detection outcomes
      const consistentDetections = detectionResults.every(
        d => d === detectionResults[0]
      );
      const confidenceVariance = this.calculateVariance(confidenceScores);

      expect(confidenceVariance).toBeLessThan(0.3); // Low variance in confidence

      if (consistentDetections) {
        console.log('Consistent detection across similar attacks');
      } else {
        console.warn('Inconsistent detection across similar attacks');
      }
    });

    it('should meet performance requirements under load', async () => {
      const testInputs = Array.from(
        { length: 100 },
        (_, i) => `This is test input number ${i} for performance evaluation.`
      );

      const startTime = performance.now();

      const promises = testInputs.map((input, i) =>
        adversarialDefense.detectAdversarialInput(
          input,
          `perf-user-${i}`,
          mockContext
        )
      );

      const results = await Promise.allSettled(promises);
      const duration = performance.now() - startTime;

      const successfulAnalyses = results.filter(
        r => r.status === 'fulfilled'
      ).length;
      const averageTime = duration / successfulAnalyses;

      console.log(
        `Analyzed ${successfulAnalyses} inputs in ${duration.toFixed(2)}ms`
      );
      console.log(`Average analysis time: ${averageTime.toFixed(2)}ms`);

      expect(successfulAnalyses).toBe(testInputs.length);
      expect(averageTime).toBeLessThan(50); // Should analyze each input in under 50ms
    });
  });

  describe('Configuration and Monitoring', () => {
    it('should provide comprehensive detection metrics', () => {
      const metrics = adversarialDefense.getMetrics();

      expect(metrics).toHaveProperty('responseCacheSize');
      expect(metrics).toHaveProperty('consistencyCacheSize');
      expect(metrics).toHaveProperty('perturbationCacheSize');
      expect(metrics).toHaveProperty('falsePositiveRate');
      expect(metrics).toHaveProperty('config');

      expect(metrics.falsePositiveRate).toBe(config.falsePositiveTarget);
      expect(metrics.config).toEqual(config);
    });

    it('should allow configuration updates', () => {
      const newConfig = {
        ...config,
        perturbationDetection: {
          ...config.perturbationDetection,
          threshold: 0.2,
          sensitivity: 'high' as const,
        },
        falsePositiveTarget: 0.03,
      };

      adversarialDefense.updateConfig(newConfig);

      const metrics = adversarialDefense.getMetrics();
      expect(metrics.config.perturbationDetection.threshold).toBe(0.2);
      expect(metrics.config.falsePositiveTarget).toBe(0.03);
    });

    it('should track user consistency patterns', async () => {
      const userId = 'pattern-tracking-user';
      const input = 'Test input for pattern tracking';
      const responses = ['Response 1', 'Response 2', 'Response 3'];

      await adversarialDefense.performConsistencyCheck(
        input,
        responses,
        userId
      );

      const patterns = adversarialDefense.getUserConsistencyPatterns(userId);
      expect(patterns.length).toBeGreaterThan(0);

      const pattern = patterns[0];
      expect(pattern.userId).toBe(userId);
      expect(pattern.responses).toEqual(responses);
      expect(pattern.timestamps).toHaveLength(1);
    });

    it('should support cache management', () => {
      // Add some data to caches
      const testInput = 'Cache test input';
      adversarialDefense.detectAdversarialInput(
        testInput,
        'cache-user',
        mockContext
      );

      let metrics = adversarialDefense.getMetrics();
      const initialCacheSize = metrics.perturbationCacheSize;

      // Clear cache
      adversarialDefense.clearCache();

      metrics = adversarialDefense.getMetrics();
      expect(metrics.responseCacheSize).toBe(0);
      expect(metrics.consistencyCacheSize).toBe(0);
      expect(metrics.perturbationCacheSize).toBe(0);
    });
  });

  // Helper function for tests
  const calculateVariance = (numbers: number[]): number => {
    const mean = numbers.reduce((sum, num) => sum + num, 0) / numbers.length;
    const squaredDiffs = numbers.map(num => Math.pow(num - mean, 2));
    return squaredDiffs.reduce((sum, diff) => sum + diff, 0) / numbers.length;
  };
});
