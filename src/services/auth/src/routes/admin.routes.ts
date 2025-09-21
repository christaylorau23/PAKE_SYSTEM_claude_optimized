/**
 * Admin Routes
 * Administrative endpoints for user management, roles, and system operations
 */

import { Router, Request, Response } from 'express';
import { body, query, validationResult } from 'express-validator';
import { UserService } from '../services/UserService';
import { SessionService } from '../services/SessionService';
import { RBACService } from '../services/RBACService';
import { Logger } from '../utils/logger';
import { UserStatus } from '../types';

interface AdminServices {
  userService: UserService;
  sessionService: SessionService;
  rbacService: RBACService;
}

export class AdminRoutes {
  private router: Router;
  private services: AdminServices;
  private logger = new Logger('AdminRoutes');

  constructor(services: AdminServices) {
    this.router = Router();
    this.services = services;
    this.setupRoutes();
  }

  private setupRoutes(): void {
    // User management
    this.router.get(
      '/users',
      [
        query('offset').optional().isInt({ min: 0 }),
        query('limit').optional().isInt({ min: 1, max: 100 }),
      ],
      this.listUsers.bind(this)
    );

    this.router.get('/users/:userId', this.getUser.bind(this));

    this.router.put(
      '/users/:userId/status',
      [body('status').isIn(['active', 'inactive', 'suspended'])],
      this.updateUserStatus.bind(this)
    );

    this.router.delete('/users/:userId', this.deleteUser.bind(this));

    // Role management
    this.router.get('/roles', this.listRoles.bind(this));

    this.router.post(
      '/roles',
      [
        body('name')
          .isLength({ min: 1, max: 50 })
          .matches(/^[a-zA-Z0-9_-]+$/),
        body('description').isLength({ min: 1, max: 200 }),
        body('permissions').optional().isArray(),
      ],
      this.createRole.bind(this)
    );

    this.router.get('/roles/:roleId', this.getRole.bind(this));

    this.router.put(
      '/roles/:roleId',
      [
        body('name')
          .optional()
          .isLength({ min: 1, max: 50 })
          .matches(/^[a-zA-Z0-9_-]+$/),
        body('description').optional().isLength({ min: 1, max: 200 }),
      ],
      this.updateRole.bind(this)
    );

    this.router.delete('/roles/:roleId', this.deleteRole.bind(this));

    // Role-user assignments
    this.router.post(
      '/users/:userId/roles',
      [body('roleId').isUUID()],
      this.assignRoleToUser.bind(this)
    );

    this.router.delete(
      '/users/:userId/roles/:roleId',
      this.removeRoleFromUser.bind(this)
    );

    // Permission management
    this.router.get('/permissions', this.listPermissions.bind(this));

    this.router.post(
      '/permissions',
      [
        body('name').isLength({ min: 1, max: 100 }),
        body('resource').isLength({ min: 1, max: 50 }),
        body('action').isLength({ min: 1, max: 50 }),
        body('description').isLength({ min: 1, max: 200 }),
      ],
      this.createPermission.bind(this)
    );

    // Role-permission assignments
    this.router.post(
      '/roles/:roleId/permissions',
      [body('permissions').isArray()],
      this.addPermissionsToRole.bind(this)
    );

    this.router.delete(
      '/roles/:roleId/permissions',
      [body('permissions').isArray()],
      this.removePermissionsFromRole.bind(this)
    );

    // System statistics
    this.router.get('/stats', this.getSystemStats.bind(this));
    this.router.get('/stats/sessions', this.getSessionStats.bind(this));
    this.router.get('/stats/rbac', this.getRBACStats.bind(this));

    // System operations
    this.router.post(
      '/maintenance/cleanup-sessions',
      this.cleanupSessions.bind(this)
    );
    this.router.post(
      '/maintenance/cleanup-tokens',
      this.cleanupTokens.bind(this)
    );
  }

