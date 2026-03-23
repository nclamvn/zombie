import { useState, useEffect, useRef, useCallback, useMemo } from "react";

/* ═══════════════════════════════════════════════════════════════
   RTR SIMULATOR — VOC COMMAND CENTER v2
   Light/Dark theme + Vietnamese/English toggle (default: VI + Light)
   ═══════════════════════════════════════════════════════════════ */

const THEMES = {
  dark: {
    bg:"#010409", bgPanel:"#0d1117", bgCard:"#161b22",
    border:"#30363d", borderActive:"#484f58",
    amber:"#f0883e", amberDim:"rgba(240,136,62,.12)",
    green:"#3fb950", greenDim:"rgba(63,185,80,.1)",
    red:"#ff7b72", redDim:"rgba(255,123,114,.1)",
    blue:"#58a6ff", blueDim:"rgba(88,166,255,.1)",
    cyan:"#39d2f5", cyanDim:"rgba(57,210,245,.08)",
    purple:"#bc8cff",
    text:"#f0f6fc", dim:"#8b949e", mid:"#d2d8de",
    gridOpacity:.3, pitchFill:"rgba(63,185,80,.08)",
  },
  light: {
    bg:"#f0f2f5", bgPanel:"#ffffff", bgCard:"#f7f8fa",
    border:"#d0d7de", borderActive:"#afb8c1",
    amber:"#bf6a02", amberDim:"rgba(191,106,2,.06)",
    green:"#1a7f37", greenDim:"rgba(26,127,55,.06)",
    red:"#cf222e", redDim:"rgba(207,34,46,.06)",
    blue:"#0969da", blueDim:"rgba(9,105,218,.06)",
    cyan:"#0a7a85", cyanDim:"rgba(10,122,133,.05)",
    purple:"#8250df",
    text:"#1f2328", dim:"#656d76", mid:"#424a53",
    gridOpacity:.12, pitchFill:"rgba(26,127,55,.06)",
  }
};

const PHASE_KEYS = ["detect","verify","decide","respond","resolve"];
const phaseColor = (p, T) => ({detect:T.amber,verify:T.blue,decide:T.cyan,respond:T.green,resolve:T.purple}[p]||T.dim);

