/**
 * CurrentUser Component - Display authenticated user info
 * 
 * Shows user's name, groups, and roles in the header with a dropdown
 */

import { User, UserCircle } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/hooks/useAuth';

export function CurrentUser() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <UserCircle className="h-5 w-5 animate-pulse" />
        <span>Loading...</span>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <UserCircle className="h-5 w-5" />
        <span>Not authenticated</span>
      </div>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2">
          <User className="h-5 w-5" />
          <span className="hidden md:inline">{user.display_name}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-72" align="end">
        <DropdownMenuLabel>
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">{user.display_name}</p>
            <p className="text-xs leading-none text-muted-foreground">{user.email}</p>
            <p className="text-xs leading-none text-muted-foreground">ID: {user.kerberos_id}</p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        {user.roles.length > 0 && (
          <>
            <DropdownMenuGroup>
              <DropdownMenuLabel className="text-xs text-muted-foreground font-normal">
                Roles
              </DropdownMenuLabel>
              <div className="px-2 py-1 flex flex-wrap gap-1">
                {user.roles.map((role) => (
                  <Badge key={role} variant="secondary" className="text-xs">
                    {role}
                  </Badge>
                ))}
              </div>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
          </>
        )}

        {user.groups.length > 0 && (
          <>
            <DropdownMenuGroup>
              <DropdownMenuLabel className="text-xs text-muted-foreground font-normal">
                Groups
              </DropdownMenuLabel>
              <div className="px-2 py-1 flex flex-wrap gap-1 max-h-32 overflow-y-auto">
                {user.groups.map((group) => (
                  <Badge key={group} variant="outline" className="text-xs">
                    {group}
                  </Badge>
                ))}
              </div>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
          </>
        )}

        <DropdownMenuGroup>
          <DropdownMenuItem disabled className="text-xs text-muted-foreground">
            Status: {user.is_active ? 'Active' : 'Inactive'}
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
