/**
 * Unit Tests for FeatureFlags System
 */

import {
  FeatureFlags,
  FeatureFlagType,
  FeatureFlagDefinition,
  agentRuntimeFlags,
  flags,
  loadFeatureFlags,
} from '../../../config/FeatureFlags';

describe('FeatureFlags System', () => {
  let testFlags: FeatureFlags;

  beforeEach(() => {
    testFlags = new FeatureFlags();

    // Clear test environment variables
    delete process.env.FEATURE_TEST_BOOLEAN;
    delete process.env.FEATURE_TEST_NUMBER;
    delete process.env.FEATURE_TEST_STRING;
    delete process.env.FEATURE_TEST_JSON;
    delete process.env.FEATURE_TEST_PERCENTAGE;
  });

  afterEach(() => {
    // Clean up environment variables
    delete process.env.FEATURE_TEST_BOOLEAN;
    delete process.env.FEATURE_TEST_NUMBER;
    delete process.env.FEATURE_TEST_STRING;
    delete process.env.FEATURE_TEST_JSON;
    delete process.env.FEATURE_TEST_PERCENTAGE;
  });

  describe('Feature Flag Registration', () => {
    it('should register a single feature flag', () => {
      const flag: FeatureFlagDefinition<boolean> = {
        key: 'TEST_FLAG',
        type: FeatureFlagType.BOOLEAN,
        defaultValue: false,
        description: 'Test flag for unit testing',
      };

      testFlags.register(flag);

      const definitions = testFlags.getDefinitions();
      expect(definitions).toHaveLength(1);
      expect(definitions[0].key).toBe('TEST_FLAG');
    });

    it('should register multiple feature flags', () => {
      const flagDefinitions: FeatureFlagDefinition[] = [
        {
          key: 'FLAG_1',
          type: FeatureFlagType.BOOLEAN,
          defaultValue: true,
          description: 'First test flag',
        },
        {
          key: 'FLAG_2',
          type: FeatureFlagType.STRING,
          defaultValue: 'default',
          description: 'Second test flag',
        },
      ];

      testFlags.registerAll(flagDefinitions);

      const definitions = testFlags.getDefinitions();
      expect(definitions).toHaveLength(2);
    });

    it('should handle flag overwriting', () => {
      const flag1: FeatureFlagDefinition<string> = {
        key: 'DUPLICATE_FLAG',
        type: FeatureFlagType.STRING,
        defaultValue: 'original',
        description: 'Original flag',
      };

      const flag2: FeatureFlagDefinition<string> = {
        key: 'DUPLICATE_FLAG',
        type: FeatureFlagType.STRING,
        defaultValue: 'updated',
        description: 'Updated flag',
      };

      testFlags.register(flag1);
      testFlags.register(flag2);

      const result = testFlags.evaluate('DUPLICATE_FLAG');
      expect(result.value).toBe('updated');
    });
  });

  describe('Boolean Flags', () => {
    beforeEach(() => {
      testFlags.register({
        key: 'TEST_BOOLEAN',
        type: FeatureFlagType.BOOLEAN,
        defaultValue: false,
        description: 'Boolean test flag',
      });
    });

    it('should return default value when no environment variable', () => {
      const result = testFlags.evaluate('TEST_BOOLEAN');

      expect(result.value).toBe(false);
      expect(result.source).toBe('default');
    });

    it('should parse boolean from environment variable (true)', () => {
      process.env.FEATURE_TEST_BOOLEAN = 'true';

      const result = testFlags.evaluate('TEST_BOOLEAN');

      expect(result.value).toBe(true);
      expect(result.source).toBe('environment');
    });

    it('should parse boolean from environment variable (1)', () => {
      process.env.FEATURE_TEST_BOOLEAN = '1';

      const result = testFlags.evaluate('TEST_BOOLEAN');

      expect(result.value).toBe(true);
      expect(result.source).toBe('environment');
    });

    it('should parse boolean from environment variable (false)', () => {
      process.env.FEATURE_TEST_BOOLEAN = 'false';

      const result = testFlags.evaluate('TEST_BOOLEAN');

      expect(result.value).toBe(false);
      expect(result.source).toBe('environment');
    });

    it('should support isEnabled convenience method', () => {
      process.env.FEATURE_TEST_BOOLEAN = 'true';

      const enabled = testFlags.isEnabled('TEST_BOOLEAN');

      expect(enabled).toBe(true);
    });
  });

  describe('Number Flags', () => {
    beforeEach(() => {
      testFlags.register({
        key: 'TEST_NUMBER',
        type: FeatureFlagType.NUMBER,
        defaultValue: 42,
        description: 'Number test flag',
      });
    });

    it('should return default number value', () => {
      const result = testFlags.evaluate<number>('TEST_NUMBER');

      expect(result.value).toBe(42);
      expect(result.source).toBe('default');
    });

    it('should parse number from environment variable', () => {
      process.env.FEATURE_TEST_NUMBER = '100';

      const result = testFlags.evaluate<number>('TEST_NUMBER');

      expect(result.value).toBe(100);
      expect(result.source).toBe('environment');
    });

    it('should handle decimal numbers', () => {
      process.env.FEATURE_TEST_NUMBER = '3.14';

      const result = testFlags.evaluate<number>('TEST_NUMBER');

      expect(result.value).toBe(3.14);
      expect(result.source).toBe('environment');
    });

    it('should handle negative numbers', () => {
      process.env.FEATURE_TEST_NUMBER = '-25';

      const result = testFlags.evaluate<number>('TEST_NUMBER');

      expect(result.value).toBe(-25);
      expect(result.source).toBe('environment');
    });
  });

  describe('String Flags', () => {
    beforeEach(() => {
      testFlags.register({
        key: 'TEST_STRING',
        type: FeatureFlagType.STRING,
        defaultValue: 'default_value',
        description: 'String test flag',
      });
    });

    it('should return default string value', () => {
      const result = testFlags.evaluate<string>('TEST_STRING');

      expect(result.value).toBe('default_value');
      expect(result.source).toBe('default');
    });

    it('should return environment string value', () => {
      process.env.FEATURE_TEST_STRING = 'env_value';

      const result = testFlags.evaluate<string>('TEST_STRING');

      expect(result.value).toBe('env_value');
      expect(result.source).toBe('environment');
    });

    it('should handle empty string values', () => {
      process.env.FEATURE_TEST_STRING = '';

      const result = testFlags.evaluate<string>('TEST_STRING');

      expect(result.value).toBe('');
      expect(result.source).toBe('environment');
    });
  });

  describe('JSON Flags', () => {
    beforeEach(() => {
      testFlags.register({
        key: 'TEST_JSON',
        type: FeatureFlagType.JSON,
        defaultValue: { default: true },
        description: 'JSON test flag',
      });
    });

    it('should return default JSON value', () => {
      const result = testFlags.evaluate('TEST_JSON');

      expect(result.value).toEqual({ default: true });
      expect(result.source).toBe('default');
    });

    it('should parse JSON from environment variable', () => {
      process.env.FEATURE_TEST_JSON = '{"enabled": true, "count": 5}';

      const result = testFlags.evaluate('TEST_JSON');

      expect(result.value).toEqual({ enabled: true, count: 5 });
      expect(result.source).toBe('environment');
    });

    it('should handle arrays in JSON', () => {
      process.env.FEATURE_TEST_JSON = '["item1", "item2", "item3"]';

      const result = testFlags.evaluate('TEST_JSON');

      expect(result.value).toEqual(['item1', 'item2', 'item3']);
      expect(result.source).toBe('environment');
    });
  });

  describe('Percentage Flags', () => {
    beforeEach(() => {
      testFlags.register({
        key: 'TEST_PERCENTAGE',
        type: FeatureFlagType.PERCENTAGE,
        defaultValue: 50,
        description: 'Percentage test flag',
      });
    });

    it('should use percentage rollout with user context', () => {
      process.env.FEATURE_TEST_PERCENTAGE = '25';

      // Test multiple users to verify percentage behavior
      const users = Array.from({ length: 100 }, (_, i) => `user_${i}`);
      const enabledCount = users.filter((userId) => {
        const result = testFlags.evaluate('TEST_PERCENTAGE', { userId });
        return result.value === true && result.source === 'percentage';
      }).length;

      // Should be approximately 25% (allowing for hash distribution variance)
      expect(enabledCount).toBeWithinRange(15, 35);
    });

    it('should be consistent for same user', () => {
      process.env.FEATURE_TEST_PERCENTAGE = '75';

      const result1 = testFlags.evaluate('TEST_PERCENTAGE', { userId: 'consistent_user' });
      const result2 = testFlags.evaluate('TEST_PERCENTAGE', { userId: 'consistent_user' });

      expect(result1.value).toBe(result2.value);
      expect(result1.source).toBe(result2.source);
    });

    it('should handle 0% and 100% edge cases', () => {
      // Test 0%
      process.env.FEATURE_TEST_PERCENTAGE = '0';
      const result0 = testFlags.evaluate('TEST_PERCENTAGE', { userId: 'test_user' });
      expect(result0.value).toBe(false);

      // Test 100%
      process.env.FEATURE_TEST_PERCENTAGE = '100';
      const result100 = testFlags.evaluate('TEST_PERCENTAGE', { userId: 'test_user' });
      expect(result100.value).toBe(true);
    });
  });

  describe('Runtime Overrides', () => {
    beforeEach(() => {
      testFlags.register({
        key: 'OVERRIDE_TEST',
        type: FeatureFlagType.BOOLEAN,
        defaultValue: false,
        description: 'Override test flag',
      });
    });

    it('should use override value', () => {
      testFlags.setOverride('OVERRIDE_TEST', true);

      const result = testFlags.evaluate('OVERRIDE_TEST');

      expect(result.value).toBe(true);
      expect(result.source).toBe('override');
    });

    it('should override environment values', () => {
      process.env.FEATURE_OVERRIDE_TEST = 'true';
      testFlags.setOverride('OVERRIDE_TEST', false);

      const result = testFlags.evaluate('OVERRIDE_TEST');

      expect(result.value).toBe(false);
      expect(result.source).toBe('override');
    });

    it('should remove overrides', () => {
      testFlags.setOverride('OVERRIDE_TEST', true);
      testFlags.removeOverride('OVERRIDE_TEST');

      const result = testFlags.evaluate('OVERRIDE_TEST');

      expect(result.value).toBe(false);
      expect(result.source).toBe('default');
    });

    it('should clear all overrides', () => {
      testFlags.setOverride('OVERRIDE_TEST', true);
      testFlags.clearOverrides();

      const result = testFlags.evaluate('OVERRIDE_TEST');

      expect(result.value).toBe(false);
      expect(result.source).toBe('default');
    });
  });

  describe('Validation', () => {
    it('should apply custom validators', () => {
      testFlags.register({
        key: 'VALIDATED_FLAG',
        type: FeatureFlagType.NUMBER,
        defaultValue: 5,
        description: 'Validated flag',
        validator: (value: number) => value > 0 && value < 100,
      });

      process.env.FEATURE_VALIDATED_FLAG = '150'; // Invalid value

      const result = testFlags.evaluate<number>('VALIDATED_FLAG');

      // Should fall back to default due to validation failure
      expect(result.value).toBe(5);
      expect(result.source).toBe('default');
    });

    it('should validate entire configuration', () => {
      testFlags.register({
        key: 'INVALID_FLAG',
        type: FeatureFlagType.NUMBER,
        defaultValue: 10,
        description: 'Flag with invalid env value',
      });

      process.env.FEATURE_INVALID_FLAG = 'not_a_number';

      const validation = testFlags.validateConfiguration();

      expect(validation.valid).toBe(false);
      expect(validation.errors.length).toBeGreaterThan(0);
      expect(validation.errors[0]).toContain('INVALID_FLAG');
    });
  });

  describe('Evaluation Logging', () => {
    beforeEach(() => {
      testFlags.register({
        key: 'LOGGED_FLAG',
        type: FeatureFlagType.BOOLEAN,
        defaultValue: true,
        description: 'Flag for logging tests',
      });
    });

    it('should log flag evaluations', () => {
      testFlags.evaluate('LOGGED_FLAG');

      const log = testFlags.getEvaluationLog();

      expect(log.length).toBe(1);
      expect(log[0].key).toBe('LOGGED_FLAG');
      expect(log[0].value).toBe(true);
      expect(log[0].source).toBe('default');
      expect(log[0].timestamp).toBeTruthy();
    });

    it('should include context in evaluation log', () => {
      const context = { userId: 'test_user', requestId: 'req_123' };

      testFlags.evaluate('LOGGED_FLAG', context);

      const log = testFlags.getEvaluationLog();

      expect(log[0].context).toEqual(context);
    });
  });

  describe('Error Handling', () => {
    it('should throw error for unregistered flag', () => {
      expect(() => testFlags.evaluate('NONEXISTENT_FLAG')).toThrow(
        "Feature flag 'NONEXISTENT_FLAG' is not registered"
      );
    });

    it('should handle malformed JSON gracefully', () => {
      testFlags.register({
        key: 'MALFORMED_JSON',
        type: FeatureFlagType.JSON,
        defaultValue: {},
        description: 'Malformed JSON test',
      });

      process.env.FEATURE_MALFORMED_JSON = '{invalid json}';

      const validation = testFlags.validateConfiguration();

      expect(validation.valid).toBe(false);
      expect(validation.errors[0]).toContain('Invalid JSON value');
    });
  });

  describe('Configuration Management', () => {
    beforeEach(() => {
      testFlags.register({
        key: 'CONFIG_FLAG',
        type: FeatureFlagType.STRING,
        defaultValue: 'default',
        description: 'Configuration test flag',
      });
    });

    it('should provide configuration overview', () => {
      process.env.FEATURE_CONFIG_FLAG = 'env_value';
      testFlags.setOverride('CONFIG_FLAG', 'override_value');

      const config = testFlags.getConfiguration();

      expect(config.CONFIG_FLAG).toBeDefined();
      expect(config.CONFIG_FLAG.defaultValue).toBe('default');
      expect(config.CONFIG_FLAG.environmentValue).toBe('env_value');
      expect(config.CONFIG_FLAG.override).toBe('override_value');
      expect(config.CONFIG_FLAG.currentValue).toBe('override_value');
    });

    it('should support custom environment variable names', () => {
      testFlags.register({
        key: 'CUSTOM_ENV_FLAG',
        type: FeatureFlagType.BOOLEAN,
        defaultValue: false,
        description: 'Custom env var flag',
        envVar: 'CUSTOM_FEATURE_VAR',
      });

      process.env.CUSTOM_FEATURE_VAR = 'true';

      const result = testFlags.evaluate('CUSTOM_ENV_FLAG');

      expect(result.value).toBe(true);
      expect(result.source).toBe('environment');
    });
  });

  describe('Agent Runtime Integration', () => {
    it('should have default agent runtime flags registered', () => {
      const definitions = agentRuntimeFlags.getDefinitions();

      expect(definitions.length).toBeGreaterThan(0);

      const flagKeys = definitions.map((def) => def.key);
      expect(flagKeys).toContain('AGENT_RUNTIME_ENABLED');
      expect(flagKeys).toContain('NULL_PROVIDER_ENABLED');
      expect(flagKeys).toContain('CONCURRENT_TASK_LIMIT');
    });

    it('should provide convenience flag functions', () => {
      expect(typeof flags.isAgentRuntimeEnabled).toBe('function');
      expect(typeof flags.isNullProviderEnabled).toBe('function');
      expect(typeof flags.getConcurrentTaskLimit).toBe('function');

      // Test actual functionality
      expect(flags.isAgentRuntimeEnabled()).toBe(true);
      expect(flags.getConcurrentTaskLimit()).toBeGreaterThan(0);
    });

    it('should validate configuration on load', () => {
      const result = loadFeatureFlags();

      expect(typeof result.success).toBe('boolean');
      expect(Array.isArray(result.errors)).toBe(true);
    });
  });
});
