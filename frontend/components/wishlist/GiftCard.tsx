"use client";

import Image from "next/image";
import { Gift, User } from "../../app/wishlist/[slug]/types";
import { useToast } from "../Toast";
import { api } from "../../lib/api";

interface Props {
  gift: Gift;
  isOwner: boolean;
  isAuthenticated: boolean;
  actionsDisabled: boolean;
  user: User | null;
  onRefetch: () => void;
  onOpenContribution: (gift: Gift) => void;
  onEdit: (gift: Gift) => void;
}

const rubFormatter = new Intl.NumberFormat("ru-RU");
const formatRub = (v: number) => rubFormatter.format(Math.round(v));

export default function GiftCard({
  gift, isOwner, isAuthenticated, actionsDisabled, user, onRefetch, onOpenContribution, onEdit,
}: Props) {
  const { toast, confirm } = useToast();

  const reserved = gift.is_reserved || !!gift.reservation;
  const canReserve = !actionsDisabled && !isOwner && !gift.is_collective && !reserved;
  const canCancelReservation = !actionsDisabled && !isOwner && !gift.is_collective && reserved && gift.reservation?.user_id === user?.id;
  const canContribute = !actionsDisabled && !isOwner && gift.is_collective && !gift.is_fully_collected;
  const userContribution = gift.contributions.find((c) => c.user_id === user?.id);
  const canCancelContribution = !actionsDisabled && !!userContribution && !gift.is_fully_collected;
  const reservationLabel = gift.reservation?.user_name || gift.reservation?.user_email || "друг";
  const imageSrc = gift.image_thumb_url || gift.image_url;

  const handleReserve = async () => {
    try { await api.post(`/gifts/${gift.id}/reserve`); onRefetch(); }
    catch (err) { toast(err instanceof Error ? err.message : "Ошибка резервирования", "error"); }
  };

  const handleCancelReservation = async () => {
    try { await api.post(`/gifts/${gift.id}/cancel-reservation`); onRefetch(); }
    catch (err) { toast(err instanceof Error ? err.message : "Ошибка отмены резерва", "error"); }
  };

  const handleCancelContribution = async () => {
    try { await api.post(`/gifts/${gift.id}/cancel-contribution`); onRefetch(); }
    catch (err) { toast(err instanceof Error ? err.message : "Не удалось отменить вклад", "error"); }
  };

  const handleDelete = async () => {
    const ok = await confirm(`Удалить подарок «${gift.title}»?`);
    if (!ok) return;
    try { await api.delete(`/gifts/${gift.id}`); onRefetch(); toast("Подарок удалён", "success"); }
    catch (err) { toast(err instanceof Error ? err.message : "Ошибка удаления", "error"); }
  };

  return (
    <article className="surface-panel p-5 md:p-6 space-y-4">
      {imageSrc && (
        <div className="h-40 rounded-xl overflow-hidden border border-[var(--line)] bg-slate-900/40 relative">
          <Image src={imageSrc} alt={gift.title} fill sizes="(max-width: 768px) 100vw, 50vw" className="object-cover" unoptimized />
        </div>
      )}

      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h3 className="text-lg md:text-xl font-semibold leading-tight">{gift.title}</h3>
          {gift.price != null && (
            <p className="text-emerald-300 font-semibold text-sm md:text-base">{formatRub(gift.price)} ₽</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {gift.is_private && <span className="text-[11px] rounded-full border border-[var(--line)] px-2 py-1 text-[var(--text-secondary)]">Приватный</span>}
          {gift.is_collective
            ? <span className="text-[11px] rounded-full border border-emerald-400/35 bg-emerald-400/10 px-2 py-1 text-emerald-200">Сбор</span>
            : <span className="text-[11px] rounded-full border border-[var(--line)] px-2 py-1 text-[var(--text-secondary)]">Резерв</span>
          }
        </div>
      </div>

      {gift.url && (
        <a href={gift.url} target="_blank" rel="noreferrer" className="inline-flex text-sm text-emerald-300 hover:text-emerald-200 break-all">
          Открыть товар
        </a>
      )}

      {gift.is_collective && gift.price != null && (
        <div className="space-y-2">
          <div className="w-full h-2.5 rounded-full bg-slate-900/80 overflow-hidden">
            <div className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all" style={{ width: `${Math.min(100, gift.collected_percent)}%` }} />
          </div>
          <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
            <span>Собрано {formatRub(gift.total_contributions)} ₽ из {formatRub(gift.price)} ₽</span>
            <span>{Math.round(gift.collected_percent)}%</span>
          </div>
          {gift.is_fully_collected && (
            <div className="rounded-lg border border-emerald-400/35 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-100">Подарок полностью собран.</div>
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
              <div key={contribution.id} className={`rounded-lg px-3 py-2 text-xs flex items-center justify-between ${contribution.user_id === user?.id ? "border border-emerald-400/30 bg-emerald-400/10" : "bg-slate-900/40"}`}>
                <span className="text-[var(--text-secondary)]">{contribution.user_name || contribution.user_email || "Аноним"}</span>
                <span className="font-semibold">{formatRub(contribution.amount)} ₽</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 pt-1">
        {canReserve && (
          <button onClick={handleReserve} className="btn-primary text-sm flex-1">Зарезервировать</button>
        )}
        {canCancelReservation && (
          <button onClick={handleCancelReservation} className="btn-ghost text-sm flex-1">Отменить резерв</button>
        )}
        {canContribute && (
          <button onClick={() => onOpenContribution(gift)} className="btn-primary text-sm flex-1">Внести вклад</button>
        )}
        {canCancelContribution && (
          <button onClick={handleCancelContribution} className="btn-ghost text-sm">Отменить вклад</button>
        )}
        {isOwner && (
          <>
            <button onClick={() => onEdit(gift)} className="btn-ghost text-sm">Изменить</button>
            <button onClick={handleDelete} className="rounded-xl px-3 py-2 text-sm border border-red-400/40 bg-red-500/10 text-red-200 hover:bg-red-500/20 transition">Удалить</button>
          </>
        )}
      </div>
    </article>
  );
}
