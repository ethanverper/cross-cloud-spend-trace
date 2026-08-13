import { useState } from "react"
import { NavLink } from "react-router-dom"
import { Menu, Moon, Sun } from "lucide-react"
import { Wordmark } from "./Wordmark"
import { NAV_ITEMS } from "./nav-config"
import { useTheme } from "@/lib/theme-context"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet"
import { cn } from "@/lib/utils"

function NavLinks({ onNavigate, orientation = "row" }: { onNavigate?: () => void; orientation?: "row" | "col" }) {
  return (
    <nav className={cn("flex", orientation === "row" ? "items-center gap-1" : "flex-col gap-1")}>
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === "/"}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              isActive ? "text-signal bg-signal/10" : "text-muted-foreground hover:text-foreground hover:bg-accent",
            )
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

export function Header() {
  const { theme, toggle } = useTheme()
  const [open, setOpen] = useState(false)

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 md:px-6">
        <NavLink to="/" className="shrink-0">
          <Wordmark size="sm" />
        </NavLink>

        <div className="hidden lg:flex">
          <NavLinks />
        </div>

        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 active:scale-[0.98] transition-transform"
            onClick={toggle}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>

          <div className="lg:hidden">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Open menu">
                  <Menu className="h-4 w-4" />
                </Button>
              </SheetTrigger>
              <SheetContent side="right" className="w-64">
                <SheetTitle className="px-4 pt-4">
                  <Wordmark size="sm" />
                </SheetTitle>
                <div className="p-4">
                  <NavLinks orientation="col" onNavigate={() => setOpen(false)} />
                </div>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </header>
  )
}
