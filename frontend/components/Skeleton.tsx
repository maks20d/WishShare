"use client";

/**
 * Базовый компонент скелетона с настраиваемыми параметрами
 */
interface SkeletonProps {
  className?: string;
  variant?: "default" | "circle" | "rounded";
  animation?: "default" | "fast" | "slow";
}

export function Skeleton({ 
  className = "", 
  variant = "default",
  animation = "default" 
}: SkeletonProps) {
  const variantClasses = {
    default: "rounded-lg",
    circle: "rounded-full",
    rounded: "rounded-xl"
  };
  
  const animationClasses = {
    default: "skeleton",
    fast: "skeleton skeleton-fast",
    slow: "skeleton skeleton-slow"
  };

  return (
    <div 
      className={`${animationClasses[animation]} ${variantClasses[variant]} ${className}`}
    />
  );
}

/**
 * Скелетон карточки подарка
 */
export function GiftCardSkeleton() {
  return (
    <div className="surface-panel p-4 flex gap-4 animate-fade-in">
      <div className="skeleton w-20 h-20 shrink-0 rounded-xl" />
      <div className="flex-1 space-y-3">
        <div className="skeleton h-5 w-3/4 skeleton-fast" />
        <div className="skeleton h-4 w-1/2" />
        <div className="flex items-center gap-2">
          <div className="skeleton h-3 w-16" />
          <div className="skeleton h-3 w-12" />
        </div>
      </div>
    </div>
  );
}

/**
 * Скелетон карточки вишлиста для дашборда
 */
export function WishlistCardSkeleton() {
  return (
    <article className="surface-panel p-5 space-y-4 animate-fade-in">
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="skeleton h-6 w-2/3 skeleton-fast" />
          <div className="skeleton h-5 w-16 rounded-full" />
        </div>
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
        <div className="flex gap-3">
          <div className="skeleton h-4 w-12" />
          <div className="skeleton h-4 w-20" />
          <div className="skeleton h-4 w-16" />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="skeleton h-10 w-full rounded-xl skeleton-fast" />
        <div className="skeleton h-10 w-full rounded-xl skeleton-fast" />
        <div className="skeleton h-10 w-full rounded-xl skeleton-fast" />
        <div className="skeleton h-10 w-full rounded-xl skeleton-fast" />
      </div>
    </article>
  );
}

/**
 * Скелетон страницы вишлиста с заголовком и списком подарков
 */
export function WishlistSkeleton() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Заголовок вишлиста */}
      <header className="surface-panel-strong p-6 md:p-8 space-y-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="skeleton h-9 w-20 rounded-xl skeleton-fast" />
              <div className="skeleton h-4 w-24 rounded-full" />
            </div>
            <div className="skeleton h-9 w-64 skeleton-fast" />
            <div className="skeleton h-4 w-96" />
            <div className="skeleton h-4 w-72" />
          </div>
          <div className="flex flex-col items-end gap-3">
            <div className="skeleton h-9 w-40 rounded-xl" />
            <div className="skeleton w-36 h-36 rounded-lg" />
          </div>
        </div>
      </header>
      
      {/* Форма добавления подарка (для владельца) */}
      <div className="surface-panel p-5 space-y-4">
        <div className="skeleton h-5 w-40 skeleton-fast" />
        <div className="grid gap-3 md:grid-cols-2">
          <div className="skeleton h-10 rounded-xl" />
          <div className="skeleton h-10 rounded-xl" />
          <div className="skeleton h-10 rounded-xl" />
          <div className="skeleton h-10 rounded-xl" />
        </div>
        <div className="skeleton h-10 w-32 rounded-xl" />
      </div>
      
      {/* Сетка подарков */}
      <div className="grid gap-4 md:grid-cols-2">
        <GiftCardSkeleton />
        <GiftCardSkeleton />
        <GiftCardSkeleton />
        <GiftCardSkeleton />
      </div>
    </div>
  );
}

/**
 * Скелетон списка вишлистов для дашборда
 */
export function DashboardWishlistsSkeleton({ count = 3 }: { count?: number }) {
  return (
    <section className="space-y-3 animate-fade-in">
      <div className="skeleton h-8 w-40 skeleton-fast" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {Array.from({ length: count }).map((_, i) => (
          <WishlistCardSkeleton key={i} />
        ))}
      </div>
    </section>
  );
}

/**
 * Скелетон формы
 */
export function FormSkeleton({ fields = 3 }: { fields?: number }) {
  return (
    <div className="surface-panel p-6 space-y-4 animate-fade-in">
      <div className="skeleton h-6 w-1/3 skeleton-fast" />
      <div className="space-y-3">
        {Array.from({ length: fields }).map((_, i) => (
          <div key={i} className="space-y-2">
            <div className="skeleton h-4 w-20" />
            <div className="skeleton h-10 w-full rounded-xl" />
          </div>
        ))}
      </div>
      <div className="skeleton h-10 w-32 rounded-xl" />
    </div>
  );
}

/**
 * Скелетон профиля пользователя
 */
