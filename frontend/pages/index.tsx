import React, { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
} from 'recharts';
import {
  Brain,
  Shield,
  Lock,
  Key,
  Users,
  TrendingUp,
  Activity,
  Heart,
  Moon,
  Zap,
  BarChart2,
  AlertTriangle,
} from 'lucide-react';

// URL of the backend API. During local development the backend runs on
// http://localhost:8000. Adjust this constant if you deploy the API
// elsewhere or behind a proxy.
const API_BASE_URL =
  typeof window !== 'undefined'
    ? process.env.NEXT_PUBLIC_API_BASE_URL
    : undefined;

const DEMO_MODE = !API_BASE_URL;


// Define TypeScript interfaces matching the backend schemas
interface HealthRecord {
  id: number;
  user_id: string;
  date: string;
  sleep_hours?: number;
  resting_hr?: number;
  hrv?: number;
  steps?: number;
  calories?: number;
  weight?: number;
  energy?: number; // computed client side
  heartRate?: number; // computed client side
}

interface TrustEntry {
  metric: string;
  date: string;
  score: number;
  drivers: string[];
}

interface AnomalyDriver {
  metric: string;
  value: number;
  z_score: number;
  direction: string;
}

interface AnomalyResult {
  user_id: string;
  date: string;
  anomaly_score: number;
  is_anomaly: boolean;
  drivers: AnomalyDriver[];
  narrative: string;
}

interface CorrelationPair {
  metric_x: string;
  metric_y: string;
  correlation: number;
}

interface SimulationResult {
  user_id: string;
  mode: string;
  modified_records: HealthRecord[];
  detected_anomalies: AnomalyResult[];
}

// Generate synthetic health data for demonstration. The algorithm creates
// somewhat realistic patterns linking sleep, activity, nutrition and energy.
function generateHealthData(days: number = 30): HealthRecord[] {
  const data: HealthRecord[] = [];
  let baseEnergy = 70;
  for (let i = 0; i < days; i++) {
    const sleep = 5 + Math.random() * 3.5;
    const steps = 5000 + Math.random() * 10000;
    const carbs = 150 + Math.random() * 150;
    const protein = 60 + Math.random() * 80;
    const stress = Math.random() * 10;
    const waterIntake = 6 + Math.random() * 4;

    let energy = baseEnergy;
    energy += (sleep - 6.5) * 8;
    energy += (steps / 1000) * 0.5;
    energy -= (carbs - 200) * 0.1;
    energy += (protein - 100) * 0.15;
    energy -= stress * 2;
    energy += (waterIntake - 8) * 2;
    energy = Math.max(30, Math.min(100, energy + (Math.random() - 0.5) * 10));
    baseEnergy = energy * 0.3 + baseEnergy * 0.7;

    const heartRate = 60 + (100 - energy) * 0.3 + Math.random() * 5;

    data.push({
      id: 0,
      user_id: 'demo',
      date: new Date(new Date().setDate(new Date().getDate() - (days - i - 1)))
        .toISOString()
        .substring(0, 10),
      sleep_hours: parseFloat(sleep.toFixed(1)),
      steps: Math.round(steps),
      calories: Math.round(carbs + protein),
      resting_hr: undefined,
      hrv: undefined,
      weight: 70 + Math.random() * 5,
      energy: Math.round(energy),
      heartRate: Math.round(heartRate),
    });
  }
  return data;
}

function computeCorrelation(xs: number[], ys: number[]): number {
  if (xs.length !== ys.length || xs.length < 2) return 0;
  const n = xs.length;
  const meanX = xs.reduce((a, b) => a + b, 0) / n;
  const meanY = ys.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let denomX = 0;
  let denomY = 0;
  for (let i = 0; i < n; i++) {
    const dx = xs[i] - meanX;
    const dy = ys[i] - meanY;
    num += dx * dy;
    denomX += dx * dx;
    denomY += dy * dy;
  }
  const denom = Math.sqrt(denomX * denomY);
  if (!denom) return 0;
  return num / denom;
}

