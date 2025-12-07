import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Upload, CheckCircle, History } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="container mx-auto px-4 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          Trading Algorithm Document Analyzer
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          AI-powered analysis for trading documentation with complete audit trails
          and compliance tracking.
        </p>
      </div>

      <div className="flex justify-center mb-12">
        <Button size="lg" className="gap-2" asChild>
          <Link to="/documents/upload">
            <Upload className="h-5 w-5" />
            Upload Document
          </Link>
        </Button>
      </div>

      <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
        <Card>
          <CardHeader>
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            <CardTitle className="text-lg">Upload & Convert</CardTitle>
            <CardDescription>
              Support for Word, PDF, RST, and Markdown documents up to 100 pages.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Documents are automatically converted to a standardized format for AI analysis.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
              <CheckCircle className="h-5 w-5 text-primary" />
            </div>
            <CardTitle className="text-lg">AI Analysis</CardTitle>
            <CardDescription>
              Multi-model AI support with Gemini, OpenAI, and Claude.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Get actionable feedback with policy compliance checking and user acceptance workflow.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center mb-2">
              <History className="h-5 w-5 text-primary" />
            </div>
            <CardTitle className="text-lg">Complete Audit Trail</CardTitle>
            <CardDescription>
              Every change is tracked with immutable event sourcing.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Version history, rollback capability, and compliance reporting for regulatory needs.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
