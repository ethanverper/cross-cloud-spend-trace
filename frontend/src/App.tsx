import { Route, Routes } from "react-router-dom"
import { AppShell } from "@/components/layout/AppShell"
import { ThemeProvider } from "@/lib/theme-context"
import { FilterProvider } from "@/lib/filter-context"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Overview } from "@/pages/Overview"
import { Inputs } from "@/pages/Inputs"
import { Results } from "@/pages/Results"
import { Interpretation } from "@/pages/Interpretation"
import { RealWorld } from "@/pages/RealWorld"
import { ToolsAndTechnologies } from "@/pages/ToolsAndTechnologies"
import { ReferencesFormulas } from "@/pages/ReferencesFormulas"
import { About } from "@/pages/About"

export default function App() {
  return (
    <ThemeProvider>
      <TooltipProvider delayDuration={150}>
        <FilterProvider>
          <AppShell>
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/inputs" element={<Inputs />} />
              <Route path="/results" element={<Results />} />
              <Route path="/interpretation" element={<Interpretation />} />
              <Route path="/real-world" element={<RealWorld />} />
              <Route path="/tools" element={<ToolsAndTechnologies />} />
              <Route path="/references" element={<ReferencesFormulas />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </AppShell>
        </FilterProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}
