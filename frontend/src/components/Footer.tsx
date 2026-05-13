export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white/70 py-4 text-xs text-slate-600 dark:border-slate-800 dark:bg-slate-950/40 dark:text-slate-300">
      <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="font-semibold text-brand-green dark:text-emerald-300">SolAgriTech</div>
          <div>www.sol-agri-tech.org · infos@sol-agri-tech.org</div>
        </div>
        <div className="md:text-right">Tous droits réservés © SolAgriTech</div>
      </div>
    </footer>
  );
}