const LANG = {
  vi: {
    title:"TRUNG TÂM CHỈ HUY VOC",
    live:"● TRỰC TIẾP", standby:"○ CHỜ LỆNH", auto:"● TỰ ĐỘNG",
    autoBtn:"▶▶ TỰ ĐỘNG 3 TÌNH HUỐNG", stopBtn:"■ DỪNG", runBtn:"▶ CHẠY",
    scenario:"Tình huống", category:"Phân loại", severity:"Mức độ",
    baseline:"Không drone", drone:"Có drone", improvement:"Cải thiện",
    capacity:"Sức chứa", attendance:"Khán giả",
    elapsed:"Thời gian", steps:"Bước", phase:"Giai đoạn",
    detection:"Phát hiện", verification:"Xác minh", decision:"Quyết định", response:"Phản ứng", total:"Tổng",
    radioTraffic:"Liên lạc vô tuyến", agentStatus:"Trạng thái đơn vị", kpiDelta:"Chênh lệch KPI",
    detect:"PHÁT HIỆN", verify:"XÁC MINH", decide:"QUYẾT ĐỊNH", respond:"PHẢN ỨNG", resolve:"GIẢI QUYẾT",
    awaiting:"ĐANG CHỜ SỰ CỐ…",
    footer_kernel:"KERNEL v1.2", footer_drone:"RTR HERA-T + VEGA-R", footer_runs:"1.800 LẦN MÔ PHỎNG", footer_fifa:"CHUẨN FIFA",
    db:"CSDL", api:"API", droneLabel:"DRONE", cctvLabel:"CCTV",
    agents:{
      voc:{l:"VOC",f:"Trung tâm Điều hành"},police:{l:"CSGT",f:"Chỉ huy Công an"},
      safety:{l:"ATLĐ",f:"Cán bộ An toàn"},medical:{l:"Y TẾ",f:"Điều phối Y tế"},
      fire:{l:"PCCC",f:"Chỉ huy PCCC"},drone:{l:"UAV",f:"Điều khiển Drone"},
      stw_n:{l:"GS-B",f:"Giám sát Bắc"},stw_s:{l:"GS-N",f:"Giám sát Nam"},
      cctv:{l:"CCTV",f:"Vận hành Camera"},
    },
    scenarios:{
      "CROWD-001":{name:"Ùn tắc cổng B — cao điểm vào sân",incLabel:"CỔNG B"},
      "MED-001":{name:"Ngừng tim — tầng trên Đông hàng 34",incLabel:"ĐÔNG TRÊN"},
      "SEC-003":{name:"Drone trái phép — tiếp cận 800m ĐB",incLabel:"UAV LẠ"},
    },
    chains:{
      "CROWD-001":{
        drone:["Mật độ tăng tại Cổng B — hàng chờ 600m+","Cam 23: mật độ 3.8 người/m² và tăng","Nhận 2 báo cáo — kéo feed drone","Drone xác nhận: 4.2 người/m², hàng 800m, CAO","Phân loại VÀNG — kích hoạt chuyển hướng","Mở Cổng C + thông báo PA","Triển khai rào — hướng dẫn sang Cổng C","Đội Cổng C sẵn sàng — tăng tiếp nhận","Mật độ giảm: 3.5 → 3.0 — chuyển hướng hiệu quả","Cổng B bình thường — XANH"],
        base:["Cổng B có vẻ đông, khó đánh giá","Một báo cáo — yêu cầu CCTV kiểm tra","Cam 23 thấy hàng nhưng không hết","Gửi đội kiểm tra bằng chân","Xác minh: mật độ rất cao, hàng 800m","Xác nhận CAO — kích hoạt chuyển hướng","Lệnh mở Cổng C","Chuyển hướng — đám đông bức xúc vì chờ","Cổng C tiếp nhận","Ổn định sau 25+ phút"]
      },
      "MED-001":{
        drone:["Feed drone: đám đông tụ tròn tầng Đông","Giám sát kề bên: khán giả vẫy tay","Hình drone: người nằm — phân loại ĐỎ","Cứu thương 3 xuất phát — yêu cầu đường","Drone: cầu thang C thông, B tắc","Hướng dẫn: CT C → Hàng 34 — ETA 90s","Đội tại chỗ — triển khai AED","Dọn Cổng D cho xe cứu thương","Sốc điện — mạch đập trở lại","Xe cứu thương tại Cổng D","Bệnh nhân ổn — chuyển xe","Sự cố y tế giải quyết — ghi nhật ký"],
        base:["Khán giả vẫy tay cách mấy khu — đi kiểm tra","Giám sát đi bộ — ETA 2 phút","Xác nhận: người bất tỉnh — cần y tế NGAY","ĐỎ — điều động y tế","Cứu thương xuất phát — đi cầu thang nào?","Kiểm tra CCTV — góc camera hạn chế","Đi cầu thang B — tắc — quay lại","Tới qua CT A — AED — chậm 8 phút","Yêu cầu xe cứu thương — dọn Cổng D","Bệnh nhân ổn sau phản ứng chậm","Giải quyết — ghi nhận chậm trễ"]
      },
      "SEC-003":{
        drone:["Máy quét RF: tín hiệu lạ 800m ĐB","Cảnh báo: drone trái phép — KHÔNG trong đội","Hạ cánh drone trinh sát — kiểm tra","Đánh giá: drone do thám, không tải trọng","Drone hợp pháp hạ hết — địch xác nhận","Kích hoạt gây nhiễu RF tần số địch","Sẵn sàng trú ẩn nếu vào không phận sân","Gây nhiễu — drone địch mất tín hiệu","Drone địch hạ — ngoài vành đai","Thu hồi drone địch — bằng chứng đảm bảo","Drone hợp pháp hoạt động lại","Chống drone giải quyết — XANH"],
        base:["Cảnh báo RF: phát hiện tín hiệu lạ","Ghi nhận — không xác nhận bằng mắt","Yêu cầu tìm bằng mắt hướng ĐB","Không thấy drone — quá xa / nhỏ","Chưa xác minh — duy trì cảnh báo","Phân loại đe dọa — kích hoạt gây nhiễu","Chuẩn bị trú ẩn một phần","Gây nhiễu — không biết hiệu quả","Tín hiệu RF yếu — có thể hạ hoặc bay đi","Tìm kiếm — khu vực rộng, không hướng dẫn","Không thu hồi — ghi nhận chưa giải quyết"]
      }
    }
  },
  en: {
    title:"VOC COMMAND CENTER",
    live:"● LIVE", standby:"○ STANDBY", auto:"● AUTO",
    autoBtn:"▶▶ AUTO-PLAY 3 SCENARIOS", stopBtn:"■ STOP", runBtn:"▶ RUN",
    scenario:"Scenario", category:"Category", severity:"Severity",
    baseline:"Baseline", drone:"Drone", improvement:"Improvement",
    capacity:"Capacity", attendance:"Attendance",
    elapsed:"Elapsed", steps:"Steps", phase:"Phase",
    detection:"Detection", verification:"Verification", decision:"Decision", response:"Response", total:"Total",
    radioTraffic:"Radio traffic", agentStatus:"Agent status", kpiDelta:"KPI delta",
    detect:"DETECT", verify:"VERIFY", decide:"DECIDE", respond:"RESPOND", resolve:"RESOLVE",
    awaiting:"AWAITING INCIDENT…",
    footer_kernel:"KERNEL v1.2", footer_drone:"RTR HERA-T + VEGA-R", footer_runs:"1,800 RUNS", footer_fifa:"FIFA ALIGNED",
    db:"DB", api:"API", droneLabel:"DRONE", cctvLabel:"CCTV",
    agents:{
      voc:{l:"VOC",f:"Venue Operations Centre"},police:{l:"POLICE",f:"Police Commander"},
      safety:{l:"SAFETY",f:"Safety Officer"},medical:{l:"MED",f:"Medical Coordinator"},
      fire:{l:"FIRE",f:"Fire Safety Cmdr"},drone:{l:"DRONE",f:"Drone Operator"},
      stw_n:{l:"STW-N",f:"Steward North"},stw_s:{l:"STW-S",f:"Steward South"},
      cctv:{l:"CCTV",f:"CCTV Operator"},
    },
    scenarios:{
      "CROWD-001":{name:"Gate B congestion — peak ingress",incLabel:"GATE B"},
      "MED-001":{name:"Cardiac arrest — East Upper Row 34",incLabel:"EAST UPPER"},
      "SEC-003":{name:"Unauthorized drone — 800m NE approach",incLabel:"HOSTILE UAV"},
    },
    chains:{
      "CROWD-001":{
        drone:["Crowd density rising at Gate B — queue 600m+","Cam 23: density 3.8 p/m² climbing","Dual report — pulling drone feed","Overhead: 4.2 p/m², 800m queue, HIGH","AMBER — activating redirect","Opening Gate C + PA announcement","Deploying barrier — guiding to Gate C","Gate C ready — intake increasing","Density dropping: 3.5→3.0 — working","Gate B normalized — GREEN"],
        base:["Crowd seems busy at Gate B","Single report — requesting CCTV","Cam 23 shows queue, can't see extent","Sending steward to assess on foot","On foot: density very high, 800m","Confirmed HIGH — activating redirect","Gate C overflow order","Executing — crowd frustrated","Gate C receiving overflow","Stabilizing after 25+ minutes"]
      },
      "MED-001":{
        drone:["Tethered: crowd circle in East Upper","Steward alerted by spectators waving","Drone: person on ground — RED","Paramedic 3 dispatched — route?","Drone: stairwell C clear, B congested","Route: stairwell C → Row 34, ETA 90s","On scene — AED deploying","Clearing Gate D for ambulance","AED shock — pulse restored","Ambulance at Gate D","Patient stable — transporting","Resolved — logging"],
        base:["Spectators waving sections away","Steward walking — ETA 2 min","Confirmed: person collapsed — NOW","RED — dispatching medical","Paramedic out — which stairwell?","Checking CCTV — angle limited","Stairwell B — congested — back","Via stairwell A — AED — 8 min delay","Ambulance request — clearing Gate D","Patient stable after delay","Resolved — delay noted for review"]
      },
      "SEC-003":{
        drone:["RF scanner: unknown 800m NE","Alert: unauthorized — NOT in fleet","Grounding recon units — check","Assessment: surveillance, no payload","Friendlies grounded — hostile confirmed","RF jamming on hostile frequency","Standby shelter if enters airspace","Jammer active — losing signal","Hostile descending — outside perimeter","Ground unit recovering — evidence","Friendlies back online — overwatch","Counter-drone GREEN — reporting"],
        base:["RF alert: unknown signal","Acknowledged — no visual","Visual search NE — stewards look up","Can't see — too far/small","Unverified — maintaining alert","Probable threat — activating jammer","Partial shelter prepared","Jamming — unknown effect","Signal fading — maybe landed","Ground search — large area, no guide","Cannot recover — logged unresolved"]
      }
    }
  }
};

