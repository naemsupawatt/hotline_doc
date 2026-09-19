import type { Metadata } from "next";

import { ReviewView } from "./ReviewView";

export const metadata: Metadata = {
  title: "ตรวจคำขอ",
  description: "ตรวจเอกสารรายฉบับและบันทึกผลการพิจารณา",
};

export default async function OfficerReviewPage({
  params,
}: {
  params: Promise<{ no: string }>;
}) {
  const { no } = await params;
  return <ReviewView applicationNo={decodeURIComponent(no)} />;
}
