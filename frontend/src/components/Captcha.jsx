import { useEffect, useState, useCallback, useRef } from "react";
import { RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

export function useCaptcha() {
  const [c, setC] = useState(null);
  const [answer, setAnswer] = useState("");
  const reload = useCallback(() => { setAnswer(""); api.get("/auth/captcha").then((r) => setC(r.data)); }, []);
  useEffect(() => { reload(); }, [reload]);
  return { captcha: c, answer, setAnswer, reload, payload: { captcha_id: c?.captcha_id || "", captcha_answer: answer } };
}

function CaptchaCanvas({ text, testId }) {
  const ref = useRef(null);
  useEffect(() => {
    const cv = ref.current;
    if (!cv || !text) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height, r = Math.random;
    const css = (n) => `rgb(${getComputedStyle(document.documentElement).getPropertyValue(n).trim().split(/\s+/).join(",")})`;
    const lt = css("--nk-brandlt"), br = css("--nk-brand");
    ctx.fillStyle = "#0d1a24"; ctx.fillRect(0, 0, W, H);
    for (let i = 0; i < 40; i++) { ctx.globalAlpha = r() * 0.35; ctx.fillStyle = lt; ctx.fillRect(r() * W, r() * H, 1.5, 1.5); }
    ctx.globalAlpha = 1;
    const chars = text.split(" ").join("  ").split("");
    ctx.font = "bold 40px 'JetBrains Mono', monospace"; ctx.textBaseline = "middle";
    let x = (W - chars.length * 19) / 2;
    chars.forEach((ch) => {
      ctx.save(); ctx.translate(x, H / 2 + (r() - 0.5) * 8); ctx.rotate((r() - 0.5) * 0.35);
      ctx.fillStyle = lt; ctx.shadowColor = br; ctx.shadowBlur = 8; ctx.fillText(ch, 0, 0); ctx.restore();
      x += 19;
    });
    for (let i = 0; i < 3; i++) {
      ctx.strokeStyle = `rgba(148,163,184,${0.25 + r() * 0.25})`; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(0, r() * H); ctx.bezierCurveTo(W * 0.3, r() * H, W * 0.6, r() * H, W, r() * H); ctx.stroke();
    }
  }, [text]);
  return <canvas ref={ref} width={300} height={80} data-testid={testId} aria-label={text} className="mx-auto h-[72px] w-full max-w-[300px] rounded-lg" />;
}

export const CaptchaField = ({ cap, testPrefix }) => (
  <div>
    <label className="mb-2 block font-display text-sm font-semibold text-slate-200">Security check</label>
    <div className="space-y-3 rounded-2xl border border-line bg-deep p-4">
      <div className="rounded-xl bg-ink p-2">
        <CaptchaCanvas text={cap.captcha?.question} testId={`${testPrefix}-captcha-canvas`} />
        <span data-testid={`${testPrefix}-captcha-question`} className="sr-only">{cap.captcha?.question}</span>
      </div>
      <div className="flex gap-2">
        <input data-testid={`${testPrefix}-captcha-input`} className="nk-input h-12 rounded-xl font-mono text-base" inputMode="numeric" required placeholder="Enter answer"
          value={cap.answer} onChange={(e) => cap.setAnswer(e.target.value)} />
        <button type="button" data-testid={`${testPrefix}-captcha-refresh`} onClick={cap.reload} title="New question"
          className="grid h-12 w-14 shrink-0 place-items-center rounded-xl border border-brand/30 bg-brand/10 text-brandlt transition-colors hover:bg-brand/20"><RefreshCw size={18} /></button>
      </div>
    </div>
  </div>
);
