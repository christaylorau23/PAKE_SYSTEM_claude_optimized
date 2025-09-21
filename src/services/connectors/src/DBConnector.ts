/**
 * PAKE System - Database Connector
 *
 * MCP-like connector for database operations with connection pooling,
 * query optimization, and comprehensive error handling.
 */

import { Pool, PoolConfig, PoolClient, QueryResult } from 'pg';
import { createHash } from 'crypto';
import {
  Connector,
  ConnectorRequest,
  ConnectorRequestType,
  ResponseEnvelope,
  ResponseStatus,
  ConnectorConfig,
} from './Connector';

export interface DBConfig extends ConnectorConfig {
  // Connection settings
  host: string;
  port: number;
  database: string;
  username: string;
  REDACTED_SECRET: string;
  ssl?: boolean;

  // Pool settings
  poolSize: number;
  idleTimeoutMs: number;
  connectionTimeoutMs: number;

  // Query settings
  queryTimeout: number;
  maxRowsPerQuery: number;
  enablePreparedStatements: boolean;

  // Monitoring
  slowQueryThreshold: number;
  enableQueryLogging: boolean;
}

export interface QueryRequest {
  sql: string;
  parameters?: any[];
  options?: {
    prepared?: boolean;
    rowMode?: 'array' | 'object';
    maxRows?: number;
  };
}

export interface QueryResult {
  rows: any[];
  rowCount: number;
  fields: Array<{
    name: string;
    dataTypeID: number;
    dataTypeSize: number;
    dataTypeModifier: number;
  }>;
  command: string;
  oid?: number;
  executionTime: number;
}

export interface TransactionContext {
  id: string;
  client: PoolClient;
  startedAt: number;
  operations: string[];
}

/**
 * Database connector with connection pooling and transaction support
 */
export class DBConnector extends Connector {
  private pool: Pool;
  private readonly preparedStatements = new Map<string, string>();
  private readonly activeTransactions = new Map<string, TransactionContext>();
  private queryCount = 0;

  constructor(name: string, config: Partial<DBConfig> = {}) {
    const dbConfig: DBConfig = {
      ...config,
      host: config.host || 'localhost',
      port: config.port || 5432,
      database: config.database || 'pake_system',
      username: config.username || 'pake_user',
      REDACTED_SECRET: config.REDACTED_SECRET || '',
      ssl: config.ssl ?? false,
      poolSize: config.poolSize || 20,
      idleTimeoutMs: config.idleTimeoutMs || 30000,
      connectionTimeoutMs: config.connectionTimeoutMs || 5000,
      queryTimeout: config.queryTimeout || 30000,
      maxRowsPerQuery: config.maxRowsPerQuery || 10000,
      enablePreparedStatements: config.enablePreparedStatements ?? true,
      slowQueryThreshold: config.slowQueryThreshold || 1000,
      enableQueryLogging: config.enableQueryLogging ?? false,
    } as DBConfig;

    super(name, dbConfig);

    // Initialize connection pool
    this.initializePool(dbConfig);

    this.logger.info('DBConnector initialized', {
      host: dbConfig.host,
      database: dbConfig.database,
      poolSize: dbConfig.poolSize,
    });
  }

  /**
   * Initialize PostgreSQL connection pool
   */
  private initializePool(config: DBConfig): void {
    const poolConfig: PoolConfig = {
      host: config.host,
      port: config.port,
      database: config.database,
      user: config.username,
      REDACTED_SECRET: config.REDACTED_SECRET,
      ssl: config.ssl,
      max: config.poolSize,
      idleTimeoutMillis: config.idleTimeoutMs,
      connectionTimeoutMillis: config.connectionTimeoutMs,
      query_timeout: config.queryTimeout,
      statement_timeout: config.queryTimeout,
    };

    this.pool = new Pool(poolConfig);

    // Handle pool events
    this.pool.on('connect', _client => {
      this.logger.debug('Database client connected', {
        totalCount: this.pool.totalCount,
        idleCount: this.pool.idleCount,
        waitingCount: this.pool.waitingCount,
      });
    });

    this.pool.on('error', err => {
      this.logger.error('Database pool error', {
        error: err.message,
        stack: err.stack,
      });
      this.connectionHealth = 0.5;
    });

    this.pool.on('remove', () => {
      this.logger.debug('Database client removed from pool');
    });
  }