function buildDemoAnomalies(records: HealthRecord[]): AnomalyResult[] {
  return records
    .slice(-14)
    .map((rec) => {
      const energy = rec.energy ?? 0;
      const sleep = rec.sleep_hours ?? 0;
      const steps = rec.steps ?? 0;
      const riskScore = Math.min(1, Math.max(0.05, (100 - energy) / 100 + (sleep < 5 ? 0.2 : 0)));
      const isAnomaly = energy < 45 || sleep < 5 || steps < 4000;
      const drivers: AnomalyDriver[] = [];
      if (sleep < 5) drivers.push({ metric: 'sleep_hours', value: sleep, z_score: -2.1, direction: 'low' });
      if (energy < 45) drivers.push({ metric: 'energy', value: energy, z_score: -1.8, direction: 'low' });
      if (steps < 4000) drivers.push({ metric: 'steps', value: steps, z_score: -1.5, direction: 'low' });
      return {
        user_id: rec.user_id,
        date: rec.date,
        anomaly_score: parseFloat(riskScore.toFixed(2)),
        is_anomaly: isAnomaly,
        drivers,
        narrative: isAnomaly
          ? 'Multiple low-signal indicators detected. Recommend verification of sensor sync and recovery.'
          : 'Signals within expected ranges.',
      };
    });
}

function buildDemoCorrelations(records: HealthRecord[]): CorrelationPair[] {
  const sleep = records.map((r) => r.sleep_hours ?? 0);
  const energy = records.map((r) => r.energy ?? 0);
  const steps = records.map((r) => r.steps ?? 0);
  const calories = records.map((r) => r.calories ?? 0);
  const weight = records.map((r) => r.weight ?? 0);
  return [
    { metric_x: 'sleep_hours', metric_y: 'energy', correlation: computeCorrelation(sleep, energy) },
    { metric_x: 'steps', metric_y: 'energy', correlation: computeCorrelation(steps, energy) },
    { metric_x: 'calories', metric_y: 'weight', correlation: computeCorrelation(calories, weight) },
    { metric_x: 'sleep_hours', metric_y: 'steps', correlation: computeCorrelation(sleep, steps) },
  ];
}

function runDemoSimulation(records: HealthRecord[], mode: string): SimulationResult {
  const modified = records.map((rec, idx) => {
    if (idx % 5 !== 0) return rec;
    if (mode === 'missing') return { ...rec, sleep_hours: undefined, steps: undefined };
    if (mode === 'delay') return { ...rec, date: rec.date };
    if (mode === 'spoof') return { ...rec, steps: (rec.steps ?? 0) * 2, calories: (rec.calories ?? 0) * 1.5 };
    if (mode === 'noise') return { ...rec, energy: Math.max(20, Math.min(100, (rec.energy ?? 50) + (Math.random() - 0.5) * 40)) };
    return rec;
  });
  const detected = buildDemoAnomalies(modified).filter((res) => res.is_anomaly);
  return {
    user_id: records[0]?.user_id ?? 'demo',
    mode,
    modified_records: modified,
    detected_anomalies: detected,
  };
}

// Helper to POST multiple records to the backend
async function uploadRecords(records: HealthRecord[]): Promise<void> {
  for (const rec of records) {
    await fetch(`${API_BASE_URL}/records`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: rec.user_id,
        date: rec.date,
        sleep_hours: rec.sleep_hours,
        resting_hr: rec.resting_hr,
        hrv: rec.hrv,
        steps: rec.steps,
        calories: rec.calories,
        weight: rec.weight,
      }),
    });
  }
}

