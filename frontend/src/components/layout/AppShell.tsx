import type { ReactNode } from "react"
import { Header } from "./Header"
import { Footer } from "./Footer"

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 mx-auto w-full max-w-7xl px-4 md:px-6 py-8 md:py-10">{children}</main>
      <Footer />
    </div>
  )
}
