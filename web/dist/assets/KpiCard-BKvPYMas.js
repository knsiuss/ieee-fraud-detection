import{j as s}from"./tanstack-B56LYOVM.js";import{c as t}from"./index-fSIoOtda.js";/**
 * @license lucide-react v0.475.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const i=[["path",{d:"M5 12h14",key:"1ays0h"}]],r=t("Minus",i);/**
 * @license lucide-react v0.475.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const c=[["polyline",{points:"22 17 13.5 8.5 8.5 13.5 2 7",key:"1r2t7k"}],["polyline",{points:"16 17 22 17 22 11",key:"11uiuu"}]],p=t("TrendingDown",c);/**
 * @license lucide-react v0.475.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const d=[["polyline",{points:"22 7 13.5 15.5 8.5 10.5 2 17",key:"126l90"}],["polyline",{points:"16 7 22 7 22 13",key:"kwv8wd"}]],x=t("TrendingUp",d),b=({title:a,value:l,subtitle:o,trend:e,icon:n})=>s.jsxs("div",{className:"panel panel-hover p-5 flex flex-col justify-between rounded-2xl relative overflow-hidden group",children:[s.jsx("div",{className:"absolute top-0 right-0 w-24 h-24 bg-apple-blue/5 rounded-full blur-2xl pointer-events-none group-hover:bg-apple-blue/10 transition-all duration-300"}),s.jsxs("div",{className:"flex items-center justify-between gap-2",children:[s.jsx("span",{className:"text-xs font-semibold uppercase tracking-wider text-text-secondary font-sans",children:a}),n&&s.jsx("span",{className:"w-8 h-8 rounded-2xl bg-surface-2/80 flex items-center justify-center text-text-secondary shrink-0 border border-border-subtle shadow-sm group-hover:scale-105 transition-transform",children:n})]}),s.jsxs("div",{className:"mt-3.5 flex items-baseline justify-between gap-2",children:[s.jsx("span",{className:"text-3xl font-bold font-mono tracking-tight text-text-primary tabular-nums leading-none",children:l}),e&&s.jsxs("div",{className:`inline-flex items-center gap-1 text-[11px] font-sans font-semibold px-2.5 py-1 rounded-full border shadow-xs ${e.direction==="up"?"text-status-approve bg-status-approve/10 border-status-approve/25":e.direction==="down"?"text-status-block bg-status-block/10 border-status-block/25":"text-text-muted bg-surface-2 border-border-subtle"}`,children:[e.direction==="up"&&s.jsx(x,{className:"w-3 h-3"}),e.direction==="down"&&s.jsx(p,{className:"w-3 h-3"}),e.direction==="neutral"&&s.jsx(r,{className:"w-3 h-3"}),s.jsx("span",{children:e.value})]})]}),(o||(e==null?void 0:e.label))&&s.jsx("div",{className:"mt-2 text-xs font-normal text-text-muted truncate font-sans",children:o||(e==null?void 0:e.label)})]});export{b as K};
