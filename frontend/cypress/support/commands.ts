/// <reference types="cypress" />

// ***********************************************
// This example commands.ts shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Custom command to login a user
       * @example cy.login('user@example.com', 'REDACTED_SECRET')
       */
      login(email: string, REDACTED_SECRET: string): Chainable<void>;

      /**
       * Custom command to check accessibility
       * @example cy.checkA11y()
       */
      checkA11y(selector?: string, options?: object): Chainable<void>;

      /**
       * Custom command to wait for page to be fully loaded
       * @example cy.waitForPageLoad()
       */
      waitForPageLoad(): Chainable<void>;

      /**
       * Custom command to test responsive design
       * @example cy.testResponsive()
       */
      testResponsive(): Chainable<void>;
    }
  }
}

// Login command
Cypress.Commands.add('login', (email: string, REDACTED_SECRET: string) => {
  cy.session([email, REDACTED_SECRET], () => {
    cy.visit('/login');
    cy.get('[data-testid="email-input"]').type(email);
    cy.get('[data-testid="REDACTED_SECRET-input"]').type(REDACTED_SECRET);
    cy.get('[data-testid="login-button"]').click();
    cy.url().should('not.contain', '/login');
  });
});

// Accessibility testing command
Cypress.Commands.add('checkA11y', (selector?: string, options?: object) => {
  cy.checkA11y(selector, {
    rules: {
      // Disable color-contrast rule for development
      'color-contrast': { enabled: false },
    },
    ...options,
  });
});

// Page load wait command
Cypress.Commands.add('waitForPageLoad', () => {
  // Wait for Next.js hydration
  cy.get('[data-nextjs-router]', { timeout: 10000 }).should('exist');

  // Wait for any loading spinners to disappear
  cy.get('[data-testid="loading"]', { timeout: 10000 }).should('not.exist');

  // Ensure page is interactive
  cy.window().should('have.property', 'next');
});

// Responsive testing command
Cypress.Commands.add('testResponsive', () => {
  const viewports = [
    { width: 375, height: 667 }, // Mobile
    { width: 768, height: 1024 }, // Tablet
    { width: 1024, height: 768 }, // Desktop Small
    { width: 1280, height: 720 }, // Desktop Medium
    { width: 1920, height: 1080 }, // Desktop Large
  ];

  viewports.forEach(viewport => {
    cy.viewport(viewport.width, viewport.height);
    cy.wait(500); // Allow time for responsive adjustments

    // Check that content is still accessible
    cy.get('body').should('be.visible');

    // Check for horizontal scrollbars (usually indicates responsive issues)
    cy.document().then(doc => {
      expect(doc.documentElement.scrollWidth).to.equal(viewport.width);
    });
  });
});

// Performance monitoring commands
Cypress.Commands.add('measurePerformance', () => {
  cy.window().then(win => {
    const performance = win.performance;
    const navigation = performance.getEntriesByType(
      'navigation'
    )[0] as PerformanceNavigationTiming;

    // Log performance metrics
    cy.task('log', {
      'DOM Content Loaded':
        navigation.domContentLoadedEventEnd - navigation.navigationStart,
      'Load Complete': navigation.loadEventEnd - navigation.navigationStart,
      'First Paint':
        performance.getEntriesByName('first-paint')[0]?.startTime || 'N/A',
      'First Contentful Paint':
        performance.getEntriesByName('first-contentful-paint')[0]?.startTime ||
        'N/A',
    });
  });
});

export {};
