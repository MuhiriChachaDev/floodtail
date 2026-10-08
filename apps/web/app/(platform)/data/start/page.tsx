"use client";

import { useState } from "react";
import { Upload, FileText, CheckCircle2 } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { Notice } from "@/components/ui/Notice";

export default function DataStartPage() {
  const [fileName, setFileName] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data · Start"
        title="Bring in risk information"
        question="What do we have? This is the front door for locations, values, and supporting records."
      />

      <Notice>
        Original input is kept. FLOODTAIL then standardises, enriches, and prepares
        it for flood analysis — without erasing where it came from.
      </Notice>

      <FlowSteps
        accent="data"
        steps={[
          { label: "Original data" },
          { label: "Standardised" },
          { label: "Enriched" },
          { label: "Ready for flood analysis" },
        ]}
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass rounded-2xl p-6">
          <h2 className="section-title mb-4">Upload a portfolio file</h2>
          <label className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-data/40 bg-data-soft px-6 py-12 text-center transition hover:border-data">
            <Upload className="mb-3 h-8 w-8 text-data" />
            <span className="text-sm font-medium text-white">
              Drop a CSV here, or click to browse
            </span>
            <span className="mt-1 text-xs text-white/45">
              Location, building type, and covered value work best
            </span>
            <input
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                setFileName(f?.name ?? null);
                setSaved(false);
              }}
            />
          </label>
          {fileName ? (
            <p className="mt-3 inline-flex items-center gap-2 text-sm text-data">
              <FileText className="h-4 w-4" /> {fileName}
            </p>
          ) : (
            <p className="mt-3 text-sm text-white/45">
              Or use the built-in Nairobi demo portfolio (600 synthetic buildings).
            </p>
          )}
          <button
            type="button"
            className="btn-primary mt-5"
            onClick={() => setSaved(true)}
          >
            Save intake
          </button>
          {saved ? (
            <p className="mt-3 inline-flex items-center gap-2 text-sm text-risk">
              <CheckCircle2 className="h-4 w-4" />
              Intake recorded. Original file preserved for traceability.
            </p>
          ) : null}
        </div>

        <div className="glass rounded-2xl p-6">
          <h2 className="section-title mb-4">Or describe risks in plain words</h2>
          <textarea
            className="input-field min-h-[180px] resize-y"
            placeholder="Example: 40 residential buildings in Eastlands, average covered value KES 5M, mostly iron-sheet and semi-permanent…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <p className="mt-3 text-xs text-white/45">
            Free text can be turned into structured rows, then checked against the
            required fields. Anything created this way is stamped as synthetic.
          </p>
          <button type="button" className="btn-ghost mt-4">
            Prepare for review
          </button>
        </div>
      </div>
    </div>
  );
}
