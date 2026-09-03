"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  MarkerType,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { DashboardLayout } from "@/components/layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";

interface GraphNode {
  id: string;
  type: string;
  amount: number;
  currency: string;
  status: string;
  source: string;
  description?: string;
}

interface GraphEdge {
  source: string;
  target: string;
  edge_type: string;
  label?: string;
}

interface EvidenceGraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

function EvidenceGraphContent() {
  const searchParams = useSearchParams();
  const caseParam = searchParams.get("case");
  const [caseId, setCaseId] = useState(caseParam || "");
  const [input, setInput] = useState(caseParam || "");
  const [data, setData] = useState<EvidenceGraphData | null>(null);
  const [loading, setLoading] = useState(false);

  const loadGraph = async (id: string) => {
    if (!id) return;
    setLoading(true);
    try {
      const res = await api.get<EvidenceGraphData>(`/cases/${id}/graph`);
      setData(res);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (caseParam) loadGraph(caseParam);
  }, [caseParam]);

  const nodeTypes = {
    payment: {
      data: { label: (n: GraphNode) => <NodeCard n={n} /> },
    },
  };

  const getNodeColor = (type: string) => {
    const map: Record<string, string> = {
      payment: "#10b981",
      settlement: "#6366f1",
      bank_transaction: "#f59e0b",
      order: "#3b82f6",
      invoice: "#8b5cf6",
      fee: "#ef4444",
      tax: "#ef4444",
      refund: "#ec4899",
      chargeback: "#dc2626",
      adjustment: "#84cc16",
    };
    return map[type] || "#6b7280";
  };

  const nodes: Node[] = (data?.nodes ?? []).map((n, i) => ({
    id: n.id,
    position: { x: (i % 4) * 180, y: Math.floor(i / 4) * 140 },
    data: {
      label: (
        <div className="rounded-lg border bg-white p-3 shadow-sm" style={{ minWidth: 140 }}>
          <div className="flex items-center gap-1">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: getNodeColor(n.type) }}
            />
            <span className="text-xs font-bold uppercase text-gray-700">{n.type}</span>
            <Badge variant="secondary" className="text-[9px]">
              {n.source}
            </Badge>
          </div>
          <p className="mt-1 font-mono text-xs text-gray-500">{n.id}</p>
          <p className="mt-1 text-sm font-semibold">
            {((n.amount ?? 0) / 100).toLocaleString("en-IN", {
              style: "currency",
              currency: n.currency || "INR",
            })}
          </p>
          <p className="text-[10px] text-gray-400">{n.status}</p>
        </div>
      ),
    },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  }));

  const edges: Edge[] = (data?.edges ?? []).map((e, i) => ({
    id: `e-${i}`,
    source: e.source,
    target: e.target,
    label: e.edge_type,
    style: { stroke: "#94a3b8", strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed },
    labelStyle: { fill: "#64748b", fontSize: 10 },
  }));

  return (
    <DashboardLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Evidence Graph</h1>
        <p className="text-sm text-gray-500">Visualize record relationships and provenance chains</p>
      </div>

      <div className="mb-4 flex gap-2">
        <Input
          placeholder="Enter Case ID (e.g. CASE_pay_123)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="max-w-md"
        />
        <Button
          onClick={() => {
            setCaseId(input);
            loadGraph(input);
          }}
        >
          Load Graph
        </Button>
      </div>

      {caseId && (
        <p className="mb-2 text-sm text-gray-500">
          Showing evidence graph for <span className="font-mono">{caseId}</span>
        </p>
      )}

      {loading && <Skeleton className="h-[500px]" />}

      {!loading && data && (
        <Card>
          <CardContent className="p-4">
            <div style={{ height: 500 }}>
              <ReactFlow
                nodes={nodes}
                edges={edges}
                fitView
                attributionPosition="bottom-right"
              >
                <Background gap={16} />
                <Controls />
                <MiniMap />
              </ReactFlow>
            </div>
          </CardContent>
        </Card>
      )}

      {!loading && !data && (
        <Card>
          <CardContent className="p-8 text-center text-sm text-gray-400">
            Enter a case ID above to view its evidence graph.
          </CardContent>
        </Card>
      )}
    </DashboardLayout>
  );
}

function NodeCard({ n }: { n: GraphNode }) {
  return (
    <div>
      <p>{n.id}</p>
    </div>
  );
}

export default function EvidenceGraphPage() {
  return (
    <Suspense>
      <EvidenceGraphContent />
    </Suspense>
  );
}
