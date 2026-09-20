"""องค์กรปกครองส่วนท้องถิ่นในจังหวัดภูเก็ต 19 แห่ง (ข้อ 4 ของโจทย์)

โจทย์กำหนดว่า "ระบบจึงต้องเก็บข้อมูลของท้องถิ่นเป็นข้อมูลในฐานข้อมูล
ไม่ใช่เขียนตายตัวไว้ในโค้ด" — ไฟล์นี้จึงเป็นแค่ seed สำหรับ import เข้า DB
ครั้งแรกเท่านั้น โค้ดส่วนอื่นต้องอ่านจากตาราง local_authority เสมอ

ข้อมูลจุดติดต่อ (โทรศัพท์/ที่อยู่/เวลาทำการ) เป็นข้อมูลจำลองสำหรับการสาธิต
ให้ Super Admin แก้ไขผ่านหน้าจอตั้งค่าได้ภายหลัง
"""

LOCAL_AUTHORITIES: list[dict[str, str]] = [
    {"code": "PKT-PAO",  "name": "องค์การบริหารส่วนจังหวัดภูเก็ต", "kind": "อบจ.",       "district": "ทั้งจังหวัด"},
    {"code": "PKT-CITY", "name": "เทศบาลนครภูเก็ต",              "kind": "เทศบาลนคร",   "district": "เมืองภูเก็ต"},
    {"code": "KTH-TOWN", "name": "เทศบาลเมืองกะทู้",             "kind": "เทศบาลเมือง",  "district": "กะทู้"},
    {"code": "PTG-TOWN", "name": "เทศบาลเมืองป่าตอง",            "kind": "เทศบาลเมือง",  "district": "กะทู้"},
    {"code": "KRN-SUB",  "name": "เทศบาลตำบลกะรน",               "kind": "เทศบาลตำบล",  "district": "เมืองภูเก็ต"},
    {"code": "RSD-SUB",  "name": "เทศบาลตำบลรัษฎา",              "kind": "เทศบาลตำบล",  "district": "เมืองภูเก็ต"},
    {"code": "RWI-SUB",  "name": "เทศบาลตำบลราไวย์",             "kind": "เทศบาลตำบล",  "district": "เมืองภูเก็ต"},
    {"code": "WCT-SUB",  "name": "เทศบาลตำบลวิชิต",              "kind": "เทศบาลตำบล",  "district": "เมืองภูเก็ต"},
    {"code": "CLG-SUB",  "name": "เทศบาลตำบลฉลอง",               "kind": "เทศบาลตำบล",  "district": "เมืองภูเก็ต"},
    {"code": "CTL-SUB",  "name": "เทศบาลตำบลเชิงทะเล",           "kind": "เทศบาลตำบล",  "district": "ถลาง"},
    {"code": "TKS-SUB",  "name": "เทศบาลตำบลเทพกระษัตรี",        "kind": "เทศบาลตำบล",  "district": "ถลาง"},
    {"code": "SST-SUB",  "name": "เทศบาลตำบลศรีสุนทร",           "kind": "เทศบาลตำบล",  "district": "ถลาง"},
    {"code": "PKL-SUB",  "name": "เทศบาลตำบลป่าคลอก",            "kind": "เทศบาลตำบล",  "district": "ถลาง"},
    {"code": "KKW-SAO",  "name": "องค์การบริหารส่วนตำบลเกาะแก้ว",   "kind": "อบต.",       "district": "เมืองภูเก็ต"},
    {"code": "TKS-SAO",  "name": "องค์การบริหารส่วนตำบลเทพกระษัตรี", "kind": "อบต.",      "district": "ถลาง"},
    {"code": "CTL-SAO",  "name": "องค์การบริหารส่วนตำบลเชิงทะเล",   "kind": "อบต.",       "district": "ถลาง"},
    {"code": "MKW-SAO",  "name": "องค์การบริหารส่วนตำบลไม้ขาว",     "kind": "อบต.",       "district": "ถลาง"},
    {"code": "SKU-SAO",  "name": "องค์การบริหารส่วนตำบลสาคู",       "kind": "อบต.",       "district": "ถลาง"},
    {"code": "KML-SAO",  "name": "องค์การบริหารส่วนตำบลกมลา",       "kind": "อบต.",       "district": "กะทู้"},
]

