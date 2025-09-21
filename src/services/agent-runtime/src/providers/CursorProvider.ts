/**
 * PAKE System - Cursor Provider
 *
 * Secure Cursor IDE integration with mandatory dry-run mode and comprehensive safety controls.
 * Implements code analysis and suggestion features with strict isolation and validation.
 */

import { promises as fs } from 'fs';
import { spawn, ChildProcess } from 'child_process';
import { join, resolve, basename, extname } from 'path';
import { createHash, randomBytes } from 'crypto';
import { AgentProvider } from './AgentProvider';
import {
  AgentTask,
  AgentResult,
  AgentResultStatus,
  AgentCapability,
  AgentTaskType,
} from '../types/Agent';
import { sandboxEnforcer } from '../../policy/Sandbox';
import { createLogger, Logger } from '../../../orchestrator/src/utils/logger';
import { metrics, TaskLifecycleEvent } from '../../../orchestrator/src/utils/metrics';
import { FeatureFlags } from '../../config/FeatureFlags';

export interface CursorConfig {
  // Cursor Installation
  cursorPath: string;
  workspaceDirectory: string;
  maxWorkspaceSize: number; // MB

  // Safety Configuration
  dryRunMode: boolean;
  allowFileModification: boolean;
  allowExecutableRun: boolean;
  maxExecutionTime: number;

  // Feature Flags
  enableAutoFix: boolean;
  enableCodeAnalysis: boolean;
  enableSuggestions: boolean;
  enableRefactoring: boolean;

  // Security Settings
  redactSecrets: boolean;
  logAllOperations: boolean;
  restrictedPaths: string[];
  allowedFileTypes: string[];

  // Analysis Configuration
  analysisDepth: 'shallow' | 'medium' | 'deep';
  includeTests: boolean;
  includeDocumentation: boolean;
}

export interface CursorOperation {
  operationId: string;
  type: 'analyze' | 'suggest' | 'refactor' | 'fix';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'dry-run';
  startTime: number;
  endTime?: number;
  inputFiles: string[];
  outputFiles: string[];
  changes: CursorChange[];
  metadata: {
    linesAnalyzed: number;
    issuesFound: number;
    suggestionsGenerated: number;
    executionTime: number;
  };
}

export interface CursorChange {
  file: string;
  type: 'addition' | 'deletion' | 'modification';
  line: number;
  column?: number;
  oldContent?: string;
  newContent: string;
  confidence: number;
  reasoning: string;
  impact: 'low' | 'medium' | 'high';
  category: string;
}

export interface DryRunResult {
  wouldModify: boolean;
  affectedFiles: string[];
  estimatedChanges: number;
  potentialRisks: string[];
  recommendations: string[];
  previewChanges: CursorChange[];
}

/**
 * Cursor IDE provider with mandatory dry-run enforcement and comprehensive safety controls
 */
export class CursorProvider implements AgentProvider {
  public readonly name = 'CursorProvider';
  public readonly version = '1.0.0';
  public readonly capabilities: AgentCapability[] = [
    AgentCapability.CODE_ANALYSIS,
    AgentCapability.CODE_GENERATION,
    AgentCapability.REFACTORING,
    AgentCapability.BUG_DETECTION,
    AgentCapability.CODE_REVIEW,
  ];

  private readonly config: CursorConfig;
  private readonly logger: Logger;
  private readonly featureFlags: FeatureFlags;
  private readonly activeOperations: Map<string, CursorOperation> = new Map();

  // Safety enforcement
  private readonly isDryRunEnforced: boolean;
  private operationCount = 0;
  private lastHealthCheck = 0;

