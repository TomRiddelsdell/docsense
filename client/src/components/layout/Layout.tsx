import { Link, Outlet, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { FileText, Upload, FolderOpen, History } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/documents', label: 'Documents', icon: FolderOpen },
  { href: '/documents/upload', label: 'Upload', icon: Upload },
  { href: '/audit', label: 'Audit Log', icon: History },
];

export default function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b sticky top-0 bg-background z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <FileText className="h-6 w-6 text-primary" />
            <span className="text-xl font-semibold">DocSense</span>
          </Link>
          <nav className="flex items-center gap-2">
            {navItems.map((item) => {
              const isActive = location.pathname === item.href || 
                (item.href !== '/' && location.pathname.startsWith(item.href));
              return (
                <Button
                  key={item.href}
                  variant={isActive ? 'default' : 'ghost'}
                  asChild
                  className={cn('gap-2', isActive && 'pointer-events-none')}
                >
                  <Link to={item.href}>
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                </Button>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t mt-auto">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          Trading Algorithm Document Analyzer - Built with Event Sourcing & CQRS
        </div>
      </footer>
    </div>
  );
}
