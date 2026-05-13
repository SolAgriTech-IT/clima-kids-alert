import { redirect } from "next/navigation";

/** Legacy URL: MVP dashboard is fully public. */
export default function LoginRedirectPage() {
  redirect("/dashboard");
}
