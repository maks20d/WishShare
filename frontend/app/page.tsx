"use client";

import Link from "next/link";
import InstallCenter from "../components/dashboard/InstallCenter";

export default function HomePage() {
  return (
    <main className="min-h-screen px-4 py-10 grid-mesh text-slate-50">
      <div className="max-w-6xl mx-auto space-y-10">
        <header className="surface-panel-strong p-8 md:p-10 hero-glow">
          <div className="grid gap-8 md:grid-cols-[1.2fr_0.8fr] md:items-center">
            <div className="space-y-5">
              <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">
                Социальный вишлист
              </p>
              <h1 className="text-4xl md:text-5xl font-semibold leading-tight">
                WishShare превращает подарки в сюрпризы, а сборы — в командную игру
              </h1>
              <p className="text-sm md:text-base text-[var(--text-secondary)] max-w-3xl">
                Создавайте списки желаний, отправляйте приватную ссылку друзьям и следите
                за прогрессом. Владелец видит только статус и сумму, имена остаются скрыты.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link href="/auth/register" className="btn-primary">
                  Создать вишлист
                </Link>
                <Link href="/auth/login" className="btn-ghost">
                  Войти
                </Link>
              </div>
            </div>
            <div className="space-y-4">
              <div className="surface-panel p-5 space-y-3">
                <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">
                  Контроль
                </p>
                <p className="text-2xl font-semibold">Сюрпризы без спойлеров</p>
                <p className="text-sm text-[var(--text-secondary)]">
                  Прогресс сборов виден всем, но данные участников скрыты от владельца.
                </p>
              </div>
              <div className="surface-panel p-5 space-y-3">
                <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-secondary)]">
                  Реалтайм
                </p>
                <p className="text-2xl font-semibold">Динамика в один клик</p>
                <p className="text-sm text-[var(--text-secondary)]">
                  Резерв, вклад или отмена моментально обновляют страницу без перезагрузки.
                </p>
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <div className="surface-panel p-6 space-y-3">
            <h2 className="text-lg font-semibold">Публичные ссылки</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Друзья открывают страницу по ссылке без регистрации и сразу видят доступные подарки.
            </p>
          </div>
          <div className="surface-panel p-6 space-y-3">
            <h2 className="text-lg font-semibold">Резерв и сбор</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Обычные подарки резервируются целиком, коллективные — собираются частями с лимитами.
            </p>
          </div>
          <div className="surface-panel p-6 space-y-3">
            <h2 className="text-lg font-semibold">Прозрачный прогресс</h2>
            <p className="text-sm text-[var(--text-secondary)]">
              Прогресс-бар показывает сбор, а владельцу скрыты имена участников.
            </p>
          </div>
        </section>

        <InstallCenter />
      </div>
    </main>
  );
}
