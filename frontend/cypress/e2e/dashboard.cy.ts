describe('Dashboard Navigation and Functionality', () => {
  beforeEach(() => {
    cy.visit('/');
    cy.waitForPageLoad();
  });

  it('loads the homepage successfully', () => {
    cy.get('h1').should('contain', 'PAKE System');
    cy.title().should('contain', 'PAKE System');
  });

  it('has accessible navigation', () => {
    cy.checkA11y();

    // Test keyboard navigation
    cy.get('nav').within(() => {
      cy.get('a').first().focus();
      cy.focused().should('be.visible');

      // Navigate through links with Tab
      cy.focused().tab();
      cy.focused().should('be.visible');
    });
  });

  it('navigates to different sections', () => {
    // Test Voice Agents navigation
    cy.get('[data-testid="nav-voice-agents"]').click();
    cy.url().should('include', '/voice-agents');
    cy.get('h1').should('contain', 'Voice Agents');

    // Test Video Generation navigation
    cy.visit('/');
    cy.get('[data-testid="nav-video-generation"]').click();
    cy.url().should('include', '/video-generation');
    cy.get('h1').should('contain', 'Video Generation');

    // Test Social Media navigation
    cy.visit('/');
    cy.get('[data-testid="nav-social-media"]').click();
    cy.url().should('include', '/social-media');
    cy.get('h1').should('contain', 'Social Media');
  });

  it('displays executive dashboard correctly', () => {
    cy.visit('/');

    // Check for key dashboard elements
    cy.get('[data-testid="executive-dashboard"]').should('be.visible');
    cy.get('[data-testid="metrics-summary"]').should('be.visible');
    cy.get('[data-testid="service-status"]').should('be.visible');

    // Verify all services are shown
    cy.get('[data-testid="service-voice-agents"]').should('be.visible');
    cy.get('[data-testid="service-video-generation"]').should('be.visible');
    cy.get('[data-testid="service-social-media"]').should('be.visible');
  });

  it('handles responsive design correctly', () => {
    cy.testResponsive();
  });

  it('measures page performance', () => {
    cy.measurePerformance();

    // Verify Core Web Vitals
    cy.window().then(win => {
      const performance = win.performance;
      const navigation = performance.getEntriesByType(
        'navigation'
      )[0] as PerformanceNavigationTiming;

      // First Contentful Paint should be under 2 seconds
      const fcp = performance.getEntriesByName('first-contentful-paint')[0];
      if (fcp) {
        expect(fcp.startTime).to.be.lessThan(2000);
      }

      // DOM Content Loaded should be fast
      const dcl =
        navigation.domContentLoadedEventEnd - navigation.navigationStart;
      expect(dcl).to.be.lessThan(3000);
    });
  });

  it('handles errors gracefully', () => {
    // Test navigation to non-existent page
    cy.visit('/non-existent-page', { failOnStatusCode: false });
    cy.get('[data-testid="error-boundary"]').should('be.visible');
    cy.get('[data-testid="error-message"]').should('contain', '404');
  });

  it('supports theme switching', () => {
    // Test dark mode toggle
    cy.get('[data-testid="theme-toggle"]').click();
    cy.get('html').should('have.class', 'dark');

    // Test light mode
    cy.get('[data-testid="theme-toggle"]').click();
    cy.get('html').should('not.have.class', 'dark');
  });

  it('maintains state across navigation', () => {
    // Set theme to dark
    cy.get('[data-testid="theme-toggle"]').click();

    // Navigate away and back
    cy.get('[data-testid="nav-voice-agents"]').click();
    cy.get('[data-testid="nav-home"]').click();

    // Verify theme is maintained
    cy.get('html').should('have.class', 'dark');
  });
});
