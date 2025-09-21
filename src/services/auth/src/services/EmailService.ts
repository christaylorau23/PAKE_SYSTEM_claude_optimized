/**
 * Email Service
 * Handles email notifications for authentication events
 */

import nodemailer, { Transporter } from 'nodemailer';
import { emailConfig } from '../config/auth.config';
import { Logger } from '../utils/logger';

interface EmailTemplate {
  subject: string;
  html: string;
  text: string;
}

export class EmailService {
  private readonly logger = new Logger('EmailService');
  private transporter: Transporter | null = null;

  constructor() {
    this.initializeTransporter();
  }

  /**
   * Initialize email transporter
   */
  private async initializeTransporter(): Promise<void> {
    try {
      this.transporter = nodemailer.createTransporter({
        host: emailConfig.smtp.host,
        port: emailConfig.smtp.port,
        secure: emailConfig.smtp.secure,
        auth: emailConfig.smtp.auth.user
          ? {
              user: emailConfig.smtp.auth.user,
              pass: emailConfig.smtp.auth.pass,
            }
          : undefined,
      });

      // Verify connection
      if (this.transporter && emailConfig.smtp.auth.user) {
        await this.transporter.verify();
        this.logger.info('Email service initialized successfully');
      } else {
        this.logger.warn('Email service initialized without authentication');
      }
    } catch (error) {
      this.logger.error('Failed to initialize email service', {
        error: error.message,
      });
    }
  }

