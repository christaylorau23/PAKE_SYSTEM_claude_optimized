/**
 * PAKE System - Web Scraping Connector
 *
 * MCP-like connector for web scraping with comprehensive robots.txt compliance,
 * rate limiting, user agent rotation, and ethical scraping practices.
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import * as cheerio from 'cheerio';
import { URL } from 'url';
import {
  Connector,
  ConnectorRequest,
  ConnectorRequestType,
  ResponseEnvelope,
  ResponseStatus,
  ConnectorConfig,
} from './Connector';
import { sandboxEnforcer } from '../../policy/Sandbox';

export interface WebScrapeConfig extends ConnectorConfig {
  // User agent rotation
  userAgents: string[];
  rotateUserAgent: boolean;

  // Robots.txt compliance
  respectRobotsTxt: boolean;
  robotsTxtCacheTtl: number;
  defaultCrawlDelay: number;

  // Rate limiting
  requestDelay: number;
  concurrentRequests: number;
  domainDelays: Map<string, number>;

  // Content processing
  followRedirects: boolean;
  maxRedirects: number;
  maxContentSize: number;

  // Parsing options
  enableJavaScript: boolean;
  waitForContent: number;

  // Proxy settings
  proxyRotation: boolean;
  proxyList: string[];
}

export interface RobotsTxt {
  userAgent: string;
  disallow: string[];
  allow: string[];
  crawlDelay?: number;
  sitemaps: string[];
  host?: string;
}

export interface ScrapeResult {
  // Content
  html: string;
  text: string;
  title?: string;

  // Metadata
  url: string;
  finalUrl?: string;
  statusCode: number;
  headers: Record<string, string>;

  // Parsed data
  links: Array<{ href: string; text: string; rel?: string }>;
  images: Array<{ src: string; alt?: string; title?: string }>;
  meta: Record<string, string>;

  // Quality indicators
  contentLength: number;
  loadTime: number;
  lastModified?: string;
  etag?: string;

  // Structured data
  jsonLd?: any[];
  microdata?: any;
  openGraph?: Record<string, string>;
}

/**
 * Web scraping connector with ethical compliance
 */
export class WebScrapeConnector extends Connector {
  private readonly httpClient: AxiosInstance;
  private readonly robotsCache = new Map<
    string,
    { robots: RobotsTxt[]; fetchedAt: number }
  >();
  private readonly userAgentIndex = 0;
  private readonly domainRequestTimes = new Map<string, number>();

  // Default user agents for rotation
  private readonly defaultUserAgents = [
    'PAKE-WebScraper/1.0 (+https://pake-system.com/robots)',
    'Mozilla/5.0 (compatible; PAKE-Bot/1.0; +https://pake-system.com/robots)',
    'PAKE-Research-Bot/1.0 (Research purposes; +https://pake-system.com/contact)',
  ];

  constructor(name: string, config: Partial<WebScrapeConfig> = {}) {
    const webConfig: WebScrapeConfig = {
      ...config,
      userAgents: config.userAgents || [],
      rotateUserAgent: config.rotateUserAgent ?? true,
      respectRobotsTxt: config.respectRobotsTxt ?? true,
      robotsTxtCacheTtl: config.robotsTxtCacheTtl || 3600, // 1 hour
      defaultCrawlDelay: config.defaultCrawlDelay || 1000, // 1 second
      requestDelay: config.requestDelay || 1000,
      concurrentRequests: config.concurrentRequests || 1,
      domainDelays: config.domainDelays || new Map(),
      followRedirects: config.followRedirects ?? true,
      maxRedirects: config.maxRedirects || 5,
      maxContentSize: config.maxContentSize || 10 * 1024 * 1024, // 10MB
      enableJavaScript: config.enableJavaScript ?? false,
      waitForContent: config.waitForContent || 0,
      proxyRotation: config.proxyRotation ?? false,
      proxyList: config.proxyList || [],
    } as WebScrapeConfig;

    super(name, webConfig);

    // Initialize HTTP client with default configuration
    this.httpClient = axios.create({
      timeout: this.config.timeout,
      maxRedirects: (webConfig as WebScrapeConfig).maxRedirects,
      maxContentLength: (webConfig as WebScrapeConfig).maxContentSize,
      validateStatus: () => true, // Don't throw on HTTP errors
      headers: {
        Accept:
          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        Connection: 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
      },
    });

    this.logger.info('WebScrapeConnector initialized', {
      respectRobotsTxt: webConfig.respectRobotsTxt,
      userAgentCount: webConfig.userAgents.length,
      defaultCrawlDelay: webConfig.defaultCrawlDelay,
    });
  }

