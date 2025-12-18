/**
 * Test page để verify MSW + API hooks hoạt động
 */

import { useUsers, useCreateUser, useUpdateUser, useDeleteUser } from '../lib/api/hooks';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { useState } from 'react';
import { toast } from 'sonner';

export function APITestPage() {
  const [searchTerm, setSearchTerm] = useState('');
  const { data: usersData, isLoading, error } = useUsers({ 
    search: searchTerm,
    skip: 0,
    limit: 5 
  });

  const createUser = useCreateUser();
  const updateUser = useUpdateUser();
  const deleteUser = useDeleteUser();

  const handleCreateTest = () => {
    createUser.mutate({
      email: `test${Date.now()}@example.com`,
      full_name: 'Test User',
      password: 'password123',
      role: 'accountant',
    }, {
      onSuccess: () => toast.success('User created successfully!'),
      onError: (err) => toast.error(`Failed: ${err.message}`),
    });
  };

  const handleUpdateTest = (userId: number) => {
    updateUser.mutate({
      id: userId,
      data: { full_name: 'Updated Name' },
    }, {
      onSuccess: () => toast.success('User updated!'),
      onError: (err) => toast.error(`Failed: ${err.message}`),
    });
  };

  const handleDeleteTest = (userId: number) => {
    deleteUser.mutate(userId, {
      onSuccess: () => toast.success('User deleted!'),
      onError: (err) => toast.error(`Failed: ${err.message}`),
    });
  };

  if (error) {
    return (
      <div className="p-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-red-600">Error</CardTitle>
          </CardHeader>
          <CardContent>
            <p>{error.message}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>🧪 API Test Page - MSW + React Query</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-gray-600 mb-2">Search users:</p>
            <Input
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-xs"
            />
          </div>

          <div>
            <Button onClick={handleCreateTest} disabled={createUser.isPending}>
              {createUser.isPending ? 'Creating...' : 'Test Create User'}
            </Button>
          </div>

          <div>
            <p className="text-sm font-semibold mb-2">Users List (Loading: {isLoading ? 'Yes' : 'No'})</p>
            {isLoading && <p className="text-gray-500">Loading users...</p>}
            {usersData && (
              <div className="space-y-2">
                <p className="text-sm text-gray-600">Total: {usersData.total} users</p>
                <div className="space-y-2">
                  {usersData.items.map((user) => (
                    <div key={user.id} className="border p-3 rounded flex justify-between items-center">
                      <div>
                        <p className="font-medium">{user.full_name || 'No name'}</p>
                        <p className="text-sm text-gray-600">{user.email}</p>
                        <p className="text-xs text-gray-500">
                          Role: {user.roles.join(', ')} | Status: {user.status}
                        </p>
                      </div>
                      <div className="space-x-2">
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => handleUpdateTest(user.id)}
                          disabled={updateUser.isPending}
                        >
                          Update
                        </Button>
                        <Button 
                          size="sm" 
                          variant="destructive"
                          onClick={() => handleDeleteTest(user.id)}
                          disabled={deleteUser.isPending}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
