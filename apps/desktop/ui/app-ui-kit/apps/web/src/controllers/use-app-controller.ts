import { useState } from "react"

export type PageId = "login" | "dashboard" | "security"

export const PAGE_TITLES: Record<PageId, string> = {
  login: "Login",
  dashboard: "Dashboard",
  security: "Security Status",
}

export function useAppController() {
  const [activePage, setActivePage] = useState<PageId>("login")

  function navigate(page: string) {
    if (
      page === "login" ||
      page === "dashboard" ||
      page === "security"
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