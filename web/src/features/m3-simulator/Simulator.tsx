import React, { useState } from 'react';
import { api } from '../../lib/api';
import type { SimulateResponse, ExplainResponse, SimulateRequest } from '../../lib/types';
import { ScoreBar } from '../../components/ui/ScoreBar';
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

  // Extract top SHAP driver if available
  const topShapFeature = explanation?.features?.[0];
  const topDriver = topShapFeature
    ? {
        label: topShapFeature.feature,
        direction: topShapFeature.contribution > 0 ? ('fraud' as const) : ('safe' as const),
      }
    : undefined;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between panel p-3.5">
        <div>
          <h2 className="text-sm font-mono font-bold text-text-primary tracking-tight">
            SIMULATION &amp; EXPLAINABILITY (XAI) STUDIO
          </h2>
          <p className="text-xs font-mono text-text-muted">
            Construct synthetic transaction parameters and inspect real-time SHAP feature attribution
          </p>
        </div>
      </div>

      {/* Preset Buttons */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-mono text-text-muted">Presets:</span>
        {presets.map((p) => {
          const Icon = p.icon;
          return (
            <button
              key={p.name}
              onClick={() => handleApplyPreset(p)}
              className="btn-interactive inline-flex items-center gap-1.5 px-2.5 py-1 bg-surface-1 hover:bg-surface-hover border border-border-subtle rounded-[6px] text-xs font-mono text-text-secondary hover:text-text-primary transition-colors"
            >
              <Icon className="w-3 h-3 text-text-muted" />
              <span>{p.name}</span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Form (5 Cols) */}
        <div className="lg:col-span-5 panel p-4 space-y-3">
          <h3 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary border-b border-border-subtle pb-2 flex items-center justify-between">
            <span>Transaction Parameters</span>
            <span className="text-[10px] font-mono text-text-muted">
              400 Auto-Imputed Feats
            </span>
          </h3>

          <div className="space-y-3 text-xs font-mono">
            <div>
              <label className="block text-text-secondary mb-1">Base Feature Profile</label>
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value as any)}
                className="w-full bg-surface-2 border border-border-subtle text-text-primary px-2.5 py-1 rounded-[6px] focus:outline-none"
              >
                <option value="typical">Typical Baseline (Median distribution)</option>
                <option value="nonfraud">Known Non-Fraud Benchmark</option>
                <option value="fraud">Known Fraud Pattern Benchmark</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-text-secondary mb-1">Amount ($)</label>
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-2.5 py-1 rounded-[6px] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-text-secondary mb-1">Card Network</label>
                <select
                  value={cardBrand}
                  onChange={(e) => setCardBrand(e.target.value)}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-2.5 py-1 rounded-[6px] focus:outline-none"
                >
                  <option value="visa">Visa (6200)</option>
                  <option value="mastercard">Mastercard (10200)</option>
                  <option value="discover">Discover (15000)</option>
                  <option value="amex">American Express (18500)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-text-secondary mb-1">Billing Distance (dist1)</label>
                <input
                  type="number"
                  value={billingDistance}
                  onChange={(e) => setBillingDistance(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-2.5 py-1 rounded-[6px] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-text-secondary mb-1">Matching Cards (C1)</label>
                <input
                  type="number"
                  value={cardMatchCount}
                  onChange={(e) => setCardMatchCount(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-2.5 py-1 rounded-[6px] focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-text-secondary mb-1">Hourly Velocity (C2)</label>
                <input
                  type="number"
                  value={purchaseFrequency}
                  onChange={(e) => setPurchaseFrequency(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-2.5 py-1 rounded-[6px] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-text-secondary mb-1">Days Inactive (D1)</label>
                <input
                  type="number"
                  value={daysSinceActivity}
                  onChange={(e) => setDaysSinceActivity(Number(e.target.value))}
                  className="w-full bg-surface-2 border border-border-subtle text-text-primary px-2.5 py-1 rounded-[6px] focus:outline-none"
                />
              </div>
            </div>

            <button
              onClick={handleRunSimulation}
              disabled={isLoading}
              className="btn-interactive w-full mt-2 py-2 bg-surface-2 hover:bg-surface-hover border border-border-subtle text-text-primary font-mono font-semibold rounded-[6px] flex items-center justify-center gap-2 cursor-pointer"
            >
              {isLoading ? (
                <span>Executing Model Inference...</span>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 text-text-secondary" />
                  <span>Run Inference &amp; Explain</span>
                </>
              )}
            </button>

            {error && <div className="text-status-block text-xs mt-2">{error}</div>}
          </div>
        </div>

        {/* Right Results & SHAP Inspector (7 Cols) */}
        <div className="lg:col-span-7 space-y-3">
          {result ? (
            <div className="panel p-4 space-y-4">
              {/* Top Decision Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle pb-3">
                <div>
                  <span className="text-[10px] font-mono text-text-muted">Transaction ID:</span>
                  <div className="font-mono font-bold text-text-primary text-xs">
                    #{result.transaction_id}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-text-secondary">Decision:</span>
                  <StatusBadge status={result.decision} size="md" />
                </div>
              </div>

              {/* ScoreBar Instrument Track */}
              <div className="p-3 bg-surface-2 rounded-[6px] border border-border-subtle space-y-2">
                <div className="flex justify-between text-[11px] font-mono text-text-secondary">
                  <span>Calculated Probability Track:</span>
                  <span className="text-text-muted">Latency: {String(result.feature_report?.latency_ms || 12.4)}ms</span>
                </div>
                <ScoreBar
                  probability={result.probability}
                  topDriver={topDriver}
                  showPercentage={true}
                />
              </div>

              {/* SHAP Waterfall Attribution */}
              {explanation && (
                <div className="pt-2 border-t border-border-subtle">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-primary flex items-center gap-1.5">
                      <Sparkles className="w-3 h-3 text-text-muted" />
                      <span>SHAP Feature Drivers (TreeExplainer)</span>
                    </h4>
                    <span className="text-[10px] font-mono text-text-muted">Top Contributing Values</span>
                  </div>
                  <ShapWaterfallChart features={explanation.features} height="240px" />
                </div>
              )}
            </div>
          ) : (
            <div className="panel p-10 text-center text-text-muted flex flex-col items-center justify-center">
              <Sparkles className="w-6 h-6 text-text-muted mb-2 opacity-40" />
              <h3 className="text-xs font-mono font-semibold text-text-primary mb-1">
                Awaiting Simulation Request
              </h3>
              <p className="text-[11px] max-w-sm font-mono text-text-muted">
                Select a preset on the left or customize parameters, then click &quot;Run Inference &amp; Explain&quot;.
              </p>
            </div>
          )}
        </div>
      </div>

      <InsightCallout title="Interpretability Note">
        SHAP isolations quantify exact feature pushes on the final probability score. Positive drivers increase fraud risk, while negative drivers reflect trust anchors.
      </InsightCallout>
    </div>
  );
};
