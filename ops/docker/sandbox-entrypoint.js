#!/usr/bin/env node

/**
 * PAKE Agent Sandbox - Secure Entry Point
 *
 * Security-hardened entry point for containerized agent execution.
 * Implements comprehensive safety controls and monitoring.
 */

const fs = require('fs');
const path = require('path');
const { spawn, execSync } = require('child_process');
const process = require('process');

// Security configuration
const SECURITY_CONFIG = {
  maxExecutionTime: parseInt(process.env.EXECUTION_TIMEOUT) * 1000 || 60000,
  maxMemoryMB: parseInt(process.env.MEMORY_LIMIT?.replace('m', '')) || 512,
  maxProcesses: parseInt(process.env.PROCESS_LIMIT) || 32,
  redactSecrets: process.env.REDACT_SECRETS === 'true',
  sandboxMode: process.env.SANDBOX_MODE || 'strict',
  logAllCommands: process.env.LOG_ALL_COMMANDS === 'true',
};

// Logging utilities
const log = (level, message, context = {}) => {
  const timestamp = new Date().toISOString();
  const logEntry = {
    timestamp,
    level,
    message,
    component: 'sandbox-entrypoint',
    pid: process.pid,
    ...context,
  };

  console.log(JSON.stringify(logEntry));

  // Also write to file for audit trail
  try {
    fs.appendFileSync(
      '/app/logs/sandbox-entrypoint.log',
      JSON.stringify(logEntry) + '\n'
    );
  } catch (error) {
    // Ignore file write errors to prevent cascade failures
  }
};

const info = (message, context) => log('info', message, context);
const warn = (message, context) => log('warn', message, context);
const error = (message, context) => log('error', message, context);
const debug = (message, context) => log('debug', message, context);

// Security validation functions
const validateSandboxIntegrity = () => {
  info('Validating sandbox integrity...');

  // Check read-only filesystem marker
  if (!fs.existsSync('/app/.readonly-fs-marker')) {
    throw new Error(
      'Sandbox integrity violation: readonly filesystem marker missing'
    );
  }

  // Verify user identity
  const uid = process.getuid();
  const gid = process.getgid();

  if (uid === 0) {
    throw new Error('Security violation: Running as root is forbidden');
  }

  if (uid !== 1001 || gid !== 1001) {
    throw new Error(
      `Security violation: Incorrect user identity ${uid}:${gid}, expected 1001:1001`
    );
  }

  // Verify environment security
  if (process.env.LD_PRELOAD) {
    throw new Error('Security violation: LD_PRELOAD detected');
  }

  info('Sandbox integrity validation passed', { uid, gid });
};

// Resource monitoring
let resourceMonitor;
const startResourceMonitoring = () => {
  info('Starting resource monitoring...');

  resourceMonitor = setInterval(() => {
    try {
      // Check memory usage
      const memInfo = execSync('cat /proc/meminfo').toString();
      const memAvailable = parseInt(
        memInfo.match(/MemAvailable:\s+(\d+)/)?.[1] || '0'
      );
      const memUsageMB = Math.max(
        0,
        SECURITY_CONFIG.maxMemoryMB - Math.floor(memAvailable / 1024)
      );

      // Check process count
      const processCount = parseInt(
        execSync(`pgrep -cu $(whoami)`).toString().trim()
      );

      if (memUsageMB > SECURITY_CONFIG.maxMemoryMB * 0.9) {
        warn('High memory usage detected', {
          memUsageMB,
          limit: SECURITY_CONFIG.maxMemoryMB,
        });
      }

      if (processCount > SECURITY_CONFIG.maxProcesses * 0.8) {
        warn('High process count detected', {
          processCount,
          limit: SECURITY_CONFIG.maxProcesses,
        });
      }

      debug('Resource status', { memUsageMB, processCount });
    } catch (monitorError) {
      warn('Resource monitoring error', { error: monitorError.message });
    }
  }, 5000); // Check every 5 seconds
};

// Secret redaction
const redactSecrets = text => {
  if (!SECURITY_CONFIG.redactSecrets || typeof text !== 'string') {
    return text;
  }

  return (
    text
      // API keys
      .replace(
        /([a-zA-Z0-9_-]*[kK]ey[a-zA-Z0-9_-]*\s*[:=]\s*)([a-zA-Z0-9+/]{20,})/g,
        '$1[REDACTED]'
      )
      // Tokens
      .replace(
        /([a-zA-Z0-9_-]*[tT]oken[a-zA-Z0-9_-]*\s*[:=]\s*)([a-zA-Z0-9+/]{20,})/g,
        '$1[REDACTED]'
      )
      // Passwords
      .replace(
        /([a-zA-Z0-9_-]*[pP]assword[a-zA-Z0-9_-]*\s*[:=]\s*)([^\s]{8,})/g,
        '$1[REDACTED]'
      )
      // Generic secrets
      .replace(
        /([a-zA-Z0-9_-]*[sS]ecret[a-zA-Z0-9_-]*\s*[:=]\s*)([a-zA-Z0-9+/]{16,})/g,
        '$1[REDACTED]'
      )
      // Base64 encoded (likely secrets)
      .replace(/([a-zA-Z0-9+/]{40,}={0,2})/g, '[REDACTED_BASE64]')
      // UUIDs that might be sensitive
      .replace(
        /([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})/g,
        '[REDACTED_UUID]'
      )
  );
};

