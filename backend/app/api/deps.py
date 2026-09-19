"""FastAPI dependencies ที่ใช้ร่วมกัน — auth, role guard, scope ของท้องถิ่น"""

# TODO: get_current_user(token)              -> ผู้ใช้ปัจจุบันจาก JWT
# TODO: require_role(*roles)                 -> guard ตามบทบาท (NFR: RBAC)
# TODO: require_same_authority(application)  -> guard T-09 + เขียน AuditLog เมื่อถูกปฏิเสธ
