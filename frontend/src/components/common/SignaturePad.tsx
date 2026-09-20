"use client";

import { Eraser, ImageUp, PenLine, Save } from "lucide-react";
import { type PointerEvent as ReactPointerEvent, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * ช่องลงลายมือชื่อ — วาดบนจอ หรืออัปโหลดรูปลายเซ็นที่เซ็นบนกระดาษมาแล้ว
 *
 * มีสองทางเสมอโดยตั้งใจ: การวาดด้วยเมาส์ทำได้ยากสำหรับบางคน และผู้ที่ใช้
 * คีย์บอร์ดอย่างเดียววาดไม่ได้เลย (NFR Accessibility) ทางอัปโหลดจึงไม่ใช่
 * ของแถม แต่เป็นทางหลักอีกทางหนึ่ง
 *
 * ผลลัพธ์เป็น PNG พื้นหลังโปร่งเสมอ เพื่อให้วางทับเส้นลงชื่อในแบบฟอร์มได้
 * โดยไม่บังเส้น ฝั่งเซิร์ฟเวอร์รับเฉพาะ image/png ตาม accepted_mime ของ A01
 */

// ขนาดจริงของภาพที่บันทึก (พิกเซล) — กว้างพอให้ลายเส้นคมตอนพิมพ์ลงกระดาษ
const WIDTH = 900;
const HEIGHT = 300;
const STROKE = 3.5;

type Props = {
  /** โยน error ออกมาได้ คอมโพเนนต์แม่เป็นผู้แสดงข้อความ */
  onSave: (png: Blob) => Promise<void>;
  /** ข้อความบนปุ่ม — ฝั่งเจ้าหน้าที่ใช้ "ลงนามและออกเอกสาร" เพราะเซ็นคือการออกเอกสาร */
  saveLabel?: string;
  disabled?: boolean;
  className?: string;
};

export function SignaturePad({ onSave, saveLabel = "บันทึกลายมือชื่อ", disabled, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawing = useRef(false);
  const [hasInk, setHasInk] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function context(): CanvasRenderingContext2D | null {
    const ctx = canvasRef.current?.getContext("2d") ?? null;
    if (ctx) {
      ctx.lineWidth = STROKE;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.strokeStyle = "#0D2344"; // หมึกสีน้ำเงินเข้มเหมือนปากกาจริง
    }
    return ctx;
  }

  /** แปลงตำแหน่งบนหน้าจอเป็นพิกัดในภาพ — ผืนผ้าใบถูกย่อด้วย CSS จึงต้องคูณกลับ */
  function pointOf(e: ReactPointerEvent<HTMLCanvasElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * WIDTH,
      y: ((e.clientY - rect.top) / rect.height) * HEIGHT,
    };
  }

  function start(e: ReactPointerEvent<HTMLCanvasElement>) {
    if (disabled) return;
    const ctx = context();
    if (!ctx) return;
    // จับ pointer ไว้ เพื่อให้ลากเลยขอบผืนผ้าใบแล้วเส้นไม่ขาดกลางคัน
    e.currentTarget.setPointerCapture(e.pointerId);
    drawing.current = true;
    const { x, y } = pointOf(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
  }

  function move(e: ReactPointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) return;
    const ctx = context();
    if (!ctx) return;
    const { x, y } = pointOf(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    if (!hasInk) setHasInk(true);
  }

  function end() {
    drawing.current = false;
  }

  function clear() {
    const canvas = canvasRef.current;
    canvas?.getContext("2d")?.clearRect(0, 0, WIDTH, HEIGHT);
    setHasInk(false);
    setError(null);
  }

  /** วางรูปที่อัปโหลดลงผืนผ้าใบแบบย่อให้พอดี แล้วปล่อยให้บันทึกเป็น PNG เส้นทางเดียวกัน */
  function drawUploadedImage(file: File) {
    setError(null);
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      const ctx = context();
      if (ctx) {
        ctx.clearRect(0, 0, WIDTH, HEIGHT);
        const scale = Math.min(WIDTH / img.width, HEIGHT / img.height);
        const w = img.width * scale;
        const h = img.height * scale;
        ctx.drawImage(img, (WIDTH - w) / 2, (HEIGHT - h) / 2, w, h);
        setHasInk(true);
      }
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      setError("เปิดไฟล์รูปนี้ไม่ได้ กรุณาเลือกไฟล์ JPG หรือ PNG");
    };
    img.src = url;
  }

  async function save() {
    const canvas = canvasRef.current;
    if (!canvas || !hasInk) return;
    setError(null);
    setPending(true);
    try {
      const png = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, "image/png"),
      );
      if (!png) throw new Error("blob");
      await onSave(png);
    } catch (err) {
      setError(
        err instanceof Error && err.message !== "blob"
          ? err.message
          : "บันทึกลายมือชื่อไม่สำเร็จ กรุณาลองใหม่อีกครั้ง",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className={className}>
      <canvas
        ref={canvasRef}
        width={WIDTH}
        height={HEIGHT}
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerLeave={end}
        aria-label="พื้นที่วาดลายมือชื่อ ลากเมาส์หรือใช้นิ้ววาด หรือเลือกอัปโหลดรูปลายเซ็นแทนได้"
        className={cn(
          "block aspect-3/1 w-full touch-none rounded-xl border-2 border-dashed border-brand-200 bg-white",
          disabled ? "cursor-not-allowed opacity-60" : "cursor-crosshair",
        )}
      />

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={save}
          disabled={disabled || pending || !hasInk}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-brand-500 px-4 py-2.5 font-semibold text-white hover:bg-brand-400 disabled:opacity-50"
        >
          <Save className="size-4" aria-hidden />
          {pending ? "กำลังบันทึก…" : saveLabel}
        </button>

        <button
          type="button"
          onClick={clear}
          disabled={disabled || pending || !hasInk}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-line px-4 py-2.5 font-semibold text-ink hover:bg-canvas disabled:opacity-50"
        >
          <Eraser className="size-4" aria-hidden />
          ล้าง
        </button>

        <label
          className={cn(
            "inline-flex min-h-11 items-center gap-2 rounded-xl border border-line px-4 py-2.5 font-semibold text-ink hover:bg-canvas",
            (disabled || pending) && "pointer-events-none opacity-50",
          )}
        >
          <ImageUp className="size-4" aria-hidden />
          อัปโหลดรูปลายเซ็น
          <input
            type="file"
            accept="image/png,image/jpeg"
            className="sr-only"
            disabled={disabled || pending}
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) drawUploadedImage(file);
              // ล้างค่าเพื่อให้เลือกไฟล์เดิมซ้ำแล้วยังทำงาน
              e.target.value = "";
            }}
          />
        </label>
      </div>

      <p className="mt-2 flex items-start gap-1.5 text-xs text-ink-muted">
        <PenLine className="mt-0.5 size-3.5 shrink-0" aria-hidden />
        เซ็นด้วยเมาส์ นิ้ว หรือปากกาสไตลัสก็ได้ ถ้าเซ็นบนกระดาษไว้แล้ว
        ให้ถ่ายรูปแล้วกดอัปโหลดรูปลายเซ็นแทน
      </p>

      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger-fg">
          {error}
        </p>
      )}
    </div>
  );
}
