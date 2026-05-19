"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Footer } from "@/components/Footer";
import { api } from "@/lib/api";
import { fetchCurrentUser, isAdminUser } from "@/lib/admin";
import { clearToken } from "@/lib/auth";

type DeliveryLine = { channel: string; status: string; error?: string | null };
type ProviderStatus = {
  email: { configured: boolean; sendgrid: boolean; smtp: boolean };
  sms: { configured: boolean };
  whatsapp: { configured: boolean };
  hints?: { email_free?: string; sms_free?: string; local_email?: string };
};

function formatDeliveries(lines: DeliveryLine[]): string {
  if (!lines.length) return "Aucun canal sollicité.";
  return lines
    .map((d) => {
      const label = d.channel === "email" ? "E-mail" : d.channel === "sms" ? "SMS" : "WhatsApp";
      if (d.status === "sent") return `${label} : envoyé`;
      if (d.status === "skipped") return `${label} : non envoyé — ${d.error ?? "configuration manquante"}`;
      return `${label} : échec — ${d.error ?? "erreur fournisseur"}`;
    })
    .join("\n");
}

export default function SimulationsPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [precip, setPrecip] = useState(8);
  const [pm10, setPm10] = useState(120);
  const [temp, setTemp] = useState(36);
  const [testEmail, setTestEmail] = useState("");
  const [testPhone, setTestPhone] = useState("");
  const [broadcastMsg, setBroadcastMsg] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [admins, setAdmins] = useState<{ id: number; email: string; full_name?: string | null }[]>([]);
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [newAdminPassword, setNewAdminPassword] = useState("");
  const [providers, setProviders] = useState<ProviderStatus | null>(null);

  useEffect(() => {
    void fetchCurrentUser().then((u) => {
      if (!isAdminUser(u)) {
        router.replace("/admin/login");
        return;
      }
      setReady(true);
      void api.get<{ id: number; email: string; full_name?: string | null }[]>("/admin/simulations/admins").then((r) => setAdmins(r.data));
      void api.get<ProviderStatus>("/admin/simulations/notification-providers").then((r) => setProviders(r.data));
    });
  }, [router]);

  async function addAdmin() {
    if (!newAdminEmail.trim() || newAdminPassword.length < 12) {
      setStatus("E-mail et mot de passe (12 caractères min.) requis pour un nouvel admin.");
      return;
    }
    try {
      await api.post("/admin/simulations/admins", {
        email: newAdminEmail.trim(),
        password: newAdminPassword,
      });
      const r = await api.get<{ id: number; email: string; full_name?: string | null }[]>("/admin/simulations/admins");
      setAdmins(r.data);
      setNewAdminEmail("");
      setNewAdminPassword("");
      setStatus("Administrateur enregistré.");
    } catch {
      setStatus("Échec création administrateur.");
    }
  }

  async function removeAdmin(id: number) {
    try {
      await api.delete(`/admin/simulations/admins/${id}`);
      setAdmins((prev) => prev.filter((a) => a.id !== id));
      setStatus("Administrateur retiré.");
    } catch {
      setStatus("Impossible de retirer cet administrateur (dernier admin actif ?).");
    }
  }

  async function runClimateSim() {
    setStatus(null);
    try {
      const r = await api.post("/admin/simulations/climate", {
        precip_mm: precip,
        pm10,
        temperature_c: temp,
      });
      setStatus(`Simulation active 2 min — alertes évaluées (${r.data.status}).`);
    } catch {
      setStatus("Échec de la simulation climatique.");
    }
  }

  async function sendTestAlert() {
    setStatus(null);
    try {
      const r = await api.post<{ deliveries: DeliveryLine[]; sent: number; providers?: ProviderStatus }>(
        "/admin/simulations/test-alert",
        {
        email: testEmail.trim() || null,
          phone_e164: testPhone.trim() || null,
        },
      );
      const lines = formatDeliveries(r.data.deliveries ?? []);
      setStatus(
        r.data.sent > 0
          ? `Résultat de l’envoi test :\n${lines}`
          : `Aucun message n’a quitté le serveur (configuration requise) :\n${lines}`,
      );
      if (r.data.providers) setProviders(r.data.providers as ProviderStatus);
    } catch {
      setStatus("Échec envoi alerte de test.");
    }
  }

  async function sendBroadcast() {
    setStatus(null);
    const words = broadcastMsg.trim().split(/\s+/).filter(Boolean);
    if (words.length > 150) {
      setStatus("Message limité à 150 mots.");
      return;
    }
    try {
      const r = await api.post<{
        notifications_sent: number;
        notifications_total: number;
        deliveries: DeliveryLine[];
      }>("/admin/simulations/broadcast", { message_fr: broadcastMsg.trim() });
      const sample = (r.data.deliveries ?? []).slice(0, 8);
      const detail = sample.length ? `\n${formatDeliveries(sample)}` : "";
      setStatus(
        `Message officiel : ${r.data.notifications_sent} envoyé(s) sur ${r.data.notifications_total} tentative(s).${detail}`,
      );
    } catch {
      setStatus("Échec envoi message officiel.");
    }
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-600">
        Vérification des droits administrateur…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-brand-cream dark:bg-slate-950">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-4 dark:border-slate-800 dark:bg-slate-900">
        <div>
          <div className="text-xs font-semibold uppercase text-brand-warn">Administration</div>
          <h1 className="text-xl font-bold text-brand-green">Simulations</h1>
        </div>
        <div className="flex gap-2 text-sm">
          <Link href="/dashboard" className="rounded-lg border px-3 py-2">
            Tableau de bord
          </Link>
          <button
            type="button"
            className="rounded-lg border px-3 py-2 text-brand-alert"
            onClick={() => {
              clearToken();
              router.push("/admin/login");
            }}
          >
            Déconnexion
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl space-y-6 px-4 py-8">
        {providers ? (
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-xs dark:border-slate-800 dark:bg-slate-900">
            <div className="font-semibold text-brand-green">Canaux de notification</div>
            <ul className="mt-2 space-y-1 text-slate-700 dark:text-slate-200">
              <li>E-mail : {providers.email.configured ? "configuré" : "non configuré (SendGrid ou SMTP)"}</li>
              <li>SMS : {providers.sms.configured ? "configuré (Twilio)" : "non configuré"}</li>
              <li>WhatsApp : {providers.whatsapp.configured ? "configuré (Twilio)" : "non configuré"}</li>
            </ul>
            <p className="mt-2 text-slate-500">
              Docker local : e-mails visibles sur{" "}
              <a href="http://localhost:8025" className="text-brand-mint underline" target="_blank" rel="noreferrer">
                Mailpit (port 8025)
              </a>
              . Formspree ne gère pas les alertes automatiques.
            </p>
          </div>
        ) : null}

        <Block title="Simulateur paramètres climatiques">
          <Slider label="Pluie / inondation (mm)" value={precip} min={0} max={80} onChange={setPrecip} />
          <Slider label="Pollution PM10 (µg/m³)" value={pm10} min={0} max={300} onChange={setPm10} />
          <Slider label="Température / chaleur (°C)" value={temp} min={5} max={45} onChange={setTemp} />
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <NumInput label="mm" value={precip} onChange={setPrecip} />
            <NumInput label="PM10" value={pm10} onChange={setPm10} />
            <NumInput label="°C" value={temp} onChange={setTemp} />
          </div>
          <button
            type="button"
            onClick={() => void runClimateSim()}
            className="mt-4 w-full rounded-lg bg-brand-green py-2.5 text-sm font-semibold text-white"
          >
            Simuler
          </button>
          <p className="mt-2 text-xs text-slate-500">
            Remplace les cartes climat du tableau de bord pendant 2 minutes, sans modifier les données API réelles.
          </p>
        </Block>

        <Block title="Simulation alerte">
          <Field label="E-mail" value={testEmail} onChange={setTestEmail} type="email" />
          <Field label="Téléphone (E.164)" value={testPhone} onChange={setTestPhone} type="tel" />
          <button
            type="button"
            onClick={() => void sendTestAlert()}
            className="mt-3 w-full rounded-lg border border-brand-green py-2.5 text-sm font-semibold text-brand-green"
          >
            Envoyer
          </button>
        </Block>

        <Block title="Gestion des administrateurs">
          <ul className="mb-3 space-y-1 text-sm">
            {admins.map((a) => (
              <li key={a.id} className="flex items-center justify-between gap-2 rounded border border-slate-100 px-2 py-1 dark:border-slate-800">
                <span>{a.email}</span>
                <button type="button" className="text-xs text-brand-alert" onClick={() => void removeAdmin(a.id)}>
                  Retirer
                </button>
              </li>
            ))}
          </ul>
          <Field label="E-mail nouvel admin" value={newAdminEmail} onChange={setNewAdminEmail} type="email" />
          <Field label="Mot de passe (12+ caractères)" value={newAdminPassword} onChange={setNewAdminPassword} type="password" />
          <button
            type="button"
            onClick={() => void addAdmin()}
            className="mt-3 w-full rounded-lg border border-brand-green py-2.5 text-sm font-semibold text-brand-green"
          >
            Ajouter un administrateur
          </button>
        </Block>

        <Block title="Message officiel aux abonnés">
          <textarea
            className="w-full rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700 dark:bg-slate-950"
            rows={5}
            value={broadcastMsg}
            onChange={(e) => setBroadcastMsg(e.target.value)}
            placeholder="Maximum 150 mots — maintenance, annonce officielle…"
          />
          <p className="text-xs text-slate-500">{broadcastMsg.trim().split(/\s+/).filter(Boolean).length} / 150 mots</p>
          <button
            type="button"
            onClick={() => void sendBroadcast()}
            className="mt-3 w-full rounded-lg bg-brand-warn py-2.5 text-sm font-semibold text-white"
          >
            Envoyer aux abonnés (canaux actifs)
          </button>
        </Block>

        {status ? (
          <pre className="whitespace-pre-wrap rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200">
            {status}
          </pre>
        ) : null}
      </main>
      <Footer />
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-4 text-sm font-semibold text-brand-green">{title}</h2>
      {children}
    </section>
  );
}

function Slider(props: { label: string; value: number; min: number; max: number; onChange: (v: number) => void }) {
  return (
    <label className="mb-3 block text-sm">
      <span className="font-medium">{props.label}</span>
      <input
        type="range"
        min={props.min}
        max={props.max}
        step={0.5}
        value={props.value}
        onChange={(e) => props.onChange(Number(e.target.value))}
        className="mt-1 w-full accent-brand-mint"
      />
      <span className="text-xs text-slate-500">{props.value}</span>
    </label>
  );
}

function NumInput(props: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="block">
      <span className="text-slate-500">{props.label}</span>
      <input
        type="number"
        className="mt-0.5 w-full rounded border border-slate-200 px-2 py-1 dark:border-slate-700 dark:bg-slate-950"
        value={props.value}
        onChange={(e) => props.onChange(Number(e.target.value))}
      />
    </label>
  );
}

function Field(props: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <label className="mb-2 block text-sm">
      <span className="font-medium">{props.label}</span>
      <input
        type={props.type ?? "text"}
        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
      />
    </label>
  );
}
