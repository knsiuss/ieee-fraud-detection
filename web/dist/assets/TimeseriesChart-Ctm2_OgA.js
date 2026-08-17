import{j as h}from"./tanstack-B56LYOVM.js";import{E as S}from"./EChartBase-PzHcDj8Y.js";import{u as v}from"./index-B5oy2iUq.js";const A=({data:o,height:y="300px",showAmount:s=!1})=>{const l=v(e=>e.theme)==="dark",d=o.map(e=>{try{return new Date(e.timestamp).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})}catch{return e.timestamp}}),c=o.map(e=>e.total),b=o.map(e=>e.approved),u=o.map(e=>e.reviewed),p=o.map(e=>e.declined),f=o.map(e=>e.amount_sum),a=l?"#4F7A5C":"#3B5A44",r=l?"#B8863A":"#A87B34",n=l?"#B23B2E":"#A83A2E",t=l?"#A8A49A":"#6E6A62",x={animationDuration:300,tooltip:{trigger:"axis",axisPointer:{type:"line",lineStyle:{color:l?"rgba(230, 227, 218, 0.2)":"rgba(110, 106, 98, 0.3)",width:1,type:"dashed"}},formatter:e=>{if(!e||!e.length)return"";const m=e[0].dataIndex,i=o[m];return`<div class="font-mono text-xs space-y-1">
          <div class="font-bold border-b border-border-subtle pb-1 mb-1 flex items-center justify-between gap-4">
            <span>${d[m]} (Window)</span>
            <span>${i.total} tx</span>
          </div>
          <div class="flex justify-between gap-6" style="color: ${a}">
            <span>Auto-Approved:</span>
            <b>${i.approved}</b>
          </div>
          <div class="flex justify-between gap-6" style="color: ${r}">
            <span>Review Queue:</span>
            <b>${i.reviewed}</b>
          </div>
          <div class="flex justify-between gap-6" style="color: ${n}">
            <span>Declined:</span>
            <b>${i.declined}</b>
          </div>
          <div class="flex justify-between gap-6 pt-1 border-t border-border-subtle">
            <span>Evaluated GMV:</span>
            <b>$${i.amount_sum.toLocaleString()}</b>
          </div>
        </div>`}},legend:{data:s?["Transaction Volume","Evaluated GMV ($)","Declined (Fraud)"]:["Total Volume","Approved","Review","Declined"],textStyle:{color:t,fontSize:11,fontFamily:"IBM Plex Mono, JetBrains Mono"},top:0,right:10,icon:"roundRect",itemWidth:10,itemHeight:3,itemGap:14},grid:{left:"3%",right:"4%",bottom:"4%",top:"16%",containLabel:!0},xAxis:{type:"category",boundaryGap:!1,data:d,axisLabel:{color:t,fontSize:10,fontFamily:"IBM Plex Mono, JetBrains Mono"},axisLine:{lineStyle:{color:l?"rgba(230, 227, 218, 0.10)":"#DCD8CE"}},axisTick:{show:!1}},yAxis:[{type:"value",name:"Volume (tx)",nameTextStyle:{color:t,fontSize:10,fontFamily:"IBM Plex Mono, JetBrains Mono"},axisLabel:{color:t,fontSize:10,fontFamily:"IBM Plex Mono, JetBrains Mono"},splitLine:{lineStyle:{color:l?"rgba(230, 227, 218, 0.05)":"rgba(110, 106, 98, 0.08)",type:"dashed"}}},...s?[{type:"value",name:"GMV ($)",nameTextStyle:{color:t,fontSize:10,fontFamily:"IBM Plex Mono, JetBrains Mono"},axisLabel:{color:t,fontSize:10,fontFamily:"IBM Plex Mono, JetBrains Mono",formatter:"${value}"},splitLine:{show:!1}}]:[]],series:s?[{name:"Transaction Volume",type:"line",smooth:.2,showSymbol:!1,data:c,itemStyle:{color:t},lineStyle:{width:1.5,color:t}},{name:"Evaluated GMV ($)",type:"line",yAxisIndex:1,smooth:.2,showSymbol:!1,data:f,itemStyle:{color:a},lineStyle:{width:1.5,color:a}},{name:"Declined (Fraud)",type:"bar",data:p,itemStyle:{color:n,borderRadius:[2,2,0,0]},barWidth:"30%"}]:[{name:"Total Volume",type:"line",smooth:.2,showSymbol:!1,data:c,itemStyle:{color:t},lineStyle:{width:1.5,color:t}},{name:"Approved",type:"line",smooth:.2,showSymbol:!1,data:b,itemStyle:{color:a},lineStyle:{width:1.5,color:a}},{name:"Review",type:"line",smooth:.2,showSymbol:!1,data:u,itemStyle:{color:r},lineStyle:{width:1.5,color:r}},{name:"Declined",type:"line",smooth:.2,showSymbol:!1,data:p,itemStyle:{color:n},lineStyle:{width:1.5,color:n}}]};return h.jsx(S,{option:x,height:y})};export{A as T};
