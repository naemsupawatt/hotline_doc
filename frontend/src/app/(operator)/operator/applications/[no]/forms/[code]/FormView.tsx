"use client";

import { Fill, Item, SystemFormPaper, Tick } from "@/components/common/SystemFormPaper";
import { Mascot } from "@/components/brand/Mascot";
import { ACCOMMODATION_KINDS } from "@/lib/applications";
import {
  HOTEL_FORM_CODE,
  NOTICE_FORM_CODE,
  type SystemForm,
  formatJuristicNo,
} from "@/lib/systemForm";

/**
 * M3/M5 — หน้ากระดาษของแบบฟอร์มที่ระบบกรอกให้
 *
 * เส้นทางเดียวรองรับทั้งสองฉบับ เพราะทุกอย่างรอบ ๆ เหมือนกันหมด (ดู
 * components/common/SystemFormPaper.tsx) ต่างกันแค่ข้อความในแบบฟอร์ม
 * ไฟล์นี้จึงมีแต่ "เนื้อความบนกระดาษ" ของแต่ละฉบับ
 *
 * ตั้งใจไม่พิมพ์เกณฑ์ตัวเลข (ไม่เกินกี่ห้อง กี่คน) ลงบนกระดาษ เพราะเกณฑ์อยู่ใน
 * ฐานข้อมูลและ Super Admin แก้ได้ (US-09) ถ้าพิมพ์ตัวเลขตายตัวลงแบบฟอร์ม
 * วันที่เกณฑ์เปลี่ยน เอกสารจะพูดไม่ตรงกับกฎที่ระบบใช้จริง
 */
export function FormView({ applicationNo, code }: { applicationNo: string; code: string }) {
  const upper = code.toUpperCase();

  if (upper === NOTICE_FORM_CODE) {
    return (
      <SystemFormPaper
        applicationNo={applicationNo}
        code={NOTICE_FORM_CODE}
        signerLabel="ผู้แจ้ง"
        body={noticeBody}
      />
    );
  }

  if (upper === HOTEL_FORM_CODE) {
    return (
      <SystemFormPaper
        applicationNo={applicationNo}
        code={HOTEL_FORM_CODE}
        signerLabel="ผู้ขออนุญาต"
        body={hotelBody}
      />
    );
  }

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center">
      <Mascot pose="support" size="md" className="mx-auto w-40" />
      <h1 className="mt-6 text-2xl font-bold text-ink">ไม่มีแบบฟอร์มรหัสนี้</h1>
      <p className="mt-2 text-ink-muted">
        ระบบมีหน้ากระดาษให้เฉพาะแบบหนังสือแจ้งฯ ({NOTICE_FORM_CODE}) และแบบ ร.ร.1 (
        {HOTEL_FORM_CODE})
      </p>
    </main>
  );
}

/** A01 — แบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม */
function noticeBody(form: SystemForm) {
  const { applicant, property } = form;
  return (
    <>
      <ApplicantLines form={form} />

      <p className="pt-2">
        ขอแจ้งต่อ{form.local_authority_name} ว่าข้าพเจ้าประกอบกิจการสถานที่พัก
        ซึ่งไม่เข้าข่ายเป็นโรงแรมตามที่กฎหมายกำหนด โดยมีรายละเอียดดังนี้
      </p>

      <ol className="space-y-3">
        <Item no={1} label="ชื่อสถานที่พัก">
          <Fill value={property.name} className="min-w-72" />
        </Item>

        <Item no={2} label="ที่ตั้ง">
          <AddressFields form={form} />
        </Item>

        <Item no={3} label="ลักษณะของสถานที่พัก">
          <span className="inline-flex flex-wrap items-center gap-x-5 gap-y-2">
            {ACCOMMODATION_KINDS.map((kind) => (
              <Tick
                key={kind.value}
                checked={property.accommodation_kind === kind.value}
                label={
                  kind.value === "other" && property.accommodation_kind === "other"
                    ? `อื่น ๆ (${property.accommodation_kind_other ?? "-"})`
                    : kind.label
                }
              />
            ))}
          </span>
        </Item>

        <Item no={4} label="จำนวนห้องพัก">
          <Fill value={property.room_count.toLocaleString("th-TH")} className="min-w-20" /> ห้อง
          <span className="ms-6">
            จำนวนผู้พักที่รับได้{" "}
            <Fill value={property.max_guests.toLocaleString("th-TH")} className="min-w-20" /> คน
          </span>
        </Item>
      </ol>

      <p className="pt-2">
        ข้าพเจ้าขอรับรองว่าข้อความและเอกสารที่ยื่นพร้อมหนังสือฉบับนี้เป็นความจริงทุกประการ
        {applicant.is_juristic && " และข้าพเจ้ามีอำนาจลงนามแทนนิติบุคคลข้างต้น"}
      </p>
    </>
  );
}

