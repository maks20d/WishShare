"use client";

import { FormEvent, useState } from "react";
import Image from "next/image";
import { api } from "../../lib/api";
import { useToast } from "../Toast";
import { OgPreviewResponse, Wishlist } from "../../app/wishlist/[slug]/types";

function getHost(value: string): string | null {
  try { return new URL(value).hostname; } catch { return null; }
}
function normalizeUrlLike(value: string): string {
  return value.replace(/^https?:\/\//, "").replace(/\/$/, "").split("?")[0].split("#")[0];
}
function isBlockedOrTechnicalTitle(title: string): boolean {
  const lower = title.toLowerCase();
  return ["access denied","403 forbidden","captcha","cloudflare","just a moment","ddos","bot"].some(k => lower.includes(k));
}
function looksLikeUrlTitle(title: string, sourceUrl?: string | null): boolean {
  if (!sourceUrl) return false;
  const norm = normalizeUrlLike(sourceUrl).toLowerCase();
  return title.toLowerCase().includes(norm.slice(0, 20));
}

interface Props {
  wishlist: Wishlist;
  onRefetch: () => void;
}

export default function AddGiftForm({ wishlist, onRefetch }: Props) {
  const { toast } = useToast();
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [price, setPrice] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [isCollective, setIsCollective] = useState(false);
  const [isPrivate, setIsPrivate] = useState(false);
  const [isAutofilling, setIsAutofilling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => { setTitle(""); setUrl(""); setPrice(""); setImageUrl(""); setIsCollective(false); setIsPrivate(false); };

  const handleAutofill = async () => {
    if (!url) return;
    setError(null);
    setIsAutofilling(true);
    try {
      const data = await api.post<OgPreviewResponse>("/parse-url", { url });
      const parsedTitle = typeof data.title === "string" ? data.title : null;
      const hasGoodTitle = !!parsedTitle && !looksLikeUrlTitle(parsedTitle, data.url || url) && !isBlockedOrTechnicalTitle(parsedTitle);
      let filledAny = false;
      if (hasGoodTitle) { setTitle(parsedTitle); filledAny = true; }
      if (data.price != null) { setPrice(String(data.price)); filledAny = true; }
      if (data.image_url) { setImageUrl(data.image_url); filledAny = true; }
      if (!filledAny) setError("Не удалось извлечь данные по этой ссылке. Введите поля вручную.");
      else if (!hasGoodTitle) setError("Название не определилось автоматически. Заполните его вручную.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить автозаполнение");
    } finally {
      setIsAutofilling(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const priceValue = price ? Number.parseFloat(price) : null;
    if (price && (!Number.isFinite(priceValue) || (priceValue ?? 0) <= 0)) {
      setError("Укажите корректную цену больше 0");
      return;
    }
    try {
      await api.post(`/wishlists/${wishlist.slug}/gifts`, {
        title,
        url: url || undefined,
        price: priceValue,
        image_url: imageUrl || undefined,
        is_collective: isCollective,
        is_private: isPrivate,
      });
      reset();
      onRefetch();
      toast("Подарок добавлен!", "success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить подарок");
    }
  };

  return (
    <section className="surface-panel p-5 md:p-7 space-y-4">
      <h2 className="text-xl font-semibold">Добавить подарок</h2>
      {error && (
        <div className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">{error}</div>
      )}
      <form onSubmit={handleSubmit} className="grid gap-3 md:grid-cols-2">
        <div className="md:col-span-2 flex gap-2">
          <input
            value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Ссылка на товар (опционально)"
            className="flex-1 rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
          />
          <button type="button" onClick={handleAutofill} disabled={!url || isAutofilling}
            className="rounded-xl px-4 py-3 text-sm border border-[var(--line-strong)] bg-slate-800/50 hover:bg-slate-700/50 transition disabled:opacity-40">
            {isAutofilling ? "..." : "Заполнить"}
          </button>
        </div>

        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Название подарка" required
          className="md:col-span-2 rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />

        <input value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Цена (₽, опционально)" type="number" min="1" step="any"
          className="rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />

        <input value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="URL изображения"
          className="rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400" />

        <label className="rounded-xl border border-[var(--line)] px-4 py-3 flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Коллективный сбор</span>
          <input type="checkbox" checked={isCollective} onChange={(e) => setIsCollective(e.target.checked)} className="h-4 w-4 accent-emerald-400" />
        </label>

        <label className="rounded-xl border border-[var(--line)] px-4 py-3 flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Приватный</span>
          <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)} className="h-4 w-4 accent-emerald-400" />
        </label>

        {imageUrl && (
          <div className="md:col-span-2 h-32 rounded-xl overflow-hidden border border-[var(--line)] bg-slate-900/40 relative">
            <Image src={imageUrl} alt="Предпросмотр" fill sizes="100vw" className="object-cover" unoptimized />
          </div>
        )}

        <button type="submit" className="btn-primary md:col-span-2">Добавить подарок</button>
      </form>
    </section>
  );
}