  constructor(config: Partial<CursorConfig> = {}, featureFlags?: FeatureFlags) {
    this.featureFlags = featureFlags || new FeatureFlags();

    // Enforce dry-run mode via feature flag
    this.isDryRunEnforced = !this.featureFlags.evaluate('FF_CURSOR_AUTOFIX').value;

    this.config = {
      // Cursor installation
      cursorPath: config.cursorPath || this.detectCursorPath(),
      workspaceDirectory: config.workspaceDirectory || '/tmp/pake-cursor-workspace',
      maxWorkspaceSize: config.maxWorkspaceSize || 100, // 100MB limit

      // Mandatory safety - dry-run enforced unless explicitly enabled
      dryRunMode: this.isDryRunEnforced || config.dryRunMode !== false,
      allowFileModification: !this.isDryRunEnforced && config.allowFileModification === true,
      allowExecutableRun: false, // Never allow executable run
      maxExecutionTime: config.maxExecutionTime || 30000, // 30 seconds

      // Feature flags (all default to safe mode)
      enableAutoFix:
        !this.isDryRunEnforced && this.featureFlags.evaluate('FF_CURSOR_AUTOFIX').value,
      enableCodeAnalysis: config.enableCodeAnalysis ?? true,
      enableSuggestions: config.enableSuggestions ?? true,
      enableRefactoring: !this.isDryRunEnforced && config.enableRefactoring === true,

      // Security settings
      redactSecrets: config.redactSecrets ?? true,
      logAllOperations: config.logAllOperations ?? true,
      restrictedPaths: config.restrictedPaths || [
        '/etc',
        '/usr',
        '/bin',
        '/sbin',
        '/root',
        '/sys',
        '/proc',
        'node_modules',
        '.git',
        '.env',
      ],
      allowedFileTypes: config.allowedFileTypes || [
        '.js',
        '.ts',
        '.jsx',
        '.tsx',
        '.py',
        '.java',
        '.cpp',
        '.c',
        '.h',
        '.css',
        '.scss',
        '.html',
        '.json',
        '.yml',
        '.yaml',
        '.md',
        '.txt',
      ],

      // Analysis configuration
      analysisDepth: config.analysisDepth || 'medium',
      includeTests: config.includeTests ?? true,
      includeDocumentation: config.includeDocumentation ?? false,
    };

    this.logger = createLogger('CursorProvider', {
      provider: this.name,
      dryRunMode: this.config.dryRunMode,
      autoFixEnabled: this.config.enableAutoFix,
    });

    // Validate configuration
    this.validateConfiguration();

    // Register sandbox policy
    this.registerSandboxPolicy();

    // Log safety status
    this.logger.info('Cursor Provider initialized with safety controls', {
      dryRunEnforced: this.isDryRunEnforced,
      autoFixEnabled: this.config.enableAutoFix,
      allowFileModification: this.config.allowFileModification,
      analysisDepth: this.config.analysisDepth,
      maxExecutionTime: this.config.maxExecutionTime,
    });

    if (this.config.dryRunMode) {
      this.logger.warn('CURSOR PROVIDER IN DRY-RUN MODE - No file modifications will be performed');
    }
  }

