import { Routes, Route } from 'react-router-dom';
import Layout from '@/components/layout/Layout';
import HomePage from '@/pages/HomePage';
import DocumentListPage from '@/pages/DocumentListPage';
import DocumentUploadPage from '@/pages/DocumentUploadPage';
import DocumentDetailPage from '@/pages/DocumentDetailPage';
import { Toaster } from '@/components/ui/sonner';

function AuditPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-4">Audit Log</h1>
      <p className="text-muted-foreground">Audit log coming soon...</p>
    </div>
  );
}

function NotFoundPage() {
  return (
    <div className="container mx-auto px-4 py-8 text-center">
      <h1 className="text-4xl font-bold mb-4">404</h1>
      <p className="text-muted-foreground">Page not found</p>
    </div>
  );
}

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="documents" element={<DocumentListPage />} />
          <Route path="documents/upload" element={<DocumentUploadPage />} />
          <Route path="documents/:id" element={<DocumentDetailPage />} />
          <Route path="documents/:id/:tab" element={<DocumentDetailPage />} />
          <Route path="audit" element={<AuditPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
      <Toaster />
    </>
  );
}

export default App;
