import { useEffect, useState, useCallback } from "react";
import { RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

export function useCaptcha() {
  const [c, setC] = useState(null);
  const [answer, setAnswer] = useState("");
  const reload = useCallback(() => { setAnswer(""); api.get("/auth/captcha").then((r) => setC(r.data)); }, []);
  useEffect(() => { reload(); }, [reload]);
  return { captcha: c, answer, setAnswer, reload, payload: { captcha_id: c?.captcha_id || "", captcha_answer: answer } };
}

export const CaptchaField = ({ cap, testPrefix }) => (
  <div>
    <label className="nk-label">Security check</label>
    <div className="flex items-center gap-2">
      <div data-testid={`${testPrefix}-captcha-question`} className="flex h-[42px] min-w-[120px] items-center justify-center gap-2 rounded-lg border border-[#22C55E]/30 bg-[#22C55E]/10 px-3 font-mono text-base font-semibold text-[#4ADE80] select-none">
        <ShieldCheck size={15} />{cap.captcha?.question || "…"}
      </div>
      <input data-testid={`${testPrefix}-captcha-input`} className="nk-input font-mono" inputMode="numeric" required placeholder="Answer"
        value={cap.answer} onChange={(e) => cap.setAnswer(e.target.value)} />
      <button type="button" data-testid={`${testPrefix}-captcha-refresh`} onClick={cap.reload} title="New question"
        className="grid h-[42px] w-[42px] shrink-0 place-items-center rounded-lg border border-[#272B29] bg-[#121413] text-slate-400 hover:text-white"><RefreshCw size={15} /></button>
    </div>
  </div>
);
