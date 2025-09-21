/**
 * PAKE System - WebScrapeConnector Tests
 *
 * Comprehensive tests for web scraping functionality including robots.txt compliance,
 * rate limiting, content extraction, and error handling.
 */

import {
  describe,
  beforeEach,
  afterEach,
  it,
  expect,
  jest,
  beforeAll,
  afterAll,
} from '@jest/globals';
import nock from 'nock';
import { WebScrapeConnector } from '../src/WebScrapeConnector';
import { ConnectorRequestType, ResponseStatus } from '../src/Connector';
import {
  sampleRequests,
  testConfigs,
  sampleResponses,
  errorScenarios,
  testHelpers,
} from './fixtures/testData';

describe('WebScrapeConnector', () => {
  let connector: WebScrapeConnector;
  let mockServer: nock.Scope;

  beforeAll(() => {
    // Disable real HTTP requests
    nock.disableNetConnect();
  });

  afterAll(() => {
    nock.enableNetConnect();
  });

  beforeEach(async () => {
    // Clean all mocks between tests
    nock.cleanAll();

    connector = new WebScrapeConnector('test-webscraper', {
      ...testConfigs.webscraper,
      timeout: 5000,
      maxRetries: 2,
      retryDelay: 100, // Fast retries for tests
    });

    await connector.connect();
  });

  afterEach(async () => {
    await connector.disconnect();
    nock.cleanAll();
  });

  describe('Basic Web Scraping', () => {
    it('should successfully scrape a basic HTML page', async () => {
      const testHtml = `
        <!DOCTYPE html>
        <html>
          <head>
            <title>Test Page</title>
            <meta name="description" content="Test page description" />
          </head>
          <body>
            <h1>Main Heading</h1>
            <p>This is test content for web scraping.</p>
            <a href="/link1">Internal Link</a>
            <a href="https://external.com/link2">External Link</a>
          </body>
        </html>
      `;

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404) // No robots.txt
        .get('/')
        .reply(200, testHtml, {
          'content-type': 'text/html; charset=utf-8',
          'last-modified': 'Mon, 15 Jan 2024 10:30:00 GMT',
        });

      const request = sampleRequests.webScrape.basic;
      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.status).toBe(ResponseStatus.SUCCESS);
      expect(response.data).toMatchObject({
        url: 'https://example.com',
        title: 'Test Page',
        content: expect.stringContaining('This is test content'),
        links: expect.arrayContaining([
          expect.objectContaining({
            href: expect.stringMatching(/link1/),
            text: 'Internal Link',
          }),
        ]),
        metadata: expect.objectContaining({
          contentType: 'text/html; charset=utf-8',
        }),
      });

      expect(mockServer.isDone()).toBe(true);
    });

    it('should extract JSON from API endpoints', async () => {
      const testData = {
        status: 'success',
        data: [
          { id: 1, name: 'Item 1' },
          { id: 2, name: 'Item 2' },
        ],
        metadata: { total: 2, page: 1 },
      };

      mockServer = nock('https://api.example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/data')
        .matchHeader('authorization', 'Bearer test-token')
        .matchHeader('x-custom-header', 'test-value')
        .reply(200, testData, {
          'content-type': 'application/json',
        });

      const request = sampleRequests.webScrape.withHeaders;
      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.json).toEqual(testData);
      expect(response.data.metadata.contentType).toBe('application/json');
      expect(mockServer.isDone()).toBe(true);
    });

    it('should handle redirects properly', async () => {
      const finalContent =
        '<html><body><h1>Redirected Content</h1></body></html>';

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/redirect')
        .reply(302, null, {
          location: 'https://example.com/final',
        })
        .get('/final')
        .reply(200, finalContent, {
          'content-type': 'text/html',
        });

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/redirect',
        parameters: { followRedirects: true },
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.finalUrl).toBe('https://example.com/final');
      expect(response.data.content).toContain('Redirected Content');
      expect(mockServer.isDone()).toBe(true);
    });
  });

  describe('Robots.txt Compliance', () => {
    it('should respect robots.txt disallow rules', async () => {
      const robotsTxt = `
        User-agent: *
        Disallow: /private/
        Disallow: /admin/
        Allow: /public/
        Crawl-delay: 1
      `;

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(200, robotsTxt, {
          'content-type': 'text/plain',
        });

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/private/secret.html',
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(false);
      expect(response.status).toBe(ResponseStatus.FORBIDDEN);
      expect(response.error?.code).toBe('ROBOTS_TXT_BLOCKED');
      expect(mockServer.isDone()).toBe(true);
    });

    it('should allow access when robots.txt permits', async () => {
      const robotsTxt = `
        User-agent: *
        Disallow: /private/
        Allow: /public/
      `;

      const publicContent = '<html><body><h1>Public Content</h1></body></html>';

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(200, robotsTxt)
        .get('/public/page.html')
        .reply(200, publicContent);

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/public/page.html',
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.content).toContain('Public Content');
      expect(mockServer.isDone()).toBe(true);
    });

    it('should respect crawl-delay from robots.txt', async () => {
      const robotsTxt = `
        User-agent: *
        Crawl-delay: 2
      `;

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(200, robotsTxt)
        .get('/page1')
        .reply(200, '<html><body>Page 1</body></html>')
        .get('/page2')
        .reply(200, '<html><body>Page 2</body></html>');

      const request1 = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/page1',
      });

      const request2 = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/page2',
      });

      const startTime = Date.now();
      await connector.fetch(request1);
      await connector.fetch(request2);
      const endTime = Date.now();

      // Should have waited at least 2 seconds between requests
      expect(endTime - startTime).toBeGreaterThan(1900); // Allow some tolerance
      expect(mockServer.isDone()).toBe(true);
    });

    it('should handle missing robots.txt gracefully', async () => {
      const content = '<html><body><h1>Content</h1></body></html>';

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404) // No robots.txt file
        .get('/page')
        .reply(200, content);

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/page',
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.content).toContain('Content');
      expect(mockServer.isDone()).toBe(true);
    });
  });

  describe('User Agent Rotation', () => {
    it('should rotate user agents across requests', async () => {
      const userAgents = new Set<string>();

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .times(5)
        .reply(404)
        .get('/test')
        .times(5)
        .reply(function () {
          const userAgent = this.req.headers['user-agent'] as string;
          userAgents.add(userAgent);
          return [200, '<html><body>Test</body></html>'];
        });

      // Make multiple requests to trigger user agent rotation
      for (let i = 0; i < 5; i++) {
        const request = testHelpers.createMockConnectorRequest({
          type: ConnectorRequestType.SCRAPE_URL,
          target: 'https://example.com/test',
        });
        await connector.fetch(request);
      }

      // Should have used multiple different user agents
      expect(userAgents.size).toBeGreaterThan(1);
      expect(mockServer.isDone()).toBe(true);
    });
  });

  describe('Rate Limiting and Backoff', () => {
    it('should implement exponential backoff on rate limit responses', async () => {
      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/rate-limited')
        .reply(429, 'Rate Limited', {
          'retry-after': '2',
        })
        .get('/rate-limited')
        .reply(429, 'Rate Limited', {
          'retry-after': '1',
        })
        .get('/rate-limited')
        .reply(200, '<html><body>Success</body></html>');

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/rate-limited',
        config: {
          timeout: 10000,
          maxRetries: 3,
          retryDelay: 500,
        },
      });

      const startTime = Date.now();
      const response = await connector.fetch(request);
      const endTime = Date.now();

      expect(response.success).toBe(true);
      expect(response.data.content).toContain('Success');
      // Should have waited for retry-after headers
      expect(endTime - startTime).toBeGreaterThan(2500);
      expect(mockServer.isDone()).toBe(true);
    });

    it('should respect concurrent request limits', async () => {
      const requestTimes: number[] = [];

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .times(3)
        .reply(404)
        .get(/\/concurrent\/\d+/)
        .times(3)
        .reply(function () {
          requestTimes.push(Date.now());
          return [200, '<html><body>Response</body></html>'];
        });

      // Make concurrent requests
      const promises = [1, 2, 3].map(i =>
        connector.fetch(
          testHelpers.createMockConnectorRequest({
            type: ConnectorRequestType.SCRAPE_URL,
            target: `https://example.com/concurrent/${i}`,
          })
        )
      );

      await Promise.all(promises);

      // With maxConcurrency: 2, the third request should be delayed
      const timeDiffs = requestTimes
        .slice(1)
        .map((time, i) => time - requestTimes[i]);
      expect(timeDiffs.some(diff => diff > 100)).toBe(true); // At least one request was delayed
      expect(mockServer.isDone()).toBe(true);
    });
  });

  describe('Sitemap Parsing', () => {
    it('should parse and extract URLs from sitemap.xml', async () => {
      const sitemapXml = `
        <?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url>
            <loc>https://example.com/page1</loc>
            <lastmod>2024-01-15</lastmod>
            <priority>0.8</priority>
          </url>
          <url>
            <loc>https://example.com/page2</loc>
            <lastmod>2024-01-10</lastmod>
            <priority>0.6</priority>
          </url>
        </urlset>
      `;

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/sitemap.xml')
        .reply(200, sitemapXml, {
          'content-type': 'application/xml',
        });

      const request = sampleRequests.webScrape.sitemap;
      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.urls).toHaveLength(2);
      expect(response.data.urls).toEqual(
        expect.arrayContaining([
          expect.objectContaining({
            loc: 'https://example.com/page1',
            lastmod: '2024-01-15',
            priority: '0.8',
          }),
          expect.objectContaining({
            loc: 'https://example.com/page2',
            lastmod: '2024-01-10',
            priority: '0.6',
          }),
        ])
      );
      expect(mockServer.isDone()).toBe(true);
    });

    it('should handle sitemap index files', async () => {
      const sitemapIndexXml = `
        <?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <sitemap>
            <loc>https://example.com/sitemap1.xml</loc>
            <lastmod>2024-01-15</lastmod>
          </sitemap>
          <sitemap>
            <loc>https://example.com/sitemap2.xml</loc>
            <lastmod>2024-01-14</lastmod>
          </sitemap>
        </sitemapindex>
      `;

      const sitemap1Xml = `
        <?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://example.com/page1</loc></url>
          <url><loc>https://example.com/page2</loc></url>
        </urlset>
      `;

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/sitemap.xml')
        .reply(200, sitemapIndexXml)
        .get('/sitemap1.xml')
        .reply(200, sitemap1Xml);

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_SITEMAP,
        target: 'https://example.com/sitemap.xml',
        parameters: { followSitemapIndex: true, maxSitemaps: 1 },
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.sitemaps).toHaveLength(2);
      expect(response.data.urls).toHaveLength(2);
      expect(mockServer.isDone()).toBe(true);
    });
  });

  describe('Error Handling', () => {
    it('should handle network timeouts gracefully', async () => {
      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/timeout')
        .delay(6000) // Longer than our 5s timeout
        .reply(200, 'Should not reach here');

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/timeout',
        config: { timeout: 5000, maxRetries: 0 },
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(false);
      expect(response.status).toBe(ResponseStatus.TIMEOUT);
      expect(response.error?.retryable).toBe(true);
    });

    it('should handle HTTP error statuses', async () => {
      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/not-found')
        .reply(404, 'Page not found');

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/not-found',
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(false);
      expect(response.status).toBe(ResponseStatus.NOT_FOUND);
      expect(response.error?.retryable).toBe(false);
    });

    it('should handle malformed HTML gracefully', async () => {
      const malformedHtml = `
        <html>
          <head>
            <title>Broken HTML
          <body>
            <div>Unclosed div
            <p>Missing closing tag
            <a href="link">Link without closing
      `;

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/malformed')
        .reply(200, malformedHtml, {
          'content-type': 'text/html',
        });

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/malformed',
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.title).toBe('Broken HTML');
      expect(response.data.content).toContain('Unclosed div');
      expect(response.warnings).toEqual(
        expect.arrayContaining([expect.stringContaining('malformed HTML')])
      );
    });
  });

  describe('Content Extraction', () => {
    it('should extract metadata from HTML pages', async () => {
      const htmlWithMetadata = `
        <!DOCTYPE html>
        <html>
          <head>
            <title>Test Page</title>
            <meta name="description" content="Test description" />
            <meta name="keywords" content="test, meta, extraction" />
            <meta property="og:title" content="OG Title" />
            <meta property="og:description" content="OG Description" />
            <meta property="og:image" content="https://example.com/image.jpg" />
            <meta name="twitter:card" content="summary" />
            <meta name="author" content="Test Author" />
            <link rel="canonical" href="https://example.com/canonical" />
          </head>
          <body>
            <h1>Main Content</h1>
          </body>
        </html>
      `;

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/metadata')
        .reply(200, htmlWithMetadata);

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/metadata',
        parameters: { extractMetadata: true },
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.metadata).toMatchObject({
        title: 'Test Page',
        description: 'Test description',
        keywords: 'test, meta, extraction',
        author: 'Test Author',
        canonical: 'https://example.com/canonical',
        openGraph: {
          title: 'OG Title',
          description: 'OG Description',
          image: 'https://example.com/image.jpg',
        },
        twitter: {
          card: 'summary',
        },
      });
    });

    it('should extract structured data (JSON-LD)', async () => {
      const htmlWithJsonLd = `
        <!DOCTYPE html>
        <html>
          <head>
            <title>Product Page</title>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org/",
              "@type": "Product",
              "name": "Test Product",
              "description": "A great test product",
              "offers": {
                "@type": "Offer",
                "price": "29.99",
                "priceCurrency": "USD"
              }
            }
            </script>
          </head>
          <body>
            <h1>Product Page</h1>
          </body>
        </html>
      `;

      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/product')
        .reply(200, htmlWithJsonLd);

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/product',
        parameters: { extractStructuredData: true },
      });

      const response = await connector.fetch(request);

      expect(response.success).toBe(true);
      expect(response.data.structuredData).toHaveLength(1);
      expect(response.data.structuredData[0]).toMatchObject({
        '@type': 'Product',
        name: 'Test Product',
        description: 'A great test product',
      });
    });
  });

  describe('Health Checks', () => {
    it('should return healthy status when operational', async () => {
      const health = await connector.healthCheck();
      expect(health).toBe(true);
    });

    it('should track connector metrics', async () => {
      mockServer = nock('https://example.com')
        .get('/robots.txt')
        .reply(404)
        .get('/metrics-test')
        .reply(200, '<html><body>Test</body></html>');

      const request = testHelpers.createMockConnectorRequest({
        type: ConnectorRequestType.SCRAPE_URL,
        target: 'https://example.com/metrics-test',
      });

      await connector.fetch(request);

      const metrics = connector.getMetrics();
      expect(metrics.totalRequests).toBe(1);
      expect(metrics.successfulRequests).toBe(1);
      expect(metrics.failedRequests).toBe(0);
      expect(metrics.averageResponseTime).toBeGreaterThan(0);
    });
  });
});
