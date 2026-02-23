/**
 * Basic client-side validators.
 * These mirror the server-side Pydantic rules for immediate UX feedback.
 */

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(value: string): boolean {
  return EMAIL_RE.test(value.trim());
}

export function validateEmail(value: string): string | null {
  if (!value.trim()) return "Email обязателен";
  if (!isValidEmail(value)) return "Введите корректный email";
  return null;
}

export function validatePassword(value: string): string | null {
  if (!value) return "Пароль обязателен";
  if (value.length < 8) return "Пароль должен содержать не менее 8 символов";
  if (value.length > 128) return "Пароль слишком длинный";
  return null;
}
