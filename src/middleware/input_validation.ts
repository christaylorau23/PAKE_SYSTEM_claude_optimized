/**
 * Input Validation Middleware for PAKE System
 * Prevents injection attacks and ensures data integrity
 *
 * SECURITY POLICY: All inputs must be validated and sanitized before processing
 */

export enum SecurityLevel {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export interface ValidationResult<T = any> {
  isValid: boolean;
  sanitizedValue: T;
  errorMessage?: string;
  securityWarnings: string[];
}

export interface ValidationSchema {
  [field: string]: {
    type: 'string' | 'email' | 'integer' | 'uuid' | 'api_key' | 'json';
    required?: boolean;
    max_length?: number;
    min?: number;
    max?: number;
    allow_html?: boolean;
  };
}

export class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class InputValidator {
  // Dangerous patterns that could indicate injection attempts
  private static readonly DANGEROUS_PATTERNS = [
    // SQL Injection patterns
    /(union|select|insert|update|delete|drop|create|alter|exec|execute)/i,
    /(script|javascript|vbscript|onload|onerror|onclick)/i,
    /(<script|<\/script|javascript:|data:|vbscript:)/i,

    // Command injection patterns
    /[;&|`$(){}[\]\\]/,
    /(cmd|command|shell|bash|sh|powershell)/i,

    // Path traversal patterns
    /\.\.\/|\.\.\\|\.\.%2f|\.\.%5c/,

    // XSS patterns
    /<[^>]*>/,
    /(alert|prompt|confirm|eval|function)/i,

    // LDAP injection patterns
    /[()=*!&|]/,

    // NoSQL injection patterns
    /[$]where|[$]ne|[$]gt|[$]lt|[$]regex/,
  ];

  /**
   * Validate and sanitize string input
   */
  static validateString(
    value: any,
    maxLength: number = 1000,
    securityLevel: SecurityLevel = SecurityLevel.MEDIUM,
    allowHtml: boolean = false
  ): ValidationResult<string> {
    if (typeof value !== 'string') {
      return {
        isValid: false,
        sanitizedValue: '',
        errorMessage: 'Input must be a string',
        securityWarnings: [],
      };
    }

    const warnings: string[] = [];

    // Length validation
    if (value.length > maxLength) {
      return {
        isValid: false,
        sanitizedValue: '',
        errorMessage: `Input exceeds maximum length of ${maxLength} characters`,
        securityWarnings: [],
      };
    }

    // Security pattern detection
    for (const pattern of this.DANGEROUS_PATTERNS) {
      if (pattern.test(value)) {
        if (
          securityLevel === SecurityLevel.HIGH ||
          securityLevel === SecurityLevel.CRITICAL
        ) {
          return {
            isValid: false,
            sanitizedValue: '',
            errorMessage: 'Input contains potentially dangerous content',
            securityWarnings: [],
          };
        } else {
          warnings.push('Input contains potentially dangerous content');
        }
      }
    }

    // HTML sanitization
    let sanitizedValue = value;
    if (!allowHtml) {
      sanitizedValue = this.escapeHtml(value);
      if (sanitizedValue !== value) {
        warnings.push('HTML content was escaped');
      }
    }

    return {
      isValid: true,
      sanitizedValue,
      securityWarnings: warnings,
    };
  }

  /**
   * Validate email address format
   */
  static validateEmail(value: unknown): ValidationResult<string> {
    if (typeof value !== 'string') {
      return {
        isValid: false,
        sanitizedValue: '',
        errorMessage: 'Email must be a string',
        securityWarnings: [],
      };
    }

    // Basic email regex
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailPattern.test(value)) {
      return {
        isValid: false,
        sanitizedValue: '',
        errorMessage: 'Invalid email format',
        securityWarnings: [],
      };
    }

    // Sanitize email
    const sanitizedEmail = value.trim().toLowerCase();

    return {
      isValid: true,
      sanitizedValue: sanitizedEmail,
      securityWarnings: [],
    };
  }

  /**
   * Validate JSON input
   */
  static validateJson(
    value: unknown,
    maxSize: number = 10000
  ): ValidationResult<unknown> {
    let parsedJson: unknown;

    if (typeof value === 'string') {
      try {
        parsedJson = JSON.parse(value);
      } catch (error) {
        return {
          isValid: false,
          sanitizedValue: null,
          errorMessage: `Invalid JSON format: ${error.message}`,
          securityWarnings: [],
        };
      }
    } else if (typeof value === 'object' && value !== null) {
      parsedJson = value;
    } else {
      return {
        isValid: false,
        sanitizedValue: null,
        errorMessage: 'Input must be JSON string or object',
        securityWarnings: [],
      };
    }

    // Size validation
    const jsonStr = JSON.stringify(parsedJson);
    if (jsonStr.length > maxSize) {
      return {
        isValid: false,
        sanitizedValue: null,
        errorMessage: `JSON exceeds maximum size of ${maxSize} characters`,
        securityWarnings: [],
      };
    }

    return {
      isValid: true,
      sanitizedValue: parsedJson,
      securityWarnings: [],
    };
  }

  /**
   * Validate integer input
   */
  static validateInteger(
    value: any,
    minVal?: number,
    maxVal?: number
  ): ValidationResult<number> {
    const intValue = parseInt(value, 10);

    if (isNaN(intValue)) {
      return {
        isValid: false,
        sanitizedValue: 0,
        errorMessage: 'Input must be a valid integer',
        securityWarnings: [],
      };
    }

    if (minVal !== undefined && intValue < minVal) {
      return {
        isValid: false,
        sanitizedValue: 0,
        errorMessage: `Integer must be at least ${minVal}`,
        securityWarnings: [],
      };
    }

    if (maxVal !== undefined && intValue > maxVal) {
      return {
        isValid: false,
        sanitizedValue: 0,
        errorMessage: `Integer must be at most ${maxVal}`,
        securityWarnings: [],
      };
    }

    return {
      isValid: true,
      sanitizedValue: intValue,
      securityWarnings: [],
    };
  }

  /**
   * Validate UUID format
   */
  static validateUuid(value: unknown): ValidationResult<string> {
    if (typeof value !== 'string') {
      return {
        isValid: false,
        sanitizedValue: '',
        errorMessage: 'UUID must be a string',
        securityWarnings: [],
      };
    }

    const uuidPattern =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidPattern.test(value)) {
      return {
        isValid: false,
        sanitizedValue: '',
        errorMessage: 'Invalid UUID format',
        securityWarnings: [],
      };
    }

    return {
      isValid: true,
      sanitizedValue: value.toLowerCase(),
      securityWarnings: [],
    };
  }

  /**
   * Validate API key format
   */
  static validateApiKey(value: unknown): ValidationResult<string> {
    if (typeof value !== 'string') {
      return {
        isValid: false,
        sanitizedValue: '',
        errorMessage: 'API key must be a string',
        securityWarnings: [],
      };
    }

    // API keys should be alphanumeric with some special characters
    const apiKeyPattern = /^[a-zA-Z0-9_-]{20,}$/;
    if (!apiKeyPattern.test(value)) {
      return {
        isValid: false,
        sanitizedValue: '',
        errorMessage: 'Invalid API key format',
        securityWarnings: [],
      };
    }

    return {
      isValid: true,
      sanitizedValue: value,
      securityWarnings: [],
    };
  }

  /**
   * Escape HTML characters
   */
  private static escapeHtml(text: string): string {
    const map: { [key: string]: string } = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;',
    };

    return text.replace(/[&<>"']/g, m => map[m]);
  }
}

export class RequestValidator {
  /**
   * Validate request data against schema
   */
  static validateRequestData(
    data: Record<string, any>,
    schema: ValidationSchema,
    securityLevel: SecurityLevel = SecurityLevel.MEDIUM
  ): ValidationResult<Record<string, any>> {
    const errors: string[] = [];
    const warnings: string[] = [];
    const sanitizedData: Record<string, any> = {};

    for (const [field, rules] of Object.entries(schema)) {
      if (!(field in data)) {
        if (rules.required) {
          errors.push(`Required field '${field}' is missing`);
        }
        continue;
      }

      const value = data[field];
      const fieldType = rules.type;

      let result: ValidationResult<any>;

      // Validate based on field type
      switch (fieldType) {
        case 'string':
          result = InputValidator.validateString(
            value,
            rules.max_length || 1000,
            securityLevel,
            rules.allow_html || false
          );
          break;
        case 'email':
          result = InputValidator.validateEmail(value);
          break;
        case 'integer':
          result = InputValidator.validateInteger(value, rules.min, rules.max);
          break;
        case 'uuid':
          result = InputValidator.validateUuid(value);
          break;
        case 'api_key':
          result = InputValidator.validateApiKey(value);
          break;
        case 'json':
          result = InputValidator.validateJson(value);
          break;
        default:
          errors.push(`Unknown field type '${fieldType}' for field '${field}'`);
          continue;
      }

      if (!result.isValid) {
        errors.push(`Field '${field}': ${result.errorMessage}`);
      } else {
        sanitizedData[field] = result.sanitizedValue;
        warnings.push(
          ...result.securityWarnings.map(w => `Field '${field}': ${w}`)
        );
      }
    }

    if (errors.length > 0) {
      return {
        isValid: false,
        sanitizedValue: {},
        errorMessage: errors.join('; '),
        securityWarnings: warnings,
      };
    }

    return {
      isValid: true,
      sanitizedValue: sanitizedData,
      securityWarnings: warnings,
    };
  }
}

/**
 * Convenience function for input validation
 */
export function validateInput<T = unknown>(
  value: unknown,
  fieldType: 'string' | 'email' | 'integer' | 'uuid' | 'api_key' | 'json',
  options: unknown = {}
): T {
  let result: ValidationResult<T>;

  switch (fieldType) {
    case 'string':
      result = InputValidator.validateString(
        value,
        options.maxLength,
        options.securityLevel,
        options.allowHtml
      );
      break;
    case 'email':
      result = InputValidator.validateEmail(value);
      break;
    case 'integer':
      result = InputValidator.validateInteger(value, options.min, options.max);
      break;
    case 'uuid':
      result = InputValidator.validateUuid(value);
      break;
    case 'api_key':
      result = InputValidator.validateApiKey(value);
      break;
    case 'json':
      result = InputValidator.validateJson(value, options.maxSize);
      break;
    default:
      throw new ValidationError(`Unknown field type: ${fieldType}`);
  }

  if (!result.isValid) {
    throw new ValidationError(result.errorMessage || 'Validation failed');
  }

  // Log security warnings
  for (const warning of result.securityWarnings) {
    console.warn(`Security warning: ${warning}`);
  }

  return result.sanitizedValue;
}