  /**
   * Fetch data from web sources
   */
  async fetch<T = ScrapeResult>(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<T>> {
    this.validateRequest(request);
    const startTime = Date.now();

    try {
      switch (request.type) {
        case ConnectorRequestType.SCRAPE_URL:
          return (await this.scrapeUrl(request)) as ResponseEnvelope<T>;

        case ConnectorRequestType.SCRAPE_SITEMAP:
          return (await this.scrapeSitemap(request)) as ResponseEnvelope<T>;

        case ConnectorRequestType.FETCH_RSS:
          return (await this.fetchRss(request)) as ResponseEnvelope<T>;

        default:
          throw new Error(`Unsupported request type: ${request.type}`);
      }
    } catch (error) {
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
   * Scrape a single URL
   */
  private async scrapeUrl(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<ScrapeResult>> {
    const startTime = Date.now();
    const url = request.target;

    this.logger.info('Starting URL scrape', { url, requestId: request.id });

    // Parse and validate URL
    const parsedUrl = new URL(url);
    const domain = parsedUrl.hostname;

    // Check sandbox policy compliance
    if (sandboxEnforcer) {
      const networkCheck = await sandboxEnforcer.validateNetworkAccess(
        this.name,
        request.id,
        url,
        'GET'
      );

      if (!networkCheck.allowed) {
        throw new Error(`Network access denied: ${networkCheck.reason}`);
      }
    }

    // Check robots.txt compliance
    if ((this.config as WebScrapeConfig).respectRobotsTxt) {
      const robotsCompliant = await this.checkRobotsCompliance(parsedUrl);
      if (!robotsCompliant.allowed) {
        throw new Error(`Blocked by robots.txt: ${parsedUrl.pathname}`);
      }

      // Apply crawl delay if specified
      if (robotsCompliant.crawlDelay) {
        await this.applyCrawlDelay(domain, robotsCompliant.crawlDelay);
      }
    }

    // Apply rate limiting
    await this.applyRateLimit(domain);

    // Configure request headers
    const headers = {
      ...this.config.headers,
      'User-Agent': this.getRotatedUserAgent(),
      Referer: parsedUrl.origin,
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    };

    try {
      // Make HTTP request
      const response = await this.httpClient.get(url, {
        headers,
        timeout: request.metadata.timeout || this.config.timeout,
      });

      // Process response
      const scrapeResult = await this.processHtmlResponse(response, parsedUrl);

      this.logger.info('URL scrape completed', {
        url,
        statusCode: response.status,
        contentLength: scrapeResult.contentLength,
        executionTime,
      });

      return this.createResponse(
        request,
        scrapeResult,
        ResponseStatus.SUCCESS,
        executionTime,
        {
          freshness: this.calculateFreshness(response.headers),
          confidence: this.calculateConfidence(scrapeResult),
          recordCount: 1,
        }
      );
    } catch (error) {
      this.logger.error('URL scrape failed', {
        url,
        error: (error as Error).message,
        executionTime,
      });

      throw error;
    }
  }

  /**
   * Scrape URLs from sitemap
   */
  private async scrapeSitemap(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<string[]>> {
    const startTime = Date.now();
    const sitemapUrl = request.target;

    this.logger.info('Fetching sitemap', { sitemapUrl, requestId: request.id });

    try {
      const response = await this.httpClient.get(sitemapUrl, {
        headers: {
          'User-Agent': this.getRotatedUserAgent(),
          Accept: 'application/xml,text/xml,*/*',
        },
      });

      const urls = this.parseSitemap(response.data);

      this.logger.info('Sitemap parsed', {
        sitemapUrl,
        urlCount: urls.length,
        executionTime,
      });

      return this.createResponse(
        request,
        urls,
        ResponseStatus.SUCCESS,
        executionTime,
        {
          recordCount: urls.length,
          freshness: this.calculateFreshness(response.headers),
        }
      );
    } catch (error) {
      throw error;
    }
  }

  /**
   * Fetch RSS feed
   */
  private async fetchRss(
    request: ConnectorRequest
  ): Promise<ResponseEnvelope<any[]>> {
    const startTime = Date.now();
    const rssUrl = request.target;

    try {
      const response = await this.httpClient.get(rssUrl, {
        headers: {
          'User-Agent': this.getRotatedUserAgent(),
          Accept: 'application/rss+xml,application/xml,text/xml,*/*',
        },
      });

      const items = this.parseRssFeed(response.data);

      return this.createResponse(
        request,
        items,
        ResponseStatus.SUCCESS,
        executionTime,
        {
          recordCount: items.length,
          freshness: this.calculateFreshness(response.headers),
        }
      );
    } catch (error) {
      throw error;
    }
  }

  /**
   * Check robots.txt compliance
   */
  private async checkRobotsCompliance(
    url: URL
  ): Promise<{ allowed: boolean; crawlDelay?: number }> {
    const domain = url.hostname;
    const robotsUrl = `${url.protocol}//${domain}/robots.txt`;

    try {
      // Check cache first
      const cached = this.robotsCache.get(domain);
      const now = Date.now();

      let robots: RobotsTxt[];

      if (
        cached &&
        now - cached.fetchedAt <
          (this.config as WebScrapeConfig).robotsTxtCacheTtl * 1000
      ) {
        robots = cached.robots;
      } else {
        // Fetch robots.txt
        robots = await this.fetchRobotsTxt(robotsUrl);
        this.robotsCache.set(domain, { robots, fetchedAt: now });
      }

      // Check compliance for current user agent
      const userAgent = this.getRotatedUserAgent();
      const applicable = this.findApplicableRobots(robots, userAgent);

      if (applicable) {
        // Check if path is disallowed
        const isDisallowed = applicable.disallow.some(pattern =>
          this.matchesPattern(url.pathname, pattern)
        );

        // Check if explicitly allowed (overrides disallow)
        const isAllowed = applicable.allow.some(pattern =>
          this.matchesPattern(url.pathname, pattern)
        );

        if (isDisallowed && !isAllowed) {
          return { allowed: false };
        }

        return {
          allowed: true,
          crawlDelay:
            applicable.crawlDelay ||
            (this.config as WebScrapeConfig).defaultCrawlDelay,
        };
      }

      return { allowed: true };
    } catch (error) {
      this.logger.warn('Failed to check robots.txt, allowing by default', {
        domain,
        error: (error as Error).message,
      });

      return { allowed: true };
    }
  }

  /**
   * Fetch and parse robots.txt
   */
  private async fetchRobotsTxt(robotsUrl: string): Promise<RobotsTxt[]> {
    try {
      const response = await this.httpClient.get(robotsUrl, {
        timeout: 10000, // 10 second timeout for robots.txt
        headers: {
          'User-Agent': this.getRotatedUserAgent(),
        },
      });

      return this.parseRobotsTxt(response.data);
    } catch (error) {
      this.logger.debug('robots.txt not accessible', {
        robotsUrl,
        error: (error as Error).message,
      });

      return []; // Empty robots.txt allows everything
    }
  }

  /**
   * Parse robots.txt content
   */
  private parseRobotsTxt(content: string): RobotsTxt[] {
    const robots: RobotsTxt[] = [];
    let current: Partial<RobotsTxt> = {};

    const lines = content.split('\n').map(line => line.trim());

    for (const line of lines) {
      if (!line || line.startsWith('#')) continue;

      const [directive, ...valueParts] = line.split(':');
      const value = valueParts.join(':').trim();

      switch (directive.toLowerCase()) {
        case 'user-agent':
          if (current.userAgent) {
            robots.push({
              userAgent: current.userAgent,
              disallow: current.disallow || [],
              allow: current.allow || [],
              crawlDelay: current.crawlDelay,
              sitemaps: current.sitemaps || [],
              host: current.host,
            });
          }
          current = { userAgent: value };
          break;

        case 'disallow':
          if (!current.disallow) current.disallow = [];
          current.disallow.push(value);
          break;

        case 'allow':
          if (!current.allow) current.allow = [];
          current.allow.push(value);
          break;

        case 'crawl-delay':
          current.crawlDelay = parseInt(value) * 1000; // Convert to ms
          break;

        case 'sitemap':
          if (!current.sitemaps) current.sitemaps = [];
          current.sitemaps.push(value);
          break;

        case 'host':
          current.host = value;
          break;
      }
    }

    // Add the last robot
    if (current.userAgent) {
      robots.push({
        userAgent: current.userAgent,
        disallow: current.disallow || [],
        allow: current.allow || [],
        crawlDelay: current.crawlDelay,
        sitemaps: current.sitemaps || [],
        host: current.host,
      });
    }

    return robots;
  }

  /**
   * Find applicable robots.txt rules for user agent
   */
  private findApplicableRobots(
    robots: RobotsTxt[],
    userAgent: string
  ): RobotsTxt | null {
    // Look for exact match first
    const exact = robots.find(
      r => r.userAgent.toLowerCase() === userAgent.toLowerCase()
    );
    if (exact) return exact;

    // Look for partial match
    const partial = robots.find(
      r =>
        userAgent.toLowerCase().includes(r.userAgent.toLowerCase()) ||
        r.userAgent.toLowerCase().includes(userAgent.toLowerCase())
    );
    if (partial) return partial;

    // Look for wildcard
    const wildcard = robots.find(r => r.userAgent === '*');
    if (wildcard) return wildcard;

    return null;
  }

  /**
   * Check if path matches robots.txt pattern
   */
  private matchesPattern(path: string, pattern: string): boolean {
    if (!pattern) return false;

    // Convert robots.txt pattern to regex
    const regexPattern = pattern
      .replace(/\*/g, '.*')
      .replace(/\?/g, '\\?')
      .replace(/\$/g, '$');

    const regex = new RegExp('^' + regexPattern);
    return regex.test(path);
  }

  /**
   * Apply crawl delay for domain
   */
  private async applyCrawlDelay(
    domain: string,
    crawlDelay: number
  ): Promise<void> {
    const lastRequestTime = this.domainRequestTimes.get(domain) || 0;
    const timeSinceLastRequest = Date.now() - lastRequestTime;

    if (timeSinceLastRequest < crawlDelay) {
      const waitTime = crawlDelay - timeSinceLastRequest;

      this.logger.debug('Applying crawl delay', {
        domain,
        crawlDelay,
        waitTime,
      });

      await this.sleep(waitTime);
    }

    this.domainRequestTimes.set(domain, Date.now());
  }

  /**
   * Apply general rate limiting
   */
  private async applyRateLimit(domain: string): Promise<void> {
    const config = this.config as WebScrapeConfig;
    const domainDelay = config.domainDelays.get(domain) || config.requestDelay;

    await this.applyCrawlDelay(domain, domainDelay);
  }

  /**
   * Get rotated user agent
   */
  private getRotatedUserAgent(): string {
    const config = this.config as WebScrapeConfig;
    const userAgents =
      config.userAgents.length > 0 ? config.userAgents : this.defaultUserAgents;

    if (!config.rotateUserAgent) {
      return userAgents[0];
    }

    return userAgents[this.userAgentIndex % userAgents.length];
  }

  /**
   * Process HTML response and extract data
   */
  private async processHtmlResponse(
    response: AxiosResponse,
    url: URL
  ): Promise<ScrapeResult> {
    const html = response.data;
    const $ = cheerio.load(html);

    // Extract basic content
    const title = $('title').text().trim();
    const text = $('body').text().replace(/\s+/g, ' ').trim();

    // Extract links
    const links = $('a[href]')
      .map((_, el) => ({
        href: $(el).attr('href') || '',
        text: $(el).text().trim(),
        rel: $(el).attr('rel'),
      }))
      .get();

    // Extract images
    const images = $('img[src]')
      .map((_, el) => ({
        src: $(el).attr('src') || '',
        alt: $(el).attr('alt'),
        title: $(el).attr('title'),
      }))
      .get();

    // Extract meta tags
    const meta: Record<string, string> = {};
    $('meta').each((_, el) => {
      const name = $(el).attr('name') || $(el).attr('property');
      const content = $(el).attr('content');
      if (name && content) {
        meta[name] = content;
      }
    });

    // Extract JSON-LD structured data
    const jsonLd: any[] = [];
    $('script[type="application/ld+json"]').each((_, el) => {
      try {
        const data = JSON.parse($(el).html() || '');
        jsonLd.push(data);
      } catch {
        // Ignore invalid JSON-LD
      }
    });

    // Extract Open Graph data
    const openGraph: Record<string, string> = {};
    $('meta[property^="og:"]').each((_, el) => {
      const property = $(el).attr('property');
      const content = $(el).attr('content');
      if (property && content) {
        openGraph[property] = content;
      }
    });

    return {
      html,
      text,
      title,
      url: url.href,
      finalUrl: response.request?.res?.responseUrl,
      statusCode: response.status,
      headers: response.headers,
      links,
      images,
      meta,
      contentLength: html.length,
      loadTime: Date.now(), // Approximate
      lastModified: response.headers['last-modified'],
      etag: response.headers['etag'],
      jsonLd,
      openGraph,
    };
  }

  /**
   * Parse sitemap XML
   */
  private parseSitemap(xml: string): string[] {
    const $ = cheerio.load(xml, { xmlMode: true });
    const urls: string[] = [];

    // Handle regular sitemap
    $('url loc').each((_, el) => {
      urls.push($(el).text());
    });

    // Handle sitemap index
    $('sitemap loc').each((_, el) => {
      urls.push($(el).text());
    });

    return urls;
  }

  /**
   * Parse RSS feed
   */
  private parseRssFeed(xml: string): any[] {
    const $ = cheerio.load(xml, { xmlMode: true });
    const items: any[] = [];

    $('item').each((_, el) => {
      const item = {
        title: $(el).find('title').text(),
        description: $(el).find('description').text(),
        link: $(el).find('link').text(),
        pubDate: $(el).find('pubDate').text(),
        guid: $(el).find('guid').text(),
      };
      items.push(item);
    });

    return items;
  }

  /**
   * Calculate content freshness score
   */
  private calculateFreshness(headers: any): number {
    const lastModified = headers['last-modified'];
    if (lastModified) {
      const lastModifiedTime = new Date(lastModified).getTime();
      const now = Date.now();
      return Math.max(0, now - lastModifiedTime) / 1000; // seconds
    }

    return 0; // Unknown freshness
  }

  /**
   * Calculate content confidence score
   */
  private calculateConfidence(result: ScrapeResult): number {
    let score = 0.5; // Base score

    // Higher confidence for successful responses
    if (result.statusCode >= 200 && result.statusCode < 300) {
      score += 0.3;
    }

    // Higher confidence for content with title
    if (result.title && result.title.length > 0) {
      score += 0.1;
    }

    // Higher confidence for substantial content
    if (result.text.length > 1000) {
      score += 0.1;
    }

    return Math.min(1.0, score);
  }

  /**
   * Map error to appropriate response status
   */
  private mapErrorToStatus(error: Error): ResponseStatus {
    const message = error.message.toLowerCase();

    if (message.includes('timeout')) {
      return ResponseStatus.TIMEOUT;
    }
    if (message.includes('rate limit') || message.includes('429')) {
      return ResponseStatus.RATE_LIMITED;
    }
    if (message.includes('401') || message.includes('unauthorized')) {
      return ResponseStatus.UNAUTHORIZED;
    }
    if (message.includes('403') || message.includes('forbidden')) {
      return ResponseStatus.FORBIDDEN;
    }
    if (message.includes('404') || message.includes('not found')) {
      return ResponseStatus.NOT_FOUND;
    }

    return ResponseStatus.ERROR;
  }

  /**
   * Check if error is retryable
   */
  private isRetryableError(error: Error): boolean {
    const message = error.message.toLowerCase();

    // Network errors are usually retryable
    if (message.includes('network') || message.includes('connection')) {
      return true;
    }

    // Timeout errors are retryable
    if (message.includes('timeout')) {
      return true;
    }

    // Rate limit errors are retryable with delay
    if (message.includes('rate limit') || message.includes('429')) {
      return true;
    }

    // Server errors (5xx) are retryable
    if (
      message.includes('500') ||
      message.includes('502') ||
      message.includes('503')
    ) {
      return true;
    }

    return false;
  }

  /**
   * Initialize connection
   */
  async connect(): Promise<void> {
    this.isConnected = true;
    this.logger.info('WebScrapeConnector connected');
  }

  /**
   * Close connection
   */
  async disconnect(): Promise<void> {
    this.isConnected = false;
    this.robotsCache.clear();
    this.domainRequestTimes.clear();
    this.logger.info('WebScrapeConnector disconnected');
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<boolean> {
    try {
      // Test connectivity with a simple HTTP request
      await this.httpClient.get('https://httpbin.org/get', {
        timeout: 5000,
        headers: {
          'User-Agent': this.getRotatedUserAgent(),
        },
      });

      this.connectionHealth = 1.0;
      this.lastHealthCheck = Date.now();
      return true;
    } catch (error) {
      this.logger.warn('Health check failed', {
        error: (error as Error).message,
      });

      this.connectionHealth = 0.0;
      this.lastHealthCheck = Date.now();
      return false;
    }
  }
}
