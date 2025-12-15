import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

/**
 * DevModeBanner - Visual indicator when auth bypass is enabled
 * 
 * Displays a yellow warning banner at the top of the page when:
 * - Backend is in development mode
 * - DEV_AUTH_BYPASS is enabled
 * - Detected via X-Dev-Mode response header
 * 
 * Security:
 * - Only possible in development environment
 * - Production blocks DEV_AUTH_BYPASS via Settings validation
 * - See: docs/decisions/023-local-development-auth-bypass.md
 */
export function DevModeBanner() {
  const [isDevMode, setIsDevMode] = useState(false);
  const [devUser, setDevUser] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const checkDevMode = async () => {
    try {
      // Make a lightweight request to check headers
      const response = await fetch('/api/v1/health', {
        method: 'GET',
      });

      // Check for dev mode headers
      const devModeHeader = response.headers.get('X-Dev-Mode');
      const devUserHeader = response.headers.get('X-Dev-User');

      if (devModeHeader === 'true') {
        setIsDevMode(true);
        setDevUser(devUserHeader);
      }
    } catch (error) {
      // Silently fail - banner just won't show
      console.debug('Failed to check dev mode:', error);
    }
  };

  useEffect(() => {
    // Check for dev mode on initial load
    void checkDevMode();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Don't show if not in dev mode or user dismissed
  if (!isDevMode || dismissed) {
    return null;
  }

  return (
    <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-yellow-600 shrink-0" />
          <div className="flex flex-col sm:flex-row sm:items-center sm:gap-2">
            <span className="text-sm font-semibold text-yellow-900">
              Development Mode Active
            </span>
            <span className="text-sm text-yellow-700">
              Authentication bypass enabled
              {devUser && (
                <>
                  {' '}· Logged in as <span className="font-mono">{devUser}</span>
                </>
              )}
            </span>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-yellow-600 hover:text-yellow-900 transition-colors"
          aria-label="Dismiss banner"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}
