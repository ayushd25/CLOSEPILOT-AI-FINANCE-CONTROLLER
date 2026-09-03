"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { api } from "@/lib/api";
import { Database, RefreshCw } from "lucide-react";

interface Dataset {
  dataset_id: string;
  name?: string;
  n_cases?: number;
  seed?: number;
  created_at?: string;
  n_records?: number;
  ground_truth_count?: number;
}

interface GenerateResponse {
  dataset_id?: string;
  n_cases?: number;
  n_records?: number;
  ground_truth_count?: number;
  inserted_records?: number;
  inserted_ground_truths?: number;
}

export default function DataSources() {
  const [nCases, setNCases] = useState(100);
  const [seed, setSeed] = useState(42);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [lastGenerate, setLastGenerate] = useState<GenerateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDatasets = async () => {
    setLoading(true);
    try {
      const res = await api.get<{ datasets: Dataset[] }>("/synthetic/datasets");
      setDatasets(res.datasets || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const generate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await api.post<GenerateResponse>("/synthetic/generate", {
        n_cases: nCases,
        seed,
      });
      setLastGenerate(res);
      await loadDatasets();
    } catch (e) {
      console.error(e);
      setError("Failed to generate synthetic data.");
    }
    setGenerating(false);
  };

  return (
    <DashboardLayout>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Database className="h-5 w-5 text-gray-500" />
            Data Sources
          </h1>
          <p className="text-sm text-gray-500">Synthetic data generation for reconciliation benchmarking</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadDatasets}>
          <RefreshCw className="mr-1 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Generate Synthetic Data</CardTitle>
            <CardDescription>
              Creates payments, settlements, and bank transactions across 20 reconciliation scenarios with hidden ground truth.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700" htmlFor="n-cases">
                  Number of cases
                </label>
                <input
                  id="n-cases"
                  type="number"
                  min={1}
                  max={1000}
                  value={nCases}
                  onChange={(e) => setNCases(Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700" htmlFor="seed">
                  Random seed
                </label>
                <input
                  id="seed"
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(Number(e.target.value))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <Button variant="outline" size="sm" onClick={generate} disabled={generating} className="w-full">
                {generating ? "Generating..." : "Generate"}
              </Button>

              {error && <p className="text-xs text-red-500">{error}</p>}

              {lastGenerate && (
                <div className="mt-4 rounded-md border p-3 text-sm">
                  <p className="font-semibold text-gray-800">Generation complete</p>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-500">
                    <span>Cases: {lastGenerate.n_cases ?? 0}</span>
                    <span>Records: {lastGenerate.n_records ?? 0}</span>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Generated Datasets</CardTitle>
            <CardDescription>Previously generated synthetic datasets</CardDescription>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-sm text-gray-400">Loading...</p>}
            {!loading && datasets.length === 0 && (
              <p className="text-sm text-gray-400">No datasets yet. Generate one to begin.</p>
            )}
            <div className="space-y-2">
              {datasets.slice(0, 8).map((d) => (
                <div key={d.dataset_id} className="rounded-md border p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-800">{d.name || d.dataset_id}</span>
                    <span className="text-xs text-gray-400">
                      {d.created_at ? new Date(d.created_at).toLocaleString() : ""}
                    </span>
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-center text-xs">
                    <div>
                      <p className="font-semibold">{d.n_cases ?? 0}</p>
                      <p className="text-gray-400">Cases</p>
                    </div>
                    <div>
                      <p className="font-semibold">{d.n_records ?? 0}</p>
                      <p className="text-gray-400">Records</p>
                    </div>
                    <div>
                      <p className="font-semibold">{d.ground_truth_count ?? 0}</p>
                      <p className="text-gray-400">Truth</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}