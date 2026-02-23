"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api";
import { connectWishlistWs } from "../../../lib/ws";
import { useAuthStore } from "../../../store/auth";
import EditGiftModal from "../../../components/EditGiftModal";
import AddGiftForm from "../../../components/wishlist/AddGiftForm";
import GiftCard from "../../../components/wishlist/GiftCard";
import ContributionModal from "../../../components/wishlist/ContributionModal";
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
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuthStore();

  const [activeContributionGift, setActiveContributionGift] = useState<Gift | null>(null);
  const [editingGift, setEditingGift] = useState<Gift | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const { data: wishlist, isLoading, isError, refetch } = useQuery<Wishlist>({
    queryKey: ["wishlist", slug],
    queryFn: () => api.get<Wishlist>(`/wishlists/${slug}`),
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

  if (isLoading) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-3xl mx-auto surface-panel-strong p-8 text-center text-[var(--text-secondary)]">
          Загрузка вишлиста...
        </div>
      </main>
    );
  }

  if (isError || !wishlist) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-3xl mx-auto surface-panel-strong p-8 text-center space-y-4">
          <h1 className="text-2xl font-bold">Вишлист не найден</h1>
          <p className="text-sm text-[var(--text-secondary)]">Ссылка недействительна или вишлист удалён.</p>
          <Link href="/" className="btn-primary inline-block">На главную</Link>
        </div>
      </main>
    );
  }

  const isOwner = !!user && user.id === wishlist.owner_id;
  const isAuthenticated = !!user;
  const actionsDisabled = isOwner;

  const handleCopyLink = async () => {
    const url = wishlist.public_token
      ? `${window.location.origin}/w/${wishlist.public_token}`
      : window.location.href;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <main className="min-h-screen px-4 py-8 md:py-10 grid-mesh">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <header className="surface-panel-strong p-6 md:p-8 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">Вишлист</p>
              <h1 className="text-3xl md:text-4xl font-semibold">{wishlist.title}</h1>
            </div>
            <button onClick={handleCopyLink} className="btn-ghost text-sm shrink-0">
              {copied ? "Скопировано ✓" : "Поделиться"}
            </button>
          </div>
          {wishlist.description && (
            <p className="text-sm text-[var(--text-secondary)] max-w-2xl">{wishlist.description}</p>
          )}
          <div className="flex flex-wrap gap-4 text-sm text-[var(--text-secondary)]">
            <span>🎁 {wishlist.gifts.length} {giftsWord(wishlist.gifts.length)}</span>
            {wishlist.event_date && (
              <span>📅 {new Date(wishlist.event_date).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })}</span>
            )}
          </div>
        </header>

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

        {/* Unauthenticated call to action */}
        {!isAuthenticated && (
          <section className="surface-panel p-6 text-center space-y-3">
            <p className="text-sm text-[var(--text-secondary)]">Войдите, чтобы зарезервировать подарок или внести вклад.</p>
            <Link href={`/auth/login?next=/wishlist/${wishlist.slug}`} className="btn-primary inline-block">Войти</Link>
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