export default function Home() {
  const [userId, setUserId] = useState('demo');
  const [healthData, setHealthData] = useState<HealthRecord[]>([]);
  const [trustScores, setTrustScores] = useState<TrustEntry[]>([]);
  const [anomalyResults, setAnomalyResults] = useState<AnomalyResult[]>([]);
  const [correlations, setCorrelations] = useState<CorrelationPair[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'trust' | 'anomaly' | 'correlation' | 'simulation'>('overview');
  const [loading, setLoading] = useState<boolean>(true);
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [simMode, setSimMode] = useState<string>('missing');

  useEffect(() => {
    async function init() { 
      setLoading(true);
      let recs: HealthRecord[] = [];
      if (!DEMO_MODE) {
        try {
          const res = await fetch(`${API_BASE_URL}/records/${userId}`);
          if (res.ok) {
            recs = await res.json();
          }
        } catch (err) {
          console.error(err);
        }
      }
      if (!recs || recs.length === 0) {
        // No data; generate synthetic and upload
        const synthetic = generateHealthData(30);
        if (!DEMO_MODE) {
          await uploadRecords(synthetic);
        }
        recs = synthetic.map((r, idx) => ({ ...r, id: idx + 1 }));
      }
      setHealthData(recs);
      // Fetch analytics
      if (!DEMO_MODE) {
        try {
          const trustRes = await fetch(`${API_BASE_URL}/trust/${userId}`);
          if (trustRes.ok) {
            const trustJson = await trustRes.json();
            setTrustScores(trustJson.scores);
          }
        } catch (err) {
          console.error(err);
        }
        try {
          const anRes = await fetch(`${API_BASE_URL}/anomaly/${userId}`);
          if (anRes.ok) {
            const anJson = await anRes.json();
            setAnomalyResults(anJson.results);
          }
        } catch (err) {
          console.error(err);
        }
        try {
          const corrRes = await fetch(`${API_BASE_URL}/correlations/${userId}`);
          if (corrRes.ok) {
            const corrJson = await corrRes.json();
            setCorrelations(corrJson.correlations);
          }
        } catch (err) {
          console.error(err);
        }
      }
      setLoading(false);
    }
    init();
  }, [userId]);

  // Aggregate trust scores to compute average per metric
  const avgTrustPerMetric: { [metric: string]: number } = {};
  if (trustScores && trustScores.length > 0) {
    const grouped: { [metric: string]: number[] } = {};
    trustScores.forEach((t) => {
      if (!grouped[t.metric]) grouped[t.metric] = [];
      grouped[t.metric].push(t.score);
    });
    for (const m of Object.keys(grouped)) {
      avgTrustPerMetric[m] = grouped[m].reduce((a, b) => a + b, 0) / grouped[m].length;
    }
  }
  const demoTrustDefaults: { [metric: string]: number } = {
  sleep_hours: 0.82,
  resting_hr: 0.74,
  hrv: 0.68,
  steps: 0.61,
  calories: 0.47,
  weight: 0.91,
};

const trustDataForChart =
  Object.keys(avgTrustPerMetric).length > 0
    ? Object.keys(avgTrustPerMetric).map((m) => ({
        metric: m,
        score: avgTrustPerMetric[m],
      }))
    : Object.keys(demoTrustDefaults).map((m) => ({
        metric: m,
        score: demoTrustDefaults[m],
      }));


  // Prepare anomaly series for chart
  const demoAnomalies = anomalyResults.length > 0 ? anomalyResults : buildDemoAnomalies(healthData);
  const anomalySeries = demoAnomalies.map((r) => ({ date: r.date, score: r.anomaly_score }));

  // Prepare correlation matrix table rows
  const corrSource = correlations.length > 0 ? correlations : buildDemoCorrelations(healthData);
  const corrRows = corrSource.map((c) => ({
    pair: `${c.metric_x} / ${c.metric_y}`,
    value: c.correlation,
  }));

  // Simulation handler
  async function runSimulation() {
    if (DEMO_MODE) {
      setSimResult(runDemoSimulation(healthData, simMode));
      return;
    }
    setLoading(true);
    setSimResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, mode: simMode, fraction: 0.2 }),
      });
      if (res.ok) {
        const simJson = await res.json();
        setSimResult(simJson);
      }
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }

  // Determine today's record (the last record chronologically)
  const todayRec = healthData.length > 0 ? healthData[healthData.length - 1] : undefined;

  // Prepare radar chart data
  const radarData = todayRec
    ? [
        { metric: 'Sleep', current: ((todayRec.sleep_hours || 0) / 10) * 100, optimal: 70 },
        { metric: 'Energy', current: (todayRec.energy || 0), optimal: 80 },
        { metric: 'Activity', current: ((todayRec.steps || 0) / 15000) * 100, optimal: 60 },
        { metric: 'Calories', current: ((todayRec.calories || 0) / 300) * 100, optimal: 70 },
        { metric: 'Weight', current: ((todayRec.weight || 0) / 100) * 100, optimal: 60 },
      ]
    : [];

  return (
    <div className="min-h-screen px-10 py-6">
      <div className="w-full max-w-none">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="relative">
              <Brain className="w-10 h-10 text-accent" />
              <Shield className="w-5 h-5 text-success absolute -bottom-1 -right-1" />
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Physio Threat Intelligence
            </h1>
          </div>
          <p className="text-gray-400 text-lg">
            Zero‑Trust Health Data Pipeline • AI‑Driven Signal Integrity & Anomaly Detection
          </p>
          <div className="mt-3 flex gap-3 text-sm flex-wrap">
            <span className="bg-success/20 text-success px-3 py-1 rounded-full flex items-center gap-1">
              <Lock className="w-3 h-3" /> Signal Trust Scoring
            </span>
            <span className="bg-accent/20 text-accent px-3 py-1 rounded-full flex items-center gap-1">
              <Key className="w-3 h-3" /> Zero‑Knowledge Analytics
            </span>
            <span className="bg-warning/20 text-warning px-3 py-1 rounded-full flex items-center gap-1">
              <Users className="w-3 h-3" /> Federated Cohort Insights
            </span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 border-b border-gray-700 mb-6 overflow-x-auto">
          {(['overview', 'trust', 'anomaly', 'correlation', 'simulation'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 capitalize font-semibold whitespace-nowrap transition-colors ${
                activeTab === tab ? 'text-accent border-b-2 border-accent' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-10 text-gray-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
            <span className="ml-3">Loading analytics…</span>
          </div>
        )}

        {!loading && activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Area Chart */}
            <div className="bg-panel rounded-xl p-6 border border-gray-700">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-accent" />
                30‑Day Health Metrics
              </h3>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={healthData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" stroke="#94a3b8" tick={{ fontSize: 10 }} />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                    <Legend />
                    <Area type="monotone" dataKey="energy" stroke="#a855f7" fill="#a855f7" fillOpacity={0.3} name="Energy" />
                    <Area type="monotone" dataKey="sleep_hours" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} name="Sleep" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
            {/* Radar Chart */}
            <div className="bg-panel rounded-xl p-6 border border-gray-700">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-warning" />
                Today's Health Vector
              </h3>
              {radarData.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart outerRadius={100} data={radarData}>
                      <PolarGrid stroke="#475569" />
                      <PolarAngleAxis dataKey="metric" stroke="#94a3b8" />
                      <PolarRadiusAxis stroke="#94a3b8" />
                      <Radar name="Current" dataKey="current" stroke="#a855f7" fill="#a855f7" fillOpacity={0.6} />
                      <Radar name="Optimal" dataKey="optimal" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
                      <Legend />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-gray-400">No data available.</p>
              )}
            </div>
            {/* Metric Cards */}
            <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { icon: Moon, label: 'Sleep', value: todayRec?.sleep_hours ? `${todayRec.sleep_hours}h` : '-' },
                { icon: Zap, label: 'Energy', value: todayRec?.energy ? `${todayRec.energy}%` : '-' },
                { icon: Activity, label: 'Steps', value: todayRec?.steps ? todayRec.steps.toLocaleString() : '-' },
                { icon: Heart, label: 'Heart Rate', value: todayRec?.heartRate ? `${todayRec.heartRate} bpm` : '-' },
              ].map((metric, i) => (
                <div key={i} className="bg-panel rounded-xl p-4 border border-gray-700">
                  <div className="flex items-center gap-2 mb-1">
                    <metric.icon className="w-5 h-5 text-accent" />
                    <span className="text-gray-400 text-sm">{metric.label}</span>
                  </div>
                  <div className="text-2xl font-bold">{metric.value}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && activeTab === 'trust' && (
          <div className="bg-panel rounded-xl p-6 border border-gray-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Lock className="w-5 h-5 text-success" /> Signal Trust Scores
            </h3>
            {trustDataForChart.length > 0 ? (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trustDataForChart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="metric" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" domain={[0, 1]} />
                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                    <Legend />
                    <Bar dataKey="score" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-gray-400">Trust scores unavailable.</p>
            )}
            <p className="text-sm text-gray-500 mt-4">Higher scores indicate greater confidence in the authenticity and integrity of the corresponding signal. Scores factor in missingness, distribution shifts and cross‑signal coherence.</p>
          </div>
        )}

        {!loading && activeTab === 'anomaly' && (
          <div className="bg-panel rounded-xl p-6 border border-gray-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-danger" /> Anomaly Detection
            </h3>
            {anomalySeries.length > 0 ? (
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={anomalySeries}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                    <XAxis dataKey="date" stroke="#94a3b8" />
                    <YAxis stroke="#94a3b8" />
                    <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }} />
                    <Legend />
                    <Line type="monotone" dataKey="score" stroke="#ef4444" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-gray-400">No anomaly data available.</p>
            )}
            <div className="mt-4 space-y-2 max-h-60 overflow-y-auto pr-2">
              {demoAnomalies.map((res, idx) => (
                <div key={idx} className="border border-gray-700 rounded-lg p-3 hover:border-danger transition-colors">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-accent">{res.date}</span>
                    {res.is_anomaly ? (
                      <span className="px-2 py-1 text-xs rounded-full bg-danger/20 text-danger">Anomaly</span>
                    ) : (
                      <span className="px-2 py-1 text-xs rounded-full bg-success/20 text-success">Normal</span>
                    )}
                  </div>
                  <p className="text-gray-400 text-sm mt-1">{res.narrative}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && activeTab === 'correlation' && (
          <div className="bg-panel rounded-xl p-6 border border-gray-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-warning" /> Cross‑Signal Correlations
            </h3>
            {corrRows.length > 0 ? (
              <div className="overflow-auto max-h-80">
                <table className="min-w-full text-sm text-left text-gray-400">
                  <thead className="text-xs uppercase text-gray-500 border-b border-gray-700">
                    <tr>
                      <th scope="col" className="py-2 px-4">Metric Pair</th>
                      <th scope="col" className="py-2 px-4">Correlation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {corrRows.map((row, idx) => (
                      <tr key={idx} className="border-b border-gray-700 hover:bg-gray-800/40">
                        <td className="py-2 px-4 whitespace-nowrap">{row.pair}</td>
                        <td className="py-2 px-4 whitespace-nowrap">{row.value.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-400">Correlation data unavailable.</p>
            )}
            <p className="text-sm text-gray-500 mt-4">Values close to ±1 indicate strong linear relationships. Discrepancies may signal data drift or sensor misalignment.</p>
          </div>
        )}

        {!loading && activeTab === 'simulation' && (
          <div className="bg-panel rounded-xl p-6 border border-gray-700">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-accent" /> Adversarial Simulation
            </h3>
            <div className="flex items-center gap-4 mb-4 flex-wrap">
              {['missing', 'delay', 'spoof', 'noise'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setSimMode(mode)}
                  className={`px-4 py-2 rounded-md border ${
                    simMode === mode ? 'bg-accent/30 border-accent text-accent' : 'border-gray-600 text-gray-300 hover:bg-gray-700'
                  }`}
                >
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </button>
              ))}
              <button
                onClick={runSimulation}
                className="px-4 py-2 rounded-md bg-accent/20 text-accent border border-accent hover:bg-accent/30"
              >
                Run Simulation
              </button>
            </div>
            {simResult ? (
              <div>
                <p className="text-gray-400 mb-2">
                  Simulation applied: <span className="font-mono text-accent">{simResult.mode}</span> on {simResult.modified_records.length} records
                </p>
                <div className="max-h-60 overflow-y-auto space-y-2 pr-2">
                  {simResult.detected_anomalies.map((res, idx) => (
                    <div key={idx} className="border border-gray-700 rounded-lg p-3 hover:border-warning transition-colors">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-accent">{res.date}</span>
                        {res.is_anomaly ? (
                          <span className="px-2 py-1 text-xs rounded-full bg-danger/20 text-danger">Anomaly</span>
                        ) : (
                          <span className="px-2 py-1 text-xs rounded-full bg-success/20 text-success">Normal</span>
                        )}
                      </div>
                      <p className="text-gray-400 text-sm mt-1">{res.narrative}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-gray-400">Choose a mode and run the simulation to test resilience against data tampering.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