/** A06 — แบบ ร.ร.1 คำขอรับใบอนุญาตประกอบธุรกิจโรงแรม */
function hotelBody(form: SystemForm) {
  const { property } = form;
  return (
    <>
      <ApplicantLines form={form} />

      <p className="pt-2">
        ขอยื่นคำขอรับใบอนุญาตประกอบธุรกิจโรงแรมต่อ{form.local_authority_name} โดยมีรายละเอียดดังนี้
      </p>

      <ol className="space-y-3">
        <Item no={1} label="ชื่อโรงแรม">
          <Fill value={property.name} className="min-w-72" />
        </Item>

        <Item no={2} label="ที่ตั้ง">
          <AddressFields form={form} />
        </Item>

        <Item no={3} label="ประเภทที่ขออนุญาต">
          <Fill value={form.property_type_name} className="min-w-64" />
        </Item>

        <Item no={4} label="ขนาดของโรงแรม">
          จำนวนห้องพัก{" "}
          <Fill value={property.room_count.toLocaleString("th-TH")} className="min-w-20" /> ห้อง
          <span className="ms-6">
            รับผู้เข้าพักได้{" "}
            <Fill value={property.max_guests.toLocaleString("th-TH")} className="min-w-20" /> คน
          </span>
        </Item>

        <Item no={5} label="ห้องอาหาร">
          <span className="inline-flex flex-wrap items-center gap-x-5">
            <Tick checked={property.has_restaurant} label="มีห้องอาหารหรือสถานที่บริการอาหาร" />
            <Tick checked={!property.has_restaurant} label="ไม่มี" />
          </span>
        </Item>

        {form.fee && (
          <Item no={6} label="ค่าธรรมเนียมใบอนุญาต">
            <Fill
              value={`${form.fee.amount.toLocaleString("th-TH")} บาท`}
              className="min-w-32"
            />
            <span>ต่อ {form.fee.validity_years} ปี</span>
          </Item>
        )}
      </ol>

      {/* ช่องแนบที่อยู่ในตัวแบบ ร.ร.1 ระบบติ๊กให้จากไฟล์ที่แนบมาแล้ว */}
      <div className="pt-2">
        <p className="font-medium">พร้อมคำขอนี้ ข้าพเจ้าได้แนบเอกสารดังต่อไปนี้</p>
        <ul className="mt-2 space-y-2 ps-6">
          {form.attachments.map((item) => (
            <li key={item.code}>
              <Tick checked={item.is_attached} label={`${item.code} ${item.name_th}`} />
            </li>
          ))}
          {form.attachments.length === 0 && (
            <li className="text-ink-muted">ไม่มีเอกสารแนบในแบบฟอร์มฉบับนี้</li>
          )}
        </ul>
        <p className="mt-2 text-sm text-ink-muted print:hidden">
          ช่องเหล่านี้ระบบติ๊กให้เองจากไฟล์ที่แนบไว้ในหน้าคำขอ ไม่ต้องติ๊กเอง
        </p>
      </div>

      <p className="pt-2">
        ข้าพเจ้าขอรับรองว่าข้อความและเอกสารที่ยื่นพร้อมคำขอนี้เป็นความจริงทุกประการ
        {form.applicant.is_juristic && " และข้าพเจ้ามีอำนาจลงนามแทนนิติบุคคลข้างต้น"}
      </p>
    </>
  );
}

function ApplicantLines({ form }: { form: SystemForm }) {
  const { applicant } = form;
  return (
    <>
      <p>
        ข้าพเจ้า <Fill value={applicant.display_name} className="min-w-64" />
        {applicant.is_juristic ? (
          <>
            {" "}
            ทะเบียนนิติบุคคลเลขที่{" "}
            <Fill value={formatJuristicNo(applicant.juristic_reg_no)} />
          </>
        ) : (
          <>
            {" "}
            เลขประจำตัวประชาชน <Fill value={applicant.national_id_masked} />
          </>
        )}
      </p>
      <p>
        โทรศัพท์ <Fill value={applicant.phone} /> อีเมล{" "}
        <Fill value={applicant.email} className="min-w-56" />
      </p>
    </>
  );
}

function AddressFields({ form }: { form: SystemForm }) {
  const a = form.property.address;
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2">
      <span>
        เลขที่ <Fill value={a.address_no} className="min-w-24" />
      </span>
      <span>
        หมู่ที่ <Fill value={a.moo} className="min-w-14" />
      </span>
      <span>
        ซอย <Fill value={a.soi} className="min-w-28" />
      </span>
      <span>
        ถนน <Fill value={a.road} className="min-w-28" />
      </span>
      <span>
        ตำบล <Fill value={a.sub_district} className="min-w-32" />
      </span>
      <span>
        อำเภอ <Fill value={a.district} className="min-w-32" />
      </span>
      <span>
        จังหวัด <Fill value={a.province} className="min-w-28" />
      </span>
      <span>
        รหัสไปรษณีย์ <Fill value={a.postal_code} className="min-w-20" />
      </span>
    </span>
  );
}
