"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { fetchHealth } from "@/lib/api";

const AGENTS = [
  { name: "Data helper", status: "Idle", task: "Waiting for intake" },
  { name: "Hazard helper", status: "Watching", task: "Rainfall signals" },
  { name: "Loss helper", status: "Idle", task: "Last run 10:32" },
  { name: "Decision helper", status: "Ready", task: "1 case prepared" },
];

export default function AiControlPage() {
  const [ollama, setOllama] = useState<string>("Checking…");

  useEffect(() => {
    fetchHealth().then((h) => {
      if (!h) {
        setOllama("API offline — demo mode");
        return;
      }
      setOllama(h.ollama?.available ? "Online" : "Unavailable (templates used)");
    });
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="AI · Control"
        title="What is FLOODTAIL’s AI doing now?"
        question="Operations view of helpers, workflows, and human controls."
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label="AI system" value={ollama} tone="data" />
        <StatCard label="Active helpers" value="4" tone="data" />
        <StatCard label="Exceptions" value="0" tone="risk" />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {AGENTS.map((a) => (
          <div key={a.name} className="glass rounded-2xl p-4">
            <div className="flex items-center justify-between">
              <p className="font-medium text-white">{a.name}</p>
              <span className="chip text-accent">{a.status}</span>
            </div>
            <p className="mt-2 text-sm text-white/55">{a.task}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
