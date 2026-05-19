"use client";

import type { FeatureCollection } from "geojson";
import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Footer } from "@/components/Footer";
import { SubscribeForm } from "@/components/SubscribeForm";
import { api } from "@/lib/api";
import { fetchCurrentUser, isAdminUser } from "@/lib/admin";

const RiskMap = dynamic(() => import("@/components/RiskMap").then((m) => m.RiskMap), { ssr: false });

type TabKey = "dashboard" | "map" | "alerts" | "subscribe";

function severityFr(v: string) {
  switch (v) {
    case "critical":
      return "CRITIQUE";
    case "high":
      return "ÉLEVÉ";
    case "moderate":
      return "MODÉRÉ";
    default:
      return "FAIBLE";
  }
}

export default function DashboardPage() {
  const [tab, setTab] = useState<TabKey>("dashboard");
  const [dark, setDark] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [cards, setCards] = useState<any>(null);
  const [tables, setTables] = useState<any>(null);
  const [zones, setZones] = useState<FeatureCollection | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  const nowLabel = useMemo(() => {
    const d = new Date();
    return d.toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" });
  }, []);

  async function refreshAll() {
    setLoadError(null);
    const [s, c, t, z] = await Promise.all([
      api.get("/dashboard/summary"),
      api.get("/dashboard/risk-cards"),
      api.get("/dashboard/tables"),
      api.get("/geo/zones"),
    ]);
    setSummary(s.data);
    setCards(c.data);
    setTables(t.data);
    setZones(z.data as FeatureCollection);
  }

  useEffect(() => {
    void refreshAll().catch(() => {
      setLoadError("Impossible de charger les données publiques. Réessayez plus tard.");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
  }, [dark]);

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/api/ws/dashboard`);
    ws.onmessage = () => {
      void refreshAll().catch(() => null);
    };
    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void fetchCurrentUser().then((u) => setIsAdmin(isAdminUser(u)));
  }, []);

  const globalSeverity = summary?.global_severity ?? "low";
  const alertBannerClass =
    globalSeverity === "critical" || globalSeverity === "high"
      ? "bg-brand-alert text-white"
      : globalSeverity === "moderate"
        ? "bg-brand-warn text-white"
        : "bg-brand-mint text-white";

  const navItems: [TabKey, string][] = [
    ["dashboard", "Tableau de bord"],
    ["map", "Carte des risques"],
    ["alerts", "Alertes"],
    ["subscribe", "Abonnement aux alertes"],
  ];

  return (
    <div className="min-h-screen bg-brand-cream dark:bg-slate-950">
      <div className="mx-auto flex max-w-[1600px]">
        <aside className="hidden w-64 shrink-0 bg-brand-green text-white md:block">
          <div className="flex items-center gap-3 px-4 py-5">
            <Image src="/solagritech-logo.jpg" alt="SolAgriTech" width={40} height={40} className="rounded-full" />
            <div className="text-sm font-semibold leading-tight">SolAgriTech</div>
          </div>
          <nav className="space-y-1 px-2 pb-6 text-sm">
            {navItems.map(([k, label]) => (
              <button
                key={k}
                onClick={() => setTab(k)}
                className={`w-full rounded-lg px-3 py-2 text-left hover:bg-white/10 ${
                  tab === k ? "bg-white/15 font-semibold" : ""
                }`}
                type="button"
              >
                {label}
              </button>
            ))}
          </nav>
          <div className="px-4 pb-6 text-xs text-white/70">Accès public · CLIMA-KIDS ALERT</div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="border-b border-slate-200 bg-white/80 px-4 py-4 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-brand-mint">CLIMA-KIDS ALERT — KOLWEZI</div>
                <div className="text-2xl font-bold text-brand-green dark:text-emerald-200">Alerte climatique pour la santé des enfants</div>
                <div className="mt-1 text-sm text-slate-600 dark:text-slate-300">{nowLabel}</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => setDark((v) => !v)}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold dark:border-slate-800 dark:bg-slate-900"
                >
                  {dark ? "Mode clair" : "Mode sombre"}
                </button>
                <button
                  type="button"
                  onClick={() => void refreshAll()}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold dark:border-slate-800 dark:bg-slate-900"
                >
                  Recharger
                </button>
                {isAdmin ? (
                  <Link
                    href="/admin/simulations"
                    className="rounded-lg bg-brand-warn px-3 py-2 text-xs font-semibold text-white"
                  >
                    Simulations
                  </Link>
                ) : (
                  <Link
                    href="/admin/login"
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200"
                  >
                    Connexion admin
                  </Link>
                )}
              </div>
            </div>

            <nav className="mt-3 flex gap-1 overflow-x-auto pb-1 md:hidden">
              {navItems.map(([k, label]) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setTab(k)}
                  className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${
                    tab === k ? "bg-brand-green text-white" : "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100"
                  }`}
                >
                  {label}
                </button>
              ))}
            </nav>

            <div className={`mt-4 flex items-center justify-between rounded-xl px-4 py-3 ${alertBannerClass}`}>
              <div className="text-sm font-semibold">NIVEAU D’ALERTE GLOBAL : {severityFr(globalSeverity)}</div>
              <div className="text-xs opacity-90">Sources : Open-Meteo · OpenAQ · NASA POWER</div>
            </div>
          </header>

          <main className="space-y-6 px-4 py-6">
            {loadError ? (
              <div className="rounded-xl border border-brand-warn/40 bg-brand-warn/10 px-4 py-3 text-sm text-slate-800 dark:text-slate-100">
                {loadError}
              </div>
            ) : null}

            {tab === "dashboard" ? (
              <>
                <section className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-6">
                  <Kpi title="Zones à risque élevé" value={`${summary?.high_risk_zones ?? "—"} quartiers`} tone="alert" />
                  <Kpi title="Écoles exposées" value={`${summary?.schools_exposed ?? "—"} écoles`} tone="ok" />
                  <Kpi title="Centres de santé" value={`${summary?.health_centers ?? "—"} centres`} tone="info" />
                  <Kpi title="Enfants potentiellement exposés" value={`${summary?.children_potentially_exposed ?? "—"}`} tone="warn" />
                  <Kpi title="Alertes envoyées aujourd’hui" value={`${summary?.alerts_sent_today ?? "—"}`} tone="purple" />
                  <Kpi title="Taux de réception" value={`${summary?.reception_rate_percent ?? "—"}%`} tone="teal" />
                </section>

                <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                  <div className="xl:col-span-2 space-y-3">
                    <div className="text-sm font-semibold text-brand-green">CARTE DES RISQUES — KOLWEZI ET ENVIRONS</div>
                    <div className="rounded-2xl border border-slate-200 bg-white p-2 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                      {zones ? <RiskMap zones={zones} /> : <div className="p-6 text-sm text-slate-600">Chargement de la carte…</div>}
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-slate-700 dark:text-slate-200">
                      {[
                        "Zones de santé",
                        "Quartiers",
                        "Écoles",
                        "Centres de santé",
                        "Sites miniers",
                        "Zones poussiéreuses",
                        "Zones inondables",
                        "Points d’eau",
                      ].map((l) => (
                        <label key={l} className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1 dark:border-slate-800 dark:bg-slate-950">
                          <input type="checkbox" defaultChecked className="accent-brand-mint" />
                          {l}
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <RiskMini title={cards?.heat?.title ?? "Chaleur extrême"} value={cards?.heat?.value ?? "—"} sev={cards?.heat?.severity ?? "—"} advice={cards?.heat?.advice ?? ""} />
                    <RiskMini title={cards?.dust?.title ?? "Poussière / pollution"} value={cards?.dust?.value ?? "—"} sev={cards?.dust?.severity ?? "—"} advice={cards?.dust?.advice ?? ""} />
                    <RiskMini title={cards?.rain?.title ?? "Pluie / inondation"} value={cards?.rain?.value ?? "—"} sev={cards?.rain?.severity ?? "—"} advice={cards?.rain?.advice ?? ""} />
                  </div>
                </section>

                <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                    <div className="mb-3 text-sm font-semibold text-brand-green">SCORE DE RISQUE ENFANT PAR ZONE</div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="text-xs text-slate-500">
                          <tr>
                            <th className="py-2">Zone</th>
                            <th className="py-2">Score /100</th>
                            <th className="py-2">Niveau</th>
                            <th className="py-2">Action recommandée</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(tables?.zone_scores ?? []).map((r: any) => (
                            <tr key={r.zone} className="border-t border-slate-100 dark:border-slate-800">
                              <td className="py-2 font-medium">{r.zone}</td>
                              <td className="py-2">
                                <div className="flex items-center gap-2">
                                  <div className="h-2 w-28 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                                    <div className="h-2 bg-brand-mint" style={{ width: `${Math.min(100, r.score)}%` }} />
                                  </div>
                                  <span className="text-xs text-slate-600">{r.score}</span>
                                </div>
                              </td>
                              <td className="py-2">{r.level}</td>
                              <td className="py-2 text-slate-700 dark:text-slate-200">{r.action}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                    <div className="mb-3 text-sm font-semibold text-brand-green">ALERTES RÉCENTES</div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="text-xs text-slate-500">
                          <tr>
                            <th className="py-2">Date</th>
                            <th className="py-2">Zone</th>
                            <th className="py-2">Risque</th>
                            <th className="py-2">Canal</th>
                            <th className="py-2">Statut</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(tables?.recent_alerts ?? []).map((r: any) => (
                            <tr key={`${r.date}-${r.zone}`} className="border-t border-slate-100 dark:border-slate-800">
                              <td className="py-2 whitespace-nowrap">{r.date}</td>
                              <td className="py-2">{r.zone}</td>
                              <td className="py-2">{r.risk}</td>
                              <td className="py-2">{r.channel}</td>
                              <td className="py-2">{r.status}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="mt-4">
                      <button type="button" onClick={() => setTab("subscribe")} className="w-full rounded-xl bg-brand-green px-4 py-3 text-sm font-semibold text-white hover:bg-brand-mint">
                        Recevoir ces alertes par e-mail / SMS / WhatsApp
                      </button>
                    </div>
                  </div>
                </section>
              </>
            ) : null}

            {tab === "map" ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <div className="mb-2 text-sm font-semibold text-brand-green">Carte interactive</div>
                {zones ? <RiskMap zones={zones} /> : <div className="p-6 text-sm">Chargement…</div>}
              </div>
            ) : null}

            {tab === "alerts" ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
                <div className="mb-3 text-sm font-semibold text-brand-green">Historique des alertes</div>
                <ul className="space-y-2 text-sm">
                  {(tables?.recent_alerts ?? []).map((r: any) => (
                    <li key={`${r.date}-${r.risk}`} className="rounded-lg border border-slate-100 p-3 dark:border-slate-800">
                      <div className="font-semibold">{r.risk}</div>
                      <div className="text-xs text-slate-600 dark:text-slate-300">
                        {r.date} · {r.zone} · {r.channel} · {r.status}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {tab === "subscribe" ? <SubscribeForm /> : null}
          </main>

          <Footer />
        </div>
      </div>
    </div>
  );
}

function Kpi(props: { title: string; value: string; tone: "alert" | "ok" | "info" | "warn" | "purple" | "teal" }) {
  const ring =
    props.tone === "alert"
      ? "border-brand-alert/30"
      : props.tone === "warn"
        ? "border-brand-warn/30"
        : "border-brand-mint/30";
  return (
    <div className={`rounded-2xl border bg-white p-4 shadow-sm dark:bg-slate-900 ${ring}`}>
      <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">{props.title}</div>
      <div className="mt-2 text-lg font-bold text-brand-green dark:text-emerald-200">{props.value}</div>
    </div>
  );
}

function RiskMini(props: { title: string; value: string; sev: string; advice: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="text-sm font-semibold text-brand-green">{props.title}</div>
      <div className="mt-2 text-2xl font-bold">{props.value}</div>
      <div className="mt-1 text-xs font-semibold text-brand-warn">Risque : {props.sev}</div>
      <div className="mt-2 text-sm text-slate-700 dark:text-slate-200">{props.advice}</div>
    </div>
  );
}

