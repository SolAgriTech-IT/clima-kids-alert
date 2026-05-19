import { api } from "./api";
import { getToken } from "./auth";

export type UserProfile = {
  id: number;
  email: string;
  role: "admin" | "user";
  full_name?: string | null;
};

export async function fetchCurrentUser(): Promise<UserProfile | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const resp = await api.get<UserProfile>("/users/me");
    return resp.data;
  } catch {
    return null;
  }
}

export function isAdminUser(user: UserProfile | null): boolean {
  if (!user) return false;
  const role = user.role;
  if (typeof role === "string") return role === "admin";
  return String(role) === "admin";
}
