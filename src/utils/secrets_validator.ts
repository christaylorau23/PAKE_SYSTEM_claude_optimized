/**
 * Centralized Secrets Validation Utility
 * Implements fail-fast pattern for missing secrets - NO FALLBACKS ALLOWED
 *
 * SECURITY POLICY: Application must crash if required secrets are missing
 * This prevents weak REDACTED_SECRET fallbacks and ensures proper secret management
 */

export class SecretsValidator {
  private static readonly REQUIRED_SECRETS = [
    'JWT_SECRET',
    'DB_PASSWORD',
    'REDIS_PASSWORD',
    'PAKE_API_KEY',
    'ANTHROPIC_API_KEY',
    'GEMINI_API_KEY',
    'DID_API_KEY',
    'HEYGEN_API_KEY',
    'WEBHOOK_SECRET',
  ] as const;

  private static readonly WEAK_PATTERNS = [
    'SECURE_WEAK_PASSWORD_REQUIRED',
    'SECURE_DB_PASSWORD_REQUIRED',
    'SECURE_API_KEY_REQUIRED',
    'SECURE_JWT_SECRET_REQUIRED',
    'SECURE_SECRET_KEY_REQUIRED',
    'your-super-secret-jwt-key-change-in-production',
    'default',
    'REDACTED_SECRET',
    'secret',
    'key',
  ];

  /**
   * Validate all required secrets at application startup
   * FAILS FAST if any required secret is missing or weak
   */
  static validateAllSecrets(): void {
    const missingSecrets: string[] = [];
    const weakSecrets: string[] = [];

    for (const secretName of this.REQUIRED_SECRETS) {
      const value = process.env[secretName];

      if (!value) {
        missingSecrets.push(secretName);
      } else if (this.isWeakSecret(value)) {
        weakSecrets.push(secretName);
      }
    }

    if (missingSecrets.length > 0) {
      const error = `CRITICAL SECURITY ERROR: Missing required secrets: ${missingSecrets.join(', ')}.
      Application cannot start without proper secret configuration.`;
      console.error(error);
      process.exit(1);
    }

    if (weakSecrets.length > 0) {
      const error = `CRITICAL SECURITY ERROR: Weak secrets detected: ${weakSecrets.join(', ')}.
      All secrets must be properly configured with strong values.`;
      console.error(error);
      process.exit(1);
    }

    console.log('✅ All secrets validated successfully');
  }

  /**
   * Get a required secret with validation
   * FAILS FAST if secret is missing or weak
   */
  static getRequiredSecret(secretName: string): string {
    const value = process.env[secretName];

    if (!value) {
      const error = `CRITICAL SECURITY ERROR: Required secret '${secretName}' is not configured.
      Application cannot continue without this secret.`;
      console.error(error);
      process.exit(1);
    }

    if (this.isWeakSecret(value)) {
      const error = `CRITICAL SECURITY ERROR: Secret '${secretName}' has a weak value.
      All secrets must be properly configured with strong values.`;
      console.error(error);
      process.exit(1);
    }

    return value;
  }

  /**
   * Get an optional secret (returns null if not set, but validates if set)
   */
  static getOptionalSecret(secretName: string): string | null {
    const value = process.env[secretName];

    if (!value) {
      return null;
    }

    if (this.isWeakSecret(value)) {
      const error = `CRITICAL SECURITY ERROR: Optional secret '${secretName}' has a weak value.
      If configured, secrets must have strong values.`;
      console.error(error);
      process.exit(1);
    }

    return value;
  }

  /**
   * Check if a secret value is weak (matches known weak patterns)
   */
  private static isWeakSecret(value: string): boolean {
    const lowerValue = value.toLowerCase();
    return this.WEAK_PATTERNS.some(pattern =>
      lowerValue.includes(pattern.toLowerCase())
    );
  }

  /**
   * Validate secret strength (minimum requirements)
   */
  static validateSecretStrength(secretName: string, value: string): boolean {
    if (value.length < 16) {
      console.error(
        `SECURITY WARNING: Secret '${secretName}' is too short (minimum 16 characters)`
      );
      return false;
    }

    if (this.isWeakSecret(value)) {
      console.error(
        `SECURITY WARNING: Secret '${secretName}' matches weak pattern`
      );
      return false;
    }

    return true;
  }

  /**
   * Get all configured secrets (for debugging - never log actual values)
   */
  static getConfiguredSecrets(): Record<string, boolean> {
    const result: Record<string, boolean> = {};

    for (const secretName of this.REQUIRED_SECRETS) {
      result[secretName] = !!process.env[secretName];
    }

    return result;
  }
}

/**
 * Initialize secrets validation on module load
 * This ensures the application fails fast if secrets are not properly configured
 */
SecretsValidator.validateAllSecrets();
