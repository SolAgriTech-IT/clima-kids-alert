"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { resolveUserLocation } from "@/lib/geolocation";

const FORMSPREE_URL = "https://formspree.io/f/xeenyjld";

type SchoolOption = { id: number; name: string };

const USER_TYPES = [
  { value: "parent", label: "Parent" },
  { value: "school", label: "École" },
  { value: "association", label: "Association" },
  { value: "other", label: "Autre / Non renseigné" },
] as const;

export function SubscribeForm() {
  const [schoolOptions, setSchoolOptions] = useState<SchoolOption[]>([]);
  const [subEmail, setSubEmail] = useState("");
  const [subPhone, setSubPhone] = useState("");
  const [subWhatsapp, setSubWhatsapp] = useState("");
  const [subSchoolId, setSubSchoolId] = useState("");
  const [userType, setUserType] = useState<string>("other");
  const [chEmail, setChEmail] = useState(true);
  const [chSms, setChSms] = useState(false);
  const [chWa, setChWa] = useState(false);
  const [subLoading, setSubLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [locLabel, setLocLabel] = useState("Localisation en cours…");
  const [homeLat, setHomeLat] = useState<number | null>(null);
  const [homeLon, setHomeLon] = useState<number | null>(null);
  const [locationSource, setLocationSource] = useState<string>("");

  useEffect(() => {
    void api
      .get("/geo/schools")
      .then((r) => {
        const feats = (r.data as { features?: { properties?: { id?: number; name?: string } }[] }).features ?? [];
        setSchoolOptions(
          feats
            .map((f) => ({
              id: f.properties?.id as number,
              name: (f.properties?.name as string) ?? `École #${f.properties?.id}`,
            }))
            .filter((o) => typeof o.id === "number"),
        );
      })
      .catch(() => setSchoolOptions([]));

    void resolveUserLocation()
      .then((loc) => {
        setHomeLat(loc.lat);
        setHomeLon(loc.lon);
        setLocationSource(loc.source);
        const src =
          loc.source === "gps"
            ? "GPS"
            : loc.source === "ip"
              ? "adresse IP"
              : loc.source === "stored"
                ? "dernière position connue"
                : "zone par défaut";
        setLocLabel(`Position détectée (${src}) : ${loc.lat.toFixed(4)}, ${loc.lon.toFixed(4)}`);
      })
      .catch(() => setLocLabel("Position par défaut (Kolwezi) — autorisez le GPS pour plus de précision."));
  }, []);

  function formFilled() {
    return subEmail.trim().length > 0;
  }

  function buildPayload() {
    const school_id = subSchoolId ? Number(subSchoolId) : null;
    return {
      email: subEmail.trim(),
      phone_e164: subPhone.trim() || null,
      whatsapp_e164: subWhatsapp.trim() || null,
      user_type: userType,
      school_id: school_id && !Number.isNaN(school_id) ? school_id : null,
      home_lat: homeLat,
      home_lon: homeLon,
      location_source: locationSource || null,
      alert_email_enabled: chEmail,
      alert_sms_enabled: chSms,
      alert_whatsapp_enabled: chWa,
    };
  }

  async function submitToFormspree() {
    const fd = new FormData();
    fd.append("email", subEmail.trim());
    fd.append("phone_e164", subPhone.trim());
    fd.append("whatsapp_e164", subWhatsapp.trim());
    fd.append("user_type", userType);
    fd.append("school_id", subSchoolId);
    fd.append("home_lat", homeLat != null ? String(homeLat) : "");
    fd.append("home_lon", homeLon != null ? String(homeLon) : "");
    fd.append("location_source", locationSource);
    fd.append("alert_email_enabled", chEmail ? "oui" : "non");
    fd.append("alert_sms_enabled", chSms ? "oui" : "non");
    fd.append("alert_whatsapp_enabled", chWa ? "oui" : "non");
    fd.append("_subject", "Abonnement alertes CLIMA-KIDS");
    await fetch(FORMSPREE_URL, { method: "POST", body: fd, headers: { Accept: "application/json" } });
  }

  async function submitSubscribe(e: React.FormEvent) {
    e.preventDefault();
    setSubLoading(true);
    setStatus(null);
    setSuccess(false);
    try {
      await submitToFormspree();
      const resp = await api.post<{ message?: string }>("/public/subscribe", buildPayload());
      setSuccess(true);
      setStatus(
        resp.data?.message ??
          "Merci. Votre abonnement aux alertes climatiques a été pris en compte avec succès.",
      );
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg).join(" · ")
            : "Échec de l’inscription. Vérifiez le format E.164 (+243…) pour téléphone / WhatsApp.";
      setStatus(msg);
    } finally {
      setSubLoading(false);
    }
  }

  async function submitUnsubscribe() {
    if (!formFilled()) {
      setStatus("Renseignez au minimum l’e-mail pour identifier votre abonnement.");
      return;
    }
    setSubLoading(true);
    setStatus(null);
    try {
      await api.post("/public/unsubscribe", {
        email: subEmail.trim(),
        phone_e164: subPhone.trim() || null,
        whatsapp_e164: subWhatsapp.trim() || null,
        user_type: userType !== "other" ? userType : null,
      });
      setStatus("Votre demande de désabonnement a été enregistrée.");
    } catch {
      setStatus("Impossible d’enregistrer la demande. Réessayez plus tard.");
    } finally {
      setSubLoading(false);
    }
  }

  if (success) {
    return (
      <div className="mx-auto max-w-xl rounded-2xl border border-brand-mint/40 bg-brand-mint/10 p-6 text-sm text-slate-800 dark:text-slate-100">
        <p className="font-semibold text-brand-green">Merci. Votre abonnement aux alertes climatiques a été pris en compte avec succès.</p>
        <p className="mt-2 text-xs opacity-90">Vous recevrez les notifications selon les canaux choisis.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-1 text-sm font-semibold text-brand-green">Abonnement aux alertes</div>
      <p className="mb-2 text-xs text-slate-600 dark:text-slate-300">
        Inscription facultative pour Kolwezi. Votre position est détectée automatiquement (GPS, puis IP ou dernière position connue).
      </p>
      <p className="mb-4 text-xs text-brand-mint">{locLabel}</p>

      <form
        action={FORMSPREE_URL}
        method="POST"
        onSubmit={submitSubscribe}
        className="space-y-4 text-sm"
      >
        <input type="hidden" name="home_lat" value={homeLat ?? ""} />
        <input type="hidden" name="home_lon" value={homeLon ?? ""} />
        <input type="hidden" name="location_source" value={locationSource} />

        <div>
          <label className="text-sm font-medium">E-mail (obligatoire)</label>
          <input
            required
            type="email"
            name="email"
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 outline-none ring-brand-mint focus:ring-2 dark:border-slate-800 dark:bg-slate-950"
            value={subEmail}
            onChange={(e) => setSubEmail(e.target.value)}
            autoComplete="email"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Téléphone (SMS), format E.164</label>
          <input
            type="tel"
            name="phone_e164"
            placeholder="+243…"
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 outline-none ring-brand-mint focus:ring-2 dark:border-slate-800 dark:bg-slate-950"
            value={subPhone}
            onChange={(e) => setSubPhone(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium">WhatsApp, format E.164</label>
          <input
            type="tel"
            name="whatsapp_e164"
            placeholder="+243…"
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 outline-none ring-brand-mint focus:ring-2 dark:border-slate-800 dark:bg-slate-950"
            value={subWhatsapp}
            onChange={(e) => setSubWhatsapp(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="subscribe-user-type" className="text-sm font-medium">
            Type d&apos;utilisateur
          </label>
          <select
            id="subscribe-user-type"
            name="user_type"
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-950"
            value={userType}
            onChange={(e) => setUserType(e.target.value)}
          >
            {USER_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="subscribe-school" className="text-sm font-medium">
            École / association (optionnel)
          </label>
          <select
            id="subscribe-school"
            name="school_id"
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-800 dark:bg-slate-950"
            value={subSchoolId}
            onChange={(e) => setSubSchoolId(e.target.value)}
          >
            <option value="">— Non renseigné —</option>
            {schoolOptions.map((s) => (
              <option key={s.id} value={String(s.id)}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2 rounded-xl border border-slate-100 p-3 dark:border-slate-800">
          <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">Canaux souhaités</div>
          <Toggle label="E-mail" name="alert_email" checked={chEmail} onChange={setChEmail} />
          <Toggle label="SMS" name="alert_sms" checked={chSms} onChange={setChSms} />
          <Toggle label="WhatsApp" name="alert_whatsapp" checked={chWa} onChange={setChWa} />
        </div>
        <button
          type="submit"
          disabled={subLoading}
          className="w-full rounded-lg bg-brand-green py-2.5 text-sm font-semibold text-white hover:bg-brand-mint disabled:opacity-60"
        >
          {subLoading ? "Envoi…" : "Valider mon abonnement"}
        </button>
        <button
          type="button"
          disabled={subLoading || !formFilled()}
          onClick={() => void submitUnsubscribe()}
          className="w-full rounded-lg border border-slate-300 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
        >
          Demande de désabonnement
        </button>
      </form>
      {status ? <div className="mt-4 text-xs text-slate-700 dark:text-slate-200">{status}</div> : null}
    </div>
  );
}

function Toggle(props: { label: string; name: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 px-3 py-2 dark:border-slate-800">
      <span>{props.label}</span>
      <input
        type="checkbox"
        name={props.name}
        checked={props.checked}
        onChange={(e) => props.onChange(e.target.checked)}
        className="accent-brand-mint"
      />
    </label>
  );
}
