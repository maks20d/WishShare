"use client";

import { FormEvent, useState, useRef, DragEvent } from "react";
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
  const [imageMode, setImageMode] = useState<"url" | "file">("url");
  const [localPreviewUrl, setLocalPreviewUrl] = useState<string | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [isCollective, setIsCollective] = useState(false);
  const [isPrivate, setIsPrivate] = useState(false);
  const [isAutofilling, setIsAutofilling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setTitle("");
    setUrl("");
    setPrice("");
    setImageUrl("");
    setImageMode("url");
    if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
    setLocalPreviewUrl(null);
    setUploadingImage(false);
    setIsCollective(false);
    setIsPrivate(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      handlePickFile(file);
    }
  };

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

  const handlePickFile = async (file: File | null) => {
    if (!file) return;
    setError(null);
    const allowed = new Set(["image/jpeg", "image/png", "image/webp"]);
    if (!allowed.has(file.type)) {
      setError("Поддерживаются только JPEG, PNG или WebP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Размер файла не должен превышать 5 МБ.");
      return;
    }
    if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
    const preview = URL.createObjectURL(file);
    setLocalPreviewUrl(preview);
    setUploadingImage(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const uploaded = await api.postForm<{ url: string; thumb_url: string }>("/uploads/images", form);
      setImageUrl(uploaded.url);
      toast("Изображение загружено", "success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить изображение");
    } finally {
      setUploadingImage(false);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handlePickFile(e.target.files?.[0] || null);
  };

  const handleRemoveImage = () => {
    if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
    setLocalPreviewUrl(null);
    setImageUrl("");
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

        <div className="md:col-span-2 space-y-2">
          <div role="group" aria-label="Способ добавления изображения" className="grid grid-cols-2 gap-2">
            <button
              type="button"
              aria-pressed={imageMode === "url"}
              onClick={() => {
                setImageMode("url");
                setError(null);
                if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
                setLocalPreviewUrl(null);
                setUploadingImage(false);
              }}
              className={`rounded-xl px-4 py-3 text-sm border ${imageMode === "url" ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-100" : "border-[var(--line)] bg-slate-950/70 text-[var(--text-secondary)] hover:bg-slate-900/60"}`}
            >
              По ссылке
            </button>
            <button
              type="button"
              aria-pressed={imageMode === "file"}
              onClick={() => {
                setImageMode("file");
                setError(null);
              }}
              className={`rounded-xl px-4 py-3 text-sm border ${imageMode === "file" ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-100" : "border-[var(--line)] bg-slate-950/70 text-[var(--text-secondary)] hover:bg-slate-900/60"}`}
            >
              Загрузить файл
            </button>
          </div>

          {imageMode === "url" ? (
            <input
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
              placeholder="URL изображения (JPEG/PNG/WebP)"
              className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
            />
          ) : (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative rounded-xl border-2 border-dashed transition-colors ${
                isDragging 
                  ? "border-emerald-400 bg-emerald-400/10" 
                  : "border-[var(--line)] bg-slate-950/70"
              } px-4 py-5 text-center`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileInputChange}
                disabled={uploadingImage}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-not-allowed"
                aria-label="Загрузить изображение"
              />
              <div className="space-y-2 pointer-events-none">
                {uploadingImage ? (
                  <>
                    <div className="animate-spin w-8 h-8 border-2 border-emerald-400 border-t-transparent rounded-full mx-auto" />
                    <p className="text-sm text-[var(--text-secondary)]">Загрузка...</p>
                  </>
                ) : isDragging ? (
                  <>
                    <svg className="w-10 h-10 mx-auto text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <p className="text-sm text-emerald-100">Отпустите для загрузки</p>
                  </>
                ) : (
                  <>
                    <svg className="w-10 h-10 mx-auto text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <p className="text-sm text-[var(--text-secondary)]">
                      Перетащите файл или <span className="text-emerald-400">выберите</span>
                    </p>
                    <p className="text-xs text-slate-500">JPEG, PNG, WebP до 5 МБ</p>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        <label className="rounded-xl border border-[var(--line)] px-4 py-3 flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Коллективный сбор</span>
          <input type="checkbox" checked={isCollective} onChange={(e) => setIsCollective(e.target.checked)} className="h-4 w-4 accent-emerald-400" />
        </label>

        <label className="rounded-xl border border-[var(--line)] px-4 py-3 flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Приватный</span>
          <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)} className="h-4 w-4 accent-emerald-400" />
        </label>

        {(localPreviewUrl || imageUrl) && (
          <div className="md:col-span-2 h-32 rounded-xl overflow-hidden border border-[var(--line)] bg-slate-900/40 relative group">
            <Image src={localPreviewUrl || imageUrl} alt="Предпросмотр изображения" fill sizes="100vw" className="object-cover" unoptimized />
            <button
              type="button"
              onClick={handleRemoveImage}
              className="absolute top-2 right-2 bg-slate-900/80 hover:bg-red-500/80 text-white p-1.5 rounded-lg transition opacity-0 group-hover:opacity-100"
              aria-label="Удалить изображение"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        <button type="submit" className="btn-primary md:col-span-2">Добавить подарок</button>
      </form>
    </section>
  );
}
