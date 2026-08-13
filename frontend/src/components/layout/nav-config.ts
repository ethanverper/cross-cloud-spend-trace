export interface NavItem {
  to: string
  label: string
}

export const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Overview" },
  { to: "/inputs", label: "Inputs" },
  { to: "/results", label: "Results" },
  { to: "/interpretation", label: "Interpretation" },
  { to: "/real-world", label: "Real World" },
  { to: "/tools", label: "Tools & Tech" },
  { to: "/references", label: "References" },
  { to: "/learning", label: "Learning" },
  { to: "/glossary", label: "Glossary" },
  { to: "/about", label: "About" },
]
