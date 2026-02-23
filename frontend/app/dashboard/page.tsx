"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "../../store/auth";
import EditWishlistModal from "../../components/EditWishlistModal";
import Tabs from "../../components/Tabs";
import WishlistsTab, { Wishlist } from "../../components/dashboard/WishlistsTab";
import CreateTab from "../../components/dashboard/CreateTab";
import ProfileTab from "../../components/dashboard/ProfileTab";

function GiftsIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19a4 4 0 00-6 0m8-9a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}

const TABS = [
  { id: "wishlists", label: "Вишлисты", icon: <GiftsIcon /> },
  { id: "create", label: "Создать", icon: <PlusIcon /> },
  { id: "profile", label: "Профиль", icon: <UserIcon /> },
];

export default function DashboardPage() {
  const { user, fetchMe, logout } = useAuthStore();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState("wishlists");
  const [editingWishlist, setEditingWishlist] = useState<Wishlist | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  // Stats are derived from the first page query cache – show 0 until loaded
  const cachedWishlists = queryClient.getQueryData<Wishlist[]>(["my-wishlists", 0]);
  const stats = useMemo(() => {
    const list = cachedWishlists || [];
    return {
      totalWishlists: list.length,
      totalGifts: list.reduce((acc, w) => acc + w.gifts.length, 0),
    };
  }, [cachedWishlists]);

  if (!user) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-lg mx-auto surface-panel-strong p-8 text-center space-y-5">
          <h1 className="text-3xl font-bold">Доступ к кабинету</h1>
          <p className="text-sm text-[var(--text-secondary)]">Войдите в аккаунт, чтобы управлять своими вишлистами.</p>
          <Link href="/auth/login" className="btn-primary w-full">Войти</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-8 md:py-10 grid-mesh">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="surface-panel-strong p-6 md:p-8 grid gap-6 md:grid-cols-[1fr_auto] md:items-center">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">Управление</p>
            <h1 className="text-3xl md:text-4xl font-semibold">Ваши вишлисты</h1>
            <p className="text-sm text-[var(--text-secondary)] max-w-2xl">
              Создавайте списки, отслеживайте прогресс и делитесь ссылками с друзьями.
            </p>
          </div>
          <div className="flex gap-3 flex-wrap md:justify-end">
            <div className="surface-panel px-4 py-3 min-w-[150px] border border-[var(--line-strong)]">
              <p className="text-xs text-[var(--text-secondary)]">Вишлистов</p>
              <p className="text-2xl font-semibold">{stats.totalWishlists}</p>
            </div>
            <div className="surface-panel px-4 py-3 min-w-[150px] border border-[var(--line-strong)]">
              <p className="text-xs text-[var(--text-secondary)]">Подарков</p>
              <p className="text-2xl font-semibold">{stats.totalGifts}</p>
            </div>
            <button
              onClick={async () => {
                await logout();
                queryClient.clear();
              }}
              className="btn-ghost"
            >
              Выйти
            </button>
          </div>
        </header>

        <Tabs tabs={TABS} defaultTab={activeTab} onChange={setActiveTab}>
          {(tab) => (
            <>
              {tab === "wishlists" && (
                <WishlistsTab
                  onEdit={(w) => { setEditingWishlist(w); setIsModalOpen(true); }}
                  onCreateClick={() => setActiveTab("create")}
                />
              )}
              {tab === "create" && (
                <CreateTab onCreated={() => setActiveTab("wishlists")} />
              )}
              {tab === "profile" && <ProfileTab />}
            </>
          )}
        </Tabs>
      </div>

      {editingWishlist && (
        <EditWishlistModal
          wishlist={editingWishlist}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSave={() => queryClient.invalidateQueries({ queryKey: ["my-wishlists"] })}
        />
      )}
    </main>
  );
}
