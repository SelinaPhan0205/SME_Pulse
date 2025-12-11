import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Lock, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { useCurrentUser, useChangePassword, useLogout } from '@/lib/api/hooks';
import { useUpdateUser } from '@/lib/api/hooks/useUsers';

interface UserMenuProps {
  userRole?: 'owner' | 'admin' | 'accountant' | 'viewer';
  userName?: string;
  userEmail?: string;
}

export function UserMenu({ 
  userRole,
  userName,
  userEmail
}: UserMenuProps) {
  const navigate = useNavigate();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch current user
  const { data: currentUser, isLoading: loadingUser } = useCurrentUser();
  const updateUserMutation = useUpdateUser();
  const changePasswordMutation = useChangePassword();
  const logoutMutation = useLogout();

  // Use API data if available, otherwise fallback to props
  const displayName = currentUser?.full_name || userName || 'User';
  const displayEmail = currentUser?.email || userEmail || '';
  const displayRole = (currentUser?.roles?.[0] as any) || userRole || 'viewer';

  // Profile form state
  const [profileName, setProfileName] = useState('');
  
  // Password form state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Update profile name when currentUser loads
  useEffect(() => {
    if (currentUser?.full_name) {
      setProfileName(currentUser.full_name);
    }
  }, [currentUser]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    setIsDropdownOpen(false);
    logoutMutation.mutate();
  };

  const handleSaveProfile = () => {
    if (!currentUser?.id) {
      toast.error('Không tìm thấy thông tin người dùng');
      return;
    }

    if (!profileName.trim()) {
      toast.error('Vui lòng nhập họ tên');
      return;
    }

    updateUserMutation.mutate(
      { id: currentUser.id, data: { full_name: profileName } },
      {
        onSuccess: () => {
          toast.success('Cập nhật thông tin thành công!');
          setIsProfileModalOpen(false);
        },
        onError: (error: any) => {
          toast.error(error?.response?.data?.detail || 'Có lỗi xảy ra khi cập nhật thông tin');
        },
      }
    );
  };

  const handleChangePassword = () => {
    if (!currentPassword.trim() || !newPassword.trim() || !confirmPassword.trim()) {
      toast.error('Vui lòng nhập đầy đủ thông tin');
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error('Mật khẩu mới không khớp!');
      return;
    }

    if (newPassword.length < 8) {
      toast.error('Mật khẩu mới phải có ít nhất 8 ký tự');
      return;
    }

    changePasswordMutation.mutate(
      {
        old_password: currentPassword,
        new_password: newPassword,
      },
      {
        onSuccess: () => {
          toast.success('Đổi mật khẩu thành công!');
          setIsPasswordModalOpen(false);
          setCurrentPassword('');
          setNewPassword('');
          setConfirmPassword('');
        },
        onError: (error: any) => {
          toast.error(error?.response?.data?.detail || 'Mật khẩu hiện tại không đúng');
        },
      }
    );
  };

  const getRoleLabel = (role: string) => {
    const roleMap: Record<string, string> = {
      owner: 'Chủ doanh nghiệp',
      admin: 'Quản trị viên',
      accountant: 'Kế toán',
      viewer: 'Người xem'
    };
    return roleMap[role] || 'Người dùng';
  };

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Avatar Button */}
      <button 
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        className="focus:outline-none"
        disabled={loadingUser}
      >
        <Avatar className="cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all">
          <AvatarFallback className="bg-gradient-to-br from-blue-500 to-blue-600 text-white font-alata">
            {getInitials(displayName)}
          </AvatarFallback>
        </Avatar>
      </button>

      {/* Dropdown Menu */}
      {isDropdownOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden z-50">
          {/* User Info Section */}
          <div className="px-4 py-3 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-white">
            <div className="flex items-center gap-3">
              <Avatar className="size-10">
                <AvatarFallback className="bg-gradient-to-br from-blue-500 to-blue-600 text-white font-alata">
                  {getInitials(displayName)}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="font-alata text-slate-900 truncate" style={{ fontSize: '15px', fontWeight: 500 }}>
                  {displayName}
                </p>
                <p className="font-darker-grotesque text-slate-500 truncate" style={{ fontSize: '13px' }}>
                  {displayEmail}
                </p>
              </div>
            </div>
          </div>

          {/* Menu Items */}
          <div className="py-2">
            <button
              onClick={() => {
                setIsProfileModalOpen(true);
                setIsDropdownOpen(false);
              }}
              className="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-slate-50 transition-colors text-left"
            >
              <User className="size-4 text-slate-600" />
              <span className="font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>
                Thông tin tài khoản
              </span>
            </button>

            <button
              onClick={() => {
                setIsPasswordModalOpen(true);
                setIsDropdownOpen(false);
              }}
              className="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-slate-50 transition-colors text-left"
            >
              <Lock className="size-4 text-slate-600" />
              <span className="font-darker-grotesque text-slate-700" style={{ fontSize: '15px' }}>
                Đổi mật khẩu
              </span>
            </button>


          </div>

          {/* Logout Section */}
          <div className="border-t border-slate-200 py-2">
            <button
              onClick={handleLogout}
              className="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-red-50 transition-colors text-left"
            >
              <LogOut className="size-4 text-red-500" />
              <span className="font-darker-grotesque text-red-600" style={{ fontSize: '15px', fontWeight: 500 }}>
                Đăng xuất
              </span>
            </button>
          </div>
        </div>
      )}

      {/* Profile Modal */}
      <Dialog open={isProfileModalOpen} onOpenChange={setIsProfileModalOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader className="sr-only">
            <DialogTitle>Thông tin tài khoản</DialogTitle>
            <DialogDescription>Xem và chỉnh sửa thông tin cá nhân</DialogDescription>
          </DialogHeader>
          
          {/* Green Header - Full Width */}
          <div className="bg-gradient-to-r from-emerald-500 to-emerald-600 p-6 -mx-6 -mt-6 mb-6">
            <h3 className="text-white font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
              Thông tin tài khoản
            </h3>
            <p className="text-emerald-50 font-darker-grotesque mt-1" style={{ fontSize: '15px' }}>
              Xem và chỉnh sửa thông tin cá nhân
            </p>
          </div>

          <div className="px-6">
            {/* Form */}
            <div className="space-y-4">
              {/* Họ tên */}
              <div className="space-y-2">
                <Label htmlFor="profile-name" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Họ tên <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="profile-name"
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                  className="font-darker-grotesque"
                  style={{ fontSize: '16px' }}
                />
              </div>

              {/* Email (read-only) */}
              <div className="space-y-2">
                <Label htmlFor="profile-email" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Email
                </Label>
                <Input
                  id="profile-email"
                  value={displayEmail}
                  readOnly
                  className="font-darker-grotesque bg-slate-50 cursor-not-allowed"
                  style={{ fontSize: '16px' }}
                />
              </div>

              {/* Vai trò (read-only) */}
              <div className="space-y-2">
                <Label htmlFor="profile-role" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Vai trò
                </Label>
                <Input
                  id="profile-role"
                  value={getRoleLabel(displayRole)}
                  readOnly
                  className="font-darker-grotesque bg-slate-50 cursor-not-allowed"
                  style={{ fontSize: '16px' }}
                />
              </div>

              {/* Open Password Modal Button */}
              <div className="pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setIsProfileModalOpen(false);
                    setIsPasswordModalOpen(true);
                  }}
                  className="w-full font-darker-grotesque"
                  style={{ fontSize: '16px' }}
                >
                  <Lock className="size-4 mr-2" />
                  Đổi mật khẩu
                </Button>
              </div>
            </div>
          </div>

          {/* Footer */}
          <DialogFooter className="mt-6 px-6 pb-6">
            <Button 
              variant="outline" 
              onClick={() => setIsProfileModalOpen(false)}
              className="font-darker-grotesque"
              style={{ fontSize: '16px' }}
              disabled={updateUserMutation.isPending}
            >
              Hủy
            </Button>
            <Button 
              onClick={handleSaveProfile}
              className="bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 font-darker-grotesque"
              style={{ fontSize: '16px' }}
              disabled={updateUserMutation.isPending}
            >
              {updateUserMutation.isPending ? 'Đang lưu...' : 'Lưu thay đổi'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Change Password Modal */}
      <Dialog open={isPasswordModalOpen} onOpenChange={setIsPasswordModalOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader className="sr-only">
            <DialogTitle>Đổi mật khẩu</DialogTitle>
            <DialogDescription>Cập nhật mật khẩu đăng nhập của bạn</DialogDescription>
          </DialogHeader>
          
          {/* Purple Header - Full Width */}
          <div className="bg-gradient-to-r from-purple-500 to-purple-600 p-6 -mx-6 -mt-6 mb-6">
            <h3 className="text-white font-alata" style={{ fontSize: '24px', fontWeight: 400 }}>
              Đổi mật khẩu
            </h3>
            <p className="text-purple-50 font-darker-grotesque mt-1" style={{ fontSize: '15px' }}>
              Cập nhật mật khẩu đăng nhập của bạn
            </p>
          </div>

          <div className="px-6">
            {/* Form */}
            <div className="space-y-4">
              {/* Mật khẩu hiện tại */}
              <div className="space-y-2">
                <Label htmlFor="current-password" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Mật khẩu hiện tại <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="current-password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="font-darker-grotesque"
                  style={{ fontSize: '16px' }}
                />
              </div>

              {/* Mật khẩu mới */}
              <div className="space-y-2">
                <Label htmlFor="new-password" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Mật khẩu mới <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="font-darker-grotesque"
                  style={{ fontSize: '16px' }}
                />
              </div>

              {/* Nhập lại mật khẩu */}
              <div className="space-y-2">
                <Label htmlFor="confirm-password" className="font-darker-grotesque" style={{ fontSize: '16px' }}>
                  Nhập lại mật khẩu mới <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="confirm-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="font-darker-grotesque"
                  style={{ fontSize: '16px' }}
                />
              </div>
            </div>
          </div>

          {/* Footer */}
          <DialogFooter className="mt-6 px-6 pb-6">
            <Button 
              variant="outline" 
              onClick={() => {
                setIsPasswordModalOpen(false);
                setCurrentPassword('');
                setNewPassword('');
                setConfirmPassword('');
              }}
              className="font-darker-grotesque"
              style={{ fontSize: '16px' }}
              disabled={changePasswordMutation.isPending}
            >
              Hủy
            </Button>
            <Button 
              onClick={handleChangePassword}
              className="bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 font-darker-grotesque"
              style={{ fontSize: '16px' }}
              disabled={changePasswordMutation.isPending}
            >
              {changePasswordMutation.isPending ? 'Đang đổi...' : 'Lưu thay đổi'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}