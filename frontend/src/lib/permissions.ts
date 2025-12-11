/**
 * Role-Based Access Control (RBAC) Configuration
 * 
 * Định nghĩa quyền truy cập cho từng role theo Use Cases:
 * 
 * | Role       | Dashboard | AR  | AP  | Payments | Forecast | Alerts | Reports | Users | Settings |
 * |------------|-----------|-----|-----|----------|----------|--------|---------|-------|----------|
 * | owner      | R         | R   | A   | R        | R        | R      | R       | -     | -        |
 * | accountant | R         | W   | W   | W        | R        | R      | R       | -     | -        |
 * | cashier    | -         | W   | -   | W        | -        | -      | -       | -     | -        |
 * | admin      | -         | -   | -   | -        | -        | -      | -       | W     | W        |
 * 
 * R = Read, W = Write, A = Approve, - = No Access
 */

// ============================================================
// ROLE DEFINITIONS
// ============================================================

export type UserRole = 'owner' | 'accountant' | 'cashier' | 'admin';

export const ROLES = {
  OWNER: 'owner' as UserRole,
  ACCOUNTANT: 'accountant' as UserRole,
  CASHIER: 'cashier' as UserRole,
  ADMIN: 'admin' as UserRole,
} as const;

// ============================================================
// MENU ITEM PERMISSIONS
// ============================================================

/**
 * Định nghĩa roles được phép truy cập từng menu
 * Based on Use Case matrix provided
 * 
 * NOTE: Dashboard is accessible to ALL roles - it's the main entry point
 * Restrictions are for specific analytics/reporting pages only
 */
export const MENU_PERMISSIONS: Record<string, UserRole[]> = {
  // Dashboard - Accessible to ALL roles (main entry point after login)
  // Different content shown based on role at component level
  dashboard: [ROLES.OWNER, ROLES.ACCOUNTANT, ROLES.CASHIER, ROLES.ADMIN],
  
  // UC05 - AR Management: Owner, Accountant, Cashier
  ar: [ROLES.OWNER, ROLES.ACCOUNTANT, ROLES.CASHIER],
  
  // UC06 - AP Management: Owner, Accountant
  ap: [ROLES.OWNER, ROLES.ACCOUNTANT],
  
  // UC05, UC15 - Payments: Owner, Accountant, Cashier
  payment: [ROLES.OWNER, ROLES.ACCOUNTANT, ROLES.CASHIER],
  
  // UC09 - Forecast: Owner, Accountant (Analytics - restricted)
  forecast: [ROLES.OWNER, ROLES.ACCOUNTANT],
  
  // UC10, UC11 - Alerts/Anomaly: Owner, Accountant (Analytics - restricted)
  anomaly: [ROLES.OWNER, ROLES.ACCOUNTANT],
  
  // UC12 - Reports: Owner, Accountant (Analytics - restricted)
  report: [ROLES.OWNER, ROLES.ACCOUNTANT],
  
  // UC02 - User Management: Admin only
  user: [ROLES.ADMIN],
  
  // UC13 - Settings: Admin only
  settings: [ROLES.ADMIN],
  
  // Công nợ parent menu - shown if user has access to AR or AP
  debt: [ROLES.OWNER, ROLES.ACCOUNTANT, ROLES.CASHIER],
};

// ============================================================
// PERMISSION HELPERS
// ============================================================

/**
 * Check if user has permission to access a menu item
 * @param userRoles - Array of roles the user has
 * @param menuId - The menu item ID to check
 * @returns true if user has access, false otherwise
 */
export function hasMenuAccess(userRoles: string[], menuId: string): boolean {
  const allowedRoles = MENU_PERMISSIONS[menuId];
  
  // If no permission defined, deny by default (security first)
  if (!allowedRoles) {
    console.warn(`No permission defined for menu: ${menuId}`);
    return false;
  }
  
  // Check if user has any of the allowed roles
  return userRoles.some(role => allowedRoles.includes(role as UserRole));
}

/**
 * Check if user has a specific role
 * @param userRoles - Array of roles the user has
 * @param role - The role to check for
 */
export function hasRole(userRoles: string[], role: UserRole): boolean {
  return userRoles.includes(role);
}

/**
 * Check if user is an admin
 */
export function isAdmin(userRoles: string[]): boolean {
  return hasRole(userRoles, ROLES.ADMIN);
}

/**
 * Check if user is an owner
 */
export function isOwner(userRoles: string[]): boolean {
  return hasRole(userRoles, ROLES.OWNER);
}

/**
 * Check if user is an accountant
 */
export function isAccountant(userRoles: string[]): boolean {
  return hasRole(userRoles, ROLES.ACCOUNTANT);
}

/**
 * Check if user is a cashier
 */
export function isCashier(userRoles: string[]): boolean {
  return hasRole(userRoles, ROLES.CASHIER);
}

/**
 * Get user roles from localStorage
 */
export function getUserRoles(): string[] {
  try {
    const rolesJson = localStorage.getItem('userRoles');
    if (rolesJson) {
      return JSON.parse(rolesJson);
    }
  } catch (e) {
    console.error('Failed to parse user roles from localStorage');
  }
  return [];
}

/**
 * Save user roles to localStorage
 */
export function setUserRoles(roles: string[]): void {
  localStorage.setItem('userRoles', JSON.stringify(roles));
}

/**
 * Clear user roles from localStorage
 */
export function clearUserRoles(): void {
  localStorage.removeItem('userRoles');
}

/**
 * Filter menu items based on user permissions
 * @param menuItems - Array of menu items with id property
 * @param userRoles - Array of user roles
 * @returns Filtered array of menu items user can access
 */
export function filterMenuByPermissions<T extends { id: string; submenu?: { id: string }[] }>(
  menuItems: T[],
  userRoles: string[]
): T[] {
  return menuItems
    .filter(item => hasMenuAccess(userRoles, item.id))
    .map(item => {
      // If item has submenu, filter it too
      if (item.submenu) {
        return {
          ...item,
          submenu: item.submenu.filter(subItem => hasMenuAccess(userRoles, subItem.id)),
        };
      }
      return item;
    })
    // Remove items with empty submenus
    .filter(item => !item.submenu || item.submenu.length > 0);
}
