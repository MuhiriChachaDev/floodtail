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
  BookOpen,
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
  fetchPortfolioProperties,
  fetchRunProperties,
  searchKnowledge,
  uploadKnowledgeDocument,
  uploadPortfolio,
  type CreateRunResponse,
  type KnowledgeDocumentResult,
  type KnowledgeSearchResult,
  type PortfolioPayload,
} from "@/lib/api";
import { formatKes } from "@/lib/format";
import { heavyRainLosses, resolveEpMetrics } from "@/lib/ep-metrics";
import { propertyRowToPoint, type PortfolioPoint } from "@/lib/map-portfolio";
import { loadLastTestRun, saveLastTestRun, type LastTestRun } from "@/lib/run-store";
import { clsx } from "clsx";

function rowsToMapPoints(
  rows: Parameters<typeof propertyRowToPoint>[0][] | undefined,
): PortfolioPoint[] {
  if (!rows?.length) return [];
  return rows
    .map((row) => propertyRowToPoint(row))
    .filter((p): p is PortfolioPoint => p != null);
}

function hazardCoverageNote(portfolio: PortfolioPayload): string | null {
  const warnings = portfolio.extra?.warnings ?? [];
  const hit = warnings.find((w) =>
    /HAZARD_ZERO_FILL|outside raster|No hazard rasters overlap|kept CSV hazard/i.test(
      w,
    ),
  );
  if (!hit) return null;
  return (
    "Hazard coverage note: city-matched rasters may be missing for this place. " +
    "Keep hazard_score_* columns in the CSV or losses can be near zero."
  );
}

type Phase = "idle" | "uploading" | "running" | "done" | "error";
type UploadMode = "csv" | "pdf";

type RagDelivery = {
  document: KnowledgeDocumentResult;
  search: KnowledgeSearchResult;
  place: string;
  query: string;
  savedAt: string;
};