const AGENT_META = [
  {id:"voc",x:300,y:150,c_dk:"#ffb020",c_lt:"#b05800",auth:5},
  {id:"police",x:150,y:70,c_dk:"#ff2850",c_lt:"#c00020",auth:5},
  {id:"safety",x:450,y:70,c_dk:"#00e06a",c_lt:"#007035",auth:4},
  {id:"medical",x:100,y:230,c_dk:"#00d8f0",c_lt:"#007888",auth:3},
  {id:"fire",x:500,y:230,c_dk:"#ff2850",c_lt:"#c00020",auth:3},
  {id:"drone",x:300,y:30,c_dk:"#2894ff",c_lt:"#0058b0",auth:2},
  {id:"stw_n",x:200,y:290,c_dk:"#9070ff",c_lt:"#5030a0",auth:2},
  {id:"stw_s",x:400,y:290,c_dk:"#9070ff",c_lt:"#5030a0",auth:2},
  {id:"cctv",x:60,y:150,c_dk:"#6880a8",c_lt:"#3a4a68",auth:1},
];
const EDGES=[["drone","voc"],["cctv","voc"],["police","voc"],["voc","safety"],["voc","medical"],["voc","fire"],["voc","stw_n"],["voc","stw_s"],["stw_n","voc"],["stw_s","voc"],["drone","police"],["safety","stw_n"],["safety","stw_s"],["medical","stw_n"]];
const SC_META=[{id:"CROWD-001",cat:"CROWD",sev:"high",trigMin:40,incX:250,incY:340},{id:"MED-001",cat:"MEDICAL",sev:"critical",trigMin:75,incX:450,incY:340},{id:"SEC-003",cat:"SECURITY",sev:"high",trigMin:70,incX:500,incY:50}];
const CHAIN_AGENTS={"CROWD-001":{drone:["stw_s","cctv","voc","drone","voc","safety","stw_s","stw_n","drone","voc"],base:["stw_s","voc","cctv","voc","stw_s","voc","safety","stw_s","stw_n","voc"]},"MED-001":{drone:["drone","stw_n","voc","medical","drone","voc","medical","safety","medical","voc","medical","voc"],base:["stw_n","voc","stw_n","voc","medical","voc","medical","medical","voc","medical","voc"]},"SEC-003":{drone:["cctv","voc","drone","police","voc","police","safety","police","voc","police","drone","voc"],base:["cctv","voc","police","stw_n","voc","police","safety","police","voc","police","voc"]}};
const CHAIN_PHASES={"CROWD-001":{drone:["detect","detect","verify","verify","decide","decide","respond","respond","resolve","resolve"],base:["detect","detect","verify","verify","verify","decide","decide","respond","respond","resolve"]},"MED-001":{drone:["detect","detect","verify","decide","decide","decide","respond","respond","respond","respond","resolve","resolve"],base:["detect","detect","verify","verify","decide","decide","respond","respond","respond","resolve","resolve"]},"SEC-003":{drone:["detect","detect","verify","verify","decide","decide","decide","respond","respond","resolve","resolve","resolve"],base:["detect","detect","verify","verify","verify","decide","decide","respond","respond","respond","resolve"]}};
const CHAIN_DELAYS={"CROWD-001":{drone:[0,1200,2200,3200,4500,5800,7000,8200,10000,12000],base:[0,3000,5000,7000,12000,14000,16000,18000,20000,25000]},"MED-001":{drone:[0,1500,2500,3500,4500,5500,7500,8500,10000,11500,13500,15000],base:[0,4000,12000,14000,15500,17000,20000,25000,27000,32000,35000]},"SEC-003":{drone:[0,1000,2000,3500,5000,6500,7500,9000,11000,13000,14500,16000],base:[0,2000,5000,9000,12000,15000,17000,20000,25000,30000,38000]}};
const CHAIN_DR={"CROWD-001":{drone:[0,0,0,1,0,0,0,0,1,0]},"MED-001":{drone:[1,0,0,0,1,0,0,0,0,0,0,0]},"SEC-003":{drone:[0,0,1,0,0,0,0,0,0,0,1,0]}};

