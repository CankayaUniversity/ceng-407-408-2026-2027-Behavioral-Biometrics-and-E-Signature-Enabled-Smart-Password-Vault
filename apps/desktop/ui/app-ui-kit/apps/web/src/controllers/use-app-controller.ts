import { useState } from "react"

export type PageId = "login" | "dashboard" | "security" | "enrollment"

export const PAGE_TITLES: Record<PageId, string> = {
  login: "Login",
  dashboard: "Dashboard",
  security: "Security Status",
  enrollment: "Enrollment",
}

export function useAppController() {
  const [activePage, setActivePage] = useState<PageId>("login")

  function navigate(page: string) {
    if (
      page === "login" ||
      page === "dashboard" ||
      page === "security" ||
      page === "enrollment"
    ) {
      setActivePage(page)
    }
  }

  return {
    activePage,
    pageTitle: PAGE_TITLES[activePage],
    navigate,
  }
}