export function ProfileSkeleton() {
  return (
    <div className="flex items-center gap-4 animate-fade-in">
      <div className="skeleton w-12 h-12 rounded-full skeleton-fast" />
      <div className="space-y-2">
        <div className="skeleton h-4 w-24" />
        <div className="skeleton h-3 w-32" />
      </div>
    </div>
  );
}

/**
 * Скелетон статистики
 */
export function StatsSkeleton({ count = 2 }: { count?: number }) {
  return (
    <div className="flex gap-3 flex-wrap md:justify-end animate-fade-in">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="surface-panel px-4 py-3 min-w-[150px] border border-[var(--line-strong)]">
          <div className="skeleton h-3 w-16 mb-2 skeleton-fast" />
          <div className="skeleton h-7 w-10" />
        </div>
      ))}
    </div>
  );
}

/**
 * Скелетон страницы авторизации (вход/регистрация)
 */
export function AuthPageSkeleton({ showNameField = false }: { showNameField?: boolean }) {
  return (
    <main className="min-h-screen px-4 py-10 grid-mesh">
      <div className="max-w-5xl mx-auto w-full grid gap-8 md:grid-cols-[1fr_0.8fr] md:items-start">
        {/* Левая колонка - форма */}
        <div className="space-y-6 animate-fade-in">
          <div className="space-y-3">
            <div className="skeleton h-6 w-24 rounded-full" />
            <div className="skeleton h-9 w-48 skeleton-fast" />
            <div className="skeleton h-4 w-64" />
          </div>

          <div className="surface-panel-strong p-7 space-y-5">
            {/* Поля формы */}
            <div className="space-y-4">
              {showNameField && (
                <div className="space-y-2">
                  <div className="skeleton h-4 w-12" />
                  <div className="skeleton h-11 w-full rounded-xl" />
                </div>
              )}
              <div className="space-y-2">
                <div className="skeleton h-4 w-12" />
                <div className="skeleton h-11 w-full rounded-xl" />
              </div>
              <div className="space-y-2">
                <div className="skeleton h-4 w-16" />
                <div className="skeleton h-11 w-full rounded-xl" />
              </div>
              
              {/* Кнопка отправки */}
              <div className="skeleton h-11 w-full rounded-xl skeleton-fast" />
            </div>

            {/* Разделитель */}
            <div className="flex items-center gap-3">
              <div className="h-px bg-[var(--line)] flex-1" />
              <div className="skeleton h-3 w-16" />
              <div className="h-px bg-[var(--line)] flex-1" />
            </div>

            {/* OAuth кнопки */}
            <div className="grid grid-cols-2 gap-2">
              <div className="skeleton h-10 rounded-xl" />
              <div className="skeleton h-10 rounded-xl" />
            </div>

            {/* Ссылка внизу */}
            <div className="skeleton h-4 w-48 mx-auto" />
          </div>
        </div>

        {/* Правая колонка - информация */}
        <aside className="surface-panel p-7 space-y-5 animate-fade-in hidden md:block">
          <div className="space-y-2">
            <div className="skeleton h-3 w-32" />
            <div className="skeleton h-7 w-48 skeleton-fast" />
            <div className="skeleton h-4 w-full" />
          </div>
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="skeleton w-2 h-2 rounded-full mt-1.5" />
                <div className="skeleton h-4 flex-1" />
              </div>
            ))}
          </div>
        </aside>
      </div>
    </main>
  );
}

/**
 * Скелетон для страницы входа
 */
export function LoginSkeleton() {
  return <AuthPageSkeleton showNameField={false} />;
}

/**
 * Скелетон для страницы регистрации
 */
export function RegisterSkeleton() {
  return <AuthPageSkeleton showNameField={true} />;
}

/**
 * Скелетон для модального окна
 */
export function ModalSkeleton({ title = true }: { title?: boolean }) {
  return (
    <div className="surface-panel-strong p-6 space-y-4 animate-scale-in">
      {title && <div className="skeleton h-6 w-40 skeleton-fast" />}
      <div className="space-y-3">
        <div className="skeleton h-10 w-full rounded-xl" />
        <div className="skeleton h-10 w-full rounded-xl" />
      </div>
      <div className="flex gap-3 justify-end">
        <div className="skeleton h-9 w-20 rounded-xl" />
        <div className="skeleton h-9 w-24 rounded-xl skeleton-fast" />
      </div>
    </div>
  );
}

/**
 * Скелетон для карточки с изображением
 */
export function ImageCardSkeleton() {
  return (
    <div className="surface-panel overflow-hidden animate-fade-in">
      <div className="skeleton h-40 w-full rounded-none" />
      <div className="p-4 space-y-3">
        <div className="skeleton h-5 w-3/4 skeleton-fast" />
        <div className="skeleton h-4 w-1/2" />
        <div className="flex justify-between items-center">
          <div className="skeleton h-4 w-20" />
          <div className="skeleton h-8 w-24 rounded-xl" />
        </div>
      </div>
    </div>
  );
}