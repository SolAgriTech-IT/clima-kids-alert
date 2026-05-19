"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Footer } from "@/components/Footer";
import { api } from "@/lib/api";
import { fetchCurrentUser, isAdminUser } from "@/lib/admin";
import { clearToken, setToken } from "@/lib/auth";

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("mulombodi@sol-agri-tech.org");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post("/auth/login", { email: email.trim(), password });
      setToken(resp.data.access_token);
      const me = await fetchCurrentUser();
      if (!isAdminUser(me)) {
        clearToken();
        setError("Ce compte n’est pas administrateur. Créez un admin via SEED_ADMIN_* ou la CLI manage_admin.");
        return;
      }
      router.push("/admin/simulations");
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 401) {
        setError("Identifiants incorrects. Essayez SEED_RESET_ADMIN_PASSWORD=true une fois (voir README).");
      } else if (status === 403) {
        setError("Compte désactivé.");
      } else {
        setError("Connexion impossible. Vérifiez que l’API est démarrée.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <AdminLoginCard
            email={email}
            password={password}
            error={error}
            loading={loading}
            onEmail={setEmail}
            onPassword={setPassword}
            onSubmit={onSubmit}
          />
        </div>
      </div>
      <Footer />
    </div>
  );
}

function AdminLoginCard(props: {
  email: string;
  password: string;
  error: string | null;
  loading: boolean;
  onEmail: (v: string) => void;
  onPassword: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}) {
  return (
    <>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand-warn">Administration</div>
      <div className="mb-6 flex items-center gap-3">
        <Image src="/solagritech-logo.jpg" alt="SolAgriTech" width={56} height={56} className="rounded-full" />
        <div>
          <div className="text-lg font-bold text-brand-green">CLIMA-KIDS ALERT</div>
          <div className="text-sm text-slate-600 dark:text-slate-300">Connexion réservée aux administrateurs</div>
          <p className="mt-1 text-xs text-slate-500">
            Déploiement par défaut : voir SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD dans le README.
          </p>
        </div>
      </div>
      <form onSubmit={props.onSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium">E-mail</label>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-brand-mint focus:ring-2 dark:border-slate-800 dark:bg-slate-950"
            value={props.email}
            onChange={(e) => props.onEmail(e.target.value)}
            type="email"
            name="email"
            required
            autoComplete="username"
          />
        </div>
        <div>
          <label className="text-sm font-medium">Mot de passe</label>
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-brand-mint focus:ring-2 dark:border-slate-800 dark:bg-slate-950"
            value={props.password}
            onChange={(e) => props.onPassword(e.target.value)}
            type="password"
            name="password"
            required
            autoComplete="current-password"
          />
        </div>
        {props.error ? <div className="text-sm text-brand-alert">{props.error}</div> : null}
        <button
          type="submit"
          disabled={props.loading}
          className="w-full rounded-lg bg-brand-green py-2 text-sm font-semibold text-white hover:bg-brand-mint disabled:opacity-60"
        >
          {props.loading ? "Connexion…" : "Se connecter (admin)"}
        </button>
      </form>
      <div className="mt-6 text-center text-sm">
        <Link href="/dashboard" className="text-brand-mint underline">
          Retour au tableau de bord public
        </Link>
      </div>
    </>
  );
}
