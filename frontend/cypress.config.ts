import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    supportFile: 'cypress/support/e2e.ts',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    viewportWidth: 1280,
    viewportHeight: 720,
    video: true,
    screenshotOnRunFailure: true,
    chromeWebSecurity: false,
    setupNodeEvents(on, config) {
      // implement node event listeners here
      on('task', {
        log(message) {
          console.log(message);
          return null;
        },
        table(message) {
          console.table(message);
          return null;
        },
      });
    },
    env: {
      // Environment variables for testing
      API_URL: 'http://localhost:3000/api',
      VAULT_URL: 'http://localhost:8200',
    },
  },

  component: {
    devServer: {
      framework: 'next',
      bundler: 'webpack',
    },
    supportFile: 'cypress/support/component.ts',
    specPattern: 'src/**/*.cy.{js,jsx,ts,tsx}',
    indexHtmlFile: 'cypress/support/component-index.html',
  },

  // Global configuration
  defaultCommandTimeout: 10000,
  requestTimeout: 10000,
  responseTimeout: 10000,
  pageLoadTimeout: 30000,
  execTimeout: 10000,
  taskTimeout: 10000,

  // Retry configuration
  retries: {
    runMode: 2,
    openMode: 0,
  },

  // Video and screenshot configuration
  videosFolder: 'cypress/videos',
  screenshotsFolder: 'cypress/screenshots',

  // Experimental features
  experimentalStudio: true,
  experimentalMemoryManagement: true,
});
