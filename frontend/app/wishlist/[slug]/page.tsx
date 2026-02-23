"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { api } from "../../../lib/api";
import { connectWishlistWs } from "../../../lib/ws";
import { useAuthStore } from "../../../store/auth";
import EditGiftModal from "../../../components/EditGiftModal";
import { ConfirmModal } from "../../../components/ConfirmModal";
import { useToast } from "../../../components/Toast";
import { WishlistSkeleton } from "../../../components/Skeleton";

type Reservation = {
  id: number;
  user_id?: number | null;
  user_name?: string | null;
  user_email?: string | null;
};

type Contribution = {
  id: number;
  user_id: number;
  amount: number;
  user_name?: string | null;
  user_email?: string | null;
};

type Gift = {
  id: number;
  title: string;
  url?: string | null;
  price?: number | null;
  image_url?: string | null;
  is_collective: boolean;
  is_private: boolean;
  is_reserved: boolean;
  reservation: Reservation | null;
  contributions: Contribution[];
  total_contributions: number;
  collected_percent: number;
  is_fully_collected: boolean;
};

type Wishlist = {
  id: number;
  slug: string;
  title: string;
  description?: string | null;
  event_date?: string | null;
  privacy?: "link_only" | "friends" | "public";
  owner_id: number;
  gifts: Gift[];
  public_token?: string | null;
};

type OgPreviewResponse = {
  url: string;
  title?: string | null;
  price?: number | null;
  image_url?: string | null;
  description?: string | null;
  brand?: string | null;
  currency?: string | null;
  availability?: string | null;
};

const rubFormatter = new Intl.NumberFormat("ru-RU");

function formatRub(value: number): string {
  return rubFormatter.format(Math.round(value));
}

function giftsWord(count: number): string {
  const mod100 = count % 100;
  const mod10 = count % 10;
  if (mod100 >= 11 && mod100 <= 14) {
    return "подарков";
  }
  if (mod10 === 1) {
    return "подарок";
  }
  if (mod10 >= 2 && mod10 <= 4) {
    return "подарка";
  }
  return "подарков";
}

function normalizeUrlLike(value: string): string {
  return value.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/\/+$/, "");
}

function isBlockedOrTechnicalTitle(title: string): boolean {
  const text = title.trim().toLowerCase();
  if (!text) return true;
  return (
    text.includes("почти готово") ||
    text.includes("just a moment") ||
    text.includes("attention required") ||
    text.includes("access denied") ||
    text.includes("captcha") ||
    text.includes("robot check") ||
    text.includes("проверка, что вы человек") ||
    text.includes("cloudflare") ||
    text === "wildberries" ||
    text === "ozon" ||
    text === "lamoda" ||
    text.includes("интернет-магазин") ||
    text.includes("маркетплейс")
  );
}

function getHost(value: string): string | null {
  try {
    const normalized = /^https?:\/\//i.test(value) ? value : `https://${value}`;
    return new URL(normalized).hostname.replace(/^www\./i, "").toLowerCase();
  } catch {
    return null;
  }
}

function looksLikeUrlTitle(title: string, sourceUrl?: string | null): boolean {
  const cleanTitle = normalizeUrlLike(title);
  if (!cleanTitle) return true;
  if (sourceUrl && cleanTitle === normalizeUrlLike(sourceUrl)) return true;
  if (cleanTitle.startsWith("http://") || cleanTitle.startsWith("https://")) return true;
  return false;
}

