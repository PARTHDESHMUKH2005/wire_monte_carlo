export function getApiBaseUrl() {
  const value = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const trimmed = value.trim().replace(/\/+$/, "");

  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  return `https://${trimmed}`;
}