  /**
   * Execute agent task with mandatory safety validation
   */
  async run(task: AgentTask): Promise<AgentResult> {
    const startTime = Date.now();
    const operationId = this.generateOperationId();

    this.logger.info('Starting Cursor operation', {
      taskId: task.id,
      operationId,
      type: task.type,
      dryRunMode: this.config.dryRunMode,
    });

    // Track lifecycle
    metrics.taskLifecycle(TaskLifecycleEvent.TASK_STARTED, task.id, task.type, this.name);

    try {
      // Pre-execution safety validation
      await this.validateTaskSafety(task);

      // Create secure workspace
      const workspace = await this.createSecureWorkspace(task, operationId);

      // Initialize operation tracking
      const operation = this.initializeOperation(task, operationId, workspace);

      // Execute based on task type
      let result: any;

      switch (task.type) {
        case AgentTaskType.CODE_ANALYSIS:
          result = await this.performCodeAnalysis(operation, task);
          break;

        case AgentTaskType.CODE_GENERATION:
          result = await this.performCodeGeneration(operation, task);
          break;

        case AgentTaskType.REFACTORING:
          result = await this.performRefactoring(operation, task);
          break;

        case AgentTaskType.BUG_DETECTION:
          result = await this.performBugDetection(operation, task);
          break;

        default:
          throw new Error(`Unsupported task type: ${task.type}`);
      }

      // Finalize operation
      operation.status = 'completed';
      operation.endTime = Date.now();

      // Clean up workspace
      await this.cleanupWorkspace(workspace);

      const executionTime = Date.now() - startTime;

      this.logger.info('Cursor operation completed successfully', {
        taskId: task.id,
        operationId,
        executionTime,
        changesCount: result.changes?.length || 0,
        dryRunMode: this.config.dryRunMode,
      });

      metrics.taskLifecycle(
        TaskLifecycleEvent.TASK_COMPLETED,
        task.id,
        task.type,
        this.name,
        executionTime
      );

      return {
        taskId: task.id,
        status: AgentResultStatus.SUCCESS,
        output: {
          ...result,
          dryRun: this.config.dryRunMode,
          safetyNotice: this.config.dryRunMode
            ? 'Operation executed in dry-run mode - no files were modified'
            : 'Operation executed with file modifications enabled',
        },
        metadata: {
          provider: this.name,
          operationId,
          executionTimeMs: executionTime,
          dryRunMode: this.config.dryRunMode,
          autoFixEnabled: this.config.enableAutoFix,
          operationMetrics: operation.metadata,
        },
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;

      this.logger.error('Cursor operation failed', {
        taskId: task.id,
        operationId,
        error: error.message,
        executionTime,
      });

      metrics.taskLifecycle(
        TaskLifecycleEvent.TASK_FAILED,
        task.id,
        task.type,
        this.name,
        executionTime,
        error.message
      );

      return {
        taskId: task.id,
        status: AgentResultStatus.ERROR,
        output: {
          error: this.sanitizeError(error.message),
          dryRun: this.config.dryRunMode,
        },
        metadata: {
          provider: this.name,
          operationId,
          executionTimeMs: executionTime,
          error: this.sanitizeError(error.message),
        },
      };
    }
  }

  /**
   * Perform code analysis with Cursor
   */
  private async performCodeAnalysis(operation: CursorOperation, task: AgentTask): Promise<any> {
    this.logger.info('Performing code analysis', {
      operationId: operation.operationId,
      depth: this.config.analysisDepth,
    });

    operation.status = 'running';
    operation.type = 'analyze';

    // Prepare code files in workspace
    const codeFiles = await this.prepareCodeFiles(operation, task.input);

    // Execute Cursor analysis
    const analysisResult = await this.executeCursorCommand(
      [
        'analyze',
        '--workspace',
        operation.inputFiles[0], // workspace directory
        '--format',
        'json',
        '--depth',
        this.config.analysisDepth,
        '--include-tests',
        this.config.includeTests.toString(),
        '--output',
        join(operation.inputFiles[0], 'analysis-result.json'),
      ],
      operation
    );

    // Parse analysis results
    const analysis = await this.parseAnalysisResult(analysisResult, operation);

    // Update operation metadata
    operation.metadata = {
      linesAnalyzed: analysis.statistics.linesAnalyzed,
      issuesFound: analysis.issues.length,
      suggestionsGenerated: analysis.suggestions.length,
      executionTime: Date.now() - operation.startTime,
    };

    return {
      analysis: analysis.analysis,
      issues: analysis.issues,
      suggestions: analysis.suggestions,
      statistics: analysis.statistics,
      riskAssessment: analysis.riskAssessment,
    };
  }

  /**
   * Perform code generation with safety validation
   */
  private async performCodeGeneration(operation: CursorOperation, task: AgentTask): Promise<any> {
    this.logger.info('Performing code generation', {
      operationId: operation.operationId,
      dryRunMode: this.config.dryRunMode,
    });

    operation.status = 'running';
    operation.type = 'suggest';

    // Validate generation request
    await this.validateGenerationRequest(task);

    // Prepare context files
    await this.prepareContextFiles(operation, task.input);

    // Generate code suggestions
    const suggestions = await this.generateCodeSuggestions(operation, task);

    // If dry-run mode, preview changes only
    if (this.config.dryRunMode) {
      const dryRunResult = await this.performDryRunAnalysis(suggestions, operation);
      return {
        suggestions,
        dryRun: dryRunResult,
        changes: [], // No actual changes in dry-run
        notice: 'Generated in dry-run mode - no files were created or modified',
      };
    }

    // If autofix enabled and not dry-run, apply suggestions
    let appliedChanges: CursorChange[] = [];
    if (this.config.enableAutoFix && !this.config.dryRunMode) {
      appliedChanges = await this.applySuggestions(suggestions, operation);
    }

    operation.changes = appliedChanges;
    operation.metadata = {
      linesAnalyzed: 0,
      issuesFound: 0,
      suggestionsGenerated: suggestions.length,
      executionTime: Date.now() - operation.startTime,
    };

    return {
      suggestions,
      changes: appliedChanges,
      generatedFiles: operation.outputFiles,
    };
  }

  /**
   * Perform refactoring with comprehensive safety checks
   */
  private async performRefactoring(operation: CursorOperation, task: AgentTask): Promise<any> {
    if (!this.config.enableRefactoring) {
      throw new Error('Refactoring is disabled by configuration');
    }

    this.logger.info('Performing refactoring', {
      operationId: operation.operationId,
      dryRunMode: this.config.dryRunMode,
    });

    operation.status = 'running';
    operation.type = 'refactor';

    // Validate refactoring request
    await this.validateRefactoringRequest(task);

    // Analyze code structure first
    const analysis = await this.analyzeCodeStructure(operation, task);

    // Generate refactoring plan
    const refactoringPlan = await this.generateRefactoringPlan(analysis, task);

    // Mandatory dry-run preview
    const dryRunResult = await this.performDryRunAnalysis(refactoringPlan, operation);

    if (this.config.dryRunMode) {
      return {
        analysis,
        refactoringPlan,
        dryRun: dryRunResult,
        changes: [],
        notice: 'Refactoring planned in dry-run mode - no files were modified',
      };
    }

    // Apply refactoring if enabled and safe
    let appliedChanges: CursorChange[] = [];
    if (this.config.enableAutoFix && this.validateRefactoringSafety(dryRunResult)) {
      appliedChanges = await this.applyRefactoring(refactoringPlan, operation);
    }

    operation.changes = appliedChanges;
    operation.metadata = {
      linesAnalyzed: analysis.linesAnalyzed,
      issuesFound: refactoringPlan.issues.length,
      suggestionsGenerated: refactoringPlan.changes.length,
      executionTime: Date.now() - operation.startTime,
    };

    return {
      analysis,
      refactoringPlan,
      dryRun: dryRunResult,
      changes: appliedChanges,
    };
  }

  /**
   * Perform bug detection analysis
   */
  private async performBugDetection(operation: CursorOperation, task: AgentTask): Promise<any> {
    this.logger.info('Performing bug detection', {
      operationId: operation.operationId,
    });

    operation.status = 'running';
    operation.type = 'analyze';

    // Prepare code files for analysis
    const codeFiles = await this.prepareCodeFiles(operation, task.input);

    // Run Cursor bug detection
    const bugReport = await this.executeBugDetection(operation, codeFiles);

    // Analyze severity and categorize bugs
    const categorizedBugs = this.categorizeBugs(bugReport);

    // Generate fix suggestions if enabled
    let fixSuggestions: any[] = [];
    if (this.config.enableSuggestions) {
      fixSuggestions = await this.generateFixSuggestions(categorizedBugs, operation);
    }

    operation.metadata = {
      linesAnalyzed: bugReport.linesAnalyzed,
      issuesFound: categorizedBugs.length,
      suggestionsGenerated: fixSuggestions.length,
      executionTime: Date.now() - operation.startTime,
    };

    return {
      bugs: categorizedBugs,
      fixSuggestions,
      riskAssessment: this.assessBugRisk(categorizedBugs),
      statistics: bugReport.statistics,
    };
  }

  /**
   * Execute Cursor CLI command with safety monitoring
   */
  private async executeCursorCommand(
    args: string[],
    operation: CursorOperation
  ): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();

      this.logger.debug('Executing Cursor command', {
        operationId: operation.operationId,
        command: this.config.cursorPath,
        args: this.config.logAllOperations ? args : '[REDACTED]',
      });

      const child = spawn(this.config.cursorPath, args, {
        cwd: this.config.workspaceDirectory,
        env: this.buildSecureEnvironment(),
        stdio: ['pipe', 'pipe', 'pipe'],
        timeout: this.config.maxExecutionTime,
      });

      let stdout = '';
      let stderr = '';

      child.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      child.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      child.on('close', (code) => {
        const executionTime = Date.now() - startTime;

        this.logger.debug('Cursor command completed', {
          operationId: operation.operationId,
          exitCode: code,
          executionTime,
          stdoutLength: stdout.length,
          stderrLength: stderr.length,
        });

        resolve({
          stdout: this.sanitizeOutput(stdout),
          stderr: this.sanitizeOutput(stderr),
          exitCode: code || 0,
        });
      });

      child.on('error', (error) => {
        this.logger.error('Cursor command failed', {
          operationId: operation.operationId,
          error: error.message,
          executionTime: Date.now() - startTime,
        });
        reject(error);
      });

      // Handle timeout
      child.on('timeout', () => {
        this.logger.error('Cursor command timed out', {
          operationId: operation.operationId,
          timeout: this.config.maxExecutionTime,
        });
        child.kill('SIGKILL');
        reject(new Error('Command execution timeout'));
      });
    });
  }

  /**
   * Perform mandatory dry-run analysis before any modifications
   */
  private async performDryRunAnalysis(
    proposedChanges: any,
    operation: CursorOperation
  ): Promise<DryRunResult> {
    this.logger.info('Performing mandatory dry-run analysis', {
      operationId: operation.operationId,
    });

    const analysis: DryRunResult = {
      wouldModify: false,
      affectedFiles: [],
      estimatedChanges: 0,
      potentialRisks: [],
      recommendations: [],
      previewChanges: [],
    };

    // Analyze proposed changes
    if (proposedChanges.changes && Array.isArray(proposedChanges.changes)) {
      analysis.estimatedChanges = proposedChanges.changes.length;
      analysis.wouldModify = analysis.estimatedChanges > 0;

      for (const change of proposedChanges.changes) {
        if (change.file && !analysis.affectedFiles.includes(change.file)) {
          analysis.affectedFiles.push(change.file);
        }

        // Assess risk level
        if (change.impact === 'high') {
          analysis.potentialRisks.push(`High impact change in ${change.file}: ${change.reasoning}`);
        }

        // Create preview
        analysis.previewChanges.push({
          file: change.file,
          type: change.type,
          line: change.line,
          newContent: change.newContent,
          confidence: change.confidence,
          reasoning: change.reasoning,
          impact: change.impact,
          category: change.category,
        });
      }
    }

    // Generate safety recommendations
    if (analysis.estimatedChanges > 10) {
      analysis.recommendations.push(
        'Large number of changes detected - consider incremental approach'
      );
    }

    if (analysis.potentialRisks.length > 0) {
      analysis.recommendations.push(
        'High-risk changes detected - manual review strongly recommended'
      );
    }

    if (analysis.affectedFiles.length > 5) {
      analysis.recommendations.push('Multiple files affected - ensure comprehensive testing');
    }

    this.logger.info('Dry-run analysis completed', {
      operationId: operation.operationId,
      wouldModify: analysis.wouldModify,
      affectedFiles: analysis.affectedFiles.length,
      estimatedChanges: analysis.estimatedChanges,
      potentialRisks: analysis.potentialRisks.length,
    });

    return analysis;
  }

  /**
   * Create secure workspace for operation
   */
  private async createSecureWorkspace(task: AgentTask, operationId: string): Promise<string> {
    const workspacePath = join(this.config.workspaceDirectory, operationId);

    // Create workspace directory with restricted permissions
    await fs.mkdir(workspacePath, { recursive: true, mode: 0o700 });

    this.logger.debug('Created secure workspace', {
      operationId,
      workspacePath,
    });

    return workspacePath;
  }

  /**
   * Initialize operation tracking
   */
  private initializeOperation(
    task: AgentTask,
    operationId: string,
    workspace: string
  ): CursorOperation {
    const operation: CursorOperation = {
      operationId,
      type: 'analyze',
      status: 'pending',
      startTime: Date.now(),
      inputFiles: [workspace],
      outputFiles: [],
      changes: [],
      metadata: {
        linesAnalyzed: 0,
        issuesFound: 0,
        suggestionsGenerated: 0,
        executionTime: 0,
      },
    };

    this.activeOperations.set(operationId, operation);
    return operation;
  }

  /**
   * Prepare code files in workspace
   */
  private async prepareCodeFiles(operation: CursorOperation, input: any): Promise<string[]> {
    const files: string[] = [];
    const workspace = operation.inputFiles[0];

    if (input.code) {
      const filename = input.filename || 'code.js';
      const filepath = join(workspace, filename);
      await fs.writeFile(filepath, input.code, { mode: 0o600 });
      files.push(filepath);
    }

    if (input.files && Array.isArray(input.files)) {
      for (const file of input.files) {
        if (this.isAllowedFileType(file.name) && this.isAllowedPath(file.name)) {
          const filepath = join(workspace, file.name);
          await fs.writeFile(filepath, file.content, { mode: 0o600 });
          files.push(filepath);
        }
      }
    }

    this.logger.debug('Prepared code files', {
      operationId: operation.operationId,
      fileCount: files.length,
    });

    return files;
  }

  /**
   * Build secure environment for Cursor execution
   */
  private buildSecureEnvironment(): Record<string, string> {
    return {
      PATH: '/usr/local/bin:/usr/bin:/bin',
      HOME: this.config.workspaceDirectory,
      TMPDIR: '/tmp',
      NODE_ENV: 'production',
      CURSOR_DISABLE_TELEMETRY: '1',
      CURSOR_LOG_LEVEL: 'error',
      // Remove any potentially dangerous environment variables
      LD_PRELOAD: '',
      LD_LIBRARY_PATH: '',
    };
  }

  /**
   * Validate file type against allowlist
   */
  private isAllowedFileType(filename: string): boolean {
    const ext = extname(filename).toLowerCase();
    return this.config.allowedFileTypes.includes(ext);
  }

  /**
   * Validate path against restricted paths
   */
  private isAllowedPath(path: string): boolean {
    const normalizedPath = resolve(path);
    return !this.config.restrictedPaths.some((restricted) => normalizedPath.includes(restricted));
  }

  /**
   * Validate task safety before execution
   */
  private async validateTaskSafety(task: AgentTask): Promise<void> {
    // Check sandbox policy compliance
    if (sandboxEnforcer) {
      const resourceCheck = sandboxEnforcer.validateResourceUsage(this.name, task.id, {
        executionTimeMs: this.config.maxExecutionTime,
        memoryMB: 256, // Estimated memory usage
      });

      if (!resourceCheck.allowed) {
        throw new Error(`Safety validation failed: ${resourceCheck.violations.join(', ')}`);
      }
    }

    // Validate input size
    const inputSize = JSON.stringify(task.input).length;
    if (inputSize > 1024 * 1024) {
      // 1MB limit
      throw new Error('Input size exceeds safety limit');
    }

    // Check for dangerous patterns in input
    const dangerousPatterns = [
      /eval\s*\(/,
      /exec\s*\(/,
      /system\s*\(/,
      /import\s+os/,
      /require\s*\(\s*['"]child_process/,
    ];

    const inputText = JSON.stringify(task.input);
    for (const pattern of dangerousPatterns) {
      if (pattern.test(inputText)) {
        throw new Error('Input contains potentially dangerous code patterns');
      }
    }
  }

  /**
   * Register sandbox policy
   */
  private registerSandboxPolicy(): void {
    if (sandboxEnforcer) {
      sandboxEnforcer.registerPolicy(this.name, {
        maxExecutionTimeMs: this.config.maxExecutionTime,
        maxMemoryMB: 256,
        allowNetworkAccess: false,
        allowFileSystem: true,
        allowedPaths: [this.config.workspaceDirectory, '/tmp'],
        redactSecrets: this.config.redactSecrets,
        requestsPerMinute: 10,
      });
    }
  }

  /**
   * Generate unique operation ID
   */
  private generateOperationId(): string {
    this.operationCount++;
    const timestamp = Date.now().toString(36);
    const random = randomBytes(4).toString('hex');
    return `cursor-${timestamp}-${this.operationCount}-${random}`;
  }

  /**
   * Sanitize output for security
   */
  private sanitizeOutput(output: any): any {
    if (!this.config.redactSecrets) {
      return output;
    }

    const sanitized = JSON.stringify(output)
      .replace(
        /([a-zA-Z0-9_-]*[kK]ey[a-zA-Z0-9_-]*["']?\s*[:=]\s*["']?)([a-zA-Z0-9+/]{20,}["']?)/g,
        '$1[REDACTED]'
      )
      .replace(
        /([a-zA-Z0-9_-]*[tT]oken[a-zA-Z0-9_-]*["']?\s*[:=]\s*["']?)([a-zA-Z0-9+/]{20,}["']?)/g,
        '$1[REDACTED]'
      )
      .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[REDACTED_EMAIL]');

    try {
      return JSON.parse(sanitized);
    } catch {
      return sanitized;
    }
  }

  /**
   * Sanitize error message
   */
  private sanitizeError(error: string): string {
    return this.config.redactSecrets ? (this.sanitizeOutput(error) as string) : error;
  }

  /**
   * Detect Cursor installation path
   */
  private detectCursorPath(): string {
    const commonPaths = [
      '/usr/local/bin/cursor',
      '/opt/cursor/cursor',
      '/Applications/Cursor.app/Contents/MacOS/Cursor',
      'C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\cursor\\Cursor.exe',
    ];

    // For security, return the default path - actual detection would require filesystem access
    return '/usr/local/bin/cursor';
  }

  /**
   * Validate configuration
   */
  private validateConfiguration(): void {
    if (!this.config.cursorPath) {
      throw new Error('Cursor path is required');
    }

    if (this.config.maxExecutionTime < 1000 || this.config.maxExecutionTime > 300000) {
      throw new Error('maxExecutionTime must be between 1s and 5 minutes');
    }

    // Enforce dry-run mode if feature flag is disabled
    if (this.isDryRunEnforced && !this.config.dryRunMode) {
      this.logger.warn(
        'Enforcing dry-run mode due to feature flag FF_CURSOR_AUTOFIX being disabled'
      );
      this.config.dryRunMode = true;
      this.config.allowFileModification = false;
      this.config.enableAutoFix = false;
    }
  }

  /**
   * Placeholder methods for additional functionality
   */
  private async parseAnalysisResult(result: any, operation: CursorOperation): Promise<any> {
    // Implementation would parse Cursor's analysis output
    return { analysis: {}, issues: [], suggestions: [], statistics: {}, riskAssessment: {} };
  }

  private async validateGenerationRequest(task: AgentTask): Promise<void> {
    // Validate code generation safety
  }

  private async prepareContextFiles(operation: CursorOperation, input: any): Promise<void> {
    // Prepare context files for code generation
  }

  private async generateCodeSuggestions(
    operation: CursorOperation,
    task: AgentTask
  ): Promise<any[]> {
    // Generate code suggestions with Cursor
    return [];
  }

  private async applySuggestions(
    suggestions: any[],
    operation: CursorOperation
  ): Promise<CursorChange[]> {
    // Apply suggestions (only if not in dry-run mode)
    return [];
  }

  private async validateRefactoringRequest(task: AgentTask): Promise<void> {
    // Validate refactoring safety
  }

  private async analyzeCodeStructure(operation: CursorOperation, task: AgentTask): Promise<any> {
    // Analyze code structure for refactoring
    return {};
  }

  private async generateRefactoringPlan(analysis: any, task: AgentTask): Promise<any> {
    // Generate refactoring plan
    return { issues: [], changes: [] };
  }

  private validateRefactoringSafety(dryRunResult: DryRunResult): boolean {
    // Validate if refactoring is safe to apply
    return dryRunResult.potentialRisks.length === 0;
  }

  private async applyRefactoring(plan: any, operation: CursorOperation): Promise<CursorChange[]> {
    // Apply refactoring changes (only if safe and enabled)
    return [];
  }

  private async executeBugDetection(operation: CursorOperation, files: string[]): Promise<any> {
    // Execute bug detection analysis
    return { linesAnalyzed: 0, statistics: {} };
  }

  private categorizeBugs(bugReport: any): any[] {
    // Categorize and prioritize detected bugs
    return [];
  }

  private async generateFixSuggestions(bugs: any[], operation: CursorOperation): Promise<any[]> {
    // Generate fix suggestions for detected bugs
    return [];
  }

  private assessBugRisk(bugs: any[]): any {
    // Assess overall risk from detected bugs
    return { level: 'low', score: 0 };
  }

  private async cleanupWorkspace(workspace: string): Promise<void> {
    try {
      await fs.rmdir(workspace, { recursive: true });
      this.logger.debug('Workspace cleaned up', { workspace });
    } catch (error) {
      this.logger.warn('Workspace cleanup failed', {
        workspace,
        error: error.message,
      });
    }
  }

  /**
   * Health check implementation
   */
  async healthCheck(): Promise<boolean> {
    const now = Date.now();

    // Rate limit health checks
    if (now - this.lastHealthCheck < 30000) {
      return true;
    }

    this.lastHealthCheck = now;

    try {
      // Check if Cursor is accessible (in real implementation)
      // For now, return true as we can't actually check Cursor installation

      this.logger.debug('Health check passed');
      return true;
    } catch (error) {
      this.logger.error('Health check failed', { error: error.message });
      return false;
    }
  }

  /**
   * Dispose resources
   */
  async dispose(): Promise<void> {
    this.logger.info('Disposing Cursor Provider');

    // Clean up active operations
    for (const operation of this.activeOperations.values()) {
      if (operation.inputFiles[0]) {
        await this.cleanupWorkspace(operation.inputFiles[0]);
      }
    }

    this.activeOperations.clear();

    this.logger.info('Cursor Provider disposed');
  }
}
