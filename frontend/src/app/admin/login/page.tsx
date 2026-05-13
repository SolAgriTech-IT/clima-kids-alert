"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Footer } from "@/components/Footer";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const resp = await api.post("/auth/login", { email, password });
      setToken(resp.data.access_token);
      router.push("/dashboard");
    } catch {
      setError("Connexion impossible. Compte administrateur requis.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand-warn">Administration</div>
          <div className="mb-6 flex items-center gap-3">
            <Image src="/solagritech-logo.jpg" alt="SolAgriTech" width={56} height={56} className="rounded-full" />
            <div>
              <div className="text-lg font-bold text-brand-green">CLIMA-KIDS ALERT</div>
              <div className="text-sm text-slate-600 dark:text-slate-300">Connexion réservée (routes /api/v1/admin/*)</div>
            </div>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="text-sm font-medium">E-mail</label>
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-brand-mint focus:ring-2 dark:border-slate-800 dark:bg-slate-950"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                autoComplete="username"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Mot de passe</label>
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-brand-mint focus:ring-2 dark:border-slate-800 dark:bg-slate-950"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                autoComplete="current-password"
              />
            </div>
            {error ? <div className="text-sm text-brand-alert">{error}</div> : null}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-brand-green py-2 text-sm font-semibold text-white hover:bg-brand-mint disabled:opacity-60"
            >
              {loading ? "Connexion…" : "Se connecter (admin)"}
            </button>
          </form>

          <div className="mt-6 text-center text-sm">
            <Link href="/dashboard" className="text-brand-mint underline">
              Retour au tableau de bord public
            </Link>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