const fmt=ms=>ms>=60000?`${Math.floor(ms/60000)}m${((ms%60000)/1000)|0}s`:`${(ms/1000).toFixed(1)}s`;
function useClock(){const[t,s]=useState(Date.now());useEffect(()=>{const i=setInterval(()=>s(Date.now()),1000);return()=>clearInterval(i)},[]);return t;}

function Panel({title,accent,children,flex,T,style}){
  return(<div style={{background:T.bgPanel,border:`1px solid ${T.border}`,borderTop:`2px solid ${accent||T.border}`,display:"flex",flexDirection:"column",flex:flex||"none",borderRadius:3,transition:"background .3s, border-color .3s",...style}}>
    {title&&<div style={{padding:"5px 10px",borderBottom:`1px solid ${T.border}`,display:"flex",alignItems:"center",gap:6}}>
      <div style={{width:5,height:5,borderRadius:1,background:accent||T.dim}}/>
      <span style={{fontSize:9,color:T.mid,letterSpacing:1.5,textTransform:"uppercase",fontWeight:600}}>{title}</span>
    </div>}
    <div style={{flex:1,overflow:"hidden",position:"relative"}}>{children}</div>
  </div>);
}

function MetricBox({label,value,unit,color,T,small}){
  return(<div style={{padding:small?"4px 6px":"6px 10px",background:T.bgCard,border:`1px solid ${T.border}`,flex:1,minWidth:0,borderRadius:2,transition:"background .3s"}}>
    <div style={{fontSize:7,color:T.dim,letterSpacing:1,textTransform:"uppercase",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{label}</div>
    <div style={{fontSize:small?14:18,fontWeight:700,color:color||T.text,lineHeight:1.2}}>{value}{unit&&<span style={{fontSize:9,color:T.dim,marginLeft:2}}>{unit}</span>}</div>
  </div>);
}

function SimPanel({title,scId,mode,step,T,L}){
  const isDrone=mode==="DRONE";
  const chains=isDrone?L.chains[scId].drone:L.chains[scId].base;
  const agents_=CHAIN_AGENTS[scId][isDrone?"drone":"base"];
  const phases_=CHAIN_PHASES[scId][isDrone?"drone":"base"];
  const delays_=CHAIN_DELAYS[scId][isDrone?"drone":"base"];
  const dr_=isDrone?(CHAIN_DR[scId]?.drone||[]):[];

  const activeMap=useMemo(()=>{const m={};for(let i=0;i<=Math.min(step,chains.length-1);i++){m[agents_[i]]={act:chains[i],p:phases_[i]};}return m;},[step,chains,agents_,phases_]);
  const activeEdges=useMemo(()=>{const s=new Set();for(let i=0;i<=Math.min(step,chains.length-1);i++){EDGES.forEach(([f,t])=>{if(f===agents_[i]||t===agents_[i])s.add(`${f}-${t}`);});}return s;},[step,agents_]);
  const cur=step>=0&&step<chains.length?{act:chains[step],p:phases_[step],d:delays_[step]}:null;
  const phaseCounts=useMemo(()=>{const c={detect:0,verify:0,decide:0,respond:0,resolve:0};for(let i=0;i<=Math.min(step,chains.length-1);i++)c[phases_[i]]++;return c;},[step,phases_]);
  const accent=isDrone?T.green:T.red;
  const scMeta=SC_META.find(s=>s.id===scId);
  const sevColor={critical:T.red,high:T.amber,moderate:T.blue}[scMeta?.sev]||T.dim;

  return(
    <Panel title={title} accent={accent} flex="1" T={T} style={{minWidth:0}}>
      <div style={{padding:"3px 8px",display:"flex",gap:3,borderBottom:`1px solid ${T.border}`}}>
        {PHASE_KEYS.map(k=>(<div key={k} style={{flex:1,textAlign:"center",padding:"2px 0",background:cur?.p===k?phaseColor(k,T)+"18":"transparent",borderBottom:cur?.p===k?`2px solid ${phaseColor(k,T)}`:"2px solid transparent",transition:"all .3s"}}>
          <div style={{fontSize:7,color:cur?.p===k?phaseColor(k,T):T.dim,fontWeight:600}}>{L[k]}</div>
          <div style={{fontSize:9,color:cur?.p===k?T.text:T.dim,fontWeight:700}}>{phaseCounts[k]}</div>
        </div>))}
      </div>
      <div style={{padding:3}}>
        <svg viewBox="0 0 600 340" style={{width:"100%",display:"block"}}>
          <defs><pattern id={`g${mode}${T===THEMES.dark?1:0}`} width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0L0 0 0 30" fill="none" stroke={T.border} strokeWidth=".2" opacity={T.gridOpacity}/></pattern></defs>
          <rect width="600" height="340" fill={`url(#g${mode}${T===THEMES.dark?1:0})`}/>
          {/* Stadium outline */}
          <ellipse cx="300" cy="250" rx="120" ry="70" fill="none" stroke={T.mid} strokeWidth="1.2" strokeDasharray="4 4" opacity=".5"/>
          <ellipse cx="300" cy="250" rx="55" ry="32" fill={T.pitchFill} stroke={T.green} strokeWidth="1" opacity=".7"/>
          <text x="300" y="253" textAnchor="middle" fill={T.mid} fontSize="7" fontWeight="600" fontFamily="monospace">PITCH</text>
          {/* Edges */}
          {EDGES.map(([f,t],i)=>{const fa=AGENT_META.find(a=>a.id===f),fb=AGENT_META.find(a=>a.id===t);if(!fa||!fb)return null;const isAct=activeEdges.has(`${f}-${t}`);const aD=activeMap[f]||activeMap[t];return<line key={i} x1={fa.x} y1={fa.y} x2={fb.x} y2={fb.y} stroke={isAct?phaseColor(aD?.p,T):T.dim} strokeWidth={isAct?1.5:.6} opacity={isAct?.7:.25}/>;
          })}
          {/* Agent nodes */}
          {AGENT_META.map(a=>{const d=activeMap[a.id];const isD=a.id==="drone";const show=isDrone||!isD;const agL=L.agents[a.id]?.l||a.id;const col_=T===THEMES.dark?a.c_dk:a.c_lt;if(!show)return<g key={a.id} opacity=".2"><circle cx={a.x} cy={a.y} r={16} fill={T.bgCard} stroke={T.dim} strokeWidth=".8" strokeDasharray="2 3"/></g>;const col=d?phaseColor(d.p,T):col_;return(<g key={a.id}>{d&&<circle cx={a.x} cy={a.y} r={22} fill={col} opacity=".12"><animate attributeName="r" values="18;26;18" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".15;.03;.15" dur="2s" repeatCount="indefinite"/></circle>}<circle cx={a.x} cy={a.y} r={16} fill={T.bgPanel} stroke={d?col:col_} strokeWidth={d?2:1.2}/><text x={a.x} y={a.y+1} textAnchor="middle" dominantBaseline="central" fill={d?T.text:col_} fontSize="7" fontWeight="700" fontFamily="monospace">{agL}</text>{d&&<text x={a.x} y={a.y+28} textAnchor="middle" fill={col} fontSize="5.5" fontFamily="monospace" fontWeight="600">{d.act.length>30?d.act.slice(0,30)+"…":d.act}</text>}</g>);})}
          {/* Incident marker */}
          {step>=0&&scMeta&&<g><circle cx={scMeta.incX} cy={scMeta.incY} r={12} fill={sevColor} opacity=".1"><animate attributeName="r" values="8;22;8" dur="1.5s" repeatCount="indefinite"/></circle><polygon points={`${scMeta.incX},${scMeta.incY-7} ${scMeta.incX+5},${scMeta.incY+3} ${scMeta.incX-5},${scMeta.incY+3}`} fill={sevColor} opacity=".85"><animate attributeName="opacity" values=".85;.4;.85" dur="1s" repeatCount="indefinite"/></polygon><text x={scMeta.incX} y={scMeta.incY+16} textAnchor="middle" fill={sevColor} fontSize="7" fontWeight="700" fontFamily="monospace">{L.scenarios[scId]?.incLabel||scId}</text></g>}
        </svg>
      </div>
      <div style={{padding:"0 6px 4px",display:"flex",gap:3}}>
        <MetricBox label={L.elapsed} value={fmt(cur?.d||0)} color={accent} T={T} small/>
        <MetricBox label={L.steps} value={`${Math.max(0,step+1)}/${chains.length}`} color={T.mid} T={T} small/>
        <MetricBox label={L.phase} value={cur?L[cur.p]:"—"} color={cur?phaseColor(cur.p,T):T.dim} T={T} small/>
      </div>
    </Panel>
  );
}

export default function VOCCommandCenter({ embedded = false, defaultTheme = "light", defaultLang = "vi" }){
  const clock=useClock();
  const[theme,setTheme]=useState(defaultTheme);
  const[lang,setLang]=useState(defaultLang);
  const[scIdx,setScIdx]=useState(0);
  const[stepD,setStepD]=useState(-1);
  const[stepB,setStepB]=useState(-1);
  const[isRun,setIsRun]=useState(false);
  const[radioLog,setRadioLog]=useState([]);
  const[autoPlay,setAutoPlay]=useState(false);
  const[doneD,setDoneD]=useState(false);
  const[doneB,setDoneB]=useState(false);
  const[scDone,setScDone]=useState(0);
  const tDr=useRef(null),tBr=useRef(null),logRef=useRef(null);
  const speed=1.2;
  const T=THEMES[theme],L=LANG[lang];
  const sc=SC_META[scIdx],scId=sc.id;

  const chainsD=L.chains[scId].drone,chainsB=L.chains[scId].base;
  const agD=CHAIN_AGENTS[scId].drone,agB=CHAIN_AGENTS[scId].base;
  const phD=CHAIN_PHASES[scId].drone,phB=CHAIN_PHASES[scId].base;
  const dlD=CHAIN_DELAYS[scId].drone,dlB=CHAIN_DELAYS[scId].base;
  const drD=CHAIN_DR[scId]?.drone||[];

  const reset=useCallback(()=>{clearTimeout(tDr.current);clearTimeout(tBr.current);setStepD(-1);setStepB(-1);setIsRun(false);setDoneD(false);setDoneB(false);setRadioLog([]);},[]);

  const run=useCallback(()=>{
    reset();setIsRun(true);let dS=0,bS=0;
    const aD=()=>{if(dS>=chainsD.length){setDoneD(true);return;}setStepD(dS);setRadioLog(p=>[...p,{a:agD[dS],act:chainsD[dS],p:phD[dS],d:dlD[dS],m:"D",dr:drD[dS]}]);const n=dS<chainsD.length-1?(dlD[dS+1]-dlD[dS])/speed:2000;dS++;tDr.current=setTimeout(aD,Math.max(n,250));};
    const aB=()=>{if(bS>=chainsB.length){setDoneB(true);return;}setStepB(bS);setRadioLog(p=>[...p,{a:agB[bS],act:chainsB[bS],p:phB[bS],d:dlB[bS],m:"B"}]);const n=bS<chainsB.length-1?(dlB[bS+1]-dlB[bS])/speed:2000;bS++;tBr.current=setTimeout(aB,Math.max(n,250));};
    tDr.current=setTimeout(aD,500);tBr.current=setTimeout(aB,500);
  },[chainsD,chainsB,agD,agB,phD,phB,dlD,dlB,drD,reset]);

  useEffect(()=>{if(doneD&&doneB&&isRun){setIsRun(false);if(autoPlay){const d=scDone+1;setScDone(d);if(d<SC_META.length)setTimeout(()=>setScIdx(d),3000);}}},[doneD,doneB,isRun,autoPlay,scDone]);
  useEffect(()=>{if(autoPlay&&!isRun&&scDone<SC_META.length&&scDone>0){const t=setTimeout(run,500);return()=>clearTimeout(t);}},[scIdx,autoPlay,isRun,scDone,run]);
  useEffect(()=>{if(logRef.current)logRef.current.scrollTop=logRef.current.scrollHeight;},[radioLog]);
  useEffect(()=>{setTheme(defaultTheme);},[defaultTheme]);
  useEffect(()=>{setLang(defaultLang);},[defaultLang]);

  const startAuto=()=>{reset();setScIdx(0);setScDone(0);setAutoPlay(true);setTimeout(run,400);};
  const stopAll=()=>{setAutoPlay(false);reset();setScDone(0);};

  const totalD=dlD[dlD.length-1],totalB=dlB[dlB.length-1];
  const imp=totalB>0?Math.round((1-totalD/totalB)*100):0;
  const now=new Date(clock);
  const timeStr=now.toLocaleTimeString("en-GB");
  const sevC={critical:T.red,high:T.amber,moderate:T.blue}[sc.sev]||T.dim;

  const KPI=[{l:L.detection,b:"59.8s",d:"19.7s",p:67},{l:L.verification,b:"175.6s",d:"39.3s",p:78},{l:L.decision,b:"45.5s",d:"20.2s",p:56},{l:L.response,b:"120.1s",d:"83.9s",p:30},{l:L.total,b:"797s",d:"400s",p:50}];

  return(
    <div style={{fontFamily:"'JetBrains Mono','SF Mono','Fira Code',monospace",background:T.bg,color:T.text,height:embedded?"100%":"100vh",display:"flex",flexDirection:"column",overflow:"hidden",fontSize:10,transition:"background .4s,color .4s"}}>
      <style>{`@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}} ::-webkit-scrollbar{width:3px} ::-webkit-scrollbar-track{background:transparent} ::-webkit-scrollbar-thumb{background:${T.border};border-radius:2px}`}</style>

      {/* TOP */}
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"6px 12px",borderBottom:`1px solid ${T.border}`,background:T.bgPanel,flexShrink:0,transition:"background .3s"}}>
        <div style={{display:"flex",alignItems:"center",gap:10}}>
          <span style={{color:T.amber,fontWeight:800,fontSize:12,letterSpacing:3}}>RTR SIMULATOR</span>
          <span style={{color:T.dim,fontSize:8,letterSpacing:1}}>{L.title}</span>
          <div style={{width:1,height:14,background:T.border}}/>
          <span style={{color:isRun?T.green:T.dim,fontSize:8,fontWeight:700,animation:isRun?"blink 1s infinite":"none"}}>{isRun?L.live:autoPlay?`${L.auto} ${scDone}/${SC_META.length}`:L.standby}</span>
        </div>
        <div style={{display:"flex",alignItems:"center",gap:6}}>
          <button onClick={()=>setLang(l=>l==="vi"?"en":"vi")} style={{background:T.bgCard,border:`1px solid ${T.border}`,padding:"3px 10px",fontSize:9,color:T.mid,fontFamily:"inherit",cursor:"pointer",borderRadius:3,fontWeight:600}}>{lang==="vi"?"VI 🇻🇳":"EN 🇬🇧"}</button>
          <button onClick={()=>setTheme(t=>t==="dark"?"light":"dark")} style={{background:T.bgCard,border:`1px solid ${T.border}`,padding:"3px 10px",fontSize:9,color:T.mid,fontFamily:"inherit",cursor:"pointer",borderRadius:3}}>{theme==="dark"?"☀":"◐"}</button>
          <span style={{color:T.amber,fontSize:11,fontWeight:700,letterSpacing:1,marginLeft:4}}>{timeStr}</span>
        </div>
      </div>

      {/* SCENARIO BAR */}
      <div style={{display:"flex",alignItems:"center",padding:"4px 12px",borderBottom:`1px solid ${T.border}`,background:T.bgPanel,flexShrink:0,gap:4,transition:"background .3s"}}>
        {SC_META.map((s,i)=>{const done=i<scDone;const active=i===scIdx&&isRun;const sC={critical:T.red,high:T.amber}[s.sev]||T.blue;
          return(<button key={s.id} onClick={()=>{if(!autoPlay){reset();setScIdx(i);}}} style={{background:active?sC+"15":done?T.greenDim:"transparent",border:`1px solid ${active?sC:done?T.green:T.border}`,padding:"3px 8px",fontSize:8,color:active?sC:done?T.green:T.dim,fontFamily:"inherit",cursor:autoPlay?"default":"pointer",borderRadius:2,transition:"all .3s"}}>{done?"✓ ":active?"▶ ":""}{s.id}</button>);
        })}
        <div style={{flex:1}}/>
        <button onClick={autoPlay?stopAll:startAuto} style={{background:autoPlay?T.redDim:T.amberDim,border:`1px solid ${autoPlay?T.red:T.amber}`,padding:"4px 14px",fontSize:9,color:autoPlay?T.red:T.amber,fontWeight:700,fontFamily:"inherit",cursor:"pointer",borderRadius:2}}>{autoPlay?L.stopBtn:L.autoBtn}</button>
        {!autoPlay&&<button onClick={isRun?reset:run} style={{background:isRun?T.redDim:T.greenDim,border:`1px solid ${isRun?T.red:T.green}`,padding:"4px 14px",fontSize:9,color:isRun?T.red:T.green,fontWeight:700,fontFamily:"inherit",cursor:"pointer",borderRadius:2}}>{isRun?L.stopBtn:L.runBtn}</button>}
      </div>

      {/* METRICS */}
      <div style={{display:"flex",gap:1,padding:"4px 12px",flexShrink:0}}>
        <MetricBox label={L.scenario} value={scId} color={sevC} T={T}/>
        <MetricBox label={L.category} value={sc.cat} color={T.mid} T={T}/>
        <MetricBox label={L.severity} value={sc.sev.toUpperCase()} color={sevC} T={T}/>
        <MetricBox label={L.baseline} value={fmt(doneB?totalB:stepB>=0?dlB[Math.min(stepB,dlB.length-1)]:0)} color={T.red} T={T}/>
        <MetricBox label={L.drone} value={fmt(doneD?totalD:stepD>=0?dlD[Math.min(stepD,dlD.length-1)]:0)} color={T.green} T={T}/>
        <MetricBox label={L.improvement} value={doneD&&doneB?`-${imp}%`:"—"} color={doneD&&doneB?T.green:T.dim} T={T}/>
        <MetricBox label={L.capacity} value="40.192" color={T.dim} T={T}/>
        <MetricBox label={L.attendance} value="37.400" color={T.amber} T={T}/>
      </div>

      {/* MAIN */}
      <div style={{flex:1,display:"flex",gap:1,padding:"0 12px 4px",overflow:"hidden",minHeight:0}}>
        <div style={{flex:3,display:"flex",gap:1,minWidth:0}}>
          <SimPanel title={L.baseline} scId={scId} mode="BASELINE" step={stepB} T={T} L={L}/>
          <SimPanel title={L.drone} scId={scId} mode="DRONE" step={stepD} T={T} L={L}/>
        </div>
        <div style={{flex:1,display:"flex",flexDirection:"column",gap:1,minWidth:200}}>
          <Panel title={L.radioTraffic} accent={T.cyan} flex="2" T={T}>
            <div ref={logRef} style={{padding:"4px 8px",overflowY:"auto",flex:1,fontSize:8,lineHeight:1.6,maxHeight:"100%"}}>
              {radioLog.map((e,i)=>{const agL=L.agents[e.a]?.l||e.a;const agM=AGENT_META.find(a=>a.id===e.a);const col=T===THEMES.dark?agM?.c_dk:agM?.c_lt;
                return(<div key={i} style={{display:"flex",gap:5,opacity:i===radioLog.length-1?1:.4,transition:"opacity .4s"}}>
                  <span style={{color:T.dim,minWidth:28,textAlign:"right",fontSize:7}}>{fmt(e.d)}</span>
                  <span style={{width:4,height:4,borderRadius:1,background:phaseColor(e.p,T),marginTop:4,flexShrink:0}}/>
                  <span style={{color:col||T.mid,fontWeight:600,minWidth:30,fontSize:7.5}}>{agL}</span>
                  <span style={{color:e.m==="D"?T.text:T.mid,fontSize:7.5}}>{e.act}{e.dr?" ▲":""}</span>
                </div>);
              })}
              {radioLog.length===0&&<div style={{color:T.dim,textAlign:"center",marginTop:20,fontSize:9}}>{L.awaiting}</div>}
            </div>
          </Panel>
          <Panel title={L.agentStatus} accent={T.amber} flex="1" T={T}>
            <div style={{padding:4,overflowY:"auto",flex:1}}>
              {AGENT_META.map(a=>{const agL=L.agents[a.id]?.l||a.id;const col=T===THEMES.dark?a.c_dk:a.c_lt;
                const findLast=(arr,ag,step_)=>{for(let i=Math.min(step_,arr.length-1);i>=0;i--)if(CHAIN_AGENTS[scId][arr===chainsD?"drone":"base"][i]===ag)return{act:arr[i],p:(arr===chainsD?phD:phB)[i]};return null;};
                const data=(stepD>=0?findLast(chainsD,a.id,stepD):null)||(stepB>=0?findLast(chainsB,a.id,stepB):null);
                return(<div key={a.id} style={{display:"flex",alignItems:"center",gap:4,padding:"2px 4px",borderBottom:`1px solid ${T.border}20`}}>
                  <div style={{width:5,height:5,borderRadius:1,background:data?phaseColor(data.p,T):T.border,boxShadow:data?`0 0 4px ${phaseColor(data.p,T)}`:"none"}}/>
                  <span style={{color:col,fontWeight:600,fontSize:7.5,minWidth:32}}>{agL}</span>
                  <span style={{color:T.dim,fontSize:7,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{data?data.act:"—"}</span>
                </div>);
              })}
            </div>
          </Panel>
          <Panel title={L.kpiDelta} accent={T.green} T={T} style={{minHeight:110}}>
            <div style={{padding:"6px 8px",display:"flex",flexDirection:"column",gap:3}}>
              {KPI.map(k=>(<div key={k.l} style={{display:"flex",alignItems:"center",gap:4}}>
                <span style={{fontSize:7,color:T.dim,minWidth:50}}>{k.l}</span>
                <div style={{flex:1,height:4,background:T.border,borderRadius:2,overflow:"hidden"}}><div style={{height:"100%",width:`${100-k.p}%`,background:T.green,borderRadius:2,transition:"width 1s"}}/></div>
                <span style={{fontSize:8,color:T.green,fontWeight:700,minWidth:28,textAlign:"right"}}>-{k.p}%</span>
              </div>))}
            </div>
          </Panel>
        </div>
      </div>

      {/* FOOTER */}
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"4px 12px",borderTop:`1px solid ${T.border}`,background:T.bgPanel,flexShrink:0,fontSize:8,transition:"background .3s"}}>
        <div style={{display:"flex",gap:10,color:T.dim}}><span>{L.footer_kernel}</span><span>|</span><span>{L.footer_drone}</span><span>|</span><span>{L.footer_runs}</span><span>|</span><span>{L.footer_fifa}</span></div>
        <div style={{display:"flex",gap:8}}><span style={{color:T.green}}>● {L.db}</span><span style={{color:T.green}}>● {L.api}</span><span style={{color:T.blue}}>● {L.droneLabel}</span><span style={{color:T.green}}>● {L.cctvLabel}</span></div>
      </div>
    </div>
  );
}
