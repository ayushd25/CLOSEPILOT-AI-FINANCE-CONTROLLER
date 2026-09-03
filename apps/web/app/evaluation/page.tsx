"use client";

import { useState, useEffect } from "react";
import { DashboardLayout } from "@/components/layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { Play, FlaskConical } from "lucide-react";

interface Dataset {
  dataset_id: string;
  name: string;
  n_cases: number;
  n_records: number;
  seed: number;
  ground_truth_count?: number;
}

interface DatasetResponse {
  datasets: Dataset[];
}

interface EvalRun {
  run_id: string;
  dataset_name: string;
  n_cases: number;
  methods: Record<string, MethodMetrics>;
  created_at: string;
}

interface MethodMetrics {
  precision: number;
  recall: number;
  false_auto_match_rate: number;
  exception_rate: number;
  auto_resolution_rate: number;
  throughput_records_per_sec: number;
  latency_seconds: number;
  total_cases: number;
}

interface EvalRunsResponse {
  runs: EvalRun[];
}

interface BaselinesResponse {
  baselines: Array<{ name: string; description: string }>;
  scenario_catalog: string[];
}

export default function EvaluationLab() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [baselines, setBaselines] = useState<BaselinesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [nCases, setNCases] = useState(100);
  const [seed, setSeed] = useState(42);
  const [selectedDataset, setSelectedDataset] = useState("");
  const [generating, setGenerating] = useState(false);
  const [runningEval, setRunningEval] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [d, r, b] = await Promise.all([
        api.get<DatasetResponse>("/synthetic/datasets"),
        api.get<EvalRunsResponse>("/evaluation/runs"),
        api.get<BaselinesResponse>("/evaluation/baselines"),
      ]);
      setDatasets(d.datasets || []);
      setRuns(r.runs || []);
      setBaselines(b);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const generateData = async () => {
    setGenerating(true);
    try {
      const res = await api.post<any>("/synthetic/generate", {
        n_cases: nCases,
        seed: seed,
      });
      await load();
      if (res?.dataset_id) setSelectedDataset(res.dataset_id);
    } catch (e) {
      console.error(e);
    }
    setGenerating(false);
  };

  const runEval = async () => {
    setRunningEval(true);
    try {
      await api.post(`/evaluation/run?dataset_id=${encodeURIComponent(selectedDataset)}`);
      await load();
    } catch (e) {
      console.error(e);
    }
    setRunningEval(false);
  };

  const fmtPct = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <DashboardLayout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Evaluation Lab</h1>
        <p className="text-sm text-gray-500">Measure ClosePilot against hidden ground truth</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-indigo-500" />
              Generate Synthetic Dataset
            </CardTitle>
            <CardDescription>Create controlled test cases with hidden ground truth</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3">
              <div>
                <label className="text-xs text-gray-500">Case Count</label>
                <Input
                  type="number"
                  value={nCases}
                  onChange={(e) => setNCases(Number(e.target.value))}
                  min={1}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">Seed</label>
                <Input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(Number(e.target.value))}
                  className="mt-1"
                />
              </div>
              <div className="flex items-end">
                <Button onClick={generateData} disabled={generating}>
                  {generating ? "Generating..." : "Generate"}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Baselines</CardTitle>
            <CardDescription>Comparison methods</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {baselines?.baselines?.map((b) => (
                <div key={b.name} className="rounded border p-3">
                  <p className="text-sm font-semibold">{b.name}</p>
                  <p className="text-xs text-gray-500">{b.description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-4 w-4 text-emerald-600" />
              Run Benchmark
            </CardTitle>
            <CardDescription>
              Select a dataset and run all baseline methods
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4 flex items-center gap-3">
              <select
                className="rounded-md border px-3 py-2 text-sm"
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
              >
                <option value="">Select a dataset...</option>
                {datasets.map((d) => (
                  <option key={d.dataset_id} value={d.dataset_id}>
                    {d.name} ({d.n_cases} cases, seed {d.seed})
                  </option>
                ))}
              </select>
              <Button onClick={runEval} disabled={!selectedDataset || runningEval}>
                {runningEval ? "Running..." : "Run Benchmark"}
              </Button>
            </div>

            {loading ? (
              <Skeleton className="h-40" />
            ) : runs.length === 0 ? (
              <p className="text-sm text-gray-400">
                No evaluation runs yet. Generate data, then run a benchmark.
              </p>
            ) : (
              <div className="space-y-4">
                {runs.map((run) => (
                  <div key={run.run_id} className="rounded-lg border p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-semibold">{run.dataset_name}</p>
                        <p className="text-xs text-gray-500">{run.n_cases} cases · {run.methods?.closepilot?.total_cases ?? 0} compared</p>
                      </div>
                      <time className="text-xs text-gray-400">
                        {new Date(run.created_at).toLocaleString()}
                      </time>
                    </div>

                    <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
                      {Object.entries(run.methods || {}).map(([method, m]) => (
                        <div key={method} className="rounded-md border bg-gray-50 p-3">
                          <p className="text-xs font-bold uppercase text-gray-500">{method}</p>
                          <div className="mt-2 space-y-1 text-xs">
                            <div className="flex justify-between">
                              <span>Precision</span>
                              <span className="font-medium">{fmtPct(m.precision)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Recall</span>
                              <span className="font-medium">{fmtPct(m.recall)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>False Auto-Match</span>
                              <span className="font-medium text-red-600">{fmtPct(m.false_auto_match_rate)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Auto-Resolve</span>
                              <span className="font-medium">{fmtPct(m.auto_resolution_rate)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Exception</span>
                              <span className="font-medium">{fmtPct(m.exception_rate)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span>Throughput</span>
                              <span className="font-medium">{m.throughput_records_per_sec.toFixed(1)}/s</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