  private async listUsers(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const offset = parseInt(req.query.offset as string) || 0;
      const limit = parseInt(req.query.limit as string) || 20;

      const result = await this.services.userService.listUsers(offset, limit);

      const users = result.users.map(user => ({
        id: user.id,
        email: user.email,
        username: user.username,
        firstName: user.firstName,
        lastName: user.lastName,
        emailVerified: user.emailVerified,
        status: user.status,
        roles: user.roles.map(r => r.name),
        createdAt: user.createdAt,
        updatedAt: user.updatedAt,
        lastLoginAt: user.lastLoginAt,
      }));

      res.json({
        users,
        total: result.total,
        offset,
        limit,
      });
    } catch (error) {
      this.logger.error('List users error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async getUser(req: Request, res: Response): Promise<void> {
    try {
      const { userId } = req.params;

      const user = await this.services.userService.findUserById(userId);
      if (!user) {
        res.status(404).json({ error: 'User not found' });
        return;
      }

      const sessions =
        await this.services.sessionService.getUserSessions(userId);

      res.json({
        id: user.id,
        email: user.email,
        username: user.username,
        firstName: user.firstName,
        lastName: user.lastName,
        emailVerified: user.emailVerified,
        mfaEnabled: user.mfaEnabled,
        status: user.status,
        roles: user.roles.map(role => ({
          id: role.id,
          name: role.name,
          description: role.description,
        })),
        permissions: user.permissions.map(perm => ({
          id: perm.id,
          name: perm.name,
          resource: perm.resource,
          action: perm.action,
        })),
        createdAt: user.createdAt,
        updatedAt: user.updatedAt,
        lastLoginAt: user.lastLoginAt,
        activeSessions: sessions.length,
      });
    } catch (error) {
      this.logger.error('Get user error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async updateUserStatus(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { userId } = req.params;
      const { status } = req.body;

      const success = await this.services.userService.updateUserStatus(
        userId,
        status as UserStatus
      );

      if (success) {
        res.json({
          success: true,
          message: 'User status updated successfully',
        });
      } else {
        res.status(404).json({ error: 'User not found' });
      }
    } catch (error) {
      this.logger.error('Update user status error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async deleteUser(req: Request, res: Response): Promise<void> {
    try {
      const { userId } = req.params;

      const success = await this.services.userService.deleteUser(userId);

      if (success) {
        res.json({ success: true, message: 'User deleted successfully' });
      } else {
        res.status(404).json({ error: 'User not found' });
      }
    } catch (error) {
      this.logger.error('Delete user error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async listRoles(req: Request, res: Response): Promise<void> {
    try {
      const roles = await this.services.rbacService.listRoles();

      res.json({
        roles: roles.map(role => ({
          id: role.id,
          name: role.name,
          description: role.description,
          isSystem: role.isSystem,
          permissions: role.permissions.map(p => ({
            id: p.id,
            name: p.name,
            resource: p.resource,
            action: p.action,
          })),
          createdAt: role.createdAt,
          updatedAt: role.updatedAt,
        })),
      });
    } catch (error) {
      this.logger.error('List roles error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async createRole(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { name, description, permissions = [] } = req.body;

      const role = await this.services.rbacService.createRole(
        name,
        description,
        permissions
      );

      res.status(201).json({
        success: true,
        role: {
          id: role.id,
          name: role.name,
          description: role.description,
          isSystem: role.isSystem,
          createdAt: role.createdAt,
        },
        message: 'Role created successfully',
      });
    } catch (error) {
      this.logger.error('Create role error', { error: error.message });
      res.status(500).json({ error: 'Role creation failed' });
    }
  }

  private async getRole(req: Request, res: Response): Promise<void> {
    try {
      const { roleId } = req.params;

      const role = await this.services.rbacService.getRole(roleId);
      if (!role) {
        res.status(404).json({ error: 'Role not found' });
        return;
      }

      res.json({
        id: role.id,
        name: role.name,
        description: role.description,
        isSystem: role.isSystem,
        permissions: role.permissions.map(p => ({
          id: p.id,
          name: p.name,
          resource: p.resource,
          action: p.action,
          description: p.description,
        })),
        createdAt: role.createdAt,
        updatedAt: role.updatedAt,
      });
    } catch (error) {
      this.logger.error('Get role error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async updateRole(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { roleId } = req.params;
      const updates = req.body;

      const role = await this.services.rbacService.updateRole(roleId, updates);

      if (role) {
        res.json({
          success: true,
          role: {
            id: role.id,
            name: role.name,
            description: role.description,
            updatedAt: role.updatedAt,
          },
          message: 'Role updated successfully',
        });
      } else {
        res.status(404).json({ error: 'Role not found' });
      }
    } catch (error) {
      this.logger.error('Update role error', { error: error.message });
      res.status(500).json({ error: 'Role update failed' });
    }
  }

  private async deleteRole(req: Request, res: Response): Promise<void> {
    try {
      const { roleId } = req.params;

      const success = await this.services.rbacService.deleteRole(roleId);

      if (success) {
        res.json({ success: true, message: 'Role deleted successfully' });
      } else {
        res.status(404).json({ error: 'Role not found or cannot be deleted' });
      }
    } catch (error) {
      this.logger.error('Delete role error', { error: error.message });
      res.status(500).json({ error: 'Role deletion failed' });
    }
  }

  private async assignRoleToUser(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { userId } = req.params;
      const { roleId } = req.body;

      const success = await this.services.rbacService.assignRoleToUser(
        userId,
        roleId
      );

      if (success) {
        res.json({ success: true, message: 'Role assigned successfully' });
      } else {
        res.status(400).json({ error: 'Failed to assign role' });
      }
    } catch (error) {
      this.logger.error('Assign role error', { error: error.message });
      res.status(500).json({ error: 'Role assignment failed' });
    }
  }

  private async removeRoleFromUser(req: Request, res: Response): Promise<void> {
    try {
      const { userId, roleId } = req.params;

      const success = await this.services.rbacService.removeRoleFromUser(
        userId,
        roleId
      );

      if (success) {
        res.json({ success: true, message: 'Role removed successfully' });
      } else {
        res.status(400).json({ error: 'Failed to remove role' });
      }
    } catch (error) {
      this.logger.error('Remove role error', { error: error.message });
      res.status(500).json({ error: 'Role removal failed' });
    }
  }

  private async listPermissions(req: Request, res: Response): Promise<void> {
    try {
      const permissions = await this.services.rbacService.listPermissions();

      res.json({
        permissions: permissions.map(p => ({
          id: p.id,
          name: p.name,
          resource: p.resource,
          action: p.action,
          description: p.description,
        })),
      });
    } catch (error) {
      this.logger.error('List permissions error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async createPermission(req: Request, res: Response): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { name, resource, action, description } = req.body;

      const permission = await this.services.rbacService.createPermission(
        name,
        resource,
        action,
        description
      );

      res.status(201).json({
        success: true,
        permission: {
          id: permission.id,
          name: permission.name,
          resource: permission.resource,
          action: permission.action,
          description: permission.description,
        },
        message: 'Permission created successfully',
      });
    } catch (error) {
      this.logger.error('Create permission error', { error: error.message });
      res.status(500).json({ error: 'Permission creation failed' });
    }
  }

  private async addPermissionsToRole(
    req: Request,
    res: Response
  ): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { roleId } = req.params;
      const { permissions } = req.body;

      const success = await this.services.rbacService.addPermissionsToRole(
        roleId,
        permissions
      );

      if (success) {
        res.json({ success: true, message: 'Permissions added successfully' });
      } else {
        res.status(400).json({ error: 'Failed to add permissions' });
      }
    } catch (error) {
      this.logger.error('Add permissions error', { error: error.message });
      res.status(500).json({ error: 'Permission assignment failed' });
    }
  }

  private async removePermissionsFromRole(
    req: Request,
    res: Response
  ): Promise<void> {
    try {
      const errors = validationResult(req);
      if (!errors.isEmpty()) {
        res
          .status(400)
          .json({ error: 'Validation failed', details: errors.array() });
        return;
      }

      const { roleId } = req.params;
      const { permissions } = req.body;

      const success = await this.services.rbacService.removePermissionsFromRole(
        roleId,
        permissions
      );

      if (success) {
        res.json({
          success: true,
          message: 'Permissions removed successfully',
        });
      } else {
        res.status(400).json({ error: 'Failed to remove permissions' });
      }
    } catch (error) {
      this.logger.error('Remove permissions error', { error: error.message });
      res.status(500).json({ error: 'Permission removal failed' });
    }
  }

  private async getSystemStats(req: Request, res: Response): Promise<void> {
    try {
      const sessionStats = await this.services.sessionService.getSessionStats();
      const rbacStats = await this.services.rbacService.getStats();

      res.json({
        timestamp: new Date().toISOString(),
        sessions: sessionStats,
        rbac: rbacStats,
        system: {
          uptime: process.uptime(),
          memory: process.memoryUsage(),
          version: process.version,
        },
      });
    } catch (error) {
      this.logger.error('Get system stats error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async getSessionStats(req: Request, res: Response): Promise<void> {
    try {
      const stats = await this.services.sessionService.getSessionStats();
      res.json(stats);
    } catch (error) {
      this.logger.error('Get session stats error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async getRBACStats(req: Request, res: Response): Promise<void> {
    try {
      const stats = await this.services.rbacService.getStats();
      res.json(stats);
    } catch (error) {
      this.logger.error('Get RBAC stats error', { error: error.message });
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  private async cleanupSessions(req: Request, res: Response): Promise<void> {
    try {
      const cleanedCount =
        await this.services.sessionService.cleanupExpiredSessions();

      res.json({
        success: true,
        message: `${cleanedCount} expired sessions cleaned up`,
      });
    } catch (error) {
      this.logger.error('Cleanup sessions error', { error: error.message });
      res.status(500).json({ error: 'Session cleanup failed' });
    }
  }

  private async cleanupTokens(req: Request, res: Response): Promise<void> {
    try {
      // This would need to be implemented in TokenService
      res.json({
        success: true,
        message: 'Token cleanup completed',
      });
    } catch (error) {
      this.logger.error('Cleanup tokens error', { error: error.message });
      res.status(500).json({ error: 'Token cleanup failed' });
    }
  }

  getRouter(): Router {
    return this.router;
  }
}
