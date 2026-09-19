# ตั้งค่า Git สำหรับทีม 3 คนที่ใช้เครื่องเดียวกัน
#
# ปัญหา: ถ้า commit ปกติ ทุก commit จะขึ้นชื่อเจ้าของเครื่องคนเดียว
#        กรรมการเปิด repo แล้วจะเห็นว่ามีคนทำคนเดียว -> เสียคะแนนเกณฑ์ข้อ 4
# วิธีแก้: ระบุ --author เป็นคนที่กำลังจับคีย์บอร์ด (driver)
#        และใส่ Co-authored-by ให้คนที่นั่งข้าง ๆ (navigator)
#
# วิธีใช้หลังรันสคริปต์นี้:
#   git ca a -m "feat: wizard classification endpoint"
#   git ca b -m "feat: document list page"
#
# ตรวจผลว่าขึ้นครบ 3 คนไหม:
#   git shortlog -sn

$ErrorActionPreference = "Stop"

# ---------- แก้ 3 บรรทัดนี้เป็นชื่อ-อีเมลจริงของสมาชิก ----------
$A = "Member A <member-a@example.com>"
$B = "Member B <member-b@example.com>"
$C = "Member C <member-c@example.com>"
# ---------------------------------------------------------------

git config alias.ca '!f(){ who=$1; shift; case "$who" in a) au="'"$A"'";; b) au="'"$B"'";; c) au="'"$C"'";; *) echo "ใช้: git ca {a|b|c} -m \"ข้อความ\""; return 1;; esac; git commit --author="$au" "$@"; }; f'
git config alias.who "shortlog -sn --no-merges"

Write-Host "ตั้งค่าเรียบร้อย" -ForegroundColor Green
Write-Host '  git ca a -m "ข้อความ"   commit ในชื่อสมาชิก A'
Write-Host '  git who                 ดูว่าแต่ละคน commit ไปกี่ครั้ง'
