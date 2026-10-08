"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Upload,
  FileText,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Play,
  Download,
  MapPin,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { Notice } from "@/components/ui/Notice";
import { StatCard } from "@/components/ui/StatCard";
import { EpCurveChart } from "@/components/charts/EpCurveChart";
import { DepthDamageChart } from "@/components/charts/DepthDamageChart";
import { HeavyRainCallout } from "@/components/charts/HeavyRainCallout";
import { resolveDepthDamage } from "@/lib/depth-damage";
import {
  createBuiltinPortfolio,
  createRun,
  fetchHealth,
  uploadPortfolio,
  type CreateRunResponse,
  type PortfolioPayload,
} from "@/lib/api";
import { formatKes } from "@/lib/format";
import { heavyRainLosses, resolveEpMetrics } from "@/lib/ep-metrics";
import { loadLastTestRun, saveLastTestRun, type LastTestRun } from "@/lib/run-store";

type Phase =
  | "idle"
  | "uploading"
  | "running"
  | "done"
  | "error";

const PIPELINE_STEPS = [
  "Check data",
  "Flood scores",
  "Damage & loss",
  "Risk figures",
  "Briefing",
];

export default function DataStartPage() {
  const [file, setFile] = useState<File | null>(null);
  const [place, setPlace] = useState("Kisumu");
  const [portfolioName, setPortfolioName] = useState("");
  const [notes, setNotes] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState("");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [modelsReady, setModelsReady] = useState<boolean | null>(null);
  const [result, setResult] = useState<LastTestRun | null>(null);

  useEffect(() => {
    setResult(loadLastTestRun());
    fetchHealth().then((h) => {
      setApiOk(Boolean(h));
      setModelsReady(Boolean(h?.registry?.registry_ready));
    });
  }, []);

  async function runPipeline(
    portfolio: PortfolioPayload,
    placeLabel: string,
  ): Promise<CreateRunResponse> {
    setPhase("running");
    setStatusMsg(
      "Running the full flood pipeline (hazard → damage → loss → risk). Please wait 30–60 seconds — do not refresh…",
    );
    const runResult = await createRun(portfolio.id);
    const saved = saveLastTestRun(placeLabel, portfolio, runResult);
    setResult(saved);
    setPhase("done");
    setStatusMsg(`Pipeline finished · status ${runResult.run.status}`);
    return runResult;
  }

  async function onUploadAndRun() {
    setError("");
    if (!file) {
      setError("Choose a CSV portfolio file first.");
      return;
    }
    if (!place.trim()) {
      setError("Enter the place this portfolio belongs to (e.g. Kisumu, Mombasa).");
      return;
    }

    try {
      setPhase("uploading");
      setStatusMsg(`Uploading portfolio for ${place.trim()}…`);
      const { portfolio, warnings } = await uploadPortfolio({
        file,
        locationLabel: place.trim(),
        name: portfolioName.trim() || undefined,
      });
      if (warnings?.length) {
        setStatusMsg(`Uploaded with notes: ${warnings.slice(0, 2).join(" · ")}`);
      }
      await runPipeline(portfolio, place.trim());
    } catch (err) {
      setPhase("error");
      setError(err instanceof Error ? err.message : String(err));
      setStatusMsg("");
    }
  }

  async function onRunBuiltin() {
    setError("");
    try {
      setPhase("uploading");
      setStatusMsg("Loading built-in Nairobi demo portfolio…");
      setPlace("Nairobi County");
      const { portfolio } = await createBuiltinPortfolio({
        locationLabel: "Nairobi County",
        name: "Nairobi built-in (synthetic)",
      });
      await runPipeline(portfolio, "Nairobi County");
    } catch (err) {
      setPhase("error");
      setError(err instanceof Error ? err.message : String(err));
      setStatusMsg("");
    }
  }

  const busy = phase === "uploading" || phase === "running";
  const resultEp = result
    ? resolveEpMetrics(result.metrics, {
        runId: result.runId,
        locationLabel: result.place,
      })
    : null;
  const resultHeavy = resultEp ? heavyRainLosses(resultEp.points) : null;
  const resultDd = result ? resolveDepthDamage(result.metrics) : null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data · Start"
        title="Bring in risk information"
        question="Upload a portfolio for any place to test the full FLOODTAIL pipeline end to end."
      >
        <div className="flex flex-wrap gap-2 text-xs">
          <span
            className={`chip ${apiOk ? "text-risk" : apiOk === false ? "text-rose-300" : ""}`}
          >
            API {apiOk == null ? "…" : apiOk ? "online" : "offline"}
          </span>
          <span
            className={`chip ${modelsReady ? "text-risk" : modelsReady === false ? "text-amber-300" : ""}`}
          >
            Models {modelsReady == null ? "…" : modelsReady ? "ready" : "not pinned"}
          </span>
        </div>
      </PageHeader>

      <Notice>
        <strong className="text-white">Test mode.</strong> Upload a CSV for another
        place (or download the Kisumu sample), then run the whole chain: check data →
        flood scores → damage → loss → risk figures. Results are labelled synthetic.
        Keep the API running on port 8000.
      </Notice>

      <FlowSteps
        accent="data"
        steps={[
          { label: "Original data" },
          { label: "Standardised" },
          { label: "Enriched" },
          { label: "Full pipeline run" },
        ]}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass rounded-2xl p-6">
          <h2 className="section-title mb-4">Upload a portfolio & run pipeline</h2>

          <label className="mb-3 block text-xs font-medium text-white/60">
            Place / location
            <div className="relative mt-1.5">
              <MapPin className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-data" />
              <input
                className="input-field !pl-10"
                placeholder="e.g. Kisumu, Mombasa, Nakuru"
                value={place}
                onChange={(e) => setPlace(e.target.value)}
                disabled={busy}
              />
            </div>
          </label>

          <label className="mb-4 block text-xs font-medium text-white/60">
            Portfolio name (optional)
            <input
              className="input-field mt-1.5"
              placeholder="e.g. Kisumu demo book"
              value={portfolioName}
              onChange={(e) => setPortfolioName(e.target.value)}
              disabled={busy}
            />
          </label>

          <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-data/40 bg-data-soft px-6 py-10 text-center transition hover:border-data">
            <Upload className="mb-3 h-8 w-8 text-data" />
            <span className="text-sm font-medium text-white">
              Drop a CSV here, or click to browse
            </span>
            <span className="mt-1 text-xs text-white/45">
              Required columns: loc_id, lat, lon, housing_class, tiv_kes
            </span>
            <input
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              disabled={busy}
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                setFile(f);
                setPhase("idle");
                setError("");
              }}
            />
          </label>

          {file ? (
            <p className="mt-3 inline-flex items-center gap-2 text-sm text-data">
              <FileText className="h-4 w-4" /> {file.name}
            </p>
          ) : (
            <p className="mt-3 text-sm text-white/45">
              Need a file? Download the Kisumu sample below.
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <a href="/samples/kisumu-demo-portfolio.csv" download className="btn-ghost !text-xs">
              <Download className="h-3.5 w-3.5" />
              Download Kisumu sample CSV
            </a>
            <button
              type="button"
              className="btn-ghost !text-xs"
              disabled={busy}
              onClick={onRunBuiltin}
            >
              Run built-in Nairobi book
            </button>
          </div>

          <button
            type="button"
            className="btn-primary mt-5 w-full"
            disabled={busy || !file}
            onClick={onUploadAndRun}
          >
            {busy ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {phase === "uploading" ? "Uploading…" : "Running pipeline…"}
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Upload & run full pipeline
              </>
            )}
          </button>

          {statusMsg ? (
            <p className="mt-3 text-sm text-white/70">{statusMsg}</p>
          ) : null}

          {error ? (
            <div className="mt-3 flex gap-2 rounded-xl border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}

          {phase === "done" ? (
            <p className="mt-3 inline-flex items-center gap-2 text-sm text-risk">
              <CheckCircle2 className="h-4 w-4" />
              Test run saved. Scroll down for results.
            </p>
          ) : null}

          <div className="mt-5 rounded-xl border border-white/10 bg-night-950/40 p-3 text-xs text-white/45">
            <p className="font-medium text-white/70">Allowed building types</p>
            <p className="mt-1">
              informal_iron_sheet · semi_permanent · permanent_masonry · concrete_rcc
            </p>
            <p className="mt-2">
              Optional hazard columns: hazard_score_common … hazard_score_extreme (0–1).
              Missing scores are filled with 0 and the ML hazard model can still score.
            </p>
          </div>
        </div>

        <div className="glass rounded-2xl p-6">
          <h2 className="section-title mb-4">Or describe risks in plain words</h2>
          <textarea
            className="input-field min-h-[180px] resize-y"
            placeholder="Example: 40 residential buildings near Kisumu lake shore, average covered value KES 5M…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={busy}
          />
          <p className="mt-3 text-xs text-white/45">
            Free-text intake is available via the API freetext stage. For a reliable
            end-to-end test, use the CSV upload on the left.
          </p>
          <p className="mt-6 text-xs uppercase tracking-wide text-white/40">
            Pipeline stages when you run
          </p>
          <ol className="mt-2 space-y-2">
            {PIPELINE_STEPS.map((step, i) => (
              <li
                key={step}
                className={`rounded-lg border px-3 py-2 text-sm ${
                  phase === "running"
                    ? "border-data/40 bg-data-soft text-data"
                    : phase === "done"
                      ? "border-risk/30 bg-risk-soft text-risk"
                      : "border-white/10 text-white/60"
                }`}
              >
                {i + 1}. {step}
              </li>
            ))}
          </ol>
        </div>
      </div>

      {result && resultEp && resultHeavy ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-xl font-semibold text-white">
                Last test run
              </h2>
              <p className="text-sm text-white/55">
                {result.place} · {result.portfolio.name} · run {result.runId} ·{" "}
                {new Date(result.savedAt).toLocaleString()}
              </p>
            </div>
            <Link href="/risk/analytics" className="btn-ghost !text-xs">
              Open EP analytics →
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Place"
              value={result.place}
              tone="data"
              hint={`${result.portfolio.n_rows} properties`}
            />
            <StatCard
              label="Value covered"
              value={formatKes(Number(result.metrics?.total_tiv_kes ?? 0))}
              tone="data"
              status={result.status}
            />
            <StatCard
              label="Expected yearly loss"
              value={formatKes(Number(result.metrics?.aal_kes ?? 0))}
              tone="risk"
              hint="AAL from EP curve"
            />
            <StatCard
              label="If rains too much"
              value={formatKes(resultHeavy.severe ?? 0)}
              tone="finance"
              hint="Severe · 1-in-100"
            />
          </div>

          <HeavyRainCallout
            severeKes={resultHeavy.severe}
            extremeKes={resultHeavy.extreme}
            locationLabel={result.place}
            source={resultEp.source}
          />

          {resultDd ? <DepthDamageChart data={resultDd} /> : null}

          {resultEp.points.length > 0 ? (
            <EpCurveChart points={resultEp.points} aalKes={resultEp.aalKes} />
          ) : null}

          {result.stages?.length ? (
            <div className="glass rounded-2xl p-5">
              <h3 className="section-title mb-3 text-base">Stage results</h3>
              <ul className="space-y-2 text-sm">
                {result.stages.map((s, idx) => (
                  <li
                    key={`${s.stage || s.name}-${idx}`}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2"
                  >
                    <span className="text-white/80">
                      {s.stage || s.name || `Stage ${idx + 1}`}
                    </span>
                    <span
                      className={
                        s.status === "OK" || s.status === "SUCCESS"
                          ? "text-risk"
                          : s.status === "FAILED"
                            ? "text-rose-300"
                            : "text-white/50"
                      }
                    >
                      {s.status || "—"}
                      {s.message ? ` · ${s.message}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
