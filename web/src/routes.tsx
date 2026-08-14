import React, { Suspense, lazy } from 'react';
import { createBrowserRouter } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { Skeleton } from './components/ui/States';

const LiveRadar = lazy(() =>
  import('./features/m1-live-radar/LiveRadar').then((m) => ({ default: m.LiveRadar }))
);
const ExecImpact = lazy(() =>
  import('./features/m2-exec-impact/ExecImpact').then((m) => ({ default: m.ExecImpact }))
);
const Simulator = lazy(() =>
  import('./features/m3-simulator/Simulator').then((m) => ({ default: m.Simulator }))
);
const ReviewQueue = lazy(() =>
  import('./features/m4-review-queue/ReviewQueue').then((m) => ({ default: m.ReviewQueue }))
);
const BatchScanner = lazy(() =>
  import('./features/m5-batch-scanner/BatchScanner').then((m) => ({ default: m.BatchScanner }))
);
const PolicyGraph = lazy(() =>
  import('./features/m6-policy-graph/PolicyGraph').then((m) => ({ default: m.PolicyGraph }))
);
const ForensicAudit = lazy(() =>
  import('./features/m7-forensic-audit/ForensicAudit').then((m) => ({ default: m.ForensicAudit }))
);
const ModelMlops = lazy(() =>
  import('./features/m8-model-mlops/ModelMlops').then((m) => ({ default: m.ModelMlops }))
);

const LoadingFallback = () => (
  <div className="p-6 space-y-4">
    <Skeleton className="h-8 w-48" />
    <div className="grid grid-cols-4 gap-4">
      <Skeleton className="h-28" />
      <Skeleton className="h-28" />
      <Skeleton className="h-28" />
      <Skeleton className="h-28" />
    </div>
    <Skeleton className="h-64" />
  </div>
);

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <LiveRadar />
          </Suspense>
        ),
      },
      {
        path: 'impact',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <ExecImpact />
          </Suspense>
        ),
      },
      {
        path: 'simulator',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <Simulator />
          </Suspense>
        ),
      },
      {
        path: 'review',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <ReviewQueue />
          </Suspense>
        ),
      },
      {
        path: 'batch',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <BatchScanner />
          </Suspense>
        ),
      },
      {
        path: 'policy',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <PolicyGraph />
          </Suspense>
        ),
      },
      {
        path: 'audit',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <ForensicAudit />
          </Suspense>
        ),
      },
      {
        path: 'model',
        element: (
          <Suspense fallback={<LoadingFallback />}>
            <ModelMlops />
          </Suspense>
        ),
      },
    ],
  },
]);
