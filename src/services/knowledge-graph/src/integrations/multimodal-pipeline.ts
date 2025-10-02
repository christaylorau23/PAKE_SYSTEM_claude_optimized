import { EventEmitter } from 'events';
import { GraphConstructor } from '@/services/graph-constructor';
import { EntityExtractor } from '@/services/entity-extractor';
import { GraphManager } from '@/services/graph-manager';
import { Document, Entity, ProcessingResult } from '@/types/graph';
import { logger, integrationLogger } from '@/utils/logger';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

interface MultiModalDocument {
  id: string;
  filePath: string;
  fileName: string;
  contentType: string;
  size: number;
  uploadedAt: string;
  processedAt?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processingResults?: {
    text?: {
      content: string;
      confidence: number;
      language: string;
    };
    image?: {
      description: string;
      objects: Array<{ name: string; confidence: number; bbox?: number[] }>;
      text: string;
      faces: number;
      scenes: string[];
    };
    audio?: {
      transcript: string;
      confidence: number;
      duration: number;
      language: string;
      speakers: number;
    };
    video?: {
      transcript: string;
      scenes: Array<{
        timestamp: number;
        description: string;
        objects: string[];
      }>;
      duration: number;
      keyframes: string[];
    };
  };
}

interface PipelineConfig {
  multimodalApiUrl: string;
  pollInterval: number;
  batchSize: number;
  retryAttempts: number;
  retryDelay: number;
  enableRealTimeSync: boolean;
  processingQueue: {
    maxConcurrency: number;
    priority: 'fifo' | 'lifo' | 'priority';
  };
}

export class MultiModalPipelineIntegration extends EventEmitter {
  private graphConstructor: GraphConstructor;
  private entityExtractor: EntityExtractor;
  private graphManager: GraphManager;
  private config: PipelineConfig;
  private isRunning: boolean = false;
  private processingQueue: Map<string, MultiModalDocument> = new Map();
  private pollTimer?: NodeJS.Timeout;
  private activeProcessing: Set<string> = new Set();

  constructor(
    graphConstructor: GraphConstructor,
    entityExtractor: EntityExtractor,
    graphManager: GraphManager,
    config: Partial<PipelineConfig> = {}
  ) {
    super();
    this.graphConstructor = graphConstructor;
    this.entityExtractor = entityExtractor;
    this.graphManager = graphManager;

    this.config = {
      multimodalApiUrl:
        process.env.MULTIMODAL_API_URL || 'http://localhost:3003/api',
      pollInterval: 5000, // 5 seconds
      batchSize: 10,
      retryAttempts: 3,
      retryDelay: 2000,
      enableRealTimeSync: true,
      processingQueue: {
        maxConcurrency: 5,
        priority: 'priority',
      },
      ...config,
    };

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    // Handle graph construction events
    this.graphConstructor.on(
      'document_processed',
      this.handleDocumentProcessed.bind(this)
    );
    this.graphConstructor.on(
      'processing_error',
      this.handleProcessingError.bind(this)
    );

    // Handle entity extraction events
    this.entityExtractor.on(
      'entities_extracted',
      this.handleEntitiesExtracted.bind(this)
    );
    this.entityExtractor.on(
      'extraction_error',
      this.handleExtractionError.bind(this)
    );

    // Handle graceful shutdown
    process.on('SIGINT', this.shutdown.bind(this));
    process.on('SIGTERM', this.shutdown.bind(this));
  }

  async start(): Promise<void> {
    if (this.isRunning) {
      logger.warn('Pipeline integration is already running');
      return;
    }

    try {
      integrationLogger.info('Starting MultiModal Pipeline Integration...');

      // Test connection to multimodal API
      await this.testMultiModalConnection();

      // Initialize graph schema if needed
      await this.initializeGraphSchema();

      // Load pending documents
      await this.loadPendingDocuments();

      // Start polling for new documents
      if (this.config.enableRealTimeSync) {
        this.startPolling();
      }

      this.isRunning = true;
      integrationLogger.info(
        'MultiModal Pipeline Integration started successfully'
      );
      this.emit('started');
    } catch (error) {
      integrationLogger.error('Failed to start pipeline integration:', error);
      throw error;
    }
  }