export default function WishlistPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const { user, fetchMe } = useAuthStore();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [giftTitle, setGiftTitle] = useState("");
  const [giftUrl, setGiftUrl] = useState("");
  const [giftPrice, setGiftPrice] = useState<string>("");
  const [giftImageUrl, setGiftImageUrl] = useState("");
  const [giftIsCollective, setGiftIsCollective] = useState(false);
  const [giftIsPrivate, setGiftIsPrivate] = useState(false);
  const [isAutofilling, setIsAutofilling] = useState(false);
  const [contributionError, setContributionError] = useState<string | null>(null);
  const [activeContributionGift, setActiveContributionGift] = useState<Gift | null>(null);
  const [contributionValue, setContributionValue] = useState("");
  const [isContributionModalOpen, setIsContributionModalOpen] = useState(false);
  const [createGiftError, setCreateGiftError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [editingGift, setEditingGift] = useState<Gift | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [deleteConfirmGift, setDeleteConfirmGift] = useState<Gift | null>(null);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const {
    data: wishlist,
    refetch,
    isLoading,
    isError
  } = useQuery<Wishlist>({
    queryKey: ["wishlist", slug],
    queryFn: () => api.get(`/wishlists/${slug}`)
  });

  useEffect(() => {
    if (!slug) return;
    const disconnect = connectWishlistWs(slug, () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist", slug] });
    });
    return disconnect;
  }, [slug, queryClient]);

  const isOwner = useMemo(
    () => (user && wishlist ? user.id === wishlist.owner_id : false),
    [user, wishlist]
  );

  const getContributionBounds = (gift: Gift | null) => {
    if (!gift || gift.price == null) return null;
    const remaining = Math.max(gift.price - gift.total_contributions, 0);
    if (remaining <= 0) return null;
    const min = Math.min(Math.max(gift.price * 0.1, 1), remaining);
    return { min, max: remaining };
  };

  const isAuthenticated = !!user;
  const contributionBounds = getContributionBounds(activeContributionGift);

  const privacyLabel = useMemo(() => {
    if (!wishlist) return "";
    if (wishlist.privacy === "public") return "Публичный";
    if (wishlist.privacy === "friends") return "Только авторизованные";
    return "По ссылке";
  }, [wishlist]);

  const handleCopyLink = async () => {
    const publicUrl =
      wishlist?.public_token
        ? `${window.location.origin}/w/${wishlist.public_token}`
        : `${window.location.origin}/wishlist/${slug}`;
    await navigator.clipboard.writeText(publicUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const confirmDeleteGift = async () => {
    if (!deleteConfirmGift) return;

    try {
      await api.delete(`/gifts/${deleteConfirmGift.id}`);
      await refetch();
      showToast("Подарок удалён", "success");
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Ошибка удаления", "error");
    } finally {
      setDeleteConfirmGift(null);
    }
  };

  const handleCreateGift = async (e: FormEvent) => {
    e.preventDefault();
    if (!wishlist) return;

    setCreateGiftError(null);

    const priceValue = Number.parseFloat(giftPrice);
    if (!Number.isFinite(priceValue) || priceValue <= 0) {
      setCreateGiftError("Укажите корректную цену больше 0");
      return;
    }

    try {
      await api.post(`/wishlists/${wishlist.slug}/gifts`, {
        title: giftTitle,
        url: giftUrl || undefined,
        price: priceValue,
        image_url: giftImageUrl || undefined,
        is_collective: giftIsCollective,
        is_private: giftIsPrivate
      });
    } catch (err) {
      setCreateGiftError(err instanceof Error ? err.message : "Не удалось добавить подарок");
      return;
    }

    setGiftTitle("");
    setGiftUrl("");
    setGiftPrice("");
    setGiftImageUrl("");
    setGiftIsCollective(false);
    setGiftIsPrivate(false);
    await refetch();
  };

  const handleAutofill = async () => {
    if (!giftUrl) return;
    setCreateGiftError(null);
    setIsAutofilling(true);
    
    // Нормализация URL
    let normalizedUrl = giftUrl.trim();
    if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
      normalizedUrl = 'https://' + normalizedUrl;
    }
    
    try {
      const data = await api.post<OgPreviewResponse>("/parse-url", {
        url: normalizedUrl
      });

      const parsedTitle = typeof data.title === "string" ? data.title : null;
      const sourceHost = getHost(normalizedUrl);
      const resultHost = data.url ? getHost(data.url) : null;
      
      // Проверяем, что title не является техническим/заблокированным
      const hasGoodTitle =
        !!parsedTitle &&
        parsedTitle.trim().length > 2 &&
        !looksLikeUrlTitle(parsedTitle, data.url || normalizedUrl) &&
        !isBlockedOrTechnicalTitle(parsedTitle);
      
      let filledAny = false;
      let filledFields: string[] = [];
      
      if (hasGoodTitle) {
        setGiftTitle(parsedTitle.trim());
        filledFields.push('название');
        filledAny = true;
      }
      
      if (data.price != null && data.price > 0) {
        setGiftPrice(String(data.price));
        filledFields.push('цену');
        filledAny = true;
      }
      
      if (data.image_url) {
        setGiftImageUrl(data.image_url);
        filledFields.push('изображение');
        filledAny = true;
      }

      // Если ничего не заполнилось
      if (!filledAny) {
        // Проверяем конкретные причины
        if (parsedTitle && isBlockedOrTechnicalTitle(parsedTitle)) {
          setCreateGiftError(
            "Сайт защищён от автоматического сбора данных (Cloudflare, капча и т.д.). " +
            "Введите данные вручную или попробуйте ссылку на другой товар."
          );
        } else if (parsedTitle && looksLikeUrlTitle(parsedTitle, data.url || normalizedUrl)) {
          setCreateGiftError(
            "Не удалось получить название товара с этой страницы. " +
            "Возможно, ссылка ведёт не на карточку товара. Введите данные вручную."
          );
        } else {
          setCreateGiftError(
            "Не удалось извлечь данные товара. " +
            "Проверьте, что ссылка ведёт на страницу товара, и введите данные вручную."
          );
        }
        return;
      }

      // Если заполнилось только что-то одно и нет названия
      if (!hasGoodTitle && filledAny) {
        setCreateGiftError(
          `Автозаполнение получило только ${filledFields.join(', ')}. ` +
          `Название товара не найдено — введите его вручную.`
        );
        return;
      }

      // Успешное заполнение
      if (filledFields.length > 0) {
        // Successfully filled fields
      }

    } catch (err) {
      let errorMessage = "Не удалось выполнить автозаполнение";
      
      if (err instanceof Error) {
        if (err.message.includes("HTTP 500") || err.message.includes("Internal server error")) {
          errorMessage = 
            "Ошибка сервера при обработке ссылки. " +
            "Убедитесь, что бэкенд запущен, и попробуйте ещё раз.";
        } else if (err.message.includes("HTTP 429") || err.message.includes("Rate limit")) {
          errorMessage = 
            "Слишком много запросов. Подождите минуту и попробуйте снова.";
        } else if (err.message.includes("Network") || err.message.includes("Failed to fetch")) {
          errorMessage = 
            "Не удалось подключиться к серверу. " +
            "Проверьте, что бэкенд запущен (http://localhost:8000).";
        } else if (err.message.includes("HTTP 404")) {
          errorMessage = 
            "Эндпоинт автозаполнения не найден. Убедитесь, что бэкенд запущен.";
        } else {
          errorMessage = err.message;
        }
      }
      
      setCreateGiftError(errorMessage);
    } finally {
      setIsAutofilling(false);
    }
  };

  const handleReserve = async (gift: Gift) => {
    await api.post(`/gifts/${gift.id}/reserve`);
    await refetch();
  };

  const handleCancelReservation = async (gift: Gift) => {
    await api.post(`/gifts/${gift.id}/cancel-reservation`);
    await refetch();
  };

  const handleCancelContribution = async (gift: Gift) => {
    try {
      await api.post(`/gifts/${gift.id}/cancel-contribution`);
      await refetch();
    } catch (err) {
      if (err instanceof Error) {
        setContributionError(err.message);
      } else {
        setContributionError("Не удалось отменить вклад");
      }
    }
  };

  const openContributionModal = (gift: Gift) => {
    setContributionError(null);
    setActiveContributionGift(gift);
    setContributionValue("");
    setIsContributionModalOpen(true);
  };

  const closeContributionModal = () => {
    setIsContributionModalOpen(false);
    setActiveContributionGift(null);
    setContributionValue("");
  };

  const handleContribute = async () => {
    const gift = activeContributionGift;
    if (!gift) return;
    setContributionError(null);
    if (!contributionValue) {
      setContributionError("Введите сумму вклада");
      return;
    }
    const amount = Number.parseFloat(contributionValue);
    if (!Number.isFinite(amount) || amount <= 0) {
      setContributionError("Введите корректную сумму вклада");
      return;
    }
    try {
      await api.post(`/gifts/${gift.id}/contribute`, {
        amount
      });
      closeContributionModal();
      await refetch();
    } catch (err) {
      if (err instanceof Error && err.message) {
        setContributionError(err.message);
      } else {
        setContributionError("Не удалось внести вклад");
      }
    }
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

  if (!wishlist || isError) {
    return (
      <main className="min-h-screen px-4 py-10 grid-mesh">
        <div className="max-w-3xl mx-auto surface-panel-strong p-8 space-y-3 text-center">
          <h1 className="text-2xl font-semibold">Не удалось открыть вишлист</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Проверьте ссылку или войдите в аккаунт, если доступ ограничен.
          </p>
          <Link href="/auth/login" className="btn-primary">
            Войти
          </Link>
        </div>
      </main>
    );
  }

  const actionsDisabled = !isAuthenticated;

  return (
    <main className="min-h-screen text-slate-50 px-4 py-8 md:py-10 grid-mesh">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="surface-panel-strong p-6 md:p-8 space-y-6 hero-glow">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <a href="/dashboard" className="btn-ghost text-sm">
                  ← Назад
                </a>
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
            </div>
            {isOwner && (
              <div className="flex flex-col items-end gap-3">
                <button onClick={handleCopyLink} className="btn-ghost text-sm md:text-base">
                  {copied ? "Ссылка скопирована" : "Поделиться ссылкой"}
                </button>
                {wishlist.public_token ? (
                  <div className="p-2 bg-white rounded-lg">
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

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="surface-panel px-4 py-3 border border-[var(--line-strong)]">
              <p className="text-xs text-[var(--text-secondary)]">Подарков</p>
              <p className="text-2xl font-bold">
                {wishlist.gifts.length} {giftsWord(wishlist.gifts.length)}
              </p>
            </div>
            <div className="surface-panel px-4 py-3 border border-[var(--line-strong)]">
              <p className="text-xs text-[var(--text-secondary)]">Коллективных</p>
              <p className="text-2xl font-bold">
                {wishlist.gifts.filter((gift) => gift.is_collective).length}
              </p>
            </div>
            <div className="surface-panel px-4 py-3 border border-[var(--line-strong)]">
              <p className="text-xs text-[var(--text-secondary)]">Дата события</p>
              <p className="text-sm md:text-base font-semibold pt-1">
                {wishlist.event_date
                  ? new Date(wishlist.event_date).toLocaleDateString("ru-RU", {
                      year: "numeric",
                      month: "long",
                      day: "numeric"
                    })
                  : "Не указана"}
              </p>
            </div>
          </div>
        </header>

        {actionsDisabled && (
          <section className="surface-panel border-emerald-400/30 bg-emerald-400/8 px-4 py-3 text-sm text-emerald-100">
            Чтобы зарезервировать подарок или внести вклад, <Link href={`/auth/login?next=${encodeURIComponent(`/wishlist/${slug}`)}`} className="underline font-semibold">войдите</Link> или <Link href={`/auth/register?next=${encodeURIComponent(`/wishlist/${slug}`)}`} className="underline font-semibold">зарегистрируйтесь</Link>.
          </section>
        )}

        {isOwner && (
          <section className="surface-panel p-6 md:p-7 space-y-4">
            <div className="flex items-center gap-3">
              <Link href="/dashboard" className="btn-ghost text-sm">
                ← Назад
              </Link>
              <div>
                <h2 className="text-xl md:text-2xl font-semibold">Добавить подарок</h2>
                <p className="text-sm text-[var(--text-secondary)] mt-1">
                  Укажите цену и тип подарка. Для коллективного сбора друзья смогут вносить сумму частями.
                </p>
              </div>
            </div>

            {createGiftError && (
              <div className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                {createGiftError}
              </div>
            )}

            <form onSubmit={handleCreateGift} className="grid gap-3 md:grid-cols-2">
              <div className="md:col-span-2">
                <label htmlFor="gift-title" className="text-sm text-[var(--text-secondary)]">
                  Название
                </label>
                <input
                  id="gift-title"
                  value={giftTitle}
                  onChange={(e) => setGiftTitle(e.target.value)}
                  placeholder="Например: Наушники Sony"
                  required
                  className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="md:col-span-2">
                <label htmlFor="gift-url" className="text-sm text-[var(--text-secondary)]">
                  Ссылка на товар
                </label>
                <div className="mt-1 flex gap-2">
                  <input
                    id="gift-url"
                    value={giftUrl}
                    onChange={(e) => setGiftUrl(e.target.value)}
                    placeholder="https://..."
                    className="flex-1 rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <button
                    type="button"
                    onClick={handleAutofill}
                    disabled={!giftUrl || isAutofilling}
                    className="btn-ghost px-4"
                  >
                    {isAutofilling ? "Заполняем..." : "Автозаполнение"}
                  </button>
                </div>
              </div>

              <div>
                <label htmlFor="gift-price" className="text-sm text-[var(--text-secondary)]">
                  Цена
                </label>
                <input
                  id="gift-price"
                  type="number"
                  min={1}
                  step={1}
                  value={giftPrice}
                  onChange={(e) => setGiftPrice(e.target.value)}
                  placeholder="0"
                  required
                  className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label htmlFor="gift-image-url" className="text-sm text-[var(--text-secondary)]">
                  Ссылка на изображение
                </label>
                <input
                  id="gift-image-url"
                  type="url"
                  value={giftImageUrl}
                  onChange={(e) => setGiftImageUrl(e.target.value)}
                  placeholder="https://.../image.jpg"
                  className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="space-y-2">
                <span className="block text-sm text-[var(--text-secondary)]">Режим</span>
                <label className="flex items-center gap-2 rounded-xl border border-[var(--line)] bg-slate-950/45 px-3 py-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={giftIsCollective}
                    onChange={(e) => setGiftIsCollective(e.target.checked)}
                    className="rounded border-[var(--line)] bg-slate-900"
                  />
                  <span className="text-sm">Коллективный сбор</span>
                </label>
                <label className="flex items-center gap-2 rounded-xl border border-[var(--line)] bg-slate-950/45 px-3 py-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={giftIsPrivate}
                    onChange={(e) => setGiftIsPrivate(e.target.checked)}
                    className="rounded border-[var(--line)] bg-slate-900"
                  />
                  <span className="text-sm">Приватный подарок</span>
                </label>
              </div>

              {giftImageUrl && (
                <div className="md:col-span-2 h-36 rounded-xl overflow-hidden border border-[var(--line)] bg-slate-900/40 relative">
                  <Image
                    src={giftImageUrl}
                    alt="Предпросмотр изображения подарка"
                    fill
                    sizes="(max-width: 768px) 100vw, 50vw"
                    className="object-cover"
                    unoptimized
                  />
                </div>
              )}

              <button type="submit" className="btn-primary md:col-span-2">
                Добавить подарок
              </button>
            </form>
          </section>
        )}

        {contributionError && (
          <div className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">
            {contributionError}
          </div>
        )}

        {wishlist.gifts.length === 0 ? (
          <section className="surface-panel p-8 md:p-10 text-center space-y-2">
            <h2 className="text-2xl font-semibold">Список пока пуст</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              {isOwner
                ? "Добавьте первый подарок через форму выше."
                : "Владелец ещё не добавил подарки в этот вишлист."}
            </p>
          </section>
        ) : (
          <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {wishlist.gifts.map((gift) => {
              const reserved = gift.is_reserved || !!gift.reservation;
              const canReserve = !actionsDisabled && !isOwner && !gift.is_collective && !reserved;

              const canCancelReservation =
                !actionsDisabled &&
                !isOwner &&
                !gift.is_collective &&
                reserved &&
                gift.reservation?.user_id === user?.id;

              const canContribute =
                !actionsDisabled &&
                !isOwner &&
                gift.is_collective &&
                !gift.is_fully_collected;

              const userContribution = gift.contributions.find((c) => c.user_id === user?.id);
              const canCancelContribution = !actionsDisabled && !!userContribution && !gift.is_fully_collected;
              const reservationLabel =
                gift.reservation?.user_name || gift.reservation?.user_email || "друг";

              const minimumContribution =
                gift.is_collective && gift.price
                  ? Math.min(Math.max(gift.price * 0.1, 1), Math.max(gift.price - gift.total_contributions, 0))
                  : null;

              return (
                <article key={gift.id} className="surface-panel p-5 md:p-6 space-y-4">
                  {gift.image_url && (
                    <div className="h-40 rounded-xl overflow-hidden border border-[var(--line)] bg-slate-900/40 relative">
                      <Image
                        src={gift.image_url}
                        alt={gift.title}
                        fill
                        sizes="(max-width: 768px) 100vw, 50vw"
                        className="object-cover"
                        unoptimized
                      />
                    </div>
                  )}

                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <h3 className="text-lg md:text-xl font-semibold leading-tight">{gift.title}</h3>
                      {gift.price != null && (
                        <p className="text-emerald-300 font-semibold text-sm md:text-base">
                          {formatRub(gift.price)} ₽
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {gift.is_private && (
                        <span className="text-[11px] rounded-full border border-[var(--line)] px-2 py-1 text-[var(--text-secondary)]">
                          Приватный
                        </span>
                      )}
                      {gift.is_collective ? (
                        <span className="text-[11px] rounded-full border border-emerald-400/35 bg-emerald-400/10 px-2 py-1 text-emerald-200">
                          Сбор
                        </span>
                      ) : (
                        <span className="text-[11px] rounded-full border border-[var(--line)] px-2 py-1 text-[var(--text-secondary)]">
                          Резерв
                        </span>
                      )}
                    </div>
                  </div>

                  {gift.url && (
                    <a
                      href={gift.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex text-sm text-emerald-300 hover:text-emerald-200 break-all"
                    >
                      Открыть товар
                    </a>
                  )}

                  {gift.is_collective && gift.price != null && (
                    <div className="space-y-2">
                      <div className="w-full h-2.5 rounded-full bg-slate-900/80 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all"
                          style={{ width: `${Math.min(100, gift.collected_percent)}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
                        <span>
                          Собрано {formatRub(gift.total_contributions)} ₽ из {formatRub(gift.price)} ₽
                        </span>
                        <span>{Math.round(gift.collected_percent)}%</span>
                      </div>
                      {gift.is_fully_collected && (
                        <div className="rounded-lg border border-emerald-400/35 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-100">
                          Подарок полностью собран.
                        </div>
                      )}
                    </div>
                  )}

                  {!gift.is_collective && reserved && (
                    <div className="rounded-lg border border-emerald-400/35 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-100">
                      {isOwner || actionsDisabled ? "Подарок зарезервирован" : `Зарезервировано: ${reservationLabel}`}
                    </div>
                  )}

                  {!isOwner && isAuthenticated && gift.is_collective && gift.contributions.length > 0 && (
                    <div className="space-y-2 border-t border-[var(--line)] pt-3">
                      <p className="text-xs uppercase tracking-wide text-[var(--text-secondary)]">Вклады</p>
                      <div className="space-y-1.5">
                        {gift.contributions.map((contribution) => (
                          <div
                            key={contribution.id}
                            className={`rounded-lg px-3 py-2 text-xs flex items-center justify-between ${
                              contribution.user_id === user?.id
                                ? "bg-emerald-500/15 border border-emerald-400/35"
                                : "bg-slate-900/50 border border-[var(--line)]"
                            }`}
                          >
                            <span>
                              {contribution.user_name || contribution.user_email || "Участник"}
                            </span>
                            <span className="font-semibold">{formatRub(contribution.amount)} ₽</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="space-y-2 border-t border-[var(--line)] pt-3">
                    {!gift.is_collective && (
                      <>
                        <button
                          disabled={!canReserve}
                          onClick={() => handleReserve(gift)}
                          className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {reserved ? "Уже зарезервировано" : "Зарезервировать"}
                        </button>
                        {canCancelReservation && (
                          <button
                            type="button"
                            onClick={() => handleCancelReservation(gift)}
                            className="w-full btn-ghost"
                          >
                            Отменить резерв
                          </button>
                        )}
                      </>
                    )}

                    {gift.is_collective && (
                      <div className="space-y-2">
                        <button
                          type="button"
                          disabled={!canContribute}
                          onClick={() => openContributionModal(gift)}
                          className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          Внести вклад
                        </button>
                        {minimumContribution != null && !gift.is_fully_collected && (
                          <p className="text-xs text-[var(--text-secondary)]">
                            Минимальный вклад: {formatRub(minimumContribution)} ₽
                          </p>
                        )}
                        {canCancelContribution && (
                          <button
                            type="button"
                            onClick={() => handleCancelContribution(gift)}
                            className="w-full btn-ghost"
                          >
                            Отменить мой вклад
                          </button>
                        )}
                      </div>
                    )}
                  </div>

                  {isOwner && (
                    <div className="flex gap-2 border-t border-[var(--line)] pt-3">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingGift(gift);
                          setIsEditModalOpen(true);
                        }}
                        className="btn-ghost flex-1"
                      >
                        Редактировать
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteConfirmGift(gift)}
                        className="rounded-xl px-4 py-3 text-sm font-medium transition border border-red-400/40 bg-red-500/10 text-red-200 hover:bg-red-500/20"
                      >
                        Удалить
                      </button>
                    </div>
                  )}
                </article>
              );
            })}
          </section>
        )}
      </div>

      {editingGift && (
        <EditGiftModal
          gift={editingGift}
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSave={() => refetch()}
        />
      )}

      {isContributionModalOpen && activeContributionGift && (
        <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="surface-panel-strong w-full max-w-lg p-6 md:p-7 space-y-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold">Внести вклад</h2>
                <p className="text-sm text-[var(--text-secondary)] mt-1">
                  {activeContributionGift.title}
                </p>
              </div>
              <button
                type="button"
                onClick={closeContributionModal}
                className="btn-ghost px-3 py-2 text-xs"
              >
                Закрыть
              </button>
            </div>

            {contributionError && (
              <div className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                {contributionError}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (contributionBounds) {
                  handleContribute();
                }
              }}
              className="space-y-4"
            >
              <div className="space-y-2 text-sm text-[var(--text-secondary)]">
                {contributionBounds ? (
                  <>
                    <p>
                      Осталось собрать: {formatRub(contributionBounds.max)} ₽
                    </p>
                    <p>
                      Минимальный вклад: {formatRub(contributionBounds.min)} ₽
                    </p>
                  </>
                ) : (
                  <p>Подарок уже полностью собран.</p>
                )}
              </div>

              <input
                type="number"
                min={contributionBounds?.min}
                max={contributionBounds?.max}
                step={1}
                value={contributionValue}
                onChange={(e) => setContributionValue(e.target.value)}
                placeholder="Сумма вклада"
                className="w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />

              <div className="flex gap-2 pt-1">
                <button type="button" onClick={closeContributionModal} className="btn-ghost flex-1">
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={!contributionBounds}
                  className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Внести
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <ConfirmModal
        isOpen={deleteConfirmGift !== null}
        title="Удалить подарок?"
        message="Это действие нельзя отменить."
        confirmText="Удалить"
        cancelText="Отмена"
        confirmVariant="danger"
        onConfirm={confirmDeleteGift}
        onCancel={() => setDeleteConfirmGift(null)}
      />
    </main>
  );
}
