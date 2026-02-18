"use client";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ reset }: ErrorPageProps) {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="text-2xl font-semibold">Произошла ошибка</h1>
      <p className="text-sm text-neutral-500">Попробуйте перезагрузить страницу.</p>
      <button
        className="rounded-full bg-black px-5 py-2 text-sm font-semibold text-white"
        onClick={reset}
        type="button"
      >
        Повторить
      </button>
    </div>
  );
}