  /**
   * Send verification email
   */
  async sendVerificationEmail(email: string, token: string): Promise<boolean> {
    try {
      if (!this.transporter) {
        this.logger.warn('Email transporter not available');
        return false;
      }

      const verificationUrl = `${process.env.FRONTEND_URL || 'http://localhost:3000'}/verify-email?token=${token}`;

      const template = this.getVerificationEmailTemplate(verificationUrl);

      await this.transporter.sendMail({
        from: emailConfig.from,
        to: email,
        subject: template.subject,
        html: template.html,
        text: template.text,
      });

      this.logger.info('Verification email sent', { email });
      return true;
    } catch (error) {
      this.logger.error('Failed to send verification email', {
        email,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Send REDACTED_SECRET reset email
   */
  async sendPasswordResetEmail(email: string, token: string): Promise<boolean> {
    try {
      if (!this.transporter) {
        this.logger.warn('Email transporter not available');
        return false;
      }

      const resetUrl = `${process.env.FRONTEND_URL || 'http://localhost:3000'}/reset-REDACTED_SECRET?token=${token}`;

      const template = this.getPasswordResetEmailTemplate(resetUrl);

      await this.transporter.sendMail({
        from: emailConfig.from,
        to: email,
        subject: template.subject,
        html: template.html,
        text: template.text,
      });

      this.logger.info('Password reset email sent', { email });
      return true;
    } catch (error) {
      this.logger.error('Failed to send REDACTED_SECRET reset email', {
        email,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Send REDACTED_SECRET reset confirmation email
   */
  async sendPasswordResetConfirmation(email: string): Promise<boolean> {
    try {
      if (!this.transporter) {
        this.logger.warn('Email transporter not available');
        return false;
      }

      const template = this.getPasswordResetConfirmationTemplate();

      await this.transporter.sendMail({
        from: emailConfig.from,
        to: email,
        subject: template.subject,
        html: template.html,
        text: template.text,
      });

      this.logger.info('Password reset confirmation sent', { email });
      return true;
    } catch (error) {
      this.logger.error('Failed to send REDACTED_SECRET reset confirmation', {
        email,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Send login notification email
   */
  async sendLoginNotification(
    email: string,
    ipAddress: string,
    userAgent: string,
    location?: string
  ): Promise<boolean> {
    try {
      if (!this.transporter) {
        this.logger.warn('Email transporter not available');
        return false;
      }

      const template = this.getLoginNotificationTemplate(
        ipAddress,
        userAgent,
        location
      );

      await this.transporter.sendMail({
        from: emailConfig.from,
        to: email,
        subject: template.subject,
        html: template.html,
        text: template.text,
      });

      this.logger.info('Login notification sent', { email });
      return true;
    } catch (error) {
      this.logger.error('Failed to send login notification', {
        email,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Send MFA backup codes email
   */
  async sendMFABackupCodes(
    email: string,
    backupCodes: string[]
  ): Promise<boolean> {
    try {
      if (!this.transporter) {
        this.logger.warn('Email transporter not available');
        return false;
      }

      const template = this.getMFABackupCodesTemplate(backupCodes);

      await this.transporter.sendMail({
        from: emailConfig.from,
        to: email,
        subject: template.subject,
        html: template.html,
        text: template.text,
      });

      this.logger.info('MFA backup codes sent', { email });
      return true;
    } catch (error) {
      this.logger.error('Failed to send MFA backup codes', {
        email,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Send security alert email
   */
  async sendSecurityAlert(
    email: string,
    alertType: string,
    details: string,
    ipAddress?: string
  ): Promise<boolean> {
    try {
      if (!this.transporter) {
        this.logger.warn('Email transporter not available');
        return false;
      }

      const template = this.getSecurityAlertTemplate(
        alertType,
        details,
        ipAddress
      );

      await this.transporter.sendMail({
        from: emailConfig.from,
        to: email,
        subject: template.subject,
        html: template.html,
        text: template.text,
      });

      this.logger.info('Security alert sent', { email, alertType });
      return true;
    } catch (error) {
      this.logger.error('Failed to send security alert', {
        email,
        alertType,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Send welcome email
   */
  async sendWelcomeEmail(email: string, firstName: string): Promise<boolean> {
    try {
      if (!this.transporter) {
        this.logger.warn('Email transporter not available');
        return false;
      }

      const template = this.getWelcomeEmailTemplate(firstName);

      await this.transporter.sendMail({
        from: emailConfig.from,
        to: email,
        subject: template.subject,
        html: template.html,
        text: template.text,
      });

      this.logger.info('Welcome email sent', { email });
      return true;
    } catch (error) {
      this.logger.error('Failed to send welcome email', {
        email,
        error: error.message,
      });
      return false;
    }
  }

  /**
   * Get verification email template
   */
  private getVerificationEmailTemplate(verificationUrl: string): EmailTemplate {
    return {
      subject: 'Verify Your Email Address - PAKE System',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify Your Email</title>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background-color: #007bff; color: white; padding: 20px; text-align: center; }
              .content { padding: 30px; background-color: #f8f9fa; }
              .button { display: inline-block; padding: 12px 30px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
              .footer { padding: 20px; text-align: center; color: #666; font-size: 14px; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>PAKE System</h1>
              </div>
              <div class="content">
                <h2>Verify Your Email Address</h2>
                <p>Thank you for creating an account with PAKE System. To complete your registration, please verify your email address by clicking the button below:</p>
                <p style="text-align: center;">
                  <a href="${verificationUrl}" class="button">Verify Email Address</a>
                </p>
                <p>If you cannot click the button, copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">${verificationUrl}</p>
                <p><strong>This link will expire in 24 hours.</strong></p>
                <p>If you did not create an account with us, please ignore this email.</p>
              </div>
              <div class="footer">
                <p>© 2025 PAKE System. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
      `,
      text: `
        PAKE System - Verify Your Email Address
        
        Thank you for creating an account with PAKE System. To complete your registration, please verify your email address by clicking the following link:
        
        ${verificationUrl}
        
        This link will expire in 24 hours.
        
        If you did not create an account with us, please ignore this email.
        
        © 2025 PAKE System. All rights reserved.
      `,
    };
  }

  /**
   * Get REDACTED_SECRET reset email template
   */
  private getPasswordResetEmailTemplate(resetUrl: string): EmailTemplate {
    return {
      subject: 'Password Reset Request - PAKE System',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background-color: #dc3545; color: white; padding: 20px; text-align: center; }
              .content { padding: 30px; background-color: #f8f9fa; }
              .button { display: inline-block; padding: 12px 30px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
              .footer { padding: 20px; text-align: center; color: #666; font-size: 14px; }
              .warning { background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; border-radius: 5px; margin: 20px 0; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>PAKE System</h1>
              </div>
              <div class="content">
                <h2>Password Reset Request</h2>
                <p>We received a request to reset your REDACTED_SECRET. Click the button below to create a new REDACTED_SECRET:</p>
                <p style="text-align: center;">
                  <a href="${resetUrl}" class="button">Reset Password</a>
                </p>
                <p>If you cannot click the button, copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">${resetUrl}</p>
                <div class="warning">
                  <strong>Security Notice:</strong>
                  <ul>
                    <li>This link will expire in 1 hour</li>
                    <li>If you did not request this reset, please ignore this email</li>
                    <li>Your REDACTED_SECRET will remain unchanged until you create a new one</li>
                  </ul>
                </div>
              </div>
              <div class="footer">
                <p>© 2025 PAKE System. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
      `,
      text: `
        PAKE System - Password Reset Request
        
        We received a request to reset your REDACTED_SECRET. Click the following link to create a new REDACTED_SECRET:
        
        ${resetUrl}
        
        Security Notice:
        - This link will expire in 1 hour
        - If you did not request this reset, please ignore this email
        - Your REDACTED_SECRET will remain unchanged until you create a new one
        
        © 2025 PAKE System. All rights reserved.
      `,
    };
  }

  /**
   * Get REDACTED_SECRET reset confirmation template
   */
  private getPasswordResetConfirmationTemplate(): EmailTemplate {
    return {
      subject: 'Password Reset Successful - PAKE System',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset Successful</title>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background-color: #28a745; color: white; padding: 20px; text-align: center; }
              .content { padding: 30px; background-color: #f8f9fa; }
              .footer { padding: 20px; text-align: center; color: #666; font-size: 14px; }
              .success { background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; margin: 20px 0; color: #155724; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>PAKE System</h1>
              </div>
              <div class="content">
                <h2>Password Reset Successful</h2>
                <div class="success">
                  <p><strong>✓ Your REDACTED_SECRET has been successfully reset.</strong></p>
                </div>
                <p>Your PAKE System account REDACTED_SECRET has been updated. You can now log in with your new REDACTED_SECRET.</p>
                <p><strong>Security Information:</strong></p>
                <ul>
                  <li>All active sessions have been terminated for your security</li>
                  <li>You will need to log in again on all devices</li>
                  <li>If you did not make this change, please contact support immediately</li>
                </ul>
                <p>For your security, we recommend:</p>
                <ul>
                  <li>Using a strong, unique REDACTED_SECRET</li>
                  <li>Enabling two-factor authentication</li>
                  <li>Regularly updating your REDACTED_SECRET</li>
                </ul>
              </div>
              <div class="footer">
                <p>© 2025 PAKE System. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
      `,
      text: `
        PAKE System - Password Reset Successful
        
        Your REDACTED_SECRET has been successfully reset.
        
        Your PAKE System account REDACTED_SECRET has been updated. You can now log in with your new REDACTED_SECRET.
        
        Security Information:
        - All active sessions have been terminated for your security
        - You will need to log in again on all devices
        - If you did not make this change, please contact support immediately
        
        For your security, we recommend:
        - Using a strong, unique REDACTED_SECRET
        - Enabling two-factor authentication
        - Regularly updating your REDACTED_SECRET
        
        © 2025 PAKE System. All rights reserved.
      `,
    };
  }

  /**
   * Get login notification template
   */
  private getLoginNotificationTemplate(
    ipAddress: string,
    userAgent: string,
    location?: string
  ): EmailTemplate {
    const timestamp = new Date().toLocaleString();

    return {
      subject: 'New Login to Your Account - PAKE System',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>New Login Notification</title>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background-color: #17a2b8; color: white; padding: 20px; text-align: center; }
              .content { padding: 30px; background-color: #f8f9fa; }
              .footer { padding: 20px; text-align: center; color: #666; font-size: 14px; }
              .info-box { background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>PAKE System</h1>
              </div>
              <div class="content">
                <h2>New Login Notification</h2>
                <p>We detected a new login to your PAKE System account:</p>
                <div class="info-box">
                  <p><strong>Time:</strong> ${timestamp}</p>
                  <p><strong>IP Address:</strong> ${ipAddress}</p>
                  <p><strong>Device:</strong> ${userAgent}</p>
                  ${location ? `<p><strong>Location:</strong> ${location}</p>` : ''}
                </div>
                <p>If this was you, you can safely ignore this email.</p>
                <p><strong>If this wasn't you:</strong></p>
                <ul>
                  <li>Change your REDACTED_SECRET immediately</li>
                  <li>Check your account for any unauthorized changes</li>
                  <li>Consider enabling two-factor authentication</li>
                  <li>Contact support if you need assistance</li>
                </ul>
              </div>
              <div class="footer">
                <p>© 2025 PAKE System. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
      `,
      text: `
        PAKE System - New Login Notification
        
        We detected a new login to your PAKE System account:
        
        Time: ${timestamp}
        IP Address: ${ipAddress}
        Device: ${userAgent}
        ${location ? `Location: ${location}` : ''}
        
        If this was you, you can safely ignore this email.
        
        If this wasn't you:
        - Change your REDACTED_SECRET immediately
        - Check your account for any unauthorized changes
        - Consider enabling two-factor authentication
        - Contact support if you need assistance
        
        © 2025 PAKE System. All rights reserved.
      `,
    };
  }

  /**
   * Get MFA backup codes template
   */
  private getMFABackupCodesTemplate(backupCodes: string[]): EmailTemplate {
    const codesList = backupCodes.map(code => `• ${code}`).join('\n        ');

    return {
      subject: 'Your MFA Backup Codes - PAKE System',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MFA Backup Codes</title>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background-color: #ffc107; color: #212529; padding: 20px; text-align: center; }
              .content { padding: 30px; background-color: #f8f9fa; }
              .footer { padding: 20px; text-align: center; color: #666; font-size: 14px; }
              .codes-box { background-color: #fff; border: 2px solid #dee2e6; padding: 20px; border-radius: 5px; margin: 20px 0; font-family: monospace; }
              .warning { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; color: #721c24; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>PAKE System</h1>
              </div>
              <div class="content">
                <h2>Your MFA Backup Codes</h2>
                <p>Here are your two-factor authentication backup codes. Keep them safe and secure:</p>
                <div class="codes-box">
                  ${backupCodes.map(code => `<div>${code}</div>`).join('')}
                </div>
                <div class="warning">
                  <strong>Important Security Information:</strong>
                  <ul>
                    <li>Each code can only be used once</li>
                    <li>Store these codes in a secure location</li>
                    <li>Don't share these codes with anyone</li>
                    <li>Use these codes if you lose access to your authenticator app</li>
                    <li>Generate new codes if you suspect they've been compromised</li>
                  </ul>
                </div>
              </div>
              <div class="footer">
                <p>© 2025 PAKE System. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
      `,
      text: `
        PAKE System - Your MFA Backup Codes
        
        Here are your two-factor authentication backup codes. Keep them safe and secure:
        
        ${codesList}
        
        Important Security Information:
        - Each code can only be used once
        - Store these codes in a secure location
        - Don't share these codes with anyone
        - Use these codes if you lose access to your authenticator app
        - Generate new codes if you suspect they've been compromised
        
        © 2025 PAKE System. All rights reserved.
      `,
    };
  }

  /**
   * Get security alert template
   */
  private getSecurityAlertTemplate(
    alertType: string,
    details: string,
    ipAddress?: string
  ): EmailTemplate {
    return {
      subject: `Security Alert: ${alertType} - PAKE System`,
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Security Alert</title>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background-color: #dc3545; color: white; padding: 20px; text-align: center; }
              .content { padding: 30px; background-color: #f8f9fa; }
              .footer { padding: 20px; text-align: center; color: #666; font-size: 14px; }
              .alert { background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; color: #721c24; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>🚨 Security Alert</h1>
              </div>
              <div class="content">
                <h2>${alertType}</h2>
                <div class="alert">
                  <p><strong>Alert Details:</strong></p>
                  <p>${details}</p>
                  ${ipAddress ? `<p><strong>IP Address:</strong> ${ipAddress}</p>` : ''}
                  <p><strong>Time:</strong> ${new Date().toLocaleString()}</p>
                </div>
                <p><strong>Recommended Actions:</strong></p>
                <ul>
                  <li>Review your account activity</li>
                  <li>Change your REDACTED_SECRET if you suspect unauthorized access</li>
                  <li>Enable two-factor authentication if not already enabled</li>
                  <li>Contact support if you need assistance</li>
                </ul>
              </div>
              <div class="footer">
                <p>© 2025 PAKE System. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
      `,
      text: `
        PAKE System - Security Alert: ${alertType}
        
        Alert Details:
        ${details}
        ${ipAddress ? `IP Address: ${ipAddress}` : ''}
        Time: ${new Date().toLocaleString()}
        
        Recommended Actions:
        - Review your account activity
        - Change your REDACTED_SECRET if you suspect unauthorized access
        - Enable two-factor authentication if not already enabled
        - Contact support if you need assistance
        
        © 2025 PAKE System. All rights reserved.
      `,
    };
  }

  /**
   * Get welcome email template
   */
  private getWelcomeEmailTemplate(firstName: string): EmailTemplate {
    return {
      subject: 'Welcome to PAKE System!',
      html: `
        <!DOCTYPE html>
        <html>
          <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to PAKE System</title>
            <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
              .container { max-width: 600px; margin: 0 auto; padding: 20px; }
              .header { background-color: #007bff; color: white; padding: 30px; text-align: center; }
              .content { padding: 30px; background-color: #f8f9fa; }
              .footer { padding: 20px; text-align: center; color: #666; font-size: 14px; }
              .feature { background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 15px 0; }
            </style>
          </head>
          <body>
            <div class="container">
              <div class="header">
                <h1>Welcome to PAKE System!</h1>
              </div>
              <div class="content">
                <h2>Hello ${firstName}! 👋</h2>
                <p>Welcome to PAKE System - your Personal Autonomous Knowledge Engine Plus. We're excited to have you on board!</p>
                
                <h3>What can you do with PAKE System?</h3>
                <div class="feature">
                  <strong>🧠 Knowledge Management</strong><br>
                  Organize and search your knowledge with AI-powered insights
                </div>
                <div class="feature">
                  <strong>📊 Advanced Analytics</strong><br>
                  Get intelligent analytics and anomaly detection
                </div>
                <div class="feature">
                  <strong>🔒 Secure & Private</strong><br>
                  Enterprise-grade security with multi-factor authentication
                </div>
                <div class="feature">
                  <strong>⚡ Workflow Automation</strong><br>
                  Automate your workflows with AI-powered task management
                </div>
                
                <h3>Getting Started</h3>
                <p>Here are some next steps to get the most out of PAKE System:</p>
                <ul>
                  <li>Complete your profile setup</li>
                  <li>Enable two-factor authentication for enhanced security</li>
                  <li>Explore the knowledge vault features</li>
                  <li>Set up your first automated workflow</li>
                </ul>
                
                <p>If you have any questions, our support team is here to help!</p>
              </div>
              <div class="footer">
                <p>© 2025 PAKE System. All rights reserved.</p>
              </div>
            </div>
          </body>
        </html>
      `,
      text: `
        Welcome to PAKE System!
        
        Hello ${firstName}!
        
        Welcome to PAKE System - your Personal Autonomous Knowledge Engine Plus. We're excited to have you on board!
        
        What can you do with PAKE System?
        
        🧠 Knowledge Management
        Organize and search your knowledge with AI-powered insights
        
        📊 Advanced Analytics
        Get intelligent analytics and anomaly detection
        
        🔒 Secure & Private
        Enterprise-grade security with multi-factor authentication
        
        ⚡ Workflow Automation
        Automate your workflows with AI-powered task management
        
        Getting Started:
        - Complete your profile setup
        - Enable two-factor authentication for enhanced security
        - Explore the knowledge vault features
        - Set up your first automated workflow
        
        If you have any questions, our support team is here to help!
        
        © 2025 PAKE System. All rights reserved.
      `,
    };
  }

  /**
   * Test email configuration
   */
  async testConfiguration(): Promise<boolean> {
    try {
      if (!this.transporter) {
        return false;
      }

      await this.transporter.verify();
      this.logger.info('Email configuration test successful');
      return true;
    } catch (error) {
      this.logger.error('Email configuration test failed', {
        error: error.message,
      });
      return false;
    }
  }
}