assert len(LOCAL_AUTHORITIES) == 19, "โจทย์กำหนดให้รองรับ อปท. 19 แห่ง"

# ---------------------------------------------------------------------------
# ลิงก์แผนที่ของสำนักงานแต่ละแห่ง (M4: "ต้องไปติดต่อที่ไหน")
#
# แยกออกจากตารางข้างบนเพื่อให้ตารางยังอ่านเป็นตารางได้ และเป็นแค่ค่าตั้งต้น
# เหมือนข้อมูลอื่นในไฟล์นี้ — Super Admin แก้ในฐานข้อมูลได้โดยไม่ต้องแก้โค้ด
#
# ใช้รูปแบบ place_id เพราะหมุดไม่ขยับตามการแก้ชื่อหรือที่อยู่ ต่างจากลิงก์ที่ฝัง
# พิกัดหรือคำค้น และหน้าเว็บใช้ place_id เดียวกันนี้ฝังแผนที่ในหน้าได้ด้วย
# (ดู frontend/src/lib/maps.ts)
# ---------------------------------------------------------------------------
MAP_PLACE_URL = "https://www.google.com/maps/place/?q=place_id:{place_id}"

MAP_PLACE_IDS: dict[str, str] = {
    "PKT-PAO": "ChIJXZwvpR0yUDAR1FNzcZVaeRY",
    "PKT-CITY": "ChIJn1ylaRoyUDARDsI7B08fRHM",
    "KTH-TOWN": "ChIJLQTZIV0wUDAR3m9dsfhZyiQ",
    "PTG-TOWN": "ChIJZ-PNY586UDARRE6Pfy3Jc8E",
    "KRN-SUB": "ChIJ4cy2yI0lUDAR3YVafsqykhY",
    "RSD-SUB": "ChIJUzPfXy8yUDAR3G7UI7Cu0ek",
    "RWI-SUB": "ChIJATzV66IoUDARgk_116KbpGc",
    "WCT-SUB": "ChIJbyXmyW8vUDARg-aJyd1kkQg",
    "CLG-SUB": "ChIJE6mQ9rovUDARRVFznNn1KKE",
    "CTL-SUB": "ChIJgfXJPWE3UDAR8taSOk1gr4E",
    "TKS-SUB": "ChIJQ54pSrk3UDARkouYMJmMk8Y",  # ไม่พบหมุดของเทศบาลตำบลแยกต่างหาก ใช้หมุดเดียวกับ อบต.เทพกระษัตรี
    "SST-SUB": "ChIJidyCteM2UDARZsou_C30l7w",
    "PKL-SUB": "ChIJH936-IQ2UDARiDNCKD15o74",
    "KKW-SAO": "ChIJ3Uf3ZWAxUDARZskH91tV1aA",
    "TKS-SAO": "ChIJQ54pSrk3UDARkouYMJmMk8Y",
    "CTL-SAO": "ChIJ2RKw-N05UDARXwMaDNG2DMA",
    "MKW-SAO": "ChIJ-0IQGSdGUDARvSQSDgmPWiM",
    "SKU-SAO": "ChIJEVMQDiRHUDARG8jtbdJ_OvI",
    "KML-SAO": "ChIJD20dTvo7UDARjzXEYWQOrok",
}

for _authority in LOCAL_AUTHORITIES:
    _authority["map_url"] = MAP_PLACE_URL.format(place_id=MAP_PLACE_IDS[_authority["code"]])

assert all(a.get("map_url") for a in LOCAL_AUTHORITIES), "อปท. ทุกแห่งต้องมีลิงก์แผนที่"
