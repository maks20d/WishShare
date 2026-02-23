"use client";

import { FormEvent, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useToast } from "../Toast";

interface Props {
  onCreated: () => void;
}

const parseEmails = (value: string): string[] =>
  value.split(/[\n,;]+/).map((e) => e.trim().toLowerCase()).filter(Boolean);

export default function CreateTab({ onCreated }: Props) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [privacy, setPrivacy] = useState<"link_only" | "friends" | "public">("link_only");
  const [isSecretSanta, setIsSecretSanta] = useState(false);
  const [accessEmailsInput, setAccessEmailsInput] = useState("");

  const reset = () => {
    setTitle(""); setDescription(""); setEventDate("");
    setPrivacy("link_only"); setIsSecretSanta(false); setAccessEmailsInput("");
  };

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.post("/wishlists", {
        title,
        description: description || null,
        event_date: eventDate || null,
        privacy,
        is_secret_santa: isSecretSanta,
        access_emails: privacy === "friends" ? parseEmails(accessEmailsInput) : [],
      });
      reset();
      await queryClient.invalidateQueries({ queryKey: ["my-wishlists"] });
      toast("Вишлист создан!", "success");
      onCreated();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Не удалось создать вишлист", "error");
    } finally {
      setCreating(false);
    }
  };

  return (
    <section className="surface-panel p-6 md:p-7 space-y-4">
      <div>
        <h2 className="text-2xl font-semibold">Создать новый вишлист</h2>
        <p className="text-sm text-[var(--text-secondary)] mt-1">Название, описание и уровень доступа можно задать сразу.</p>
      </div>
      <form onSubmit={handleCreate} className="grid gap-3 md:grid-cols-2">
        <input
          value={title} onChange={(e) => setTitle(e.target.value)}
          placeholder="Название события" required minLength={1} maxLength={255}
          className="rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
        />
        <input
          type="date" value={eventDate} onChange={(e) => setEventDate(e.target.value)}
          className="rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
        />
        <textarea
          value={description} onChange={(e) => setDescription(e.target.value)}
          placeholder="Короткое описание (опционально)" maxLength={2000}
          className="md:col-span-2 rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm min-h-[96px] focus:outline-none focus:ring-2 focus:ring-emerald-400"
        />
        <select
          value={privacy} onChange={(e) => setPrivacy(e.target.value as "link_only" | "friends" | "public")}
          className="rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-400"
        >
          <option value="link_only">По ссылке</option>
          <option value="friends">Только по email</option>
          <option value="public">Публичный</option>
        </select>
        {privacy === "friends" && (
          <div className="md:col-span-2">
            <label className="text-sm text-[var(--text-secondary)]">Email-адреса с доступом</label>
            <textarea
              value={accessEmailsInput} onChange={(e) => setAccessEmailsInput(e.target.value)}
              placeholder={"email1@example.com\nemail2@example.com"}
              className="mt-1 w-full rounded-xl bg-slate-950/70 border border-[var(--line)] px-4 py-3 text-sm min-h-[96px] focus:outline-none focus:ring-2 focus:ring-emerald-400"
            />
            <p className="text-xs text-[var(--text-secondary)] mt-2">Укажите email в отдельных строках или через запятую.</p>
          </div>
        )}
        <label className="rounded-xl border border-[var(--line)] px-4 py-3 flex items-center justify-between text-sm">
          <span className="text-[var(--text-secondary)]">Secret Santa режим</span>
          <input type="checkbox" checked={isSecretSanta} onChange={(e) => setIsSecretSanta(e.target.checked)} className="h-4 w-4 accent-emerald-400" />
        </label>
        <button type="submit" disabled={creating} className="btn-primary md:col-span-2">
          {creating ? "Создаём..." : "Создать вишлист"}
        </button>
      </form>
    </section>
  );
}