  /**
   * Fetch data using database operations
   */
  async fetch<T = QueryResult>(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<T>> {
    this.validateRequest(request);
    const startTime = Date.now();

    try {
      switch (request.type) {
        case ConnectorRequestType.SELECT:
        case ConnectorRequestType.QUERY:
          return (await this.executeQuery(request)) as ResponseEnvelope<T>;

        case ConnectorRequestType.INSERT:
        case ConnectorRequestType.UPDATE:
        case ConnectorRequestType.DELETE:
          return (await this.executeModification(
            request
          )) as ResponseEnvelope<T>;

        default:
          throw new Error(`Unsupported request type: ${request.type}`);
      }
    } catch (error) {
      const executionTime = Date.now() - startTime;
      return this.createErrorResponse(
        request,
        error as Error,
        this.mapErrorToStatus(error as Error),
        executionTime,
        this.isRetryableError(error as Error)
      );
    }
  }

  /**
   * Execute SELECT query
   */
  private async executeQuery(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<QueryResult>> {
    const startTime = Date.now();
    const queryRequest = this.parseQueryRequest(request);

    this.logger.debug('Executing query', {
      requestId: request.id,
      sqlPreview: queryRequest.sql.substring(0, 100),
      parameterCount: queryRequest.parameters?.length || 0,
    });

    let client: PoolClient | null = null;

    try {
      client = await this.pool.connect();

      // Apply row limit for safety
      const maxRows = Math.min(
        queryRequest.options?.maxRows ||
          (this.config as DBConfig).maxRowsPerQuery,
        (this.config as DBConfig).maxRowsPerQuery
      );

      // Execute query with timeout
      const result = await this.executeWithTimeout(
        this.performQuery(client, queryRequest, maxRows),
        request.metadata.timeout || this.config.timeout
      );

      const executionTime = Date.now() - startTime;

      // Log slow queries
      if (
        (this.config as DBConfig).enableQueryLogging ||
        executionTime > (this.config as DBConfig).slowQueryThreshold
      ) {
        this.logger.warn('Slow query detected', {
          requestId: request.id,
          executionTime,
          rowCount: result.rowCount,
          sql: queryRequest.sql,
        });
      }

      this.logger.debug('Query completed', {
        requestId: request.id,
        executionTime,
        rowCount: result.rowCount,
      });

      return this.createResponse(
        request,
        result,
        ResponseStatus.SUCCESS,
        executionTime,
        {
          recordCount: result.rowCount,
          confidence: 1.0, // Database queries have high confidence
          freshness: 0, // Just fetched from database
        }
      );
    } finally {
      if (client) {
        client.release();
      }
    }
  }

  /**
   * Execute modification query (INSERT/UPDATE/DELETE)
   */
  private async executeModification(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<QueryResult>> {
    const startTime = Date.now();
    const queryRequest = this.parseQueryRequest(request);

    this.logger.debug('Executing modification', {
      requestId: request.id,
      type: request.type,
      sqlPreview: queryRequest.sql.substring(0, 100),
    });

    let client: PoolClient | null = null;

    try {
      client = await this.pool.connect();

      const result = await this.executeWithTimeout(
        this.performQuery(client, queryRequest),
        request.metadata.timeout || this.config.timeout
      );

      const executionTime = Date.now() - startTime;

      this.logger.info('Modification completed', {
        requestId: request.id,
        type: request.type,
        executionTime,
        affectedRows: result.rowCount,
      });

      return this.createResponse(
        request,
        result,
        ResponseStatus.SUCCESS,
        executionTime,
        {
          recordCount: result.rowCount,
        }
      );
    } finally {
      if (client) {
        client.release();
      }
    }
  }

  /**
   * Perform the actual database query
   */
  private async performQuery(
    client: PoolClient,
    queryRequest: QueryRequest,
    maxRows?: number
  ): Promise<QueryResult> {
    const startTime = Date.now();
    let sql = queryRequest.sql;

    // Add LIMIT clause for SELECT queries if not present
    if (maxRows && sql.trim().toLowerCase().startsWith('select')) {
      if (!sql.toLowerCase().includes('limit')) {
        sql += ` LIMIT ${maxRows}`;
      }
    }

    // Use prepared statements if enabled and beneficial
    if (
      (this.config as DBConfig).enablePreparedStatements &&
      queryRequest.parameters
    ) {
      const stmtHash = createHash('md5').update(sql).digest('hex');

      if (!this.preparedStatements.has(stmtHash)) {
        this.preparedStatements.set(stmtHash, `stmt_${stmtHash}`);
      }

      const stmtName = this.preparedStatements.get(stmtHash)!;

      try {
        // Prepare statement if not already prepared
        await client.query(`PREPARE ${stmtName} AS ${sql}`);
      } catch {
        // Statement might already be prepared, ignore error
      }

      // Execute prepared statement
      const pgResult = await client.query(
        `EXECUTE ${stmtName}`,
        queryRequest.parameters
      );

      return {
        rows: pgResult.rows,
        rowCount: pgResult.rowCount || 0,
        fields: pgResult.fields || [],
        command: pgResult.command,
        oid: pgResult.oid,
        executionTime: Date.now() - startTime,
      };
    } else {
      // Execute direct query
      const pgResult = await client.query(sql, queryRequest.parameters);

      return {
        rows: pgResult.rows,
        rowCount: pgResult.rowCount || 0,
        fields: pgResult.fields || [],
        command: pgResult.command,
        oid: pgResult.oid,
        executionTime: Date.now() - startTime,
      };
    }
  }

  /**
   * Parse query request from connector request
   */
  private parseQueryRequest(request: ConnectorRequest): QueryRequest {
    if (typeof request.parameters === 'string') {
      // SQL string provided directly
      return {
        sql: request.parameters,
        parameters: request.config.parameters as any[],
      };
    }

    if (request.parameters.sql) {
      // Structured query request
      return {
        sql: request.parameters.sql,
        parameters: request.parameters.parameters,
        options: request.parameters.options,
      };
    }

    // Build query based on request type and target
    return this.buildQuery(request);
  }

  /**
   * Build SQL query from request parameters
   */
  private buildQuery(request: ConnectorRequest): QueryRequest {
    const tableName = request.target;
    const params = request.parameters;

    switch (request.type) {
      case ConnectorRequestType.SELECT: {
        const columns = params.columns ? params.columns.join(', ') : '*';
        const whereClause = this.buildWhereClause(params.where);
        const orderClause = params.orderBy ? `ORDER BY ${params.orderBy}` : '';
        const limitClause = params.limit ? `LIMIT ${params.limit}` : '';

        return {
          sql: `SELECT ${columns} FROM ${tableName} ${whereClause} ${orderClause} ${limitClause}`.trim(),
          parameters: this.extractWhereParameters(params.where),
        };
      }

      case ConnectorRequestType.INSERT: {
        const insertColumns = Object.keys(params.data);
        const placeholders = insertColumns
          .map((_, i) => `$${i + 1}`)
          .join(', ');

        return {
          sql: `INSERT INTO ${tableName} (${insertColumns.join(', ')}) VALUES (${placeholders}) RETURNING *`,
          parameters: Object.values(params.data),
        };
      }

      case ConnectorRequestType.UPDATE: {
        const updateColumns = Object.keys(params.data);
        const setClause = updateColumns
          .map((col, i) => `${col} = $${i + 1}`)
          .join(', ');
        const updateWhereClause = this.buildWhereClause(
          params.where,
          updateColumns.length
        );

        return {
          sql: `UPDATE ${tableName} SET ${setClause} ${updateWhereClause} RETURNING *`,
          parameters: [
            ...Object.values(params.data),
            ...this.extractWhereParameters(params.where),
          ],
        };
      }

      case ConnectorRequestType.DELETE: {
        const deleteWhereClause = this.buildWhereClause(params.where);

        return {
          sql: `DELETE FROM ${tableName} ${deleteWhereClause} RETURNING *`,
          parameters: this.extractWhereParameters(params.where),
        };
      }

      default:
        throw new Error(`Cannot build query for request type: ${request.type}`);
    }
  }

  /**
   * Build WHERE clause from parameters
   */
  private buildWhereClause(whereParams: any, paramOffset: number = 0): string {
    if (!whereParams || Object.keys(whereParams).length === 0) {
      return '';
    }

    const conditions = Object.keys(whereParams).map((col, i) => {
      const paramIndex = paramOffset + i + 1;
      return `${col} = $${paramIndex}`;
    });

    return `WHERE ${conditions.join(' AND ')}`;
  }

  /**
   * Extract parameters for WHERE clause
   */
  private extractWhereParameters(whereParams: any): any[] {
    if (!whereParams) return [];
    return Object.values(whereParams);
  }

  /**
   * Begin database transaction
   */
  async beginTransaction(transactionId?: string): Promise<string> {
    const txId =
      transactionId ||
      `tx_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    try {
      const client = await this.pool.connect();
      await client.query('BEGIN');

      const transaction: TransactionContext = {
        id: txId,
        client,
        startedAt: Date.now(),
        operations: [],
      };

      this.activeTransactions.set(txId, transaction);

      this.logger.info('Transaction started', { transactionId: txId });

      return txId;
    } catch (error) {
      this.logger.error('Failed to start transaction', {
        transactionId: txId,
        error: (error as Error).message,
      });
      throw error;
    }
  }

  /**
   * Commit transaction
   */
  async commitTransaction(transactionId: string): Promise<void> {
    const transaction = this.activeTransactions.get(transactionId);
    if (!transaction) {
      throw new Error(`Transaction not found: ${transactionId}`);
    }

    try {
      await transaction.client.query('COMMIT');
      transaction.client.release();
      this.activeTransactions.delete(transactionId);

      const duration = Date.now() - transaction.startedAt;

      this.logger.info('Transaction committed', {
        transactionId,
        duration,
        operationCount: transaction.operations.length,
      });
    } catch (error) {
      // Rollback on commit failure
      await this.rollbackTransaction(transactionId);
      throw error;
    }
  }

  /**
   * Rollback transaction
   */
  async rollbackTransaction(transactionId: string): Promise<void> {
    const transaction = this.activeTransactions.get(transactionId);
    if (!transaction) {
      this.logger.warn('Transaction not found for rollback', { transactionId });
      return;
    }

    try {
      await transaction.client.query('ROLLBACK');
      transaction.client.release();
      this.activeTransactions.delete(transactionId);

      this.logger.info('Transaction rolled back', { transactionId });
    } catch (error) {
      this.logger.error('Failed to rollback transaction', {
        transactionId,
        error: (error as Error).message,
      });
    }
  }

  /**
   * Execute query within transaction
   */
  async executeInTransaction(
    transactionId: string,
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<QueryResult>> {
    const transaction = this.activeTransactions.get(transactionId);
    if (!transaction) {
      throw new Error(`Transaction not found: ${transactionId}`);
    }

    const startTime = Date.now();
    const queryRequest = this.parseQueryRequest(request);

    try {
      const result = await this.performQuery(transaction.client, queryRequest);

      transaction.operations.push(
        `${request.type}: ${queryRequest.sql.substring(0, 50)}...`
      );

      const executionTime = Date.now() - startTime;

      return this.createResponse(
        request,
        result,
        ResponseStatus.SUCCESS,
        executionTime,
        {
          recordCount: result.rowCount,
          confidence: 1.0,
        }
      );
    } catch (error) {
      this.logger.error('Transaction query failed', {
        transactionId,
        requestId: request.id,
        error: (error as Error).message,
      });

      const executionTime = Date.now() - startTime;
      return this.createErrorResponse(
        request,
        error as Error,
        this.mapErrorToStatus(error as Error),
        executionTime,
        false // Don't retry within transaction
      );
    }
  }

  /**
   * Map database error to response status
   */
  private mapErrorToStatus(error: Error): ResponseStatus {
    const message = error.message.toLowerCase();

    if (
      message.includes('timeout') ||
      message.includes('canceling statement due to statement timeout')
    ) {
      return ResponseStatus.TIMEOUT;
    }
    if (message.includes('connection') || message.includes('connect')) {
      return ResponseStatus.SERVICE_UNAVAILABLE;
    }
    if (message.includes('authentication') || message.includes('REDACTED_SECRET')) {
      return ResponseStatus.UNAUTHORIZED;
    }
    if (message.includes('permission') || message.includes('access')) {
      return ResponseStatus.FORBIDDEN;
    }
    if (message.includes('does not exist') || message.includes('not found')) {
      return ResponseStatus.NOT_FOUND;
    }
    if (message.includes('syntax error') || message.includes('invalid')) {
      return ResponseStatus.INVALID_REQUEST;
    }

    return ResponseStatus.ERROR;
  }

  /**
   * Check if database error is retryable
   */
  private isRetryableError(error: Error): boolean {
    const message = error.message.toLowerCase();

    // Connection errors are retryable
    if (message.includes('connection') || message.includes('connect')) {
      return true;
    }

    // Timeout errors are retryable
    if (message.includes('timeout')) {
      return true;
    }

    // Pool exhaustion is retryable
    if (message.includes('pool') || message.includes('client')) {
      return true;
    }

    // Lock timeout is retryable
    if (message.includes('lock') || message.includes('deadlock')) {
      return true;
    }

    return false;
  }

  /**
   * Get connection pool statistics
   */
  getPoolStats(): {
    totalCount: number;
    idleCount: number;
    waitingCount: number;
    activeTransactions: number;
  } {
    return {
      totalCount: this.pool.totalCount,
      idleCount: this.pool.idleCount,
      waitingCount: this.pool.waitingCount,
      activeTransactions: this.activeTransactions.size,
    };
  }

  /**
   * Initialize connection
   */
  async connect(): Promise<void> {
    try {
      // Test connection by executing a simple query
      const client = await this.pool.connect();
      await client.query('SELECT 1');
      client.release();

      this.isConnected = true;
      this.connectionHealth = 1.0;
      this.logger.info('DBConnector connected successfully');
    } catch (error) {
      this.isConnected = false;
      this.connectionHealth = 0.0;
      this.logger.error('Failed to connect to database', {
        error: (error as Error).message,
      });
      throw error;
    }
  }

  /**
   * Close connection
   */
  async disconnect(): Promise<void> {
    try {
      // Rollback any active transactions
      for (const [txId] of this.activeTransactions) {
        await this.rollbackTransaction(txId);
      }

      await this.pool.end();
      this.isConnected = false;
      this.connectionHealth = 0.0;
      this.logger.info('DBConnector disconnected');
    } catch (error) {
      this.logger.error('Error during disconnect', {
        error: (error as Error).message,
      });
    }
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      const client = await this.pool.connect();
      const result = await client.query('SELECT NOW()');
      client.release();

      this.connectionHealth = 1.0;
      this.lastHealthCheck = Date.now();

      this.logger.debug('Health check passed', {
        serverTime: result.rows[0].now,
        poolStats: this.getPoolStats(),
      });

      return true;
    } catch (error) {
      this.connectionHealth = 0.0;
      this.lastHealthCheck = Date.now();

      this.logger.warn('Health check failed', {
        error: (error as Error).message,
        poolStats: this.getPoolStats(),
      });

      return false;
    }
  }
}
