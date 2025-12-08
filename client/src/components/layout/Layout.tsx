import { Link, Outlet, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { FileText, Upload, FolderOpen, History } from 'lucide-react';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/documents', label: 'Documents', shortLabel: 'Docs', icon: FolderOpen },
  { href: '/documents/upload', label: 'Upload', shortLabel: 'Upload', icon: Upload },
  { href: '/audit', label: 'Audit Log', shortLabel: 'Audit', icon: History },
];

export default function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b sticky top-0 bg-background z-50">
        <div className="container mx-auto px-3 sm:px-4 py-3 sm:py-4 flex items-center justify-between gap-2">
          <Link to="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity shrink-0">
            <FileText className="h-6 w-6 text-primary" />
            <span className="text-lg sm:text-xl font-semibold hidden xs:inline">DocSense</span>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2">
            {navItems.map((item) => {
              const isActive = location.pathname === item.href || 
                (item.href !== '/' && location.pathname.startsWith(item.href));
              const isExactMatch = location.pathname === item.href;
              return (
                <Button
                  key={item.href}
                  variant={isActive ? 'default' : 'ghost'}
                  size="sm"
                  asChild
                  className={cn('gap-1 sm:gap-2 px-2 sm:px-4', isExactMatch && 'pointer-events-none')}
                >
                  <Link to={item.href}>
                    <item.icon className="h-5 w-5" />
                    <span className="hidden sm:inline">{item.label}</span>
                    <span className="sm:hidden text-xs">{item.shortLabel}</span>
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
