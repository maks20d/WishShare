'use client';

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import { api } from "../../../lib/api";
import { encodePathParam, normalizeRouteParam } from "../../../lib/routeParams";

type Gift = {
  id: number;
  title: string;
  url: string | null;
  price: number | null;
  image_url: string | null;
  is_collective: boolean;
  is_private: boolean;
  created_at: string;
  is_reserved: boolean;
  total_contributions: number;
  collected_percent: number;
  is_fully_collected: boolean;
  is_unavailable?: boolean;
  unavailable_reason?: string | null;
};

type Wishlist = {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  event_date: string | null;
  privacy: "public" | "link_only" | "friends";
  created_at: string;
  owner_id: number;
  gifts: Gift[];
};

export default function PublicWishlistPage() {
  const params = useParams<{ token?: string | string[] }>();
  const token = normalizeRouteParam(params.token);
  const encodedToken = encodePathParam(token);
  const [data, setData] = useState<Wishlist | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const fetchData = async () => {
      try {
        const res = await api.get<Wishlist>(`/wishlists/token/${encodedToken}`);
        if (active) setData(res);
      } catch (e) {
        if (active) {
          setError(e instanceof Error ? e.message : "Не удалось загрузить вишлист");
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    if (token && encodedToken) fetchData();
    return () => {
      active = false;
    };
  }, [token, encodedToken]);

  const title = useMemo(() => data?.title ?? "Вишлист", [data]);

  if (loading) {
    return <div className="max-w-6xl mx-auto p-6">Загрузка…</div>;
  }
  if (!token) {
    return <div className="max-w-6xl mx-auto p-6 text-red-600">Некорректная ссылка</div>;
  }
  if (error) {
    return <div className="max-w-6xl mx-auto p-6 text-red-600">{error}</div>;
  }
  if (!data) {
    return <div className="max-w-6xl mx-auto p-6">Вишлист не найден</div>;
  }

  return (
    <main className="min-h-screen px-4 py-8 md:py-10 grid-mesh">
      <div className="max-w-6xl mx-auto space-y-6">
      <header className="surface-panel-strong p-5 md:p-7 space-y-2">
        <h1 className="text-2xl md:text-3xl font-bold">{title}</h1>
        {data.description ? (
          <p className="text-sm md:text-base text-[var(--text-secondary)]">{data.description}</p>
        ) : null}
      </header>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.gifts.map((g) => {
          const unavailable = !!g.is_unavailable;
          return (
            <article key={g.id} className={`surface-panel p-4 space-y-3 ${unavailable ? "opacity-70" : ""}`}>
              {g.image_url ? (
                <div className="relative w-full h-48 bg-[var(--surface)] rounded">
                  <Image
                    src={g.image_url}
                    alt={g.title}
                    fill
                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                    style={{ objectFit: "cover" }}
                    unoptimized
                  />
                </div>
              ) : null}
              <div className="space-y-1">
                <h3 className="font-semibold">
                  {g.url ? (
                    <a href={g.url} target="_blank" rel="noopener noreferrer" className="link">
                      {g.title}
                    </a>
                  ) : (
                    g.title
                  )}
                </h3>
                {typeof g.price === "number" ? (
                  <p className="text-sm">Цена: {g.price.toFixed(2)}</p>
                ) : null}
                <div className="text-xs text-[var(--text-secondary)]">
                  Сбор: {Math.min(g.collected_percent, 100).toFixed(0)}%
                  {g.is_fully_collected ? " (собрано)" : null}
                </div>
                {unavailable ? (
                  <div className="text-xs text-red-600">
                    Недоступен. {g.unavailable_reason || "Этот товар был удалён из каталога"}
                  </div>
                ) : null}
              </div>
            </article>
          );
        })}
      </section>
      </div>
    </main>
  );
}