export default function DataStartPage() {
  const [uploadMode, setUploadMode] = useState<UploadMode>("csv");
  const [file, setFile] = useState<File | null>(null);
  const [place, setPlace] = useState("Kisumu");
  const [portfolioName, setPortfolioName] = useState("");
  const [ragQuery, setRagQuery] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState("");
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [modelsReady, setModelsReady] = useState<boolean | null>(null);
  const [result, setResult] = useState<LastTestRun | null>(null);
  const [ragResult, setRagResult] = useState<RagDelivery | null>(null);

  useEffect(() => {
    setResult(loadLastTestRun());
    fetchHealth().then((h) => {
      setApiOk(Boolean(h));
      setModelsReady(Boolean(h?.registry?.registry_ready));
    });
  }, []);

  function switchMode(mode: UploadMode) {
    setUploadMode(mode);
    setFile(null);
    setPhase("idle");
    setError("");
    setStatusMsg("");
  }

  async function runPipeline(
    portfolio: PortfolioPayload,
    placeLabel: string,
  ): Promise<CreateRunResponse> {
    setPhase("running");
    setStatusMsg(
      "Running the full flood pipeline (hazard → damage → loss → risk). Please wait 30–60 seconds — do not refresh…",
    );
    const runResult = await createRun(portfolio.id);

    // Always try to cache lat/lon with the run so Home/map follow ANY new place
    // even if the API later restarts (in-memory store).
    let mapPoints: PortfolioPoint[] = [];
    const runProps = await fetchRunProperties(runResult.run.id, { limit: 600 });
    mapPoints = rowsToMapPoints(runProps?.properties);
    if (!mapPoints.length && portfolio.id) {
      const portProps = await fetchPortfolioProperties(portfolio.id, {
        limit: 600,
      });
      mapPoints = rowsToMapPoints(portProps?.properties);
    }

    const saved = saveLastTestRun(placeLabel, portfolio, runResult, {
      mapPoints: mapPoints.length ? mapPoints : undefined,
    });
    setResult(saved);
    setPhase("done");

    const coverage = hazardCoverageNote(portfolio);
    const mapNote = mapPoints.length
      ? `${mapPoints.length} map locations cached`
      : "map coords unavailable — re-open Data → Start after API is up";
    setStatusMsg(
      [
        `Pipeline finished · status ${runResult.run.status}`,
        mapNote,
        coverage,
      ]
        .filter(Boolean)
        .join(" · "),
    );
    return runResult;
  }

  async function onUploadAndRun() {
    setError("");
    if (!file) {
      setError(
        uploadMode === "csv"
          ? "Choose a CSV portfolio file first."
          : "Choose a PDF or Word document first.",
      );
      return;
    }

    if (uploadMode === "pdf") {
      await onIngestKnowledge();
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

  async function onIngestKnowledge() {
    if (!file) return;
    try {
      setPhase("uploading");
      setStatusMsg(`Ingesting ${file.name} into the knowledge (RAG) layer…`);
      const { document } = await uploadKnowledgeDocument({
        file,
        locationLabel: place.trim() || undefined,
        title: portfolioName.trim() || undefined,
      });

      setPhase("running");
      const query =
        ragQuery.trim() ||
        [
          "Summarise the key flood risk, exposure, underwriting, and capital points",
          place.trim() ? `for ${place.trim()}` : "",
          "from this document.",
        ]
          .filter(Boolean)
          .join(" ");

      setStatusMsg("Retrieving grounded passages from the document…");
      const search = await searchKnowledge({
        query,
        k: 6,
        documentId: document.document_id,
      });

      setRagResult({
        document,
        search,
        place: place.trim() || "Document",
        query,
        savedAt: new Date().toISOString(),
      });
      setPhase("done");
      setStatusMsg(
        `Knowledge ingest done · ${document.n_chunks} chunks · ${search.n_hits} passages delivered`,
      );
    } catch (err) {
      setPhase("error");
      setError(err instanceof Error ? err.message : String(err));
      setStatusMsg("");
    }
  }

  async function onRunBuiltin() {
    setError("");
    try {
      setUploadMode("csv");
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

  const accept =
    uploadMode === "csv"
      ? ".csv,text/csv"
      : ".pdf,.docx,.doc,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data · Start"
        title="Bring in risk information"
        question="Upload a portfolio CSV for the CAT pipeline, or a PDF/Word file for the knowledge (RAG) layer."
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
        <strong className="text-white">Two intake paths.</strong> CSV drives the
        deterministic flood pipeline (map, EP, capital). PDF / Word goes through
        RAG — text is chunked, embedded, and retrieved passages are delivered
        here. RAG does not invent loss, EP, or AAL numbers.
      </Notice>

      <FlowSteps
        accent="data"
        steps={
          uploadMode === "csv"
            ? [
                { label: "Original data" },
                { label: "Standardised" },
                { label: "Enriched" },
                { label: "Full pipeline run" },
              ]
            : [
                { label: "PDF / Word" },
                { label: "Extract" },
                { label: "Embed" },
                { label: "Retrieve output" },
              ]
        }
      />

        <div className="glass rounded-2xl p-4 sm:p-6">
          <h2 className="section-title mb-4">Upload & deliver</h2>

          <fieldset className="mb-4">
            <legend className="mb-2 text-xs font-medium text-white/60">
              What are you uploading?
            </legend>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => switchMode("csv")}
                className={clsx(
                  "rounded-xl border px-3 py-3 text-left text-sm transition",
                  uploadMode === "csv"
                    ? "border-data/50 bg-data-soft text-white"
                    : "border-white/10 bg-night-950/40 text-white/65 hover:border-white/25",
                )}
              >
                <span className="block font-medium">CSV portfolio</span>
                <span className="mt-0.5 block text-[11px] text-white/45">
                  Runs CAT pipeline · map & EP
                </span>
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => switchMode("pdf")}
                className={clsx(
                  "rounded-xl border px-3 py-3 text-left text-sm transition",
                  uploadMode === "pdf"
                    ? "border-accent/50 bg-accent/10 text-white"
                    : "border-white/10 bg-night-950/40 text-white/65 hover:border-white/25",
                )}
              >
                <span className="block font-medium">PDF / Word</span>
                <span className="mt-0.5 block text-[11px] text-white/45">
                  RAG knowledge · retrieved output
                </span>
              </button>
            </div>
          </fieldset>

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
            {uploadMode === "csv" ? "Portfolio name (optional)" : "Document title (optional)"}
            <input
              className="input-field mt-1.5"
              placeholder={
                uploadMode === "csv"
                  ? "e.g. Kisumu demo book"
                  : "e.g. Treaty wording · flood briefing"
              }
              value={portfolioName}
              onChange={(e) => setPortfolioName(e.target.value)}
              disabled={busy}
            />
          </label>

          {uploadMode === "pdf" ? (
            <label className="mb-4 block text-xs font-medium text-white/60">
              What should we retrieve? (optional)
              <input
                className="input-field mt-1.5"
                placeholder="e.g. flood exclusions, attachment, capital guidance…"
                value={ragQuery}
                onChange={(e) => setRagQuery(e.target.value)}
                disabled={busy}
              />
            </label>
          ) : null}

          <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-data/40 bg-data-soft px-6 py-10 text-center transition hover:border-data">
            <Upload className="mb-3 h-8 w-8 text-data" />
            <span className="text-sm font-medium text-white">
              {uploadMode === "csv"
                ? "Drop a CSV here, or click to browse"
                : "Drop a PDF or Word file here, or click to browse"}
            </span>
            <span className="mt-1 text-xs text-white/45">
              {uploadMode === "csv"
                ? "Required columns: loc_id, lat, lon, housing_class, tiv_kes"
                : "Supported: .pdf · .docx · .doc — ingested via RAG, not as portfolio rows"}
            </span>
            <input
              type="file"
              accept={accept}
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
              {uploadMode === "csv"
                ? "Need a file? Download the Kisumu sample below."
                : "Upload underwriting notes, treaty wording, or a flood briefing PDF."}
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            {uploadMode === "csv" ? (
              <>
                <a
                  href="/samples/kisumu-demo-portfolio.csv"
                  download
                  className="btn-ghost !text-xs"
                >
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
              </>
            ) : (
              <Link href="/ai/knowledge" className="btn-ghost !text-xs">
                <BookOpen className="h-3.5 w-3.5" />
                Open knowledge & evidence
              </Link>
            )}
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
                {phase === "uploading"
                  ? uploadMode === "pdf"
                    ? "Ingesting…"
                    : "Uploading…"
                  : uploadMode === "pdf"
                    ? "Retrieving…"
                    : "Running pipeline…"}
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                {uploadMode === "csv"
                  ? "Upload & run full pipeline"
                  : "Ingest PDF & deliver RAG output"}
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
              {uploadMode === "pdf"
                ? "RAG output ready below."
                : "Test run saved. Scroll down for results."}
            </p>
          ) : null}

          <div className="mt-5 rounded-xl border border-white/10 bg-night-950/40 p-3 text-xs text-white/45">
            {uploadMode === "csv" ? (
              <>
                <p className="font-medium text-white/70">Allowed building types</p>
                <p className="mt-1">
                  informal_iron_sheet · semi_permanent · permanent_masonry ·
                  concrete_rcc
                </p>
                <p className="mt-2">
                  Optional hazard columns: hazard_score_common …
                  hazard_score_extreme (0–1).
                </p>
              </>
            ) : (
              <>
                <p className="font-medium text-white/70">RAG path</p>
                <p className="mt-1">
                  Document → extract text → chunk → embed → search. Output is
                  grounded passages from <em>this</em> file only — not CAT loss
                  math.
                </p>
              </>
            )}
          </div>
      </div>

      {ragResult ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-xl font-semibold text-white">
                RAG delivery
              </h2>
              <p className="text-sm text-white/55">
                {ragResult.document.filename} · {ragResult.place} ·{" "}
                {ragResult.document.n_chunks} chunks ·{" "}
                {new Date(ragResult.savedAt).toLocaleString()}
              </p>
            </div>
            <Link href="/ai/knowledge" className="btn-ghost !text-xs">
              Knowledge & evidence →
            </Link>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Document"
              value={ragResult.document.filename}
              tone="data"
              hint={ragResult.document.document_id}
            />
            <StatCard
              label="Chunks stored"
              value={String(ragResult.document.n_chunks)}
              tone="data"
              status={ragResult.document.backend}
            />
            <StatCard
              label="Passages delivered"
              value={String(ragResult.search.n_hits)}
              tone="risk"
              hint="Top retrieval hits"
            />
            <StatCard
              label="Place tagged"
              value={ragResult.place}
              tone="neutral"
            />
          </div>

          {ragResult.document.warnings?.length ? (
            <Notice>
              Ingest notes: {ragResult.document.warnings.slice(0, 3).join(" · ")}
            </Notice>
          ) : null}

          <div className="glass rounded-2xl p-5">
            <h3 className="section-title mb-2 text-base">Query</h3>
            <p className="text-sm text-white/70">{ragResult.query}</p>
          </div>

          {ragResult.search.context ? (
            <div className="glass rounded-2xl p-5">
              <h3 className="section-title mb-3 text-base">Delivered context</h3>
              <pre className="max-h-[320px] overflow-auto whitespace-pre-wrap rounded-xl border border-white/10 bg-night-950/50 p-4 text-xs leading-relaxed text-white/75">
                {ragResult.search.context}
              </pre>
            </div>
          ) : null}

          <div className="glass rounded-2xl p-5">
            <h3 className="section-title mb-3 text-base">Grounded passages</h3>
            {ragResult.search.hits.length === 0 ? (
              <p className="text-sm text-white/50">
                No passages matched. Try a broader retrieval query and re-ingest,
                or check that the PDF contains selectable text (not only images).
              </p>
            ) : (
              <ul className="space-y-3">
                {ragResult.search.hits.map((hit, idx) => (
                  <li
                    key={`${hit.document_id}-${hit.chunk_index}-${idx}`}
                    className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3"
                  >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-white/45">
                      <span>
                        Passage {idx + 1} · chunk {hit.chunk_index}
                      </span>
                      <span className="chip">score {hit.score.toFixed(3)}</span>
                    </div>
                    <p className="text-sm leading-relaxed text-white/80">
                      {hit.content}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : null}

      {result && resultEp && resultHeavy ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="font-display text-xl font-semibold text-white">
                Last CAT pipeline run
              </h2>
              <p className="text-sm text-white/55">
                {result.place} · {result.portfolio.name} · run {result.runId} ·{" "}
                {new Date(result.savedAt).toLocaleString()}
              </p>
            </div>
            <Link href="/finance#capital" className="btn-ghost !text-xs">
              Open capital view →
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
