import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ConnectionLineType,
  MarkerType,
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { GitBranch, AlertCircle } from 'lucide-react';
import { useDocumentParameters } from '@/hooks/useDocuments';
import type { Parameter } from '@/types/api';

interface ParameterGraphProps {
  documentId: string;
}

const typeColors: Record<string, string> = {
  numeric: '#3b82f6',
  percentage: '#10b981',
  duration: '#f59e0b',
  boolean: '#8b5cf6',
  text: '#6b7280',
  ratio: '#ef4444',
};

function createNodesAndEdges(parameters: Parameter[]): { nodes: Node[]; edges: Edge[] } {
  const paramMap = new Map<string, Parameter>();
  parameters.forEach((p) => paramMap.set(p.id, p));

  const sectionGroups = new Map<string, Parameter[]>();
  parameters.forEach((p) => {
    const section = p.section || 'General';
    if (!sectionGroups.has(section)) {
      sectionGroups.set(section, []);
    }
    sectionGroups.get(section)!.push(p);
  });

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  let yOffset = 0;

  sectionGroups.forEach((params) => {
    params.forEach((param, idx) => {
      const xPos = 50 + (idx % 3) * 300;
      const yPos = yOffset + Math.floor(idx / 3) * 120;

      nodes.push({
        id: param.id,
        type: 'default',
        position: { x: xPos, y: yPos },
        data: {
          label: (
            <div className="text-left p-1">
              <div className="font-semibold text-sm">{param.name}</div>
              <div className="text-xs text-gray-500 mt-1">
                <span
                  className="inline-block px-1.5 py-0.5 rounded text-white text-[10px]"
                  style={{ backgroundColor: typeColors[param.type] || '#6b7280' }}
                >
                  {param.type}
                </span>
                {param.value && (
                  <span className="ml-2 font-mono">{param.value}</span>
                )}
              </div>
            </div>
          ),
        },
        style: {
          background: 'white',
          border: `2px solid ${typeColors[param.type] || '#6b7280'}`,
          borderRadius: '8px',
          padding: '8px',
          minWidth: '180px',
        },
      });

      param.dependencies.forEach((depId) => {
        if (paramMap.has(depId)) {
          edges.push({
            id: `${depId}-${param.id}`,
            source: depId,
            target: param.id,
            type: ConnectionLineType.SmoothStep,
            animated: true,
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#94a3b8',
            },
            style: { stroke: '#94a3b8', strokeWidth: 2 },
          });
        }
      });

    });

    yOffset += Math.ceil(params.length / 3) * 120 + 80;
  });

  return { nodes, edges };
}

export default function ParameterGraph({ documentId }: ParameterGraphProps) {
  const { data, isLoading, isError, refetch } = useDocumentParameters(documentId);

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!data?.parameters) {
      return { initialNodes: [], initialEdges: [] };
    }
    const { nodes, edges } = createNodesAndEdges(data.parameters);
    return { initialNodes: nodes, initialEdges: edges };
  }, [data?.parameters]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Parameter Graph</CardTitle>
          <CardDescription>Loading parameters...</CardDescription>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[500px] w-full" />
        </CardContent>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Parameter Graph</CardTitle>
          <CardDescription>Failed to load parameters</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-12 text-center">
            <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
            <p className="text-muted-foreground">
              Could not extract parameters from this document.
            </p>
            <button
              onClick={() => refetch()}
              className="mt-4 text-primary hover:underline"
            >
              Try again
            </button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data?.parameters || data.parameters.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Parameter Graph</CardTitle>
          <CardDescription>
            Visualize trading parameters and their relationships
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="py-12 text-center">
            <GitBranch className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <CardTitle className="text-lg mb-2">No Parameters Found</CardTitle>
            <CardDescription>
              No trading parameters were detected in this document.
              Upload a document with trading algorithm details to see the parameter graph.
            </CardDescription>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Parameter Graph</CardTitle>
            <CardDescription>
              {data.total} parameters extracted from the document
            </CardDescription>
          </div>
          <div className="flex gap-2 flex-wrap">
            {Object.entries(typeColors).map(([type, color]) => (
              <Badge
                key={type}
                variant="outline"
                className="text-xs"
                style={{ borderColor: color, color }}
              >
                {type}
              </Badge>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-[500px] border rounded-lg overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            attributionPosition="bottom-right"
          >
            <Background />
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                const param = data.parameters.find((p) => p.id === node.id);
                return typeColors[param?.type || 'text'] || '#6b7280';
              }}
              maskColor="rgba(0, 0, 0, 0.1)"
            />
          </ReactFlow>
        </div>
      </CardContent>
    </Card>
  );
}
