import { Bell, Menu, X, Plus, Edit, Trash2, Eye, UserCog, Shield, Users, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { UserMenu } from './UserMenu';
import { Badge } from './ui/badge';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { useState } from 'react';
import { useSidebar } from '../contexts/SidebarContext';
import { useUsers, useCreateUser, useUpdateUser, useDeleteUser } from '../lib/api/hooks';
import { User } from '../lib/api/services/users';
import { toast } from 'sonner';

export function UserManagement() {
  const { isSidebarOpen, toggleSidebar } = useSidebar();
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isViewDialogOpen, setIsViewDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  // Fetch users from API
  const itemsPerPage = 10;
  const { data: usersData, isLoading: loadingUsers } = useUsers({
    search: searchTerm || undefined,
    role: roleFilter !== 'all' ? roleFilter : undefined,
    status: statusFilter !== 'all' ? statusFilter : undefined,
    skip: (currentPage - 1) * itemsPerPage,
    limit: itemsPerPage,
  });

  // Mutations
  const createUserMutation = useCreateUser();
  const updateUserMutation = useUpdateUser();
  const deleteUserMutation = useDeleteUser();

  // Map API data
  const users = usersData?.items || [];
  const totalPages = Math.ceil((usersData?.total || 0) / itemsPerPage);

  // Form states
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    role: 'accountant' as 'owner' | 'admin' | 'accountant' | 'cashier',
    status: 'active' as 'active' | 'inactive',
    password: '',
  });

  const getRoleBadge = (role: string) => {
    const roleConfig: Record<string, { label: string; className: string }> = {
      owner: { label: 'Owner', className: 'bg-purple-100 text-purple-700 border-purple-200' },
      admin: { label: 'Admin', className: 'bg-violet-100 text-violet-700 border-violet-200' },
      accountant: { label: 'Accountant', className: 'bg-indigo-100 text-indigo-700 border-indigo-200' },
      cashier: { label: 'Cashier', className: 'bg-blue-100 text-blue-700 border-blue-200' },
    };
    const config = roleConfig[role] || roleConfig['accountant'];
    return (
      <Badge className={`${config.className} border font-darker-grotesque`} style={{ fontSize: '14px' }}>
        {config.label}
      </Badge>
    );
  };

  const getStatusBadge = (status: string) => {
    return status === 'active' ? (
      <Badge className="bg-green-100 text-green-700 border-green-200 border font-darker-grotesque" style={{ fontSize: '14px' }}>
        Đang hoạt động
      </Badge>
    ) : (
      <Badge className="bg-gray-100 text-gray-700 border-gray-200 border font-darker-grotesque" style={{ fontSize: '14px' }}>
        Vô hiệu hóa
      </Badge>
    );
  };

  const handleAddUser = () => {
    createUserMutation.mutate(
      {
        email: formData.email,
        full_name: formData.full_name,
        password: formData.password,
        role: formData.role,
      },
      {
        onSuccess: () => {
          setIsAddDialogOpen(false);
          resetForm();
          toast.success('Đã thêm tài khoản thành công!');
        },
        onError: () => {
          toast.error('Lỗi khi thêm tài khoản');
        },
      }
    );
  };

  const handleEditUser = () => {
    if (!selectedUser) return;
    updateUserMutation.mutate(
      {
        id: selectedUser.id,
        data: {
          full_name: formData.full_name,
          status: formData.status,
          role: formData.role,
        },
      },
      {
        onSuccess: () => {
          setIsEditDialogOpen(false);
          setSelectedUser(null);
          resetForm();
          toast.success('Đã cập nhật tài khoản!');
        },
        onError: () => {
          toast.error('Lỗi khi cập nhật tài khoản');
        },
      }
    );
  };

  const handleDeleteUser = (userId: number) => {
    if (confirm('Bạn có chắc chắn muốn vô hiệu hóa tài khoản này?')) {
      deleteUserMutation.mutate(userId, {
        onSuccess: () => {
          toast.success('Đã vô hiệu hóa tài khoản!');
        },
        onError: () => {
          toast.error('Lỗi khi vô hiệu hóa tài khoản');
        },
      });
    }
  };

  const resetForm = () => {
    setFormData({
      full_name: '',
      email: '',
      role: 'accountant',
      status: 'active',
      password: '',
    });
  };

  const openEditDialog = (user: User) => {
    setSelectedUser(user);
    setFormData({
      full_name: user.full_name || '',
      email: user.email,
      role: (user.roles?.[0] as 'owner' | 'admin' | 'accountant' | 'cashier') || 'accountant',
      status: (user.status as 'active' | 'inactive') || 'active',
      password: '',
    });
    setIsEditDialogOpen(true);
  };

  const openViewDialog = (user: User) => {
    setSelectedUser(user);
    setIsViewDialogOpen(true);
  };

  const totalUsers = usersData?.total || 0;
  const activeUsers = users.filter(u => u.status === 'active').length;
  const inactiveUsers = users.filter(u => u.status === 'inactive').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-violet-50/20 to-slate-100">
      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80">
        <div className="flex h-16 items-center px-8">
          <Button variant="ghost" size="icon" className="mr-4" onClick={toggleSidebar}>
            {isSidebarOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </Button>
          <div className="flex-1">
            <h1 className="text-slate-900 font-crimson-pro" style={{ fontSize: '28px', fontWeight: 500 }}>SME Pulse</h1>
          </div>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="size-5" />
              <span className="absolute top-2 right-2 size-2 bg-red-500 rounded-full"></span>
            </Button>
            <UserMenu 
              userRole="owner"
              userName="Nguyễn Văn An"
              userEmail="an.nguyen@sme.com"
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-8 max-w-[1400px] mx-auto">
        <div className="mb-6" style={{ lineHeight: 1.2 }}>
          <h2 className="text-slate-900 mb-1 font-alata" style={{ fontSize: '32px', fontWeight: 400 }}>Quản lý tài khoản</h2>
          <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '18px' }}>
            Quản lý người dùng và phân quyền hệ thống
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <Card className="border-0 shadow-md bg-gradient-to-br from-violet-500 to-violet-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-violet-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Tổng tài khoản</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '32px', fontWeight: 700 }}>
                    {totalUsers}
                  </p>
                </div>
                <Users className="size-12 text-violet-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md bg-gradient-to-br from-green-500 to-green-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-green-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Đang hoạt động</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '32px', fontWeight: 700 }}>
                    {activeUsers}
                  </p>
                </div>
                <UserCog className="size-12 text-green-200" />
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-md bg-gradient-to-br from-gray-500 to-gray-600 transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 cursor-pointer">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-gray-100 font-darker-grotesque" style={{ fontSize: '15px', fontWeight: 500 }}>Vô hiệu hóa</p>
                  <p className="text-white font-alata mt-2" style={{ fontSize: '32px', fontWeight: 700 }}>
                    {inactiveUsers}
                  </p>
                </div>
                <Shield className="size-12 text-gray-200" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters and Actions */}
        <Card className="border-0 shadow-lg bg-white mb-6">
          <CardContent className="pt-6">
            <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
              <div className="flex flex-col sm:flex-row gap-3 flex-1 w-full">
                {/* Search */}
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-5 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Tìm theo tên hoặc email..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-violet-500"
                    style={{ fontSize: '16px' }}
                  />
                </div>

                {/* Role Filter */}
                <Select value={roleFilter} onValueChange={setRoleFilter}>
                  <SelectTrigger className="w-full sm:w-[180px] font-darker-grotesque" style={{ fontSize: '16px' }}>
                    <SelectValue placeholder="Vai trò" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Tất cả vai trò</SelectItem>
                    <SelectItem value="owner" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Owner</SelectItem>
                    <SelectItem value="admin" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Admin</SelectItem>
                    <SelectItem value="accountant" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Accountant</SelectItem>
                    <SelectItem value="cashier" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Cashier</SelectItem>
                  </SelectContent>
                </Select>

                {/* Status Filter */}
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-full sm:w-[180px] font-darker-grotesque" style={{ fontSize: '16px' }}>
                    <SelectValue placeholder="Trạng thái" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Tất cả trạng thái</SelectItem>
                    <SelectItem value="active" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Đang hoạt động</SelectItem>
                    <SelectItem value="inactive" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Vô hiệu hóa</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={() => setIsAddDialogOpen(true)}
                className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white font-darker-grotesque whitespace-nowrap"
                style={{ fontSize: '16px' }}
              >
                <Plus className="size-4 mr-2" />
                Thêm tài khoản
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Users Table */}
        <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-violet-50/80 border-b-2 border-violet-100">
                <tr>
                  <th className="text-left p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                    Họ tên
                  </th>
                  <th className="text-left p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                    Email
                  </th>
                  <th className="text-left p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                    Vai trò
                  </th>
                  <th className="text-left p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                    Trạng thái
                  </th>
                  <th className="text-center p-4 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                    Thao tác
                  </th>
                </tr>
              </thead>
              <tbody>
                {loadingUsers ? (
                  // Loading skeleton
                  Array.from({ length: 5 }).map((_, index) => (
                    <tr key={`skeleton-${index}`} className="border-b border-slate-100">
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <div className="size-10 bg-slate-200 rounded-full animate-pulse"></div>
                          <div className="h-4 bg-slate-200 rounded animate-pulse w-32"></div>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="h-4 bg-slate-200 rounded animate-pulse w-40"></div>
                      </td>
                      <td className="p-4">
                        <div className="h-6 bg-slate-200 rounded animate-pulse w-24"></div>
                      </td>
                      <td className="p-4">
                        <div className="h-6 bg-slate-200 rounded animate-pulse w-28"></div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center justify-center gap-2">
                          <div className="size-8 bg-slate-200 rounded animate-pulse"></div>
                          <div className="size-8 bg-slate-200 rounded animate-pulse"></div>
                          <div className="size-8 bg-slate-200 rounded animate-pulse"></div>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-12 text-center">
                      <p className="text-slate-500 font-darker-grotesque" style={{ fontSize: '16px' }}>
                        Không tìm thấy tài khoản nào
                      </p>
                    </td>
                  </tr>
                ) : (
                  users.map((user, index) => (
                    <tr 
                      key={user.id} 
                      className={`border-b border-slate-100 hover:bg-violet-50/50 transition-colors ${
                        index % 2 === 0 ? 'bg-white' : 'bg-violet-50/20'
                      }`}
                    >
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <Avatar>
                            <AvatarFallback className="bg-violet-100 text-violet-700 font-alata">
                              {(user.full_name || user.email).split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <span className="font-darker-grotesque text-slate-900" style={{ fontSize: '16px', fontWeight: 500 }}>
                            {user.full_name || 'No name'}
                          </span>
                        </div>
                      </td>
                      <td className="p-4">
                        <span className="font-darker-grotesque text-slate-600" style={{ fontSize: '15px' }}>
                          {user.email}
                        </span>
                      </td>
                      <td className="p-4">
                        {getRoleBadge(user.roles?.[0] || 'accountant')}
                      </td>
                      <td className="p-4">
                        {getStatusBadge(user.status)}
                      </td>
                      <td className="p-4">
                        <div className="flex items-center justify-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openViewDialog(user)}
                            className="text-slate-600 hover:text-violet-600 hover:bg-violet-50"
                          >
                            <Eye className="size-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openEditDialog(user)}
                            className="text-slate-600 hover:text-blue-600 hover:bg-blue-50"
                          >
                            <Edit className="size-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteUser(user.id)}
                            disabled={user.status === 'inactive'}
                            className="text-slate-600 hover:text-red-600 hover:bg-red-50 disabled:opacity-50"
                          >
                            <Trash2 className="size-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-1 p-4 border-t bg-violet-50/30">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="font-darker-grotesque disabled:opacity-50"
              >
                <ChevronLeft className="size-4" />
              </Button>
              
              {(() => {
                const renderPageNumbers = () => {
                  const pages = [];
                  
                  if (totalPages <= 7) {
                    // Show all pages if 7 or less
                    for (let i = 1; i <= totalPages; i++) {
                      pages.push(
                        <Button
                          key={i}
                          variant={currentPage === i ? "default" : "ghost"}
                          size="sm"
                          onClick={() => setCurrentPage(i)}
                          className={`font-darker-grotesque min-w-[40px] ${
                            currentPage === i
                              ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700'
                              : 'hover:bg-violet-100'
                          }`}
                          style={{ fontSize: '15px' }}
                        >
                          {i}
                        </Button>
                      );
                    }
                  } else {
                    // Always show first page
                    pages.push(
                      <Button
                        key={1}
                        variant={currentPage === 1 ? "default" : "ghost"}
                        size="sm"
                        onClick={() => setCurrentPage(1)}
                        className={`font-darker-grotesque min-w-[40px] ${
                          currentPage === 1
                            ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700'
                            : 'hover:bg-violet-100'
                        }`}
                        style={{ fontSize: '15px' }}
                      >
                        1
                      </Button>
                    );

                    if (currentPage <= 3) {
                      // Near the start: 1 2 3 4 ... 10
                      for (let i = 2; i <= Math.min(4, totalPages - 1); i++) {
                        pages.push(
                          <Button
                            key={i}
                            variant={currentPage === i ? "default" : "ghost"}
                            size="sm"
                            onClick={() => setCurrentPage(i)}
                            className={`font-darker-grotesque min-w-[40px] ${
                              currentPage === i
                                ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700'
                                : 'hover:bg-violet-100'
                            }`}
                            style={{ fontSize: '15px' }}
                          >
                            {i}
                          </Button>
                        );
                      }
                      if (totalPages > 5) {
                        pages.push(
                          <span key="dots-end" className="px-2 text-slate-400 font-darker-grotesque" style={{ fontSize: '15px' }}>
                            ...
                          </span>
                        );
                      }
                    } else if (currentPage >= totalPages - 2) {
                      // Near the end: 1 ... 7 8 9 10
                      pages.push(
                        <span key="dots-start" className="px-2 text-slate-400 font-darker-grotesque" style={{ fontSize: '15px' }}>
                          ...
                        </span>
                      );
                      for (let i = Math.max(2, totalPages - 3); i < totalPages; i++) {
                        pages.push(
                          <Button
                            key={i}
                            variant={currentPage === i ? "default" : "ghost"}
                            size="sm"
                            onClick={() => setCurrentPage(i)}
                            className={`font-darker-grotesque min-w-[40px] ${
                              currentPage === i
                                ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700'
                                : 'hover:bg-violet-100'
                            }`}
                            style={{ fontSize: '15px' }}
                          >
                            {i}
                          </Button>
                        );
                      }
                    } else {
                      // In the middle: 1 ... 4 5 6 ... 10
                      pages.push(
                        <span key="dots-start" className="px-2 text-slate-400 font-darker-grotesque" style={{ fontSize: '15px' }}>
                          ...
                        </span>
                      );
                      for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                        pages.push(
                          <Button
                            key={i}
                            variant={currentPage === i ? "default" : "ghost"}
                            size="sm"
                            onClick={() => setCurrentPage(i)}
                            className={`font-darker-grotesque min-w-[40px] ${
                              currentPage === i
                                ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700'
                                : 'hover:bg-violet-100'
                            }`}
                            style={{ fontSize: '15px' }}
                          >
                            {i}
                          </Button>
                        );
                      }
                      pages.push(
                        <span key="dots-end" className="px-2 text-slate-400 font-darker-grotesque" style={{ fontSize: '15px' }}>
                          ...
                        </span>
                      );
                    }

                    // Always show last page
                    pages.push(
                      <Button
                        key={totalPages}
                        variant={currentPage === totalPages ? "default" : "ghost"}
                        size="sm"
                        onClick={() => setCurrentPage(totalPages)}
                        className={`font-darker-grotesque min-w-[40px] ${
                          currentPage === totalPages
                            ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:from-violet-600 hover:to-purple-700'
                            : 'hover:bg-violet-100'
                        }`}
                        style={{ fontSize: '15px' }}
                      >
                        {totalPages}
                      </Button>
                    );
                  }
                  
                  return pages;
                };

                return renderPageNumbers();
              })()}
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="font-darker-grotesque disabled:opacity-50"
              >
                <ChevronRight className="size-4" />
              </Button>
            </div>
          )}
        </div>
      </main>

      {/* Add User Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-alata text-slate-900" style={{ fontSize: '24px' }}>
              Thêm tài khoản mới
            </DialogTitle>
            <DialogDescription className="font-darker-grotesque text-slate-600" style={{ fontSize: '16px' }}>
              Tạo tài khoản người dùng mới cho hệ thống
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Họ tên
              </label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-violet-500"
                style={{ fontSize: '15px' }}
                placeholder="Nguyễn Văn A"
              />
            </div>
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-violet-500"
                style={{ fontSize: '15px' }}
                placeholder="email@company.com"
              />
            </div>
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Vai trò
              </label>
              <Select value={formData.role} onValueChange={(value: string) => setFormData({ ...formData, role: value as 'owner' | 'admin' | 'accountant' | 'cashier' })}>
                <SelectTrigger className="font-darker-grotesque" style={{ fontSize: '15px' }}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="owner" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Owner</SelectItem>
                  <SelectItem value="admin" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Admin</SelectItem>
                  <SelectItem value="accountant" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Accountant</SelectItem>
                  <SelectItem value="cashier" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Cashier</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Mật khẩu
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-violet-500"
                style={{ fontSize: '15px' }}
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Trạng thái
              </label>
              <Select value={formData.status} onValueChange={(value: string) => setFormData({ ...formData, status: value as 'active' | 'inactive' })}>
                <SelectTrigger className="font-darker-grotesque" style={{ fontSize: '15px' }}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Đang hoạt động</SelectItem>
                  <SelectItem value="inactive" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Vô hiệu hóa</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)} className="font-darker-grotesque">
              Hủy
            </Button>
            <Button onClick={handleAddUser} className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white font-darker-grotesque">
              Thêm tài khoản
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-alata text-slate-900" style={{ fontSize: '24px' }}>
              Chỉnh sửa tài khoản
            </DialogTitle>
            <DialogDescription className="font-darker-grotesque text-slate-600" style={{ fontSize: '16px' }}>
              Cập nhật thông tin tài khoản người dùng
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Họ tên
              </label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-violet-500"
                style={{ fontSize: '15px' }}
              />
            </div>
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Email
              </label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-violet-500"
                style={{ fontSize: '15px' }}
              />
            </div>
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Vai trò
              </label>
              <Select value={formData.role} onValueChange={(value: string) => setFormData({ ...formData, role: value as 'owner' | 'admin' | 'accountant' | 'cashier' })}>
                <SelectTrigger className="font-darker-grotesque" style={{ fontSize: '15px' }}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="owner" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Owner</SelectItem>
                  <SelectItem value="admin" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Admin</SelectItem>
                  <SelectItem value="accountant" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Accountant</SelectItem>
                  <SelectItem value="cashier" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Cashier</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Mật khẩu mới (để trống nếu không đổi)
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-darker-grotesque focus:outline-none focus:ring-2 focus:ring-violet-500"
                style={{ fontSize: '15px' }}
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="block mb-2 font-darker-grotesque text-slate-700" style={{ fontSize: '15px', fontWeight: 600 }}>
                Trạng thái
              </label>
              <Select value={formData.status} onValueChange={(value: string) => setFormData({ ...formData, status: value as 'active' | 'inactive' })}>
                <SelectTrigger className="font-darker-grotesque" style={{ fontSize: '15px' }}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Đang hoạt động</SelectItem>
                  <SelectItem value="inactive" className="font-darker-grotesque" style={{ fontSize: '15px' }}>Vô hiệu hóa</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)} className="font-darker-grotesque">
              Hủy
            </Button>
            <Button onClick={handleEditUser} className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white font-darker-grotesque">
              Lưu thay đổi
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* View User Dialog */}
      <Dialog open={isViewDialogOpen} onOpenChange={setIsViewDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-alata text-slate-900" style={{ fontSize: '24px' }}>
              Thông tin tài khoản
            </DialogTitle>
            <DialogDescription className="font-darker-grotesque text-slate-600" style={{ fontSize: '16px' }}>
              Chi tiết người dùng
            </DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-4 py-4">
              <div className="flex items-center gap-4 pb-4 border-b">
                <Avatar className="size-16">
                  <AvatarFallback className="bg-violet-100 text-violet-700 font-alata text-2xl">
                    {(selectedUser.full_name || selectedUser.email).split(' ').map((n: string) => n[0]).join('').slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="font-darker-grotesque text-slate-900" style={{ fontSize: '18px', fontWeight: 600 }}>
                    {selectedUser.full_name}
                  </p>
                  <p className="text-slate-600 font-darker-grotesque" style={{ fontSize: '15px' }}>
                    {selectedUser.email}
                  </p>
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Vai trò</p>
                  {getRoleBadge(selectedUser.roles?.[0] || 'accountant')}
                </div>
                <div>
                  <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Trạng thái</p>
                  {getStatusBadge(selectedUser.status)}
                </div>
                <div>
                  <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Ngày tạo</p>
                  <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '15px' }}>
                    {new Date(selectedUser.created_at).toLocaleDateString('vi-VN')}
                  </p>
                </div>
                {selectedUser.last_login && (
                  <div>
                    <p className="text-slate-500 font-darker-grotesque mb-1" style={{ fontSize: '14px' }}>Đăng nhập gần nhất</p>
                    <p className="text-slate-900 font-darker-grotesque" style={{ fontSize: '15px' }}>
                      {selectedUser.last_login}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsViewDialogOpen(false)} className="font-darker-grotesque">
              Đóng
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}