  async stop(): Promise<void> {
    if (!this.isRunning) return;

    integrationLogger.info('Stopping MultiModal Pipeline Integration...');

    this.isRunning = false;

    // Stop polling
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = undefined;
    }

    // Wait for active processing to complete
    await this.waitForActiveProcessing();

    integrationLogger.info('MultiModal Pipeline Integration stopped');
    this.emit('stopped');
  }

  private async testMultiModalConnection(): Promise<void> {
    try {
      const response = await axios.get(
        `${this.config.multimodalApiUrl}/health`,
        {
          timeout: 5000,
        }
      );

      if (response.status !== 200) {
        throw new Error(
          `MultiModal API health check failed: ${response.status}`
        );
      }

      integrationLogger.info('MultiModal API connection verified');
    } catch (error) {
      integrationLogger.error('MultiModal API connection failed:', error);
      throw new Error('Failed to connect to MultiModal API');
    }
  }

  private async initializeGraphSchema(): Promise<void> {
    try {
      // Ensure required node types and relationships exist
      const schemaQueries = [
        'CREATE CONSTRAINT multimodal_doc_id_unique IF NOT EXISTS FOR (d:MultiModalDocument) REQUIRE d.id IS UNIQUE',
        'CREATE INDEX multimodal_doc_content_type IF NOT EXISTS FOR (d:MultiModalDocument) ON (d.contentType)',
        'CREATE INDEX multimodal_doc_status IF NOT EXISTS FOR (d:MultiModalDocument) ON (d.status)',
        'CREATE INDEX multimodal_doc_processed_at IF NOT EXISTS FOR (d:MultiModalDocument) ON (d.processedAt)',
      ];

      for (const query of schemaQueries) {
        await this.graphManager.executeQuery(query);
      }

      integrationLogger.info(
        'Graph schema initialized for multimodal integration'
      );
    } catch (error) {
      integrationLogger.error('Failed to initialize graph schema:', error);
      throw error;
    }
  }

  private startPolling(): void {
    this.pollTimer = setInterval(() => {
      this.pollForNewDocuments().catch(error => {
        integrationLogger.error('Polling error:', error);
      });
    }, this.config.pollInterval);

    integrationLogger.info(
      `Started polling every ${this.config.pollInterval}ms`
    );
  }

  private async pollForNewDocuments(): Promise<void> {
    try {
      const response = await axios.get(
        `${this.config.multimodalApiUrl}/documents/processed`,
        {
          params: {
            limit: this.config.batchSize,
            status: 'completed',
          },
          timeout: 10000,
        }
      );

      const documents: MultiModalDocument[] = response.data.documents || [];

      if (documents.length > 0) {
        integrationLogger.info(
          `Found ${documents.length} newly processed documents`
        );

        for (const doc of documents) {
          if (
            !this.processingQueue.has(doc.id) &&
            !this.activeProcessing.has(doc.id)
          ) {
            this.processingQueue.set(doc.id, doc);
            this.processDocumentAsync(doc);
          }
        }
      }
    } catch (error) {
      integrationLogger.error('Failed to poll for new documents:', error);
    }
  }

  private async loadPendingDocuments(): Promise<void> {
    try {
      // Query graph for documents that need processing
      const query = `
        MATCH (d:MultiModalDocument)
        WHERE d.graphProcessingStatus IS NULL OR d.graphProcessingStatus = 'pending'
        RETURN d
        LIMIT ${this.config.batchSize * 2}
      `;

      const result = await this.graphManager.executeQuery(query);

      for (const record of result) {
        const docData = record.d.properties;
        const document: MultiModalDocument = {
          id: docData.id,
          filePath: docData.filePath,
          fileName: docData.fileName,
          contentType: docData.contentType,
          size: docData.size,
          uploadedAt: docData.uploadedAt,
          processedAt: docData.processedAt,
          status: docData.status || 'pending',
          processingResults: docData.processingResults
            ? JSON.parse(docData.processingResults)
            : undefined,
        };

        if (document.status === 'completed' && document.processingResults) {
          this.processingQueue.set(document.id, document);
          this.processDocumentAsync(document);
        }
      }

      integrationLogger.info(
        `Loaded ${this.processingQueue.size} pending documents for graph processing`
      );
    } catch (error) {
      integrationLogger.error('Failed to load pending documents:', error);
    }
  }

  private async processDocumentAsync(
    document: MultiModalDocument
  ): Promise<void> {
    if (
      this.activeProcessing.size >= this.config.processingQueue.maxConcurrency
    ) {
      // Queue is full, document will be processed later
      return;
    }

    this.activeProcessing.add(document.id);
    this.processingQueue.delete(document.id);

    try {
      await this.processDocument(document);
    } catch (error) {
      integrationLogger.error(
        `Failed to process document ${document.id}:`,
        error
      );
      this.emit('document_error', { document, error });
    } finally {
      this.activeProcessing.delete(document.id);

      // Process next queued document
      if (this.processingQueue.size > 0) {
        const nextDoc = this.processingQueue.values().next().value;
        if (nextDoc) {
          this.processDocumentAsync(nextDoc);
        }
      }
    }
  }

  private async processDocument(
    multiModalDoc: MultiModalDocument
  ): Promise<void> {
    integrationLogger.info(
      `Processing document: ${multiModalDoc.fileName} (${multiModalDoc.contentType})`
    );

    const startTime = Date.now();

    try {
      // Mark document as being processed
      await this.updateDocumentStatus(multiModalDoc.id, 'processing');

      // Create document node in graph
      const graphDocument: Document = {
        id: multiModalDoc.id,
        title: multiModalDoc.fileName,
        content: this.extractTextContent(multiModalDoc),
        filePath: multiModalDoc.filePath,
        contentType: multiModalDoc.contentType,
        size: multiModalDoc.size,
        createdAt: new Date(multiModalDoc.uploadedAt),
        updatedAt: new Date(),
        metadata: {
          originalDocument: multiModalDoc,
          processingResults: multiModalDoc.processingResults,
          multiModalType: this.determineMultiModalType(multiModalDoc),
        },
      };

      // Add document to graph
      await this.graphManager.addNode(graphDocument);

      // Extract entities from all modalities
      const entities = await this.extractMultiModalEntities(
        multiModalDoc,
        graphDocument
      );

      // Build graph connections
      const processingResult: ProcessingResult = {
        documentId: graphDocument.id,
        entities,
        relationships: [],
        concepts: [],
        processingTime: Date.now() - startTime,
        timestamp: new Date(),
      };

      // Process through graph constructor
      await this.graphConstructor.processDocument(
        graphDocument,
        processingResult
      );

      // Mark as completed
      await this.updateDocumentStatus(multiModalDoc.id, 'completed');

      integrationLogger.info(
        `Successfully processed document ${multiModalDoc.fileName} in ${Date.now() - startTime}ms`
      );
      this.emit('document_processed', {
        document: multiModalDoc,
        processingResult,
      });
    } catch (error) {
      await this.updateDocumentStatus(multiModalDoc.id, 'failed');
      throw error;
    }
  }

  private extractTextContent(document: MultiModalDocument): string {
    const results = document.processingResults;
    if (!results) return '';

    const textParts: string[] = [];

    // Text content
    if (results.text?.content) {
      textParts.push(results.text.content);
    }

    // OCR from images
    if (results.image?.text) {
      textParts.push(`[OCR] ${results.image.text}`);
    }

    // Audio transcription
    if (results.audio?.transcript) {
      textParts.push(`[Audio] ${results.audio.transcript}`);
    }

    // Video transcription
    if (results.video?.transcript) {
      textParts.push(`[Video] ${results.video.transcript}`);
    }

    return textParts.join('\n\n');
  }

  private async extractMultiModalEntities(
    multiModalDoc: MultiModalDocument,
    graphDoc: Document
  ): Promise<Entity[]> {
    const allEntities: Entity[] = [];
    const results = multiModalDoc.processingResults;

    if (!results) return allEntities;

    try {
      // Extract from text content
      if (results.text?.content) {
        const textEntities = await this.entityExtractor.extractFromText(
          results.text.content,
          graphDoc.id
        );
        allEntities.push(...textEntities.entities);
      }

      // Extract from image analysis
      if (results.image) {
        const imageEntities = await this.extractImageEntities(
          results.image,
          graphDoc.id
        );
        allEntities.push(...imageEntities);
      }

      // Extract from audio analysis
      if (results.audio) {
        const audioEntities = await this.extractAudioEntities(
          results.audio,
          graphDoc.id
        );
        allEntities.push(...audioEntities);
      }

      // Extract from video analysis
      if (results.video) {
        const videoEntities = await this.extractVideoEntities(
          results.video,
          graphDoc.id
        );
        allEntities.push(...videoEntities);
      }

      integrationLogger.info(
        `Extracted ${allEntities.length} entities from multimodal document ${multiModalDoc.fileName}`
      );
      return allEntities;
    } catch (error) {
      integrationLogger.error('Failed to extract multimodal entities:', error);
      return allEntities;
    }
  }

  private async extractImageEntities(
    imageResults: any,
    documentId: string
  ): Promise<Entity[]> {
    const entities: Entity[] = [];

    // Object entities
    if (imageResults.objects) {
      for (const obj of imageResults.objects) {
        if (obj.confidence >= 0.7) {
          entities.push({
            id: uuidv4(),
            name: obj.name,
            type: 'OBJECT',
            confidence: obj.confidence,
            source: documentId,
            properties: {
              detectionConfidence: obj.confidence,
              boundingBox: obj.bbox,
              modality: 'image',
            },
          });
        }
      }
    }

    // Scene entities
    if (imageResults.scenes) {
      for (const scene of imageResults.scenes) {
        entities.push({
          id: uuidv4(),
          name: scene,
          type: 'SCENE',
          confidence: 0.8,
          source: documentId,
          properties: {
            modality: 'image',
          },
        });
      }
    }

    // OCR text entities
    if (imageResults.text) {
      const ocrEntities = await this.entityExtractor.extractFromText(
        imageResults.text,
        documentId
      );
      entities.push(
        ...ocrEntities.entities.map(e => ({
          ...e,
          properties: {
            ...e.properties,
            modality: 'image-ocr',
          },
        }))
      );
    }

    return entities;
  }

  private async extractAudioEntities(
    audioResults: any,
    documentId: string
  ): Promise<Entity[]> {
    const entities: Entity[] = [];

    // Speaker entities
    if (audioResults.speakers && audioResults.speakers > 0) {
      for (let i = 1; i <= audioResults.speakers; i++) {
        entities.push({
          id: uuidv4(),
          name: `Speaker ${i}`,
          type: 'PERSON',
          confidence: 0.8,
          source: documentId,
          properties: {
            modality: 'audio',
            speakerId: i,
          },
        });
      }
    }

    // Extract entities from transcript
    if (audioResults.transcript) {
      const transcriptEntities = await this.entityExtractor.extractFromText(
        audioResults.transcript,
        documentId
      );
      entities.push(
        ...transcriptEntities.entities.map(e => ({
          ...e,
          properties: {
            ...e.properties,
            modality: 'audio-transcript',
          },
        }))
      );
    }

    return entities;
  }

  private async extractVideoEntities(
    videoResults: any,
    documentId: string
  ): Promise<Entity[]> {
    const entities: Entity[] = [];

    // Scene-based entities
    if (videoResults.scenes) {
      for (const scene of videoResults.scenes) {
        // Scene entity
        entities.push({
          id: uuidv4(),
          name: scene.description,
          type: 'SCENE',
          confidence: 0.8,
          source: documentId,
          properties: {
            timestamp: scene.timestamp,
            modality: 'video',
          },
        });

        // Objects in scene
        if (scene.objects) {
          for (const obj of scene.objects) {
            entities.push({
              id: uuidv4(),
              name: obj,
              type: 'OBJECT',
              confidence: 0.7,
              source: documentId,
              properties: {
                timestamp: scene.timestamp,
                modality: 'video',
              },
            });
          }
        }
      }
    }

    // Extract entities from transcript
    if (videoResults.transcript) {
      const transcriptEntities = await this.entityExtractor.extractFromText(
        videoResults.transcript,
        documentId
      );
      entities.push(
        ...transcriptEntities.entities.map(e => ({
          ...e,
          properties: {
            ...e.properties,
            modality: 'video-transcript',
          },
        }))
      );
    }

    return entities;
  }

  private determineMultiModalType(document: MultiModalDocument): string {
    const results = document.processingResults;
    if (!results) return 'unknown';

    const hasText = !!results.text;
    const hasImage = !!results.image;
    const hasAudio = !!results.audio;
    const hasVideo = !!results.video;

    if (hasVideo) return hasAudio ? 'video-with-audio' : 'video';
    if (hasAudio && hasImage) return 'multimedia';
    if (hasAudio) return 'audio';
    if (hasImage && hasText) return 'document-with-images';
    if (hasImage) return 'image';
    if (hasText) return 'text';

    return 'unknown';
  }

  private async updateDocumentStatus(
    documentId: string,
    status: string
  ): Promise<void> {
    const query = `
      MATCH (d:MultiModalDocument {id: $documentId})
      SET d.graphProcessingStatus = $status,
          d.graphProcessedAt = datetime()
      RETURN d
    `;

    await this.graphManager.executeQuery(query, { documentId, status });
  }

  private async waitForActiveProcessing(
    timeout: number = 30000
  ): Promise<void> {
    const startTime = Date.now();

    while (this.activeProcessing.size > 0) {
      if (Date.now() - startTime > timeout) {
        integrationLogger.warn(
          `Timeout waiting for active processing to complete. ${this.activeProcessing.size} documents still processing.`
        );
        break;
      }

      await new Promise(resolve => setTimeout(resolve, 100));
    }
  }

  private async shutdown(): Promise<void> {
    integrationLogger.info('Shutting down MultiModal Pipeline Integration...');
    await this.stop();
  }

  // Event handlers
  private handleDocumentProcessed(result: any): void {
    integrationLogger.info(`Document processed in graph: ${result.documentId}`);
    this.emit('graph_document_processed', result);
  }

  private handleProcessingError(error: any): void {
    integrationLogger.error('Graph processing error:', error);
    this.emit('graph_processing_error', error);
  }

  private handleEntitiesExtracted(result: any): void {
    integrationLogger.info(
      `Entities extracted: ${result.entities.length} from ${result.documentId}`
    );
    this.emit('entities_extracted', result);
  }

  private handleExtractionError(error: any): void {
    integrationLogger.error('Entity extraction error:', error);
    this.emit('extraction_error', error);
  }

  // Public API
  async getProcessingStats(): Promise<any> {
    return {
      queueSize: this.processingQueue.size,
      activeProcessing: this.activeProcessing.size,
      isRunning: this.isRunning,
      config: this.config,
    };
  }

  async forceProcessDocument(documentId: string): Promise<void> {
    try {
      const response = await axios.get(
        `${this.config.multimodalApiUrl}/documents/${documentId}`
      );
      const document = response.data.document;

      if (document && document.status === 'completed') {
        await this.processDocument(document);
      } else {
        throw new Error('Document not ready for processing');
      }
    } catch (error) {
      integrationLogger.error(
        `Failed to force process document ${documentId}:`,
        error
      );
      throw error;
    }
  }
}

export default MultiModalPipelineIntegration;
