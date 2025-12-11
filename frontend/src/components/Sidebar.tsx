import { X, Home, FileText, CreditCard, TrendingUp, AlertCircle, BarChart3, Settings, ChevronDown, ChevronRight, Users } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Button } from './ui/button';
import { useState } from 'react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [isDebtOpen, setIsDebtOpen] = useState(false);

  const handleNavigate = (path: string) => {
    navigate(path);
    onClose();
  };

  const menuItems = [
    {
      id: 'dashboard',
      label: 'Dashboard',
      icon: Home,
      path: '/dashboard',
    },
    {
      id: 'debt',
      label: 'Công nợ',
      icon: FileText,
      hasSubmenu: true,
      submenu: [
        { id: 'ar', label: 'Công nợ phải thu', path: '/dashboard/ar' },
        { id: 'ap', label: 'Công nợ phải trả', path: '/dashboard/ap' },
      ],
    },
    {
      id: 'payment',
      label: 'Thanh toán',
      icon: CreditCard,
      path: '/dashboard/payments',
    },
    {
      id: 'forecast',
      label: 'Dự báo dòng tiền',
      icon: TrendingUp,
      path: '/dashboard/forecast',
    },
    {
      id: 'anomaly',
      label: 'Cảnh báo bất thường',
      icon: AlertCircle,
      path: '/dashboard/anomaly',
    },
    {
      id: 'report',
      label: 'Báo cáo',
      icon: BarChart3,
      path: '/dashboard/reports',
    },
    {
      id: 'user',
      label: 'Tài khoản',
      icon: Users,
      path: '/dashboard/users',
    },
    {
      id: 'settings',
      label: 'Cấu hình',
      icon: Settings,
      path: '/dashboard/settings',
    },
  ];

  return (
    <>
      {/* Backdrop - only covers content below header */}
      {isOpen && (
        <div
          className="fixed top-16 left-0 right-0 bottom-0 bg-black/50 z-40 transition-opacity duration-300"
          onClick={onClose}
        />
      )}

      {/* Sidebar - starts below header */}
      <div
        className={`fixed top-16 left-0 bottom-0 w-[300px] bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out overflow-y-auto ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Menu Items */}
        <nav className="p-4">
          <ul className="space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || 
                             (item.submenu && item.submenu.some(sub => location.pathname === sub.path));
              
              return (
                <li key={item.id}>
                  {/* Main Menu Item */}
                  <button
                    onClick={() => {
                      if (item.hasSubmenu) {
                        setIsDebtOpen(!isDebtOpen);
                      } else {
                        handleNavigate(item.path!);
                      }
                    }}
                    className={`w-full flex items-center justify-between px-4 py-3.5 rounded-lg transition-all duration-200 font-darker-grotesque group ${
                      isActive
                        ? 'bg-blue-600 text-white shadow-md'
                        : 'text-slate-700 hover:bg-slate-100'
                    }`}
                    style={{ fontSize: '22px', fontWeight: 500 }}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className={`size-6 ${isActive ? 'text-white' : 'text-slate-600 group-hover:text-blue-600'}`} />
                      <span>{item.label}</span>
                    </div>
                    {item.hasSubmenu && (
                      isDebtOpen ? (
                        <ChevronDown className="size-5" />
                      ) : (
                        <ChevronRight className="size-5" />
                      )
                    )}
                  </button>

                  {/* Submenu */}
                  {item.hasSubmenu && item.submenu && (
                    <div
                      className={`overflow-hidden transition-all duration-300 ${
                        isDebtOpen ? 'max-h-40 opacity-100 mt-2' : 'max-h-0 opacity-0'
                      }`}
                    >
                      <ul className="ml-8 space-y-2">
                        {item.submenu.map((subItem) => {
                          const isSubActive = location.pathname === subItem.path;
                          return (
                            <li key={subItem.id}>
                              <button
                                onClick={() => handleNavigate(subItem.path)}
                                className={`w-full text-left px-4 py-3 rounded-lg transition-all duration-200 font-darker-grotesque ${
                                  isSubActive
                                    ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600 shadow-sm font-semibold'
                                    : 'text-slate-600 hover:bg-slate-100 border-l-4 border-transparent hover:border-slate-300'
                                }`}
                                style={{ fontSize: '20px' }}
                              >
                                {subItem.label}
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </>
  );
}