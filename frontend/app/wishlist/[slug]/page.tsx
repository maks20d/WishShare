"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { api, ApiError } from "../../../lib/api";
import { connectWishlistWs } from "../../../lib/ws";
import { useAuthStore } from "../../../store/auth";
import EditGiftModal from "../../../components/EditGiftModal";
import { useToast } from "../../../components/Toast";
import { WishlistSkeleton } from "../../../components/Skeleton";
import AddGiftForm from "../../../components/wishlist/AddGiftForm";
import GiftCard from "../../../components/wishlist/GiftCard";
import ContributionModal from "../../../components/wishlist/ContributionModal";
import { encodePathParam, normalizeRouteParam } from "../../../lib/routeParams";
import { Gift, Wishlist } from "./types";

function giftsWord(count: number): string {
  const mod100 = count % 100;
  const mod10 = count % 10;
  if (mod100 >= 11 && mod100 <= 14) return "подарков";
  if (mod10 === 1) return "подарок";
  if (mod10 >= 2 && mod10 <= 4) return "подарка";
  return "подарков";
}

export default function WishlistPage() {
  const { slug: rawSlug } = useParams<{ slug?: string | string[] }>();
  const slug = normalizeRouteParam(rawSlug);
  const encodedSlug = encodePathParam(slug);
  const { user } = useAuthStore();
  const { toast } = useToast();

  const [activeContributionGift, setActiveContributionGift] = useState<Gift | null>(null);
  const [editingGift, setEditingGift] = useState<Gift | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const { data: wishlist, isLoading, isError, error, refetch } = useQuery<Wishlist>({
    queryKey: ["wishlist", slug],
    queryFn: () => api.get<Wishlist>(`/wishlists/${encodedSlug}`),
    enabled: Boolean(slug && encodedSlug),
    retry: 1,
  });

  // WebSocket realtime updates
  useEffect(() => {
    if (!slug) return;
    const disconnect = connectWishlistWs(slug, (msg) => {
      if (msg.type === "gift_updated" || msg.type === "gift_reserved" || msg.type === "contribution_added") {
        refetch();
      }
    });
    return disconnect;
  }, [slug, refetch]);

  // Compute derived state - must be before any early returns
  const isOwner = useMemo(() => !!user && !!wishlist && user.id === wishlist.owner_id, [user, wishlist]);
  const isAuthenticated = !!user;
  const actionsDisabled = isOwner;

  const privacyLabel = useMemo(() => {
    if (!wishlist) return "";
    if (wishlist.privacy === "public") return "Публичный";
    if (wishlist.privacy === "friends") return "Только авторизованные";
    return "По ссылке";
  }, [wishlist]);

  const handleCopyLink = async () => {
    if (!wishlist) return;
    const url = wishlist.public_token
      ? `${window.location.origin}/w/${wishlist.public_token}`
      : window.location.href;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    toast("Ссылка скопирована", "success");
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-6xl mx-auto">
          <WishlistSkeleton />
        </div>
      </main>
    );
  }

  if (!slug) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-3xl mx-auto surface-panel-strong p-8 text-center space-y-4">
          <h1 className="text-2xl font-bold">Некорректная ссылка</h1>
          <p className="text-sm text-[var(--text-secondary)]">Проверьте адрес и попробуйте открыть вишлист снова.</p>
          <Link href="/" className="btn-primary inline-block">На главную</Link>
        </div>
      </main>
    );
  }

  const apiError = error as ApiError | undefined;
  const isAuthError = apiError?.code === "UNAUTHORIZED" || apiError?.code === "FORBIDDEN";

  if (isAuthError) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-3xl mx-auto surface-panel-strong p-8 text-center space-y-4">
          <h1 className="text-2xl font-bold">Доступ ограничен</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Для просмотра этого вишлиста нужно войти или получить доступ от владельца.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href={`/auth/login?next=${encodeURIComponent(`/wishlist/${encodedSlug}`)}`} className="btn-primary">
              Войти
            </Link>
            <Link href={`/auth/register?next=${encodeURIComponent(`/wishlist/${encodedSlug}`)}`} className="btn-ghost">
              Зарегистрироваться
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (isError || !wishlist) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-3xl mx-auto surface-panel-strong p-8 text-center space-y-4">
          <h1 className="text-2xl font-bold">Вишлист не найден</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {apiError?.message || "Ссылка недействительна или вишлист удалён."}
          </p>
          <Link href="/" className="btn-primary inline-block">На главную</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen text-slate-50 px-4 py-8 md:py-10 grid-mesh">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <header className="surface-panel-strong p-6 md:p-8 space-y-6 hero-glow">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <Link href="/dashboard" className="btn-ghost text-sm">
                  ← Назад
                </Link>
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">
                  <span>{privacyLabel}</span>
                </div>
              </div>
              <h1 className="text-3xl md:text-4xl font-bold leading-tight">{wishlist.title}</h1>
              {wishlist.description && (
                <p className="text-sm md:text-base text-[var(--text-secondary)] max-w-3xl">
                  {wishlist.description}
                </p>
              )}
              <div className="flex flex-wrap gap-4 text-sm text-[var(--text-secondary)]">
                <span>🎁 {wishlist.gifts.length} {giftsWord(wishlist.gifts.length)}</span>
                {wishlist.event_date && (
                  <span>📅 {new Date(wishlist.event_date).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })}</span>
                )}
              </div>
            </div>
            {isOwner && (
              <div className="flex flex-col md:items-end gap-3">
                <button onClick={handleCopyLink} className="btn-ghost text-sm md:text-base w-full md:w-auto">
                  {copied ? "Ссылка скопирована" : "Поделиться ссылкой"}
                </button>
                {wishlist.public_token ? (
                  <div className="hidden md:block p-2 bg-white rounded-lg">
                    <QRCodeSVG
                      value={`${typeof window !== "undefined" ? window.location.origin : ""}/w/${wishlist.public_token}`}
                      size={140}
                      level="M"
                      bgColor="#ffffff"
                      fgColor="#000000"
                    />
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </header>

        {/* Unauthenticated call to action */}
        {!isAuthenticated && (
          <section className="surface-panel border-emerald-400/30 bg-emerald-400/8 px-4 py-3 text-sm text-emerald-100">
            Чтобы зарезервировать подарок или внести вклад,{" "}
            <Link href={`/auth/login?next=${encodeURIComponent(`/wishlist/${encodedSlug}`)}`} className="underline font-semibold">
              войдите
            </Link>{" "}
            или{" "}
            <Link href={`/auth/register?next=${encodeURIComponent(`/wishlist/${encodedSlug}`)}`} className="underline font-semibold">
              зарегистрируйтесь
            </Link>.
          </section>
        )}

        {/* Owner: add gift form */}
        {isOwner && <AddGiftForm wishlist={wishlist} onRefetch={refetch} />}

        {/* Gifts grid */}
        {wishlist.gifts.length === 0 ? (
          <section className="surface-panel p-8 md:p-10 text-center space-y-2">
            <h2 className="text-2xl font-semibold">Список пока пуст</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              {isOwner ? "Добавьте первый подарок через форму выше." : "Владелец ещё не добавил подарки."}
            </p>
          </section>
        ) : (
          <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {wishlist.gifts.map((gift) => (
              <GiftCard
                key={gift.id}
                gift={gift}
                isOwner={isOwner}
                isAuthenticated={isAuthenticated}
                actionsDisabled={actionsDisabled}
                user={user}
                onRefetch={refetch}
                onOpenContribution={setActiveContributionGift}
                onEdit={(g) => { setEditingGift(g); setIsEditModalOpen(true); }}
              />
            ))}
          </section>
        )}
      </div>

      {/* Contribution modal */}
      {activeContributionGift && (
        <ContributionModal
          gift={activeContributionGift}
          onClose={() => setActiveContributionGift(null)}
          onRefetch={refetch}
        />
      )}

      {/* Edit gift modal */}
      {editingGift && (
        <EditGiftModal
          gift={editingGift}
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSave={() => { refetch(); setIsEditModalOpen(false); }}
        />
      )}
    </main>
  );
}
