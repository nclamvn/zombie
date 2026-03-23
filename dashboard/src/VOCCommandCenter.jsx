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
      "CROWD-001":{name:"⚠ NGUY CƠ GIẪM ĐẠP — Cổng B — 4.2 người/m²",incLabel:"⚠ CỔNG B"},
      "MED-001":{name:"🔴 NGỪNG TIM — Tầng Đông — Bệnh nhân ngừng thở",incLabel:"🔴 CẤP CỨU"},
      "SEC-003":{name:"🛑 DRONE ĐỊCH — Tiếp cận 800m — Có thể mang tải",incLabel:"🛑 UAV ĐỊCH"},
    },
    chains:{
      "CROWD-001":{
        drone:[
          "⚠ CẢNH BÁO: mật độ Cổng B vượt 3.8 người/m² — tăng nhanh!",
          "Camera 23 xác nhận: hàng chờ 600m+ — đám đông bắt đầu xô đẩy",
          "DRONE TRINH SÁT: triển khai ngay — feed trực tiếp lên VOC",
          "🔴 DRONE XÁC NHẬN: 4.2 người/m², hàng 800m — NGUY CƠ GIẪM ĐẠP!",
          "VOC PHÂN LOẠI ĐỎ — Kích hoạt Phương án Chuyển hướng KHẨN",
          "LỆNH: Mở tất cả lane Cổng C + PA toàn sân + bật đèn hướng dẫn",
          "Đội giám sát triển khai rào chắn — hướng dẫn 3.000 người sang Cổng C",
          "Cổng C tiếp nhận: throughput tăng 200→350 người/phút",
          "📉 DRONE: Mật độ GIẢM 4.2→3.0 người/m² — nguy cơ được kiểm soát",
          "✅ GIẢI QUYẾT trong 2 phút — Cổng B ổn định — XANH"
        ],
        base:[
          "Cổng B hình như đông... khó đánh giá từ vị trí giám sát",
          "VOC: chỉ 1 báo cáo — yêu cầu CCTV kiểm tra Cổng B",
          "CCTV: Camera 23 thấy hàng dài nhưng góc hạn chế — không đo được mật độ",
          "VOC: Gửi 2 giám sát đi bộ kiểm tra — ETA 3 phút...",
          "⏳ 5 phút trôi qua... giám sát đang di chuyển qua đám đông",
          "Giám sát tại chỗ: MẬT ĐỘ RẤT CAO! Hàng 800m! Đám đông bắt đầu xô!",
          "🔴 XÁC NHẬN MUỘN — Kích hoạt chuyển hướng — đã mất 7 phút!",
          "Mở Cổng C nhưng đám đông BỨC XÚC — la hét, xô đẩy rào chắn",
          "Cổng C tiếp nhận chậm — thiếu nhân sự điều phối",
          "⚠ Ổn định sau 25+ phút — 3 người bị thương nhẹ do chen lấn"
        ]
      },
      "MED-001":{
        drone:[
          "🔴 DRONE PHÁT HIỆN: đám đông tụ thành VÒNG TRÒN tầng Đông Trên!",
          "Giám sát kề bên: Khán giả la hét vẫy tay cầu cứu!",
          "DRONE ZOOM: Người đàn ông NẰM BẤT ĐỘNG — không thở — PHÂN LOẠI ĐỎ!",
          "Y TẾ 3 XUẤT PHÁT NGAY — drone dẫn đường thời gian thực!",
          "🛸 DRONE: Cầu thang C THÔNG — cầu thang B TẮC NGHẼN — tránh!",
          "Hướng dẫn: Cầu thang C → hành lang 7 → Hàng 34 — ETA 90 giây!",
          "💓 ĐỘI Y TẾ TẠI CHỖ — triển khai AED — bắt đầu sốc điện!",
          "An toàn dọn Cổng D — xe cứu thương sẵn sàng tiếp nhận",
          "⚡ SỐC ĐIỆN LẦN 1 — TIM ĐẬP TRỞ LẠI! Mạch 72bpm!",
          "Xe cứu thương tại Cổng D — cáng đang vào",
          "Bệnh nhân ổn định — SpO2 96% — đang chuyển lên xe",
          "✅ CỨU SỐNG THÀNH CÔNG — Tổng: 2 phút 30 giây từ phát hiện"
        ],
        base:[
          "Khán giả vẫy tay cách 3 khu — giám sát không rõ chuyện gì",
          "Giám sát ĐI BỘ đến kiểm tra — phải đi qua 3 khu đông...",
          "⏳ 4 PHÚT... giám sát chưa tới — đám đông cản đường",
          "Tới nơi: NGƯỜI BẤT TỈNH! Không thở! CẦN Y TẾ KHẨN CẤP!",
          "🔴 ĐỎ — Điều động y tế — NHƯNG ĐI CẦU THANG NÀO?!",
          "Kiểm tra CCTV — góc camera bị cột che — KHÔNG THẤY!",
          "Y tế đi cầu thang B — TẮC NGHẼN hoàn toàn — QUAY LẠI!",
          "⏳ 8 PHÚT TRỄ — Y tế đi vòng cầu thang A — AED triển khai muộn",
          "Sốc điện thành công NHƯNG não thiếu oxy 8 phút — TIÊN LƯỢNG XẤU",
          "Xe cứu thương tới — bệnh nhân sống nhưng TỔN THƯƠNG NẶNG",
          "⚠ SỐNG nhưng DI CHỨNG — nếu tới sớm 6 phút sẽ hồi phục hoàn toàn"
        ]
      },
      "SEC-003":{
        drone:[
          "🛑 RADAR RF: TÍN HIỆU LẠ 800m ĐÔNG BẮC — đang tiếp cận!",
          "VOC CẢNH BÁO: Drone KHÔNG trong đội — phân tích tín hiệu KHẨN!",
          "🛸 HẠ TOÀN BỘ DRONE HỢP PHÁP — tránh nhầm lẫn đối tượng!",
          "DRONE trinh sát: Đối tượng loại quadcopter — CÓ THỂ MANG TẢI!",
          "Phân biệt hoàn tất: drone hợp pháp ĐÃ HẠ — đối tượng ĐÃ XÁC NHẬN",
          "⚡ KÍCH HOẠT GÂY NHIỄU RF — tần số 2.4GHz + 5.8GHz!",
          "An toàn: sẵn sàng trú ẩn nếu UAV vào không phận khán đài",
          "GÂY NHIỄU HIỆU QUẢ — drone địch MẤT TÍN HIỆU ĐIỀU KHIỂN!",
          "📉 DRONE ĐỊCH RƠI — hạ cánh bắt buộc ngoài vành đai 200m",
          "Cảnh sát THU GIỮ thiết bị — bảo toàn bằng chứng — kiểm tra tải",
          "🛸 Drone hợp pháp CẤT CÁNH LẠI — overwatch khôi phục 100%",
          "✅ MỐI ĐE DỌA VÔ HIỆU HÓA — 2 phút 40 giây — BÁO CÁO BỘ QUỐC PHÒNG"
        ],
        base:[
          "Radar RF: tín hiệu lạ — hướng Đông Bắc",
          "VOC ghi nhận — KHÔNG CÓ HÌNH ẢNH xác nhận bằng mắt",
          "Yêu cầu giám sát NHÌN LÊN TRỜI tìm drone — hướng ĐB",
          "⏳ 3 phút... giám sát: KHÔNG THẤY GÌ — trời mây, drone quá nhỏ",
          "VOC: Vẫn chưa xác minh — chỉ có tín hiệu RF — không biết loại gì",
          "⏳ 7 phút — Phân loại MỐI ĐE DỌA CÓ THỂ — kích hoạt gây nhiễu",
          "Chuẩn bị phương án trú ẩn — 40.000 khán giả trong nguy hiểm",
          "Gây nhiễu tần số — KHÔNG BIẾT HIỆU QUẢ vì không có hình ảnh!",
          "Tín hiệu RF yếu dần — drone bay đi hay rơi? KHÔNG RÕ!",
          "Cảnh sát tìm kiếm mặt đất — khu vực 2km² — KHÔNG CÓ DẪN ĐƯỜNG",
          "⚠ KHÔNG THU HỒI ĐƯỢC — mối đe dọa CHƯA XÁC NHẬN — ghi nhận LỖ HỔNG"
        ]
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
      "CROWD-001":{name:"⚠ CRUSH RISK — Gate B — 4.2 p/m² density",incLabel:"⚠ GATE B"},
      "MED-001":{name:"🔴 CARDIAC ARREST — East Upper — Patient not breathing",incLabel:"🔴 CARDIAC"},
      "SEC-003":{name:"🛑 HOSTILE DRONE — 800m NE approach — Possible payload",incLabel:"🛑 HOSTILE UAV"},
    },
    chains:{
      "CROWD-001":{
        drone:[
          "⚠ ALERT: Gate B density exceeding 3.8 p/m² — rising fast!",
          "Camera 23 confirms: 600m+ queue — crowd starting to PUSH",
          "DRONE DEPLOYED: live overhead feed to VOC — 15 seconds",
          "🔴 DRONE CONFIRMS: 4.2 p/m², 800m queue — CRUSH RISK IMMINENT!",
          "VOC CLASSIFIES RED — Activating Emergency Redirect Protocol",
          "ORDER: Open all Gate C lanes + PA full stadium + guide lights ON",
          "Stewards deploying barriers — redirecting 3,000 people to Gate C",
          "Gate C receiving: throughput up 200→350 persons/minute",
          "📉 DRONE: Density FALLING 4.2→3.0 p/m² — redirect WORKING",
          "✅ RESOLVED in 2 minutes — Gate B stable — GREEN"
        ],
        base:[
          "Gate B looks busy... hard to tell from steward position",
          "VOC: only 1 report — requesting CCTV check Gate B",
          "CCTV: Camera 23 shows queue but angle limited — can't measure density",
          "VOC: Sending 2 stewards on foot to assess — ETA 3 minutes...",
          "⏳ 5 minutes elapsed... stewards still moving through crowd",
          "Steward arrives: DENSITY VERY HIGH! 800m queue! Crowd PUSHING!",
          "🔴 LATE CONFIRMATION — Activating redirect — 7 minutes LOST!",
          "Gate C opened but crowd FRUSTRATED — shouting, pushing barriers",
          "Gate C receiving slow — understaffed for overflow",
          "⚠ Stabilized after 25+ minutes — 3 minor crush injuries reported"
        ]
      },
      "MED-001":{
        drone:[
          "🔴 DRONE DETECTS: crowd forming CIRCLE in East Upper section!",
          "Adjacent steward: Spectators SCREAMING and waving for help!",
          "DRONE ZOOM: Male on ground NOT BREATHING — CLASSIFYING RED!",
          "PARAMEDIC TEAM 3 DISPATCHED — drone guiding route in real-time!",
          "🛸 DRONE: Stairwell C CLEAR — stairwell B BLOCKED — avoid!",
          "Route guidance: Stairwell C → corridor 7 → Row 34 — ETA 90 sec!",
          "💓 MEDICAL ON SCENE — AED deployed — initiating defibrillation!",
          "Safety clearing Gate D — ambulance staging ready",
          "⚡ FIRST SHOCK DELIVERED — HEARTBEAT RESTORED! Pulse 72bpm!",
          "Ambulance at Gate D — stretcher team entering",
          "Patient stable — SpO2 96% — transferring to ambulance",
          "✅ LIFE SAVED — Total: 2 min 30 sec from detection to pulse"
        ],
        base:[
          "Spectators waving 3 sections away — steward can't see what's happening",
          "Steward WALKING to investigate — pushing through packed crowd...",
          "⏳ 4 MINUTES... steward still not there — crowd blocking path",
          "Arrives: MAN DOWN! NOT BREATHING! NEED MEDICAL IMMEDIATELY!",
          "🔴 RED — Dispatching medical — BUT WHICH STAIRWELL?!",
          "Checking CCTV — camera BLOCKED by pillar — CANNOT SEE!",
          "Paramedic takes stairwell B — COMPLETELY BLOCKED — TURNING BACK!",
          "⏳ 8 MINUTE DELAY — Rerouting via stairwell A — AED deploying LATE",
          "Shock delivered BUT brain without oxygen for 8 minutes — POOR PROGNOSIS",
          "Ambulance arrives — patient alive but SIGNIFICANT DAMAGE",
          "⚠ SURVIVED but PERMANENT INJURY — 6 minutes earlier = full recovery"
        ]
      },
      "SEC-003":{
        drone:[
          "🛑 RF RADAR: UNKNOWN SIGNAL 800m NORTHEAST — closing fast!",
          "VOC ALERT: Drone NOT IN FLEET — analyzing signal URGENTLY!",
          "🛸 ALL FRIENDLY DRONES GROUNDED — preventing misidentification!",
          "RECON DRONE: Target is quadcopter — POSSIBLE PAYLOAD detected!",
          "Deconfliction complete: friendlies DOWN — hostile CONFIRMED",
          "⚡ RF JAMMING ACTIVE — targeting 2.4GHz + 5.8GHz bands!",
          "Safety: shelter-in-place READY if UAV breaches stadium airspace",
          "JAMMING EFFECTIVE — hostile drone LOSING CONTROL SIGNAL!",
          "📉 HOSTILE DRONE FALLING — forced landing 200m outside perimeter",
          "Police SECURING device — preserving evidence — checking payload",
          "🛸 Friendly drones RELAUNCHING — overwatch restored 100%",
          "✅ THREAT NEUTRALIZED — 2 min 40 sec — REPORTING TO DEFENSE MINISTRY"
        ],
        base:[
          "RF radar: unknown signal — northeast direction",
          "VOC acknowledged — NO VISUAL CONFIRMATION available",
          "Requesting stewards to LOOK UP at sky — northeast direction",
          "⏳ 3 minutes... stewards: CAN'T SEE ANYTHING — cloudy, drone too small",
          "VOC: Still UNVERIFIED — only RF signal — don't know drone type",
          "⏳ 7 minutes — Classifying PROBABLE THREAT — activating jammer",
          "Preparing shelter plan — 40,000 spectators potentially at risk",
          "Jamming broadcast frequencies — NO WAY TO KNOW IF EFFECTIVE!",
          "RF signal fading — drone flew away or crashed? UNKNOWN!",
          "Police ground search — 2km² area — NO GUIDANCE for search team",
          "⚠ CANNOT RECOVER — threat UNCONFIRMED — logging SECURITY GAP"
        ]
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
const CHAIN_DELAYS={"CROWD-001":{drone:[0,800,1500,2500,3500,4500,5500,6500,8000,10000],base:[0,4000,8000,12000,17000,22000,25000,28000,32000,40000]},"MED-001":{drone:[0,1000,2000,3000,4000,5000,6500,7500,9000,10500,12000,14000],base:[0,5000,14000,20000,24000,27000,30000,36000,42000,48000,55000]},"SEC-003":{drone:[0,800,1800,3000,4500,5500,6500,8000,10000,12000,13500,15000],base:[0,3000,7000,12000,18000,25000,30000,34000,40000,48000,58000]}};
const CHAIN_DR={"CROWD-001":{drone:[0,0,0,1,0,0,0,0,1,0]},"MED-001":{drone:[1,0,0,0,1,0,0,0,0,0,0,0]},"SEC-003":{drone:[0,0,1,0,0,0,0,0,0,0,1,0]}};

const fmt=ms=>ms>=60000?`${Math.floor(ms/60000)}m${((ms%60000)/1000)|0}s`:`${(ms/1000).toFixed(1)}s`;
function useClock(){const[t,s]=useState(Date.now());useEffect(()=>{const i=setInterval(()=>s(Date.now()),1000);return()=>clearInterval(i)},[]);return t;}

function Panel({title,accent,children,flex,T,style}){
  return(<div style={{background:T.bgPanel,border:`1px solid ${T.border}`,borderTop:`2px solid ${accent||T.border}`,display:"flex",flexDirection:"column",flex:flex||"none",borderRadius:3,transition:"background .3s, border-color .3s",...style}}>
    {title&&<div style={{padding:"5px 10px",borderBottom:`1px solid ${T.border}`,display:"flex",alignItems:"center",gap:6}}>
      <div style={{width:6,height:6,borderRadius:1,background:accent||T.dim}}/>
      <span style={{fontSize:13,color:T.mid,letterSpacing:1.5,textTransform:"uppercase",fontWeight:800}}>{title}</span>
    </div>}
    <div style={{flex:1,overflow:"hidden",position:"relative"}}>{children}</div>
  </div>);
}

function MetricBox({label,value,unit,color,T,small}){
  return(<div style={{padding:small?"5px 8px":"8px 12px",background:T.bgCard,border:`1px solid ${T.border}`,flex:1,minWidth:0,borderRadius:2,transition:"background .3s"}}>
    <div style={{fontSize:10,color:T.dim,letterSpacing:1,textTransform:"uppercase",whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",fontWeight:700}}>{label}</div>
    <div style={{fontSize:small?20:26,fontWeight:800,color:color||T.text,lineHeight:1.2}}>{value}{unit&&<span style={{fontSize:12,color:T.dim,marginLeft:2}}>{unit}</span>}</div>
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
          <div style={{fontSize:10,color:cur?.p===k?phaseColor(k,T):T.dim,fontWeight:700}}>{L[k]}</div>
          <div style={{fontSize:13,color:cur?.p===k?T.text:T.dim,fontWeight:800}}>{phaseCounts[k]}</div>
        </div>))}
      </div>
      <div style={{padding:3}}>
        <svg viewBox="0 0 600 340" style={{width:"100%",display:"block"}}>
          <defs><pattern id={`g${mode}${T===THEMES.dark?1:0}`} width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0L0 0 0 30" fill="none" stroke={T.border} strokeWidth=".2" opacity={T.gridOpacity}/></pattern></defs>
          <rect width="600" height="340" fill={`url(#g${mode}${T===THEMES.dark?1:0})`}/>
          {/* Stadium outline */}
          <ellipse cx="300" cy="250" rx="120" ry="70" fill="none" stroke={T.mid} strokeWidth="1.2" strokeDasharray="4 4" opacity=".5"/>
          <ellipse cx="300" cy="250" rx="55" ry="32" fill={T.pitchFill} stroke={T.green} strokeWidth="1" opacity=".7"/>
          <text x="300" y="253" textAnchor="middle" fill={T.mid} fontSize="10" fontWeight="700" fontFamily="monospace">PITCH</text>
          {/* Edges */}
          {EDGES.map(([f,t],i)=>{const fa=AGENT_META.find(a=>a.id===f),fb=AGENT_META.find(a=>a.id===t);if(!fa||!fb)return null;const isAct=activeEdges.has(`${f}-${t}`);const aD=activeMap[f]||activeMap[t];return<line key={i} x1={fa.x} y1={fa.y} x2={fb.x} y2={fb.y} stroke={isAct?phaseColor(aD?.p,T):T.dim} strokeWidth={isAct?1.5:.6} opacity={isAct?.7:.25}/>;
          })}
          {/* Agent nodes */}
          {AGENT_META.map(a=>{const d=activeMap[a.id];const isD=a.id==="drone";const show=isDrone||!isD;const agL=L.agents[a.id]?.l||a.id;const col_=T===THEMES.dark?a.c_dk:a.c_lt;if(!show)return<g key={a.id} opacity=".2"><circle cx={a.x} cy={a.y} r={20} fill={T.bgCard} stroke={T.dim} strokeWidth=".8" strokeDasharray="2 3"/></g>;const col=d?phaseColor(d.p,T):col_;return(<g key={a.id}>{d&&<circle cx={a.x} cy={a.y} r={26} fill={col} opacity=".12"><animate attributeName="r" values="22;30;22" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".15;.03;.15" dur="2s" repeatCount="indefinite"/></circle>}<circle cx={a.x} cy={a.y} r={20} fill={T.bgPanel} stroke={d?col:col_} strokeWidth={d?2.5:1.5}/><text x={a.x} y={a.y+1} textAnchor="middle" dominantBaseline="central" fill={d?T.text:col_} fontSize="10" fontWeight="800" fontFamily="monospace">{agL}</text>{d&&<text x={a.x} y={a.y+32} textAnchor="middle" fill={col} fontSize="8" fontFamily="monospace" fontWeight="700">{d.act.length>28?d.act.slice(0,28)+"…":d.act}</text>}</g>);})}
          {/* Incident marker */}
          {step>=0&&scMeta&&<g><circle cx={scMeta.incX} cy={scMeta.incY} r={12} fill={sevColor} opacity=".1"><animate attributeName="r" values="8;22;8" dur="1.5s" repeatCount="indefinite"/></circle><polygon points={`${scMeta.incX},${scMeta.incY-7} ${scMeta.incX+5},${scMeta.incY+3} ${scMeta.incX-5},${scMeta.incY+3}`} fill={sevColor} opacity=".85"><animate attributeName="opacity" values=".85;.4;.85" dur="1s" repeatCount="indefinite"/></polygon><text x={scMeta.incX} y={scMeta.incY+18} textAnchor="middle" fill={sevColor} fontSize="10" fontWeight="800" fontFamily="monospace">{L.scenarios[scId]?.incLabel||scId}</text></g>}
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

      {/* TOP — standalone only */}
      {!embedded&&<div style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"6px 12px",borderBottom:`1px solid ${T.border}`,background:T.bgPanel,flexShrink:0}}>
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
      </div>}

      {/* SINGLE CONTROL BAR — everything in one compact row */}
      <div style={{display:"flex",alignItems:"center",padding:"3px 10px",borderBottom:`1px solid ${T.border}`,background:T.bgPanel,flexShrink:0,gap:3}}>
        <span style={{color:isRun?T.green:T.dim,fontSize:8,fontWeight:700,animation:isRun?"blink 1s infinite":"none"}}>
          {isRun?"●":"○"}
        </span>
        {SC_META.map((s,i)=>{const done=i<scDone;const active=i===scIdx&&isRun;const sC={critical:T.red,high:T.amber}[s.sev]||T.blue;
          return(<button key={s.id} onClick={()=>{if(!autoPlay){reset();setScIdx(i);}}} style={{background:active?sC+"15":done?T.greenDim:"transparent",border:`1px solid ${active?sC:done?T.green:T.border}`,padding:"2px 7px",fontSize:8,color:active?sC:done?T.green:T.dim,fontFamily:"inherit",cursor:autoPlay?"default":"pointer",borderRadius:2}}>{done?"✓ ":active?"▶ ":""}{s.id}</button>);
        })}
        <div style={{flex:1}}/>
        <button onClick={autoPlay?stopAll:startAuto} style={{background:autoPlay?T.redDim:T.amberDim,border:`1px solid ${autoPlay?T.red:T.amber}`,padding:"3px 12px",fontSize:8,color:autoPlay?T.red:T.amber,fontWeight:700,fontFamily:"inherit",cursor:"pointer",borderRadius:2}}>{autoPlay?L.stopBtn:L.autoBtn}</button>
        {!autoPlay&&<button onClick={isRun?reset:run} style={{background:isRun?T.redDim:T.greenDim,border:`1px solid ${isRun?T.red:T.green}`,padding:"3px 12px",fontSize:8,color:isRun?T.red:T.green,fontWeight:700,fontFamily:"inherit",cursor:"pointer",borderRadius:2}}>{isRun?L.stopBtn:L.runBtn}</button>}
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
            <div ref={logRef} style={{padding:"4px 8px",overflowY:"auto",flex:1,fontSize:11,lineHeight:1.7,maxHeight:"100%"}}>
              {radioLog.map((e,i)=>{const agL=L.agents[e.a]?.l||e.a;const agM=AGENT_META.find(a=>a.id===e.a);const col=T===THEMES.dark?agM?.c_dk:agM?.c_lt;
                return(<div key={i} style={{display:"flex",gap:6,opacity:i===radioLog.length-1?1:.4,transition:"opacity .4s"}}>
                  <span style={{color:T.dim,minWidth:36,textAlign:"right",fontSize:10}}>{fmt(e.d)}</span>
                  <span style={{width:6,height:6,borderRadius:1,background:phaseColor(e.p,T),marginTop:5,flexShrink:0}}/>
                  <span style={{color:col||T.mid,fontWeight:700,minWidth:36,fontSize:11}}>{agL}</span>
                  <span style={{color:e.m==="D"?T.text:T.mid,fontSize:11}}>{e.act}{e.dr?" ▲":""}</span>
                </div>);
              })}
              {radioLog.length===0&&<div style={{color:T.dim,textAlign:"center",marginTop:20,fontSize:13}}>{L.awaiting}</div>}
            </div>
          </Panel>
          <Panel title={L.agentStatus} accent={T.amber} flex="1" T={T}>
            <div style={{padding:4,overflowY:"auto",flex:1}}>
              {AGENT_META.map(a=>{const agL=L.agents[a.id]?.l||a.id;const col=T===THEMES.dark?a.c_dk:a.c_lt;
                const findLast=(arr,ag,step_)=>{for(let i=Math.min(step_,arr.length-1);i>=0;i--)if(CHAIN_AGENTS[scId][arr===chainsD?"drone":"base"][i]===ag)return{act:arr[i],p:(arr===chainsD?phD:phB)[i]};return null;};
                const data=(stepD>=0?findLast(chainsD,a.id,stepD):null)||(stepB>=0?findLast(chainsB,a.id,stepB):null);
                return(<div key={a.id} style={{display:"flex",alignItems:"center",gap:5,padding:"3px 6px",borderBottom:`1px solid ${T.border}20`}}>
                  <div style={{width:7,height:7,borderRadius:2,background:data?phaseColor(data.p,T):T.border,boxShadow:data?`0 0 5px ${phaseColor(data.p,T)}`:"none"}}/>
                  <span style={{color:col,fontWeight:700,fontSize:11,minWidth:40}}>{agL}</span>
                  <span style={{color:T.dim,fontSize:10,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{data?data.act:"—"}</span>
                </div>);
              })}
            </div>
          </Panel>
          <Panel title={L.kpiDelta} accent={T.green} T={T} style={{minHeight:110}}>
            <div style={{padding:"6px 8px",display:"flex",flexDirection:"column",gap:3}}>
              {KPI.map(k=>(<div key={k.l} style={{display:"flex",alignItems:"center",gap:5}}>
                <span style={{fontSize:10,color:T.dim,minWidth:65,fontWeight:600}}>{k.l}</span>
                <div style={{flex:1,height:6,background:T.border,borderRadius:3,overflow:"hidden"}}><div style={{height:"100%",width:`${100-k.p}%`,background:T.green,borderRadius:3,transition:"width 1s"}}/></div>
                <span style={{fontSize:12,color:T.green,fontWeight:800,minWidth:36,textAlign:"right"}}>-{k.p}%</span>
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
