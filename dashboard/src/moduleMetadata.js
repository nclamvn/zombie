/**
 * Module Metadata Registry — bilingual labels for all 17 RTR modules
 * Used by reportGenerator.js for bilingual report export
 */

export const MODULE_META = {
  stadium_operations: {
    name: { vi: "An toàn Sân vận động (FIFA)", en: "Stadium Operations — FIFA" },
    desc: { vi: "Mô phỏng chuỗi quyết định tại Trung tâm Điều hành Sân vận động (VOC) trong các sự cố ngày thi đấu", en: "Decision chain simulation at the Venue Operations Centre (VOC) during match-day incidents" },
    category: "public_safety",
  },
  counter_uas: {
    name: { vi: "Chống Drone (Counter-UAS)", en: "Counter-UAS Defense" },
    desc: { vi: "Mô phỏng phát hiện, phân loại và vô hiệu hóa drone trái phép xâm nhập không phận bảo vệ", en: "Detection, classification and neutralization of unauthorized drones in protected airspace" },
    category: "defense",
  },
  isr_surveillance: {
    name: { vi: "Trinh sát, Giám sát (ISR)", en: "Intelligence, Surveillance & Reconnaissance" },
    desc: { vi: "Mô phỏng nhiệm vụ trinh sát bằng drone: biên giới, biển, ban đêm, giám sát liên tục", en: "Drone ISR missions: border, maritime, night operations, persistent surveillance" },
    category: "defense",
  },
  swarm_tactics: {
    name: { vi: "Chiến thuật Bay đàn (Swarm)", en: "Swarm Tactics" },
    desc: { vi: "Mô phỏng đội hình 200 drone: tấn công phối hợp, áp chế phòng không, chống bầy đối phương", en: "200-drone formation simulation: coordinated attack, SEAD, counter-swarm operations" },
    category: "defense",
  },
  border_patrol: {
    name: { vi: "Tuần tra Biên giới", en: "Border Patrol & Surveillance" },
    desc: { vi: "Mô phỏng tuần tra biên giới Lạng Sơn: phát hiện buôn lậu, vượt biên, drone qua biên", en: "Lang Son border patrol: smuggling detection, illegal crossing, cross-border drones" },
    category: "defense",
  },
  perimeter_defense: {
    name: { vi: "Bảo vệ Căn cứ / Cơ sở", en: "Perimeter Defense" },
    desc: { vi: "Mô phỏng bảo vệ vành đai: xâm nhập đêm, bom thư, drone do thám", en: "Perimeter security simulation: night intrusion, suspicious packages, reconnaissance drones" },
    category: "defense",
  },
  concert_festival: {
    name: { vi: "Concert / Lễ hội / Festival", en: "Concert & Festival Safety" },
    desc: { vi: "Mô phỏng an toàn sự kiện 60.000 người: giẫm đạp, say nắng, thời tiết xấu", en: "60,000-person event safety: crowd crush, heat stroke, severe weather" },
    category: "public_safety",
  },
  traffic_management: {
    name: { vi: "Giám sát Giao thông Đô thị", en: "Urban Traffic Management" },
    desc: { vi: "Mô phỏng giao thông TPHCM: ùn tắc, tai nạn, VIP motorcade, ngập lụt", en: "HCMC traffic simulation: congestion, accidents, VIP escort, urban flooding" },
    category: "public_safety",
  },
  crowd_management: {
    name: { vi: "Quản lý Đám đông / Biểu tình", en: "Crowd & Protest Management" },
    desc: { vi: "Mô phỏng quản lý đám đông: biểu tình, flash mob, giải tán hòa bình", en: "Crowd management simulation: protests, flash mobs, peaceful de-escalation" },
    category: "public_safety",
  },
  search_rescue: {
    name: { vi: "Tìm kiếm Cứu nạn (SAR)", en: "Search & Rescue" },
    desc: { vi: "Mô phỏng SAR: tìm kiếm trong rừng, sập nhà, trên biển, trẻ lạc, lũ quét", en: "SAR simulation: forest search, building collapse, maritime, missing child, flash flood" },
    category: "emergency",
  },
  fire_response: {
    name: { vi: "Ứng phó Cháy rừng & Tòa nhà", en: "Fire Emergency Response" },
    desc: { vi: "Mô phỏng chữa cháy: rừng, chung cư cao tầng, chợ, kho hóa chất", en: "Fire response: forest fire, high-rise, market fire, chemical warehouse" },
    category: "emergency",
  },
  flood_disaster: {
    name: { vi: "Ứng phó Lũ lụt & Thiên tai", en: "Flood & Natural Disaster Response" },
    desc: { vi: "Mô phỏng lũ lụt Cửu Long: lũ quét, triều cường, sạt lở, vỡ đê", en: "Mekong flood simulation: flash flood, tidal surge, landslide, dam breach" },
    category: "emergency",
  },
  hazmat_response: {
    name: { vi: "Sự cố Hóa chất / Phóng xạ", en: "HAZMAT Response" },
    desc: { vi: "Mô phỏng sự cố hóa chất: tràn hóa chất, rò rỉ phóng xạ, đám mây độc", en: "HAZMAT simulation: chemical spill, radiation leak, toxic cloud" },
    category: "emergency",
  },
  infrastructure_inspection: {
    name: { vi: "Kiểm tra Hạ tầng", en: "Infrastructure Inspection" },
    desc: { vi: "Mô phỏng kiểm tra: cầu Long Biên, đường dây điện, đập thủy điện", en: "Infrastructure inspection: Long Bien bridge, power lines, hydroelectric dam" },
    category: "industrial",
  },
  agriculture: {
    name: { vi: "Nông nghiệp Chính xác", en: "Precision Agriculture" },
    desc: { vi: "Mô phỏng nông nghiệp An Giang 500ha: phát hiện sâu bệnh, tưới tiêu, phun thuốc", en: "An Giang 500ha precision agriculture: pest detection, irrigation, spraying" },
    category: "industrial",
  },
  mapping_survey: {
    name: { vi: "Đo đạc & Bản đồ 3D", en: "Mapping & 3D Survey" },
    desc: { vi: "Mô phỏng đo đạc Thủ Đức: bản đồ 3D, giám sát xây dựng, địa hình", en: "Thu Duc survey: 3D mapping, construction monitoring, terrain survey" },
    category: "industrial",
  },
  delivery_logistics: {
    name: { vi: "Vận chuyển & Logistics", en: "Drone Delivery & Logistics" },
    desc: { vi: "Mô phỏng giao hàng Phú Quốc: vận chuyển đảo, y tế khẩn cấp, hàng hóa", en: "Phu Quoc delivery: island logistics, emergency medical, cargo transport" },
    category: "industrial",
  },
};

export const KPI_LABELS = {
  detection_latency: { vi: "Thời gian Phát hiện", en: "Detection Latency" },
  verification_time: { vi: "Thời gian Xác minh", en: "Verification Time" },
  decision_time: { vi: "Thời gian Quyết định", en: "Decision Time" },
  response_time: { vi: "Thời gian Phản ứng", en: "Response Time" },
  total_resolution: { vi: "Tổng thời gian Giải quyết", en: "Total Resolution Time" },
};

export const CATEGORY_LABELS = {
  defense: { vi: "Quốc phòng", en: "Defense" },
  public_safety: { vi: "An toàn Công cộng", en: "Public Safety" },
  emergency: { vi: "Cứu hộ Khẩn cấp", en: "Emergency Response" },
  industrial: { vi: "Công nghiệp", en: "Industrial" },
  general: { vi: "Khác", en: "Other" },
};
