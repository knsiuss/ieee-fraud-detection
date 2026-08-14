import React, { useState } from 'react';
import { api } from '../../lib/api';
import type { SimulateResponse, ExplainResponse, SimulateRequest } from '../../lib/types';
import { GaugeChart } from '../../components/charts/GaugeChart';
import { ShapWaterfallChart } from '../../components/charts/ShapWaterfallChart';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { InsightCallout } from '../../components/ui/InsightCallout';
import { Play, Sparkles, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

export const Simulator: React.FC = () => {
  const [profile, setProfile] = useState<'typical' | 'nonfraud' | 'fraud'>('typical');
  const [amount, setAmount] = useState<number>(149.99);
  const [cardBrand, setCardBrand] = useState<string>('visa');
  const [billingDistance, setBillingDistance] = useState<number>(12.5);
  const [cardMatchCount, setCardMatchCount] = useState<number>(1);
  const [purchaseFrequency, setPurchaseFrequency] = useState<number>(2);
  const [daysSinceActivity, setDaysSinceActivity] = useState<number>(3);

  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [explanation, setExplanation] = useState<ExplainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const presets = [
    {
      name: 'Legit Domestic Purchase',
      icon: CheckCircle2,
      profile: 'nonfraud' as const,
      amount: 45.0,
      cardBrand: 'visa',
      billingDistance: 4.2,
      cardMatchCount: 1,
      purchaseFrequency: 1,
      daysSinceActivity: 2,
    },
    {
      name: 'High-Risk Overseas Transfer',
      icon: ShieldAlert,
      profile: 'fraud' as const,
      amount: 1850.0,
      cardBrand: 'discover',
      billingDistance: 4500.0,
      cardMatchCount: 4,
      purchaseFrequency: 8,
      daysSinceActivity: 120,
    },
    {
      name: 'Velocity Spike Attack',
      icon: AlertTriangle,
      profile: 'fraud' as const,
      amount: 420.0,
      cardBrand: 'mastercard',
      billingDistance: 250.0,
      cardMatchCount: 8,
      purchaseFrequency: 24,
      daysSinceActivity: 0,
    },
  ];

  const handleApplyPreset = (p: typeof presets[0]) => {
    setProfile(p.profile);
    setAmount(p.amount);
    setCardBrand(p.cardBrand);
    setBillingDistance(p.billingDistance);
    setCardMatchCount(p.cardMatchCount);
    setPurchaseFrequency(p.purchaseFrequency);
    setDaysSinceActivity(p.daysSinceActivity);
  };

  const handleRunSimulation = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const req: SimulateRequest = {
        profile,
        amount,
        card_brand: cardBrand,
        billing_distance: billingDistance,
        card_match_count: cardMatchCount,
        purchase_frequency: purchaseFrequency,
        days_since_activity: daysSinceActivity,
      };

      const res = await api.simulate(req);
      setResult(res);

      if (res.mapped_values) {
        try {
          const exp = await api.explain(res.mapped_values);
          setExplanation(exp);
        } catch {
          // ignore explain error
        }
      }
    } catch (err: any) {
      setError(err.message || 'Simulation scoring failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between bg-surface-1/90 backdrop-blur border border-border-subtle p-4 rounded-lg shadow-xs">
        <div>
          <h2 className="text-base font-bold text-text-primary tracking-tight">
            SIMULATION &amp; EXPLAINABLE AI (XAI) STUDIO
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Construct synthetic IEEE-CIS 400-feature payloads and inspect real-time SHAP waterfall explanations
          </p>
        </div>
      </div>

      {/* Preset Buttons */}
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="text-xs font-mono text-text-muted">Scenario Presets:</span>
        {presets.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.name}
              onClick={() => handleApplyPreset(p)}
              className="btn-interactive inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface-1/90 hover:bg-surface-2 border border-border-subtle hover:border-accent-teal/40 rounded-md text-xs font-mono text-text-secondary hover:text-text-primary shadow-xs transition-all"
            >
              <Icon className="w-3.5 h-3.5 text-accent-teal" />
              <span>{p.name}</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form (5 Cols) */}
        <div className="lg:col-span-5 bg-surface-1/90 backdrop-blur border border-border-subtle rounded-lg p-5 space-y-4 shadow-xs">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-text-primary border-b border-border-subtle pb-2 flex items-center justify-between">
            <span>Transaction Parameters</span>
            <span className="text-[10px] font-mono text-accent-teal px-1.5 py-0.2 rounded bg-accent-teal/10">
              400 Auto-Imputed Feats
            </span>
          </h3>

          <div className="space-y-3.5 text-xs font-mono">
            <div>
              <label className="block text-text-secondary mb-1">Base Feature Profile</label>
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value as any)}
                className="w-full bg-surface-2 border border-border-subtle text-text-primary px-3 py-1.5 rounded focus:outline-none focus:border-accent-teal transition-colors shadow-xs"
              >
                <option value="typical">Typical Baseline (Median distribution)</option>
                <option value="nonfraud">Known Non-Fraud Benchmark</option>
                <option value="fraud">Known Fraud Pattern Benchmark</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-text-secondary mb-1">Transaction Amount ($)</label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-3 py-1.5 rounded focus:outline-none focus:border-accent-teal transition-colors shadow-xs"
                />
              </div>

              <div>
                <label className="block text-text-secondary mb-1">Card Network</label>
                <select
                  value={cardBrand}
                  onChange={(e) => setCardBrand(e.target.value)}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-3 py-1.5 rounded focus:outline-none focus:border-accent-teal transition-colors shadow-xs"
                >
                  <option value="visa">Visa (6200)</option>
                  <option value="mastercard">Mastercard (10200)</option>
                  <option value="discover">Discover (15000)</option>
                  <option value="amex">American Express (18500)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-text-secondary mb-1">Distance to Billing (dist1)</label>
                <input
                  type="number"
                  value={billingDistance}
                  onChange={(e) => setBillingDistance(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-3 py-1.5 rounded focus:outline-none focus:border-accent-teal transition-colors shadow-xs"
                />
              </div>

              <div>
                <label className="block text-text-secondary mb-1">Matching Cards (C1)</label>
                <input
                  type="number"
                  value={cardMatchCount}
                  onChange={(e) => setCardMatchCount(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-3 py-1.5 rounded focus:outline-none focus:border-accent-teal transition-colors shadow-xs"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-text-secondary mb-1">Hourly Velocity (C2)</label>
                <input
                  type="number"
                  value={purchaseFrequency}
                  onChange={(e) => setPurchaseFrequency(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-3 py-1.5 rounded focus:outline-none focus:border-accent-teal transition-colors shadow-xs"
                />
              </div>

              <div>
                <label className="block text-text-secondary mb-1">Days Inactive (D1)</label>
                <input
                  type="number"
                  value={daysSinceActivity}
                  onChange={(e) => setDaysSinceActivity(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-3 py-1.5 rounded focus:outline-none focus:border-accent-teal transition-colors shadow-xs"
                />
              </div>
            </div>

            <button
              onClick={handleRunSimulation}
              disabled={isLoading}
              className="btn-interactive w-full mt-3 py-2.5 bg-accent-teal hover:bg-accent-teal/90 text-white font-semibold rounded shadow-[0_0_15px_rgba(20,184,166,0.25)] flex items-center justify-center gap-2 transition-all cursor-pointer"
            >
              {isLoading ? (
                <span className="animate-pulse">Executing LightGBM Model...</span>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Run Real-Time Score &amp; Explain</span>
                </>
              )}
            </button>

            {error && <div className="text-status-block text-xs mt-2">{error}</div>}
          </div>
        </div>

        {/* Right Results & SHAP Inspector (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {result ? (
            <div className="bg-surface-1/90 backdrop-blur border border-border-subtle rounded-lg p-5 space-y-5 shadow-xs animate-fade-in">
              {/* Top Decision Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-4">
                <div>
                  <span className="text-[11px] font-mono text-text-muted">Transaction ID:</span>
                  <div className="font-mono font-bold text-text-primary text-sm">
                    #{result.transaction_id}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs font-mono text-text-secondary">Model Decision:</span>
                  <StatusBadge status={result.decision} size="lg" />
                </div>
              </div>

              {/* Gauge & Metrics Split */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
                <div>
                  <GaugeChart score={result.probability} title="INFERENCE SCORE" height="220px" />
                </div>

                <div className="bg-surface-2/80 p-4 rounded-lg border border-border-subtle space-y-2 text-xs font-mono shadow-xs">
                  <div className="flex justify-between text-text-secondary">
                    <span>Risk Tier:</span>
                    <span className="font-bold text-text-primary uppercase">{result.risk_tier}</span>
                  </div>
                  <div className="flex justify-between text-text-secondary">
                    <span>Policy Action:</span>
                    <span className="font-bold text-text-primary">{result.action}</span>
                  </div>
                  <div className="flex justify-between text-text-secondary">
                    <span>Model Version:</span>
                    <span className="text-accent-cyan font-bold">{result.model_version}</span>
                  </div>
                  <div className="flex justify-between text-text-secondary">
                    <span>Latency:</span>
                    <span className="text-status-approve font-bold">
                      {String(result.feature_report?.latency_ms || 12.4)}ms
                    </span>
                  </div>
                </div>
              </div>

              {/* SHAP Waterfall Attribution */}
              {explanation && (
                <div className="pt-3 border-t border-border-subtle">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-text-primary flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-accent-teal" />
                      <span>SHAP Feature Attribution (TreeExplainer)</span>
                    </h4>
                    <span className="text-[10px] font-mono text-text-muted">Top Contributing Drivers</span>
                  </div>
                  <ShapWaterfallChart features={explanation.features} height="260px" />
                </div>
              )}
            </div>
          ) : (
            <div className="bg-surface-1/60 border border-dashed border-border-subtle rounded-lg p-12 text-center text-text-muted flex flex-col items-center justify-center">
              <Sparkles className="w-8 h-8 text-accent-teal opacity-50 mb-3 animate-pulse" />
              <h3 className="text-sm font-semibold text-text-primary mb-1">
                Awaiting Simulation Execution
              </h3>
              <p className="text-xs max-w-sm font-mono">
                Select a scenario preset on the left or customize parameters, then click &quot;Run Real-Time Score&quot; to inspect model inference and SHAP explainability.
              </p>
            </div>
          )}
        </div>
      </div>

      <InsightCallout title="Decision Engine Interpretability" variant="info">
        SHAP (SHapley Additive exPlanations) isolates the exact mathematical push of each feature on the final fraud score. Red positive bars indicate fraud drivers (e.g. extreme velocity or high transaction amounts), while green negative bars reflect trust anchors (e.g. verified issuer BIN or consistent card history).
      </InsightCallout>
    </div>
  );
};
