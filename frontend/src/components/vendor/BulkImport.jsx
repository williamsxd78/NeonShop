import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Eye, Lock, Type, Upload, ArrowLeft, ArrowRight, Check, FileText } from "lucide-react";
import { api, errMsg, money } from "@/lib/api";
import { useSite } from "@/lib/site";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { DEFAULT_IMAGES, TagInput } from "@/components/vendor/ProductForm";

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const LABEL_RE = /^([A-Za-z][\w'’ ]{0,29}?)\s*:\s*(.+)$/;
const FIELD_SPLIT_RE = /\s+(?=[A-Z][\w'’]*(?:\s[a-z][\w'’]*)?\s*:\s)/;
const splitFields = (l) => (LABEL_RE.test(l) ? l.split(FIELD_SPLIT_RE).map((f) => f.trim()).filter(Boolean) : [l]);
export const fieldValue = (f) => { const m = f.match(LABEL_RE); return m ? m[2].trim() : f; };
const fieldLabel = (f) => f.match(LABEL_RE)?.[1].trim().toLowerCase() || "";
const NAME_LABELS = ["product", "product name", "name", "title", "item", "game", "software", "app"];
export const guessTitle = (fields) => { const i = fields.findIndex((f) => NAME_LABELS.includes(fieldLabel(f))); return i >= 0 ? [i] : []; };

export function splitBlocks(text, sep) {
  const re = sep === "blank" ? /\n\s*\n/ : sep === "dashes" ? /^\s*-{3,}\s*$/m : new RegExp(`^\\s*${esc(sep.trim())}\\s*$`, "m");
  return text.split(sep === "blank" ? re : new RegExp(re.source, "gm"))
    .map((p) => p.split("\n").map((l) => l.trim()).filter(Boolean).flatMap(splitFields)).filter((b) => b.length);
}
const makeTitle = (b, titles, prefix, n) => titles.filter((i) => i < b.length).map((i) => fieldValue(b[i])).join(" · ") || `${prefix} #${n}`;

const SEPS = [["dashes", "Line of dashes ----"], ["blank", "Empty line"], ["custom", "Custom text"]];
const Steps = ({ step }) => (
  <div className="mb-2 flex gap-2">{["Sample", "Choose fields", "Bulk upload"].map((l, i) => (
    <div key={l} className={`flex-1 rounded-full border px-2 py-1 text-center font-mono text-[10px] uppercase ${step === i ? "border-[#22C55E]/60 bg-[#22C55E]/10 text-[#4ADE80]" : step > i ? "border-[#272B29] text-[#4ADE80]" : "border-[#272B29] text-slate-500"}`}>{i + 1}. {l}</div>
  ))}</div>
);

function LinePicker({ lines, pub, setPub, titles, setTitles }) {
  return (
    <div className="max-h-[42vh] overflow-y-auto rounded-xl border border-[#272B29]" data-testid="bulk-line-picker">
      {lines.map((ln, i) => {
        const on = pub.includes(i);
        const ti = titles.indexOf(i);
        return (
          <div key={i} className={`flex items-center gap-2 border-b border-[#272B29] px-3 py-2 last:border-0 ${on ? "bg-[#22D3EE]/[0.06]" : ""}`}>
            <span className="w-6 font-mono text-[10px] text-slate-600">{i + 1}</span>
            <code className="min-w-0 flex-1 break-all text-xs text-slate-200">{ln}</code>
            <button type="button" data-testid={`bulk-line-title-${i}`} onClick={() => setTitles(ti >= 0 ? titles.filter((x) => x !== i) : [...titles, i].slice(-3))} title="Use in product name"
              className={`flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-semibold ${ti >= 0 ? "border-[#FFB800]/60 bg-[#FFB800]/15 text-[#FFB800]" : "border-[#272B29] text-slate-500"}`}><Type size={12} />{ti >= 0 ? `Name${titles.length > 1 ? ` ${ti + 1}` : ""}` : "Name"}</button>
            <button type="button" data-testid={`bulk-line-toggle-${i}`} onClick={() => setPub(on ? pub.filter((x) => x !== i) : [...pub, i].sort((a, b) => a - b))}
              className={`flex w-24 items-center justify-center gap-1 rounded-md border px-2 py-1 text-[11px] font-semibold ${on ? "border-[#22D3EE]/50 bg-[#22D3EE]/10 text-[#22D3EE]" : "border-[#272B29] text-slate-500"}`}>
              {on ? <><Eye size={12} />Public</> : <><Lock size={12} />Hidden</>}
            </button>
          </div>
        );
      })}
    </div>
  );
}

const PreviewCard = ({ b, pub, titles, prefix, n, price }) => (
  <div className="rounded-xl border border-[#272B29] bg-[#121413] p-3 pl-4 relative">
    <span className="absolute inset-y-2 left-0 w-1 rounded-r-full bg-[#22D3EE]" />
    <div className="text-sm font-semibold" data-testid={`bulk-preview-title-${n}`}>{makeTitle(b, titles, prefix, n)}</div>
    {pub.filter((i) => i < b.length && !titles.includes(i)).map((i) => <div key={i} className="truncate font-mono text-[11px] text-slate-400">{b[i]}</div>)}
    <div className="mt-1 font-mono text-sm text-[#4ADE80]">{money(price * 100)}</div>
  </div>
);

export function BulkImport({ open, onOpenChange, onDone }) {
  const [step, setStep] = useState(0);
  const [sample, setSample] = useState("");
  const [sepMode, setSepMode] = useState("dashes");
  const [custom, setCustom] = useState("");
  const [pub, setPub] = useState([]);
  const [titles, setTitles] = useState([]);
  const { categories: CATEGORIES } = useSite();
  const [meta, setMeta] = useState({ title_prefix: "Item", category: "", price: "", image: "", tags: [], deliver: "all" });
  const [bulk, setBulk] = useState("");
  const [busy, setBusy] = useState(false);
  const sep = sepMode === "custom" ? custom : sepMode;
  const lines = useMemo(() => splitBlocks(sample, sep)[0] || [], [sample, sep]);
  const cat = meta.category || CATEGORIES[0] || "";
  const blocks = useMemo(() => (bulk.trim() && sep ? splitBlocks(bulk, sep) : []), [bulk, sep]);
  const odd = blocks.filter((b) => b.length !== lines.length).length;

  const reset = () => { setStep(0); setSample(""); setPub([]); setTitles([]); setBulk(""); };
  const close = (o) => { onOpenChange(o); if (!o) reset(); };
  const readFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 3_000_000) return toast.error("File too large (max 3MB)");
    const r = new FileReader();
    r.onload = () => { setBulk(String(r.result).replace(/\r\n/g, "\n")); toast.success(`Loaded ${f.name}`); };
    r.readAsText(f);
  };
  const submit = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/vendor/products/bulk", { text: bulk, separator: sep, public_lines: pub, title_lines: titles, ...meta, category: cat, price: parseFloat(meta.price), image: meta.image || null });
      toast.success(`${data.created} products imported${data.skipped ? `, ${data.skipped} duplicates skipped` : ""}`);
      close(false); onDone();
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const setM = (k) => (e) => setMeta({ ...meta, [k]: e.target.value });

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-h-[94vh] overflow-y-auto border-[#272B29] bg-[#0E100F] sm:max-w-2xl" data-testid="bulk-import-dialog">
        <DialogHeader>
          <DialogTitle className="font-display">Bulk import</DialogTitle>
          <DialogDescription>Each item in your file becomes its own listing. Buyers only see the lines you mark Public until they buy.</DialogDescription>
        </DialogHeader>
        <Steps step={step} />

        {step === 0 && (
          <div className="space-y-4">
            <div>
              <label className="nk-label">How are items separated?</label>
              <div className="flex flex-wrap gap-2">{SEPS.map(([v, l]) => (
                <button type="button" key={v} data-testid={`bulk-sep-${v}`} onClick={() => setSepMode(v)}
                  className={`rounded-lg border px-3 py-2 text-xs font-semibold ${sepMode === v ? "border-[#22C55E]/60 bg-[#22C55E]/10 text-[#4ADE80]" : "border-[#272B29] text-slate-400"}`}>{l}</button>
              ))}</div>
              {sepMode === "custom" && <input data-testid="bulk-sep-custom-input" className="nk-input mt-2 font-mono" placeholder="e.g. ===== or #END" value={custom} onChange={(e) => setCustom(e.target.value)} />}
            </div>
            <div>
              <label className="nk-label">Paste one example item</label>
              <textarea data-testid="bulk-sample-input" className="nk-input min-h-[220px] font-mono text-xs" value={sample} onChange={(e) => setSample(e.target.value)}
                placeholder={"Product: Example Pro License\nPlan: Yearly\nRegion: Global\nLicense key: XXXX-XXXX-XXXX\nActivation: Account > Licenses > Activate"} />
              <p className="mt-1 text-[11px] text-slate-500" data-testid="bulk-sample-count">{lines.length} fields detected{lines.length ? `: ${lines.map((l) => l.match(LABEL_RE)?.[1] || "text").join(" · ")}` : ""}</p>
            </div>
            <button data-testid="bulk-next-1" disabled={!lines.length} onClick={() => { if (!titles.length) setTitles(guessTitle(lines)); setStep(1); }} className="nk-btn-primary w-full">Next: choose what buyers see <ArrowRight size={16} /></button>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <p className="text-xs text-slate-400">Tap <b className="text-[#FFB800]">Name</b> on the field that holds the product name (pick up to 3, e.g. Product + Plan). Mark fields buyers can see before buying as <b className="text-[#22D3EE]">Public</b>.</p>
            <LinePicker lines={lines} pub={pub} setPub={setPub} titles={titles} setTitles={setTitles} />
            <div className="rounded-lg border border-[#FFB800]/25 bg-[#FFB800]/[0.05] px-3 py-2 text-xs" data-testid="bulk-name-preview">
              <span className="text-slate-500">Product name: </span>
              {titles.length ? <b className="text-slate-100">{makeTitle(lines, titles, meta.title_prefix, 1)}</b> : <span className="text-[#FFB800]">No name field selected, so items will be named "{meta.title_prefix} #1, #2…"</span>}
            </div>
            <div>
              <label className="nk-label">After purchase the buyer receives</label>
              <div className="grid grid-cols-2 gap-2">{[["all", "All lines (full item)"], ["hidden", "Only the hidden lines"]].map(([v, l]) => (
                <button type="button" key={v} data-testid={`bulk-deliver-${v}`} onClick={() => setMeta({ ...meta, deliver: v })}
                  className={`rounded-lg border px-3 py-2 text-xs font-semibold ${meta.deliver === v ? "border-[#A855F7]/60 bg-[#A855F7]/10 text-[#C084FC]" : "border-[#272B29] text-slate-400"}`}>{l}</button>
              ))}</div>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {!titles.length && <div><label className="nk-label">Title prefix</label><input data-testid="bulk-title-prefix" className="nk-input" value={meta.title_prefix} onChange={setM("title_prefix")} /></div>}
              <div><label className="nk-label">Category</label><select data-testid="bulk-category" className="nk-input" value={cat} onChange={setM("category")}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select></div>
              <div><label className="nk-label">Price each (USD)</label><input data-testid="bulk-price" className="nk-input font-mono" type="number" min="0.01" step="0.01" value={meta.price} onChange={setM("price")} /></div>
            </div>
            <div><label className="nk-label">Tags</label><TagInput tags={meta.tags} onChange={(tags) => setMeta({ ...meta, tags })} /></div>
            <div>
              <label className="nk-label">Cover image (empty = category default)</label>
              <div className="flex gap-2">{DEFAULT_IMAGES.map((u, i) => (
                <button type="button" key={u} data-testid={`bulk-image-${i}`} onClick={() => setMeta({ ...meta, image: meta.image === u ? "" : u })}
                  className={`h-11 w-14 overflow-hidden rounded-md border-2 ${meta.image === u ? "border-[#22C55E]" : "border-transparent opacity-60"}`}><img src={u} alt="" className="h-full w-full object-cover" /></button>
              ))}</div>
            </div>
            <div className="flex gap-2">
              <button data-testid="bulk-back-1" onClick={() => setStep(0)} className="nk-btn-ghost"><ArrowLeft size={16} />Back</button>
              <button data-testid="bulk-next-2" disabled={!pub.length || !(parseFloat(meta.price) > 0)} onClick={() => setStep(2)} className="nk-btn-primary flex-1"><Check size={16} />Confirm selection</button>
            </div>
            {!pub.length && <p className="text-[11px] text-[#FFB800]">Select at least one public field.</p>}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="nk-label mb-0">Paste all items or upload a file</label>
              <label className="nk-btn-ghost nk-btn-sm cursor-pointer"><Upload size={14} />.txt / .csv<input data-testid="bulk-file-input" type="file" accept=".txt,.csv,text/plain" className="hidden" onChange={readFile} /></label>
            </div>
            <textarea data-testid="bulk-data-input" className="nk-input min-h-[200px] font-mono text-xs" value={bulk} onChange={(e) => setBulk(e.target.value)} placeholder={"item 1 lines…\n--------------------------------------------------\nitem 2 lines…"} />
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span data-testid="bulk-detected-count" className="flex items-center gap-1 font-mono text-[#4ADE80]"><FileText size={13} />{blocks.length} items detected</span>
              {odd > 0 && <span data-testid="bulk-odd-warning" className="text-[#FFB800]">{odd} item(s) have a different line count than the sample. Check them before importing.</span>}
            </div>
            {blocks.length > 0 && (
              <div><div className="nk-label">Preview: what buyers will see</div>
                <div className="grid gap-2 sm:grid-cols-3" data-testid="bulk-preview">{blocks.slice(0, 3).map((b, i) => <PreviewCard key={i} b={b} n={i + 1} pub={pub} titles={titles} prefix={meta.title_prefix} price={parseFloat(meta.price)} />)}</div>
              </div>
            )}
            <div className="flex gap-2">
              <button data-testid="bulk-back-2" onClick={() => setStep(1)} className="nk-btn-ghost"><ArrowLeft size={16} />Back</button>
              <button data-testid="bulk-submit-btn" disabled={busy || !blocks.length} onClick={submit} className="nk-btn-primary flex-1">{busy ? "Importing…" : `Import ${blocks.length} products`}</button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
