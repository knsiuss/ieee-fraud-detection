import{a as g,h as b,j as e,i as x,k as f,l as w}from"./tanstack-B56LYOVM.js";import{c as l}from"./index-B5oy2iUq.js";/**
 * @license lucide-react v0.475.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const v=[["path",{d:"m6 9 6 6 6-6",key:"qrunsl"}]],j=l("ChevronDown",v);/**
 * @license lucide-react v0.475.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const N=[["path",{d:"m18 15-6-6-6 6",key:"153udz"}]],y=l("ChevronUp",N);/**
 * @license lucide-react v0.475.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const C=[["path",{d:"m7 15 5 5 5-5",key:"1hf1tw"}],["path",{d:"m7 9 5-5 5 5",key:"sgt6xg"}]],S=l("ChevronsUpDown",C);function M({columns:c,data:p,onRowClick:n,selectedRowId:d,idAccessor:i,emptyMessage:m="No records in ledger."}){const[h,u]=g.useState([]),a=b({data:p,columns:c,state:{sorting:h},onSortingChange:u,getCoreRowModel:w(),getSortedRowModel:f()});return e.jsx("div",{className:"w-full overflow-hidden panel rounded-2xl border border-border-subtle shadow-soft",children:e.jsx("div",{className:"overflow-x-auto max-h-[560px]",children:e.jsxs("table",{className:"w-full text-left text-xs border-collapse",children:[e.jsx("thead",{className:"bg-surface-2/60 backdrop-blur-md sticky top-0 z-10 border-b border-border-subtle text-text-secondary uppercase tracking-wider font-sans font-semibold text-[11px]",children:a.getHeaderGroups().map(o=>e.jsx("tr",{children:o.headers.map(t=>{const r=t.column.getCanSort(),s=t.column.getIsSorted();return e.jsx("th",{className:`px-4 py-3 select-none ${r?"cursor-pointer hover:text-text-primary transition-colors":""}`,onClick:t.column.getToggleSortingHandler(),children:e.jsxs("div",{className:"flex items-center gap-1.5",children:[x(t.column.columnDef.header,t.getContext()),r&&e.jsx("span",{className:"text-text-muted",children:s==="asc"?e.jsx(y,{className:"w-3.5 h-3.5 text-apple-blue"}):s==="desc"?e.jsx(j,{className:"w-3.5 h-3.5 text-apple-blue"}):e.jsx(S,{className:"w-3 h-3 opacity-30"})})]})},t.id)})},o.id))}),e.jsx("tbody",{className:"divide-y divide-border-subtle/30 font-mono text-xs",children:a.getRowModel().rows.length===0?e.jsx("tr",{children:e.jsx("td",{colSpan:c.length,className:"px-4 py-12 text-center text-text-muted font-sans text-xs",children:m})}):a.getRowModel().rows.map(o=>{const t=i?i(o.original):void 0,r=d&&t===d;return e.jsx("tr",{onClick:()=>n&&n(o.original),className:`transition-all duration-150 ${n?"cursor-pointer":""} ${r?"bg-surface-hover/90 text-text-primary font-semibold shadow-inner":"hover:bg-surface-hover/50 text-text-secondary hover:text-text-primary"}`,children:o.getVisibleCells().map(s=>e.jsx("td",{className:"px-4 py-2.5 whitespace-nowrap",children:x(s.column.columnDef.cell,s.getContext())},s.id))},o.id)})})]})})})}export{M as D};