// Secure process execution
const executeSecureProcess = (command, args = [], options = {}) => {
  return new Promise((resolve, reject) => {
    info('Executing secure process', {
      command: redactSecrets(command),
      args: args.map(redactSecrets),
      options: { ...options, env: '[REDACTED]' },
    });

    const child = spawn(command, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: '/app',
      uid: 1001,
      gid: 1001,
      env: {
        PATH: '/usr/local/bin:/usr/bin:/bin',
        NODE_ENV: 'sandbox',
        HOME: '/app',
        TMPDIR: '/app/temp',
      },
      ...options,
    });

    let stdout = '';
    let stderr = '';

    // Capture output with size limits
    const maxOutputSize = 1024 * 1024; // 1MB limit

    child.stdout.on('data', data => {
      if (stdout.length < maxOutputSize) {
        stdout += data.toString();
      }
    });

    child.stderr.on('data', data => {
      if (stderr.length < maxOutputSize) {
        stderr += data.toString();
      }
    });

    // Set execution timeout
    const timeout = setTimeout(() => {
      error('Process execution timeout', {
        command,
        timeoutMs: SECURITY_CONFIG.maxExecutionTime,
      });
      child.kill('SIGKILL');
      reject(new Error('Process execution timeout'));
    }, SECURITY_CONFIG.maxExecutionTime);

    child.on('close', code => {
      clearTimeout(timeout);

      const result = {
        exitCode: code,
        stdout: redactSecrets(stdout),
        stderr: redactSecrets(stderr),
        executionTime: Date.now() - startTime,
      };

      info('Process execution completed', {
        command: redactSecrets(command),
        exitCode: code,
        executionTime: result.executionTime,
      });

      if (code === 0) {
        resolve(result);
      } else {
        reject(new Error(`Process exited with code ${code}`));
      }
    });

    child.on('error', err => {
      clearTimeout(timeout);
      error('Process execution error', {
        command: redactSecrets(command),
        error: err.message,
      });
      reject(err);
    });

    const startTime = Date.now();
  });
};

// Main application bootstrap
const bootstrapApplication = async () => {
  info('Bootstrapping PAKE Agent Sandbox application...');

  try {
    // Initialize the actual agent runtime
    const agentRuntime = require('/app/src/index.js');

    // Start HTTP server for agent API
    const express = require('express');
    const app = express();

    // Security middleware
    app.use((req, res, next) => {
      // Log all requests (with redaction)
      if (SECURITY_CONFIG.logAllCommands) {
        info('HTTP request', {
          method: req.method,
          url: req.url,
          headers: redactSecrets(JSON.stringify(req.headers)),
          userAgent: req.get('user-agent'),
        });
      }

      // Security headers
      res.setHeader('X-Sandbox-Mode', SECURITY_CONFIG.sandboxMode);
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.setHeader('X-Frame-Options', 'DENY');
      res.setHeader('X-XSS-Protection', '1; mode=block');

      next();
    });

    // Body parsing with size limits
    app.use(express.json({ limit: '1mb' }));

    // Health check endpoint
    app.get('/health', (req, res) => {
      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        sandbox: {
          mode: SECURITY_CONFIG.sandboxMode,
          uptime: process.uptime(),
          memory: process.memoryUsage(),
          pid: process.pid,
        },
      });
    });

    // Agent execution endpoint
    app.post('/execute', async (req, res) => {
      try {
        const task = req.body;

        info('Executing agent task', {
          taskId: task.id,
          type: task.type,
          contentLength: task.input?.content?.length || 0,
        });

        // Execute through agent runtime
        const result = await agentRuntime.executeTask(task);

        // Redact sensitive information from response
        const sanitizedResult = {
          ...result,
          output: redactSecrets(JSON.stringify(result.output)),
          metadata: {
            ...result.metadata,
            executionTime: Date.now() - startTime,
          },
        };

        info('Agent task completed', {
          taskId: task.id,
          status: result.status,
          executionTime: sanitizedResult.metadata.executionTime,
        });

        res.json(sanitizedResult);
      } catch (execError) {
        error('Agent task execution failed', {
          taskId: req.body.id,
          error: execError.message,
        });

        res.status(500).json({
          error: 'Task execution failed',
          message: redactSecrets(execError.message),
        });
      }

      const startTime = Date.now();
    });

    // Start server
    const port = 8080;
    app.listen(port, '0.0.0.0', () => {
      info('PAKE Agent Sandbox server started', { port });
    });
  } catch (bootstrapError) {
    error('Application bootstrap failed', { error: bootstrapError.message });
    process.exit(1);
  }
};

// Signal handlers for graceful shutdown
const gracefulShutdown = signal => {
  info('Received shutdown signal', { signal });

  // Clear resource monitor
  if (resourceMonitor) {
    clearInterval(resourceMonitor);
  }

  // Final security audit
  try {
    execSync('/app/security-audit.sh audit');
    info('Final security audit completed');
  } catch (auditError) {
    warn('Final security audit failed', { error: auditError.message });
  }

  info('PAKE Agent Sandbox shutdown complete');
  process.exit(0);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Unhandled error handlers
process.on('uncaughtException', err => {
  error('Uncaught exception', { error: err.message, stack: err.stack });
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  error('Unhandled promise rejection', { reason, promise });
  process.exit(1);
});

// Main execution
(async () => {
  try {
    info('PAKE Agent Sandbox starting up', {
      version: '1.0.0',
      nodeVersion: process.version,
      platform: process.platform,
      arch: process.arch,
      security: SECURITY_CONFIG,
    });

    // Run security validation
    validateSandboxIntegrity();

    // Start resource monitoring
    startResourceMonitoring();

    // Bootstrap application
    await bootstrapApplication();
  } catch (startupError) {
    error('Sandbox startup failed', { error: startupError.message });
    process.exit(1);
  }
})();